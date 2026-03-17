from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.models.background_job import BackgroundJob, BackgroundJobType
from app.models.update_step import UpdateStep
from app.schemas import job as schema_job
from app.schemas import update as schema_update
from app.services import job_service, update_service

router = APIRouter()


def _update_log_out(row) -> dict:
    return {
        "id": int(row.id),
        "from_version": row.from_version,
        "to_version": row.to_version,
        "status": row.status.value if row.status else None,
        "started_at": row.started_at,
        "finished_at": row.finished_at,
        "started_by": row.started_by,
        "job_id": row.job_id,
        "details_json": row.details_json,
        "error_message": row.error_message,
    }


def _raise_update_error(exc: Exception, status_code: int = 400) -> None:
    raise HTTPException(status_code=status_code, detail=str(exc))


async def _ensure_no_update_in_progress(db: AsyncSession) -> None:
    try:
        await update_service.ensure_no_update_in_progress(db)
    except update_service.UpdateError as exc:
        _raise_update_error(exc, status_code=409)


async def _enqueue_system_update_job(
    db: AsyncSession,
    *,
    current_user,
    params_json: dict,
) -> dict:
    await _ensure_no_update_in_progress(db)
    job = await job_service.enqueue_job(
        db,
        job_type=BackgroundJobType.SYSTEM_UPDATE,
        params_json={**params_json, "started_by": int(current_user.id)},
        created_by=current_user.id,
    )
    await db.commit()
    return {"job_id": job.id, "status": job.status.value}


@router.get("/system/updates/config", response_model=schema_update.UpdateConfigOut)
async def get_system_update_config(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    return await update_service.get_update_config(db)


@router.post("/system/updates/config", response_model=schema_update.UpdateConfigOut)
async def set_system_update_config(
    payload: schema_update.UpdateConfigIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    return await update_service.set_update_config(
        db,
        default_with_backup=payload.default_with_backup,
    )


@router.get("/system/updates/meta", response_model=schema_update.SystemUpdateMetaOut)
async def get_system_update_meta(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    row = await update_service.get_or_create_system_meta(db)
    await db.commit()
    return {
        "backend_version": row.backend_version,
        "frontend_version": row.frontend_version,
        "db_schema_version": row.db_schema_version,
        "last_update_at": row.last_update_at,
        "last_update_by": row.last_update_by,
    }


@router.get("/system/updates/check", response_model=schema_update.SystemUpdateCheckOut)
async def check_system_update(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    try:
        payload = await update_service.check_for_update(db)
        await db.commit()
        return payload
    except update_service.UpdateError as exc:
        _raise_update_error(exc)


@router.get("/system/updates/manifest")
async def get_system_update_manifest_compat(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    # kept for backward compatibility with previous UI
    try:
        return await update_service.load_update_manifest(db)
    except update_service.UpdateError as exc:
        _raise_update_error(exc)


@router.get("/system/updates/logs", response_model=schema_update.UpdatesLogListOut)
async def list_system_update_logs(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    rows = await update_service.list_updates_logs(db, limit=limit)
    return {"items": [_update_log_out(r) for r in rows]}


@router.post("/system/updates/apply", response_model=schema_job.JobCreateOut)
async def apply_system_update(
    payload: schema_update.SystemUpdateApplyIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    return await _enqueue_system_update_job(
        db,
        current_user=current_user,
        params_json={
            "mode": "UPDATE",
            "target_version": payload.target_version,
            "with_backup": bool(payload.with_backup) if payload.with_backup is not None else bool(payload.backup),
        },
    )


@router.post("/system/updates/rollback", response_model=schema_job.JobCreateOut)
async def rollback_system_update(
    payload: schema_update.SystemRollbackIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    return await _enqueue_system_update_job(
        db,
        current_user=current_user,
        params_json={
            "mode": "ROLLBACK",
            "update_log_id": payload.update_log_id,
            "to_version": payload.to_version,
        },
    )


@router.post("/system/updates/{update_log_id}/rollback", response_model=schema_job.JobCreateOut)
async def rollback_system_update_by_log_id(
    update_log_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    return await _enqueue_system_update_job(
        db,
        current_user=current_user,
        params_json={
            "mode": "ROLLBACK",
            "update_log_id": update_log_id,
        },
    )


@router.get("/system/updates/status/{job_id}", response_model=schema_update.SystemUpdateStatusOut)
async def get_system_update_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    job = (await db.execute(select(BackgroundJob).where(BackgroundJob.id == job_id))).scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    update_log = await update_service.get_update_log_by_job_id(db, job_id=job_id)
    steps = []
    if update_log:
        rows = (
            await db.execute(
                select(UpdateStep).where(UpdateStep.update_log_id == update_log.id).order_by(UpdateStep.id.asc())
            )
        ).scalars().all()
        steps = [
            {
                "id": int(row.id),
                "update_log_id": int(row.update_log_id),
                "job_id": row.job_id,
                "step_name": row.step_name,
                "status": row.status.value if row.status else None,
                "output_text": row.output_text,
                "started_at": row.started_at,
                "finished_at": row.finished_at,
            }
            for row in rows
        ]

    result_json = dict(job.result_json or {})
    return {
        "job_id": job.id,
        "job_status": job.status.value if job.status else None,
        "phase": result_json.get("phase"),
        "progress_pct": result_json.get("progress_pct"),
        "message": result_json.get("message"),
        "update_log": _update_log_out(update_log) if update_log else None,
        "steps": steps,
    }
