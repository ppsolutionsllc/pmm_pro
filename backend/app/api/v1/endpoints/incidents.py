from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.time import utcnow
from app.db.session import get_db
from app.models.admin_incident import AdminIncident, IncidentStatus, IncidentType
from app.models.background_job import BackgroundJob, BackgroundJobType
from app.models.department import Department
from app.models.posting_session import PostingOperation, PostingSession
from app.models.request import Request
from app.schemas import incident as schema_incident
from app.services import incident_service, job_service
from app.services import request_workflow as workflow

router = APIRouter()


def _incident_out(row: AdminIncident) -> dict[str, Any]:
    return {
        "id": row.id,
        "type": row.type.value if row.type else None,
        "severity": row.severity.value if row.severity else None,
        "status": row.status.value if row.status else None,
        "message": row.message,
        "request_id": row.request_id,
        "posting_session_id": row.posting_session_id,
        "job_id": row.job_id,
        "created_at": row.created_at,
        "created_by": row.created_by,
        "resolved_at": row.resolved_at,
        "resolved_by": row.resolved_by,
    }


def _parse_dt(value: str | None, field_name: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}, use ISO datetime")


@router.get("/admin/incidents", response_model=schema_incident.IncidentListOut)
async def list_admin_incidents(
    status: str | None = Query(None),
    severity: str | None = Query(None),
    type: str | None = Query(None),
    q: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    dt_from = _parse_dt(date_from, "date_from")
    dt_to = _parse_dt(date_to, "date_to")

    base = select(AdminIncident)
    if status:
        base = base.where(AdminIncident.status == status)
    if severity:
        base = base.where(AdminIncident.severity == severity)
    if type:
        base = base.where(AdminIncident.type == type)
    if q:
        base = base.where(AdminIncident.message.ilike(f"%{q.strip()}%"))
    if dt_from:
        base = base.where(AdminIncident.created_at >= dt_from)
    if dt_to:
        base = base.where(AdminIncident.created_at <= dt_to)

    total = (
        await db.execute(
            select(func.count()).select_from(base.order_by(None).subquery())
        )
    ).scalar_one()

    rows = (
        await db.execute(
            base.order_by(AdminIncident.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    unresolved_count = (
        await db.execute(
            select(func.count())
            .select_from(AdminIncident)
            .where(AdminIncident.status != IncidentStatus.RESOLVED)
        )
    ).scalar_one()

    return {
        "items": [_incident_out(r) for r in rows],
        "page": page,
        "page_size": page_size,
        "total": int(total or 0),
        "unresolved_count": int(unresolved_count or 0),
    }


@router.get("/admin/incidents/unresolved_count")
async def get_unresolved_incidents_count(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    unresolved_count = (
        await db.execute(
            select(func.count())
            .select_from(AdminIncident)
            .where(AdminIncident.status != IncidentStatus.RESOLVED)
        )
    ).scalar_one()
    return {"unresolved_count": int(unresolved_count or 0)}


@router.get("/admin/incidents/{incident_id}", response_model=schema_incident.IncidentDetailOut)
async def get_admin_incident_detail(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    row = (await db.execute(select(AdminIncident).where(AdminIncident.id == incident_id))).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Incident not found")

    request_summary = None
    if row.request_id:
        req = (
            await db.execute(
                select(Request, Department.name)
                .join(Department, Department.id == Request.department_id, isouter=True)
                .where(Request.id == row.request_id)
            )
        ).first()
        if req:
            req_row, dept_name = req
            request_summary = {
                "id": req_row.id,
                "request_number": req_row.request_number,
                "status": req_row.status.value if req_row.status else None,
                "department_id": req_row.department_id,
                "department_name": dept_name,
            }

    posting_session_summary = None
    if row.posting_session_id:
        ps = (
            await db.execute(
                select(PostingSession).where(PostingSession.id == row.posting_session_id)
            )
        ).scalars().first()
        if ps:
            posting_session_summary = {
                "id": ps.id,
                "operation": ps.operation.value if ps.operation else None,
                "status": ps.status.value if ps.status else None,
                "started_at": ps.started_at,
                "finished_at": ps.finished_at,
                "error_code": ps.error_code,
                "error_message": ps.error_message,
            }

    job_summary = None
    if row.job_id:
        job = (
            await db.execute(
                select(BackgroundJob).where(BackgroundJob.id == row.job_id)
            )
        ).scalars().first()
        if job:
            job_summary = {
                "id": job.id,
                "type": job.type.value if job.type else None,
                "status": job.status.value if job.status else None,
                "created_at": job.created_at,
                "started_at": job.started_at,
                "finished_at": job.finished_at,
                "error_message": job.error_message,
            }

    return {
        **_incident_out(row),
        "details_json": row.details_json,
        "resolution_comment": row.resolution_comment,
        "request_summary": request_summary,
        "posting_session_summary": posting_session_summary,
        "job_summary": job_summary,
    }


@router.patch("/admin/incidents/{incident_id}", response_model=schema_incident.IncidentDetailOut)
async def patch_admin_incident(
    incident_id: str,
    payload: schema_incident.IncidentPatchIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    row = (
        await db.execute(
            select(AdminIncident).where(AdminIncident.id == incident_id).with_for_update()
        )
    ).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Incident not found")

    if payload.message is not None:
        row.message = payload.message[:512]

    if payload.status is not None:
        try:
            next_status = IncidentStatus(payload.status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")

        if next_status == IncidentStatus.RESOLVED and not (payload.resolution_comment or "").strip():
            raise HTTPException(status_code=400, detail="resolution_comment is required for RESOLVED")

        row.status = next_status
        if next_status == IncidentStatus.RESOLVED:
            row.resolved_at = utcnow()
            row.resolved_by = int(current_user.id)
            row.resolution_comment = (payload.resolution_comment or "").strip()
        else:
            row.resolved_at = None
            row.resolved_by = None
            if payload.resolution_comment is not None:
                row.resolution_comment = payload.resolution_comment.strip() or None
    elif payload.resolution_comment is not None:
        row.resolution_comment = payload.resolution_comment.strip() or None

    await db.commit()
    await db.refresh(row)
    return {
        **_incident_out(row),
        "details_json": row.details_json,
        "resolution_comment": row.resolution_comment,
        "request_summary": None,
        "posting_session_summary": None,
        "job_summary": None,
    }


def _retry_allowed(incident_type: IncidentType) -> bool:
    return incident_type in {
        IncidentType.POSTING_FAILED,
        IncidentType.EXPORT_FAILED,
        IncidentType.RECONCILE_FAILED,
    }


@router.post("/admin/incidents/{incident_id}/retry", response_model=schema_incident.IncidentRetryOut)
async def retry_admin_incident(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    row = (
        await db.execute(
            select(AdminIncident).where(AdminIncident.id == incident_id).with_for_update()
        )
    ).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Incident not found")
    if not _retry_allowed(row.type):
        raise HTTPException(status_code=400, detail="Retry not available for this incident type")

    actor_user_id = int(current_user.id)
    retry_at = utcnow().isoformat()

    if row.type == IncidentType.POSTING_FAILED:
        if not row.request_id:
            raise HTTPException(status_code=400, detail="Incident has no request_id for retry")

        retry_operation = PostingOperation.CONFIRM
        if row.posting_session_id:
            prior = (
                await db.execute(select(PostingSession).where(PostingSession.id == row.posting_session_id))
            ).scalars().first()
            if prior and prior.operation:
                retry_operation = prior.operation
        if retry_operation not in {PostingOperation.CONFIRM, PostingOperation.MONTH_END_CONFIRM}:
            retry_operation = PostingOperation.CONFIRM

        posting_session, state = await workflow.start_posting_session(
            db,
            request_id=row.request_id,
            operation=retry_operation,
            idempotency_key=f"incident-retry:{row.id}:{retry_at}",
            started_by_user_id=actor_user_id,
        )
        if state == "IN_PROGRESS":
            raise HTTPException(status_code=409, detail="Retry posting is already in progress")
        if state == "PROCEED":
            try:
                result = await workflow.confirm_request_posting(
                    db,
                    request_id=row.request_id,
                    actor_user_id=actor_user_id,
                    force_admin_month_end=True,
                    audit_action="MONTH_END_CONFIRM" if retry_operation == PostingOperation.MONTH_END_CONFIRM else "CONFIRM",
                )
                await workflow.mark_posting_session_success(
                    db,
                    posting_session=posting_session,
                    result_ref=workflow.confirm_result_ref(result),
                )
            except Exception as exc:
                await workflow.mark_posting_session_failed(
                    db,
                    posting_session=posting_session,
                    error_code="INCIDENT_RETRY_FAILED",
                    error_message=str(exc),
                )
                await db.commit()
                raise HTTPException(status_code=400, detail=str(exc))

        details = dict(row.details_json or {})
        details["last_retry"] = {
            "at": retry_at,
            "by": actor_user_id,
            "session_id": posting_session.id,
        }
        row.details_json = details
        row.status = IncidentStatus.IN_PROGRESS
        row.resolved_at = None
        row.resolved_by = None
        row.resolution_comment = None
        await db.commit()
        return {
            "ok": True,
            "incident_id": row.id,
            "status": row.status.value,
            "session_id": posting_session.id,
            "job_id": None,
        }

    source_job_id = row.job_id
    if not source_job_id:
        raise HTTPException(status_code=400, detail="Incident has no job reference for retry")

    source_job = (
        await db.execute(select(BackgroundJob).where(BackgroundJob.id == source_job_id))
    ).scalars().first()
    if not source_job:
        raise HTTPException(status_code=404, detail="Source job not found")

    if row.type == IncidentType.RECONCILE_FAILED and source_job.type != BackgroundJobType.RECONCILE:
        raise HTTPException(status_code=400, detail="Retry mismatch: expected reconcile job")
    if row.type == IncidentType.EXPORT_FAILED and source_job.type not in {
        BackgroundJobType.REQUESTS_EXPORT,
        BackgroundJobType.DEBTS_EXPORT,
        BackgroundJobType.VEHICLE_REPORT_EXPORT,
        BackgroundJobType.PDF_EXPORT,
        BackgroundJobType.XLSX_EXPORT,
    }:
        raise HTTPException(status_code=400, detail="Retry mismatch: expected export job")

    job = await job_service.enqueue_job(
        db,
        job_type=source_job.type,
        params_json=dict(source_job.params_json or {}),
        created_by=actor_user_id,
    )
    details = dict(row.details_json or {})
    details["last_retry"] = {
        "at": retry_at,
        "by": actor_user_id,
        "source_job_id": source_job.id,
        "job_id": job.id,
    }
    row.details_json = details
    row.job_id = job.id
    row.status = IncidentStatus.IN_PROGRESS
    row.resolved_at = None
    row.resolved_by = None
    row.resolution_comment = None
    await db.commit()
    job_service.schedule_background_job(job.id)

    return {
        "ok": True,
        "incident_id": row.id,
        "status": row.status.value,
        "session_id": None,
        "job_id": job.id,
    }
