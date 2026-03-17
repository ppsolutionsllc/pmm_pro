from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.api import deps
from app.config import settings
from app.db.session import get_db
from app.models.request import Request, RequestStatus
from app.models.request_item import RequestItem
from app.models.request_snapshot import RequestSnapshot
from app.models.request_audit import RequestAudit
from app.models.posting_session import PostingOperation, PostingSession
from app.models.background_job import BackgroundJobType
from app.models.stock import FuelType, StockIssue
from app.schemas import request as schema_request
from app.schemas import request_settings as schema_request_settings
from app.crud import department as crud_department
from app.crud import request as crud_request
from app.services import job_service
from app.services import pdf_template_service
from app.services import request_workflow as workflow

router = APIRouter()
logger = logging.getLogger(__name__)
posting_logger = logging.getLogger("app.posting")


def _status_str(v):
    if hasattr(v, "value"):
        return v.value
    return v


def _requested_fuel_summary(req: Request) -> dict[FuelType, dict[str, float]]:
    out: dict[FuelType, dict[str, float]] = defaultdict(lambda: {
        "requested_liters": 0.0,
        "requested_kg": 0.0,
        "issued_liters": 0.0,
        "issued_kg": 0.0,
        "missing_liters": 0.0,
        "missing_kg": 0.0,
    })
    coeff = {
        FuelType.AB: float(req.coeff_snapshot_ab or 0.0),
        FuelType.DP: float(req.coeff_snapshot_dp or 0.0),
    }
    for item in req.items or []:
        v = getattr(item, "vehicle", None)
        if not v:
            continue
        ft: FuelType = v.fuel_type
        liters = float(item.required_liters or 0.0)
        out[ft]["requested_liters"] += liters

    for ft, row in out.items():
        c = coeff[ft] if coeff[ft] > 0 else 0.0
        row["requested_liters"] = round(row["requested_liters"], 6)
        row["requested_kg"] = round(row["requested_liters"] * c, 2) if c else 0.0
    return out


def _fuel_summary_rows(req: Request) -> list[dict]:
    requested = _requested_fuel_summary(req)
    issue = getattr(req, "stock_issue", None)
    if issue:
        for ln in issue.lines or []:
            ft = ln.fuel_type
            row = requested[ft]
            row["requested_liters"] = round(float(ln.requested_liters or row["requested_liters"]), 6)
            row["requested_kg"] = round(float(ln.requested_kg or row["requested_kg"]), 2)
            row["issued_liters"] = round(float(ln.issued_liters or 0.0), 6)
            row["issued_kg"] = round(float(ln.issued_kg or 0.0), 2)
            row["missing_liters"] = round(float(ln.missing_liters or 0.0), 6)
            row["missing_kg"] = round(float(ln.missing_kg or 0.0), 2)

    rows = []
    for ft in sorted(requested.keys(), key=lambda x: 0 if x == FuelType.AB else 1):
        rows.append({"fuel_type": ft.value, **requested[ft]})
    return rows


def _debt_rows(req: Request) -> list[dict]:
    issue = getattr(req, "stock_issue", None)
    if issue:
        out = []
        for ln in issue.lines or []:
            if float(ln.missing_liters or 0.0) <= 0:
                continue
            out.append(
                {
                    "fuel_type": ln.fuel_type.value,
                    "requested_liters": float(ln.requested_liters or 0.0),
                    "requested_kg": float(ln.requested_kg or 0.0),
                    "issued_liters": float(ln.issued_liters or 0.0),
                    "issued_kg": float(ln.issued_kg or 0.0),
                    "missing_liters": float(ln.missing_liters or 0.0),
                    "missing_kg": float(ln.missing_kg or 0.0),
                }
            )
        return out

    out = []
    for d in req.fuel_debts or []:
        if str(getattr(d.status, "value", d.status)) != "OPEN":
            continue
        out.append(
            {
                "fuel_type": d.fuel_type.value,
                "requested_liters": 0.0,
                "requested_kg": 0.0,
                "issued_liters": 0.0,
                "issued_kg": 0.0,
                "missing_liters": float(d.missing_liters or 0.0),
                "missing_kg": float(d.missing_kg or 0.0),
            }
        )
    return out


def _fuel_summary_rows_from_breakdown(breakdown: dict | None) -> list[dict]:
    if not isinstance(breakdown, dict):
        return []
    rows: list[dict] = []
    for key, ft in (("AB", "АБ"), ("DP", "ДП")):
        node = breakdown.get(key) or {}
        requested = node.get("requested") or {}
        posted = node.get("posted") or {}
        debt = node.get("debt") or {}
        rows.append(
            {
                "fuel_type": ft,
                "requested_liters": float(requested.get("liters") or 0.0),
                "requested_kg": float(requested.get("kg") or 0.0),
                "issued_liters": float(posted.get("liters") or 0.0),
                "issued_kg": float(posted.get("kg") or 0.0),
                "missing_liters": float(debt.get("liters") or 0.0),
                "missing_kg": float(debt.get("kg") or 0.0),
            }
        )
    return rows


def _persisted_fuel_summary_rows(issue: StockIssue | None, breakdown_override: dict | None = None) -> list[dict]:
    rows = _fuel_summary_rows_from_breakdown(breakdown_override)
    if rows:
        return rows

    rows = _fuel_summary_rows_from_breakdown(
        issue.breakdown_json if issue and isinstance(issue.breakdown_json, dict) else None
    )
    if rows:
        return rows

    out = []
    if issue:
        for ln in issue.lines or []:
            out.append(
                {
                    "fuel_type": ln.fuel_type.value,
                    "requested_liters": float(ln.requested_liters or 0.0),
                    "requested_kg": float(ln.requested_kg or 0.0),
                    "issued_liters": float(ln.issued_liters or 0.0),
                    "issued_kg": float(ln.issued_kg or 0.0),
                    "missing_liters": float(ln.missing_liters or 0.0),
                    "missing_kg": float(ln.missing_kg or 0.0),
                }
            )
    out.sort(key=lambda r: 0 if r.get("fuel_type") == FuelType.AB.value else 1)
    return out


def _persisted_debt_rows_from_fuel_summary(fuel_summary: list[dict]) -> list[dict]:
    return [row for row in (fuel_summary or []) if float(row.get("missing_liters") or 0.0) > 0]


def _posting_session_out(row: PostingSession) -> dict:
    result_json = row.result_json if getattr(row, "result_json", None) is not None else row.result_ref
    return {
        "id": row.id,
        "request_id": row.request_id,
        "operation": row.operation.value if row.operation else None,
        "idempotency_key": row.idempotency_key,
        "status": row.status.value if row.status else None,
        "started_at": row.started_at,
        "finished_at": row.finished_at,
        "started_by_user_id": row.started_by_user_id,
        "error_code": row.error_code,
        "error_message": row.error_message,
        "result_json": result_json,
        "result_ref": row.result_ref,
        "retry_count": int(row.retry_count or 0),
    }


def _breakdown_payload(fuel_summary: list[dict]) -> dict:
    out = {
        "AB": {
            "requested": {"liters": 0.0, "kg": 0.0},
            "posted": {"liters": 0.0, "kg": 0.0},
            "debt": {"liters": 0.0, "kg": 0.0},
        },
        "DP": {
            "requested": {"liters": 0.0, "kg": 0.0},
            "posted": {"liters": 0.0, "kg": 0.0},
            "debt": {"liters": 0.0, "kg": 0.0},
        },
    }
    for row in fuel_summary or []:
        ft = str(row.get("fuel_type") or "")
        key = "AB" if ft == "АБ" else "DP" if ft == "ДП" else None
        if not key:
            continue
        out[key] = {
            "requested": {
                "liters": float(row.get("requested_liters") or 0.0),
                "kg": float(row.get("requested_kg") or 0.0),
            },
            "posted": {
                "liters": float(row.get("issued_liters") or 0.0),
                "kg": float(row.get("issued_kg") or 0.0),
            },
            "debt": {
                "liters": float(row.get("missing_liters") or 0.0),
                "kg": float(row.get("missing_kg") or 0.0),
            },
        }
    return out


def _breakdown_payload_from_issue(issue: StockIssue | None, fuel_summary: list[dict]) -> dict:
    if issue and issue.breakdown_json and isinstance(issue.breakdown_json, dict):
        lines = issue.breakdown_json.get("lines") or []
        out = {
            "AB": {
                "requested": {"liters": 0.0, "kg": 0.0},
                "posted": {"liters": 0.0, "kg": 0.0},
                "debt": {"liters": 0.0, "kg": 0.0},
            },
            "DP": {
                "requested": {"liters": 0.0, "kg": 0.0},
                "posted": {"liters": 0.0, "kg": 0.0},
                "debt": {"liters": 0.0, "kg": 0.0},
            },
        }
        for row in lines:
            ft = str(row.get("fuel_type") or "")
            key = "AB" if ft == "АБ" else "DP" if ft == "ДП" else None
            if not key:
                continue
            out[key] = {
                "requested": {
                    "liters": float(row.get("requested_liters") or 0.0),
                    "kg": float(row.get("requested_kg") or 0.0),
                },
                "posted": {
                    "liters": float(row.get("issued_liters") or 0.0),
                    "kg": float(row.get("issued_kg") or 0.0),
                },
                "debt": {
                    "liters": float(row.get("missing_liters") or 0.0),
                    "kg": float(row.get("missing_kg") or 0.0),
                },
            }
        return out
    return _breakdown_payload(fuel_summary)


def _confirm_message(state: str, result: str, has_debt: bool, issue_doc_no: str | None) -> str:
    doc_tail = f" Акт № {issue_doc_no}" if issue_doc_no else ""
    if state == "ALREADY_CONFIRMED":
        return f"Заявку вже проведено.{doc_tail}".strip()
    if has_debt or result == "POSTED_WITH_DEBT":
        return f"Отримання підтверджено частково. Створено заборгованість.{doc_tail}".strip()
    return f"Отримання підтверджено. Списання виконано.{doc_tail}".strip()


def _confirm_response_payload(
    fresh: Request,
    result: str,
    posting_session: PostingSession | None,
    issue_doc_no_override: str | None = None,
    breakdown_override: dict | None = None,
    state_override: str | None = None,
) -> dict:
    posting_session_id = posting_session.id if posting_session else None
    issue_doc_no = issue_doc_no_override
    issue = fresh.stock_issue
    if issue_doc_no is None and issue:
        issue_doc_no = issue.issue_doc_no
    state = state_override or ("ALREADY_CONFIRMED" if result == "ALREADY_CONFIRMED" else result)
    breakdown = breakdown_override or _breakdown_payload_from_issue(issue, _fuel_summary_rows(fresh))
    fuel_summary = _persisted_fuel_summary_rows(issue, breakdown_override=breakdown)
    debts = _persisted_debt_rows_from_fuel_summary(fuel_summary)
    has_debt = bool(fresh.has_debt)
    message = _confirm_message(state=state, result=result, has_debt=has_debt, issue_doc_no=issue_doc_no)
    return {
        "id": fresh.id,
        "department_id": fresh.department_id,
        "request_number": fresh.request_number,
        "status": fresh.status.value if fresh.status else None,
        "created_at": fresh.created_at,
        "submitted_at": fresh.submitted_at,
        "approved_at": fresh.approved_at,
        "operator_issued_at": fresh.operator_issued_at,
        "dept_confirmed_at": fresh.dept_confirmed_at,
        "stock_posted_at": fresh.stock_posted_at,
        "route_id": fresh.route_id,
        "route_is_manual": fresh.route_is_manual,
        "route_text": fresh.route_text,
        "distance_km_per_trip": fresh.distance_km_per_trip,
        "justification_text": fresh.justification_text,
        "persons_involved_count": fresh.persons_involved_count,
        "training_days_count": fresh.training_days_count,
        "planned_activity_ids": [a.id for a in (fresh.planned_activities or [])],
        "is_rejected": bool(fresh.is_rejected),
        "rejection_comment": fresh.rejection_comment,
        "rejected_at": fresh.rejected_at,
        "rejected_by": fresh.rejected_by,
        "has_debt": has_debt,
        "coeff_snapshot_ab": fresh.coeff_snapshot_ab,
        "coeff_snapshot_dp": fresh.coeff_snapshot_dp,
        "coeff_snapshot_at": fresh.coeff_snapshot_at,
        "result": result,
        "state": state,
        "already_confirmed": state == "ALREADY_CONFIRMED",
        "posting_session_id": posting_session_id,
        "issue_id": issue.id if issue else None,
        "issue_doc_no": issue_doc_no,
        "fuel_summary": fuel_summary,
        "debts": debts,
        "request": {
            "id": fresh.id,
            "request_number": fresh.request_number,
            "status": fresh.status.value if fresh.status else None,
            "has_debt": has_debt,
        },
        "posting_session": {
            "id": posting_session_id,
            "status": posting_session.status.value if posting_session and posting_session.status else None,
        } if posting_session_id else None,
        "issue": {
            "id": issue.id if issue else None,
            "issue_doc_no": issue_doc_no,
        },
        "breakdown": breakdown,
        "message": message,
    }


@router.post("/requests", response_model=schema_request.RequestOut)
async def create_request(
    data: schema_request.RequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("DEPT_USER")),
):
    if current_user.department_id is None:
        raise HTTPException(status_code=400, detail="User has no department")
    dept = await crud_department.get_department(db, current_user.department_id)
    if not dept or dept.is_deleted or not dept.is_active:
        raise HTTPException(status_code=400, detail="Підрозділ деактивовано або видалено")
    # Drafts are unlimited by business rule.
    return await crud_request.create_request(
        db,
        dept_id=current_user.department_id,
        created_by=current_user.id,
        route_id=None,
        route_is_manual=False,
        route_text=None,
        distance_km_per_trip=None,
        justification_text=None,
        persons_involved_count=int(data.persons_involved_count or 0),
        training_days_count=int(data.training_days_count or 0),
    )


@router.post("/requests/admin", response_model=schema_request.RequestOut)
async def create_request_as_admin(
    data: schema_request.RequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    dept = await crud_department.get_department(db, data.department_id)
    if not dept or dept.is_deleted or not dept.is_active:
        raise HTTPException(status_code=400, detail="Підрозділ деактивовано або видалено")
    return await crud_request.create_request(
        db,
        dept_id=data.department_id,
        created_by=current_user.id,
        route_id=None,
        route_is_manual=False,
        route_text=None,
        distance_km_per_trip=None,
        justification_text=None,
        persons_involved_count=int(data.persons_involved_count or 0),
        training_days_count=int(data.training_days_count or 0),
    )


@router.put("/requests/{req_id}", response_model=schema_request.RequestOut)
async def update_request(
    req_id: int,
    data: schema_request.RequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("DEPT_USER")),
):
    req = await crud_request.get_request(db, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Request belongs to another department")
    if req.status != RequestStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Can only edit drafts")

    from sqlalchemy import update
    await db.execute(
        update(Request).where(Request.id == req_id).values(
            route_id=None,
            route_is_manual=False,
            route_text=None,
            distance_km_per_trip=None,
            justification_text=None,
            persons_involved_count=int(data.persons_involved_count or 0),
            training_days_count=int(data.training_days_count or 0),
        )
    )
    await db.commit()
    return await crud_request.get_request(db, req_id)


@router.delete("/requests/{req_id}")
async def delete_draft_request(
    req_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "DEPT_USER"])),
):
    result = await db.execute(
        select(Request)
        .options(
            selectinload(Request.items),
            selectinload(Request.planned_activities),
            selectinload(Request.stock_issue),
        )
        .where(Request.id == req_id)
    )
    req = result.scalars().first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if current_user.role.value == "DEPT_USER" and req.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Request belongs to another department")
    if req.status != RequestStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Видаляти можна лише чернетки")
    if req.stock_issue is not None:
        raise HTTPException(status_code=409, detail="Чернетку з проведенням видалити неможливо")

    # Clear M2M links explicitly to avoid leftover association rows.
    req.planned_activities = []
    await db.flush()
    await db.delete(req)
    await db.commit()
    return {"ok": True}


@router.post("/requests/{req_id}/planned-activities", response_model=schema_request.RequestOut)
async def set_request_planned_activities(
    req_id: int,
    data: schema_request_settings.SetPlannedActivitiesIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "DEPT_USER"])),
):
    try:
        if current_user.role.value == "DEPT_USER":
            req = await crud_request.get_request(db, req_id)
            if not req:
                raise ValueError("Request not found")
            if req.department_id != current_user.department_id:
                raise ValueError("Request belongs to another department")
            if req.status != RequestStatus.DRAFT:
                raise ValueError("Can only edit drafts")
        return await crud_request.set_planned_activities(db, req_id, data.planned_activity_ids)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/requests/{req_id}/items", response_model=schema_request.RequestItemOut)
async def add_item(
    req_id: int,
    data: schema_request.RequestItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("DEPT_USER")),
):
    try:
        req = await crud_request.get_request(db, req_id)
        if not req:
            raise HTTPException(status_code=404, detail="Request not found")
        if req.department_id != current_user.department_id:
            raise HTTPException(status_code=403, detail="Request belongs to another department")
        if req.status != RequestStatus.DRAFT:
            raise HTTPException(status_code=400, detail="Can only edit drafts")
        return await crud_request.add_item(
            db,
            req_id,
            planned_activity_id=getattr(data, "planned_activity_id", None),
            vehicle_id=data.vehicle_id,
            route_id=data.route_id,
            route_is_manual=bool(data.route_is_manual),
            route_text=data.route_text,
            distance_km_per_trip=data.distance_km_per_trip,
            justification_text=data.justification_text,
            persons_involved_count=data.persons_involved_count,
            training_days_count=data.training_days_count,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/requests/{req_id}/items/{item_id}")
async def delete_item(
    req_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("DEPT_USER")),
):
    req = await crud_request.get_request(db, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Request belongs to another department")
    if req.status != RequestStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Can only edit drafts")

    result = await db.execute(select(RequestItem).where(RequestItem.id == item_id, RequestItem.request_id == req_id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)
    await db.commit()
    return {"ok": True}


@router.get("/requests", response_model=List[schema_request.RequestOut])
async def list_requests(
    status: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "DEPT_USER", "OPERATOR"])),
):
    q = select(Request).options(selectinload(Request.stock_issue))
    if current_user.role.value == "DEPT_USER":
        q = q.where(Request.department_id == current_user.department_id)
    elif current_user.role.value == "OPERATOR":
        # Operator is global and not tied to a department.
        q = q.where(Request.status.in_([RequestStatus.APPROVED, RequestStatus.ISSUED_BY_OPERATOR]))
    if status:
        q = q.where(Request.status == status)
    if department_id:
        q = q.where(Request.department_id == department_id)
    if search:
        q = q.where(Request.request_number.ilike(f"%{search}%"))
    q = q.order_by(Request.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/requests/{req_id}")
async def get_request_detail(
    req_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "DEPT_USER", "OPERATOR"])),
):
    result = await db.execute(
        select(Request)
        .options(
            selectinload(Request.items).selectinload(RequestItem.vehicle),
            selectinload(Request.items).selectinload(RequestItem.planned_activity),
            selectinload(Request.planned_activities),
            selectinload(Request.stock_issue).selectinload(StockIssue.lines),
            selectinload(Request.fuel_debts),
            selectinload(Request.audits),
        )
        .where(Request.id == req_id)
    )
    req = result.scalars().first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if current_user.role.value == "DEPT_USER" and req.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Request belongs to another department")
    if current_user.role.value == "OPERATOR":
        if req.status not in [RequestStatus.APPROVED, RequestStatus.ISSUED_BY_OPERATOR]:
            raise HTTPException(status_code=403, detail="Operation not permitted")

    items = []
    for item in req.items:
        items.append(
            {
                "id": item.id,
                "planned_activity_id": getattr(item, "planned_activity_id", None),
                "planned_activity_name": item.planned_activity.name if getattr(item, "planned_activity", None) else None,
                "vehicle_id": item.vehicle_id,
                "vehicle_name": item.vehicle.brand if item.vehicle else None,
                "vehicle_plate": item.vehicle.identifier if item.vehicle else None,
                "vehicle_fuel_type": item.vehicle.fuel_type.value if item.vehicle else None,
                "route_id": getattr(item, "route_id", None),
                "route_is_manual": bool(getattr(item, "route_is_manual", False)),
                "route_text": getattr(item, "route_text", None),
                "distance_km_per_trip": getattr(item, "distance_km_per_trip", None),
                "justification_text": getattr(item, "justification_text", None),
                "persons_involved_count": getattr(item, "persons_involved_count", None),
                "training_days_count": getattr(item, "training_days_count", None),
                "consumption_l_per_km_snapshot": item.consumption_l_per_km_snapshot,
                "total_km": item.total_km,
                "required_liters": item.required_liters,
                "required_kg": item.required_kg,
            }
        )

    issue = req.stock_issue
    audits = sorted(req.audits or [], key=lambda x: x.created_at or "", reverse=True)
    return {
        "id": req.id,
        "request_number": req.request_number,
        "department_id": req.department_id,
        "status": req.status.value if req.status else None,
        "is_rejected": bool(getattr(req, "is_rejected", False)),
        "rejection_comment": getattr(req, "rejection_comment", None),
        "rejected_at": str(getattr(req, "rejected_at", None)) if getattr(req, "rejected_at", None) else None,
        "rejected_by": getattr(req, "rejected_by", None),
        "has_debt": bool(getattr(req, "has_debt", False)),
        "issue_doc_no": issue.issue_doc_no if issue else None,
        "issue_status": issue.status.value if issue and issue.status else None,
        "route_id": getattr(req, "route_id", None),
        "route_is_manual": bool(getattr(req, "route_is_manual", False)),
        "route_text": req.route_text,
        "distance_km_per_trip": req.distance_km_per_trip,
        "justification_text": req.justification_text,
        "persons_involved_count": getattr(req, "persons_involved_count", 0),
        "training_days_count": getattr(req, "training_days_count", 0),
        "planned_activity_ids": [a.id for a in (req.planned_activities or [])],
        "planned_activities": [{"id": a.id, "name": a.name, "is_active": a.is_active} for a in (req.planned_activities or [])],
        "created_at": str(req.created_at) if req.created_at else None,
        "created_by": req.created_by,
        "submitted_at": str(req.submitted_at) if req.submitted_at else None,
        "submitted_by": req.submitted_by,
        "approved_at": str(req.approved_at) if req.approved_at else None,
        "approved_by": req.approved_by,
        "operator_issued_at": str(req.operator_issued_at) if req.operator_issued_at else None,
        "operator_issued_by": req.operator_issued_by,
        "dept_confirmed_at": str(req.dept_confirmed_at) if req.dept_confirmed_at else None,
        "dept_confirmed_by": req.dept_confirmed_by,
        "stock_posted_at": str(req.stock_posted_at) if req.stock_posted_at else None,
        "stock_posted_by": req.stock_posted_by,
        "coeff_snapshot_ab": req.coeff_snapshot_ab,
        "coeff_snapshot_dp": req.coeff_snapshot_dp,
        "coeff_snapshot_at": str(req.coeff_snapshot_at) if req.coeff_snapshot_at else None,
        "coeff_snapshot_by": req.coeff_snapshot_by,
        "fuel_summary": _fuel_summary_rows(req),
        "debts": _debt_rows(req),
        "audits": [
            {
                "id": a.id,
                "actor_user_id": a.actor_user_id,
                "action": a.action,
                "from_status": a.from_status,
                "to_status": a.to_status,
                "message": a.message,
                "created_at": str(a.created_at) if a.created_at else None,
            }
            for a in audits
        ],
        "items": items,
    }


@router.get("/requests/{req_id}/audit")
async def get_request_audit(
    req_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "DEPT_USER", "OPERATOR"])),
):
    req = await crud_request.get_request(db, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if current_user.role.value == "DEPT_USER" and req.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Request belongs to another department")

    rows = (
        await db.execute(
            select(RequestAudit)
            .where(RequestAudit.request_id == req_id)
            .order_by(RequestAudit.created_at.desc())
        )
    ).scalars().all()
    return [
        {
            "id": r.id,
            "actor_user_id": r.actor_user_id,
            "action": r.action,
            "from_status": r.from_status,
            "to_status": r.to_status,
            "message": r.message,
            "created_at": str(r.created_at) if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/requests/{req_id}/posting-sessions", response_model=list[schema_request.PostingSessionOut])
async def get_request_posting_sessions(
    req_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "DEPT_USER", "OPERATOR"])),
):
    req = await crud_request.get_request(db, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if current_user.role.value == "DEPT_USER" and req.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Request belongs to another department")

    rows = (
        await db.execute(
            select(PostingSession)
            .where(PostingSession.request_id == req_id)
            .order_by(PostingSession.started_at.desc())
        )
    ).scalars().all()
    return [_posting_session_out(r) for r in rows]


@router.get("/requests/{req_id}/snapshots")
async def get_request_snapshots(
    req_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "DEPT_USER", "OPERATOR"])),
):
    req = await crud_request.get_request(db, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if current_user.role.value == "DEPT_USER" and req.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Request belongs to another department")

    rows = (
        await db.execute(
            select(RequestSnapshot)
            .where(RequestSnapshot.request_id == req_id)
            .order_by(RequestSnapshot.created_at.desc())
        )
    ).scalars().all()
    return [
        {
            "id": r.id,
            "stage": r.stage.value if r.stage else None,
            "payload_json": r.payload_json,
            "created_at": str(r.created_at) if r.created_at else None,
            "created_by": r.created_by,
        }
        for r in rows
    ]


@router.get("/posting-sessions/{session_id}", response_model=schema_request.PostingSessionOut)
async def get_posting_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "DEPT_USER", "OPERATOR"])),
):
    row = (await db.execute(select(PostingSession).where(PostingSession.id == session_id))).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Posting session not found")
    if current_user.role.value == "DEPT_USER" and row.request_id:
        req = await crud_request.get_request(db, row.request_id)
        if req and req.department_id != current_user.department_id:
            raise HTTPException(status_code=403, detail="Operation not permitted")
    return _posting_session_out(row)


@router.post("/requests/{req_id}/reject", response_model=schema_request.RequestOut)
async def reject_request(
    req_id: int,
    data: schema_request.RequestRejectIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    try:
        req = await workflow.reject_request_to_draft(
            db,
            request_id=req_id,
            comment=data.comment,
            admin_user_id=current_user.id,
        )
        await db.commit()
        return req
    except workflow.WorkflowConflictError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/requests/{req_id}/submit", response_model=schema_request.RequestOut)
async def submit_request(
    req_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("DEPT_USER")),
):
    req = await crud_request.get_request(db, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Request belongs to another department")
    if req.status != RequestStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Cannot submit")

    try:
        req = await workflow.transition_request_status(
            db,
            request_id=req_id,
            actor_user_id=current_user.id,
            to_status=RequestStatus.SUBMITTED,
            action="SUBMIT",
        )
        await db.commit()
        return req
    except workflow.WorkflowConflictError as exc:
        await db.rollback()
        detail = str(exc) or "Не вдалося подати заявку"
        status_code = 409 if "активна заявка" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="У підрозділу вже є активна заявка")


@router.post("/requests/{req_id}/approve", response_model=schema_request.RequestOut)
async def approve_request(
    req_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    req = await crud_request.get_request(db, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != RequestStatus.SUBMITTED:
        raise HTTPException(status_code=400, detail="Cannot approve")

    try:
        req = await workflow.transition_request_status(
            db,
            request_id=req_id,
            actor_user_id=current_user.id,
            to_status=RequestStatus.APPROVED,
            action="APPROVE",
        )
        await db.commit()
        return req
    except (workflow.WorkflowConflictError, IntegrityError):
        await db.rollback()
        raise HTTPException(status_code=409, detail="У підрозділу вже є активна заявка")


@router.post("/requests/{req_id}/issue", response_model=schema_request.RequestOut)
async def issue_request(
    req_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("OPERATOR")),
):
    req = await crud_request.get_request(db, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != RequestStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Cannot issue")

    try:
        req = await workflow.transition_request_status(
            db,
            request_id=req_id,
            actor_user_id=current_user.id,
            to_status=RequestStatus.ISSUED_BY_OPERATOR,
            action="ISSUE",
        )
        await db.commit()
        return req
    except (workflow.WorkflowConflictError, IntegrityError):
        await db.rollback()
        raise HTTPException(status_code=409, detail="У підрозділу вже є активна заявка")


@router.post("/requests/{req_id}/confirm", response_model=schema_request.RequestConfirmOut)
async def confirm_request(
    req_id: int,
    data: schema_request.RequestConfirmIn | None = None,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("DEPT_USER")),
):
    actor_user_id = int(current_user.id)
    req = await crud_request.get_request(db, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Request belongs to another department")

    body_key = data.idempotency_key if data else None
    idem_key = workflow.normalize_idempotency_key(idempotency_key or body_key)
    if not idem_key:
        idem_key = f"CONFIRM:{req_id}:{actor_user_id}"
    posting_session: PostingSession | None = None

    try:
        posting_session, session_state = await workflow.start_posting_session(
            db,
            request_id=req_id,
            operation=PostingOperation.CONFIRM,
            idempotency_key=idem_key,
            started_by_user_id=actor_user_id,
        )
        if session_state == "IN_PROGRESS":
            raise HTTPException(status_code=409, detail="Проведення виконується. Спробуйте ще раз через кілька секунд.")

        if session_state == "SUCCESS":
            existing_result_payload = posting_session.result_json or posting_session.result_ref or {}
            existing_result = (existing_result_payload.get("result")) or "POSTED"
            existing_issue_doc_no = existing_result_payload.get("issue_doc_no")
            fresh = (
                await db.execute(
                    select(Request)
                    .options(
                        selectinload(Request.items).selectinload(RequestItem.vehicle),
                        selectinload(Request.stock_issue).selectinload(StockIssue.lines),
                        selectinload(Request.fuel_debts),
                        selectinload(Request.planned_activities),
                    )
                    .where(Request.id == req_id)
                )
            ).scalars().first()
            return _confirm_response_payload(
                fresh,
                existing_result,
                posting_session,
                existing_issue_doc_no,
                breakdown_override=existing_result_payload.get("breakdown"),
                state_override="ALREADY_CONFIRMED",
            )

        result = await workflow.confirm_request_posting(
            db,
            request_id=req_id,
            actor_user_id=actor_user_id,
            force_admin_month_end=False,
            audit_action="CONFIRM",
        )
        await workflow.mark_posting_session_success(
            db,
            posting_session=posting_session,
            result_ref=workflow.confirm_result_ref(result),
        )
        await db.commit()

        fresh = (
            await db.execute(
                select(Request)
                .options(
                    selectinload(Request.items).selectinload(RequestItem.vehicle),
                    selectinload(Request.stock_issue).selectinload(StockIssue.lines),
                    selectinload(Request.fuel_debts),
                    selectinload(Request.planned_activities),
                )
                .where(Request.id == req_id)
            )
        ).scalars().first()
        return _confirm_response_payload(
            fresh,
            result.result,
            posting_session,
            result.issue.issue_doc_no if result.issue else None,
            breakdown_override=(posting_session.result_json or posting_session.result_ref or {}).get("breakdown"),
            state_override="ALREADY_CONFIRMED" if result.result == "ALREADY_CONFIRMED" else None,
        )
    except workflow.MonthEndConfirmRequiredError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    except workflow.WorkflowConflictError as e:
        await db.rollback()
        try:
            session_for_fail, state = await workflow.start_posting_session(
                db,
                request_id=req_id,
                operation=PostingOperation.CONFIRM,
                idempotency_key=idem_key,
                started_by_user_id=actor_user_id,
            )
            if state != "SUCCESS":
                await workflow.mark_posting_session_failed(
                    db,
                    posting_session=session_for_fail,
                    error_code="CONFIRM_FAILED",
                    error_message=str(e),
                )
                await workflow.create_admin_alert(
                    db,
                    alert_type="REQUEST_CONFIRM_FAILED",
                    severity="HIGH",
                    message=f"Request {req_id} confirm failed: {e}",
                    request_id=req_id,
                    posting_session_id=session_for_fail.id,
                )
                await db.commit()
        except Exception:
            await db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as exc:
        logger.exception("Failed to post request %s into stock ledger", req_id)
        posting_logger.exception("REQUEST_CONFIRM_EXCEPTION request_id=%s error=%s", req_id, exc)
        await db.rollback()
        alert_id = None
        session_id = None
        try:
            session_for_fail, state = await workflow.start_posting_session(
                db,
                request_id=req_id,
                operation=PostingOperation.CONFIRM,
                idempotency_key=idem_key,
                started_by_user_id=actor_user_id,
            )
            session_id = session_for_fail.id
            if state != "SUCCESS":
                await workflow.mark_posting_session_failed(
                    db,
                    posting_session=session_for_fail,
                    error_code="CONFIRM_EXCEPTION",
                    error_message=str(exc),
                )
            alert = await workflow.create_admin_alert(
                db,
                alert_type="REQUEST_CONFIRM_FAILED",
                severity="HIGH",
                message=f"Request {req_id} confirm failed: {exc}",
                request_id=req_id,
                posting_session_id=session_for_fail.id,
            )
            await db.commit()
            alert_id = alert.id
        except Exception:
            logger.exception("Failed to create admin alert for request %s", req_id)
        detail = "Failed to post stock issue"
        if alert_id:
            detail += f". Admin alert created: #{alert_id}"
        if session_id:
            detail += f". Posting session: {session_id}"
        raise HTTPException(status_code=500, detail=detail) from exc


@router.post("/requests/admin/month-end-confirm")
async def month_end_confirm_requests(
    data: schema_request.AdminMonthEndConfirmIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    actor_user_id = int(current_user.id)
    req_ids = [int(x) for x in (data.request_ids or []) if x is not None]
    if data.async_mode:
        job = await job_service.enqueue_job(
            db,
            job_type=BackgroundJobType.MONTH_END_BATCH,
            params_json={
                "request_ids": req_ids or None,
                "actor_user_id": actor_user_id,
            },
            created_by=actor_user_id,
        )
        await db.commit()
        job_service.schedule_background_job(job.id)
        return {"job_id": job.id, "status": job.status.value}

    rows = await workflow.month_end_pending_request_ids(db, request_ids=req_ids or None)
    processed = []
    failed = []
    base_key = workflow.normalize_idempotency_key(data.idempotency_key) or f"month-end:{datetime.utcnow().isoformat()}"

    for rid in rows:
        idem_key = f"{base_key}:request:{rid}"
        try:
            posting_session, state = await workflow.start_posting_session(
                db,
                request_id=int(rid),
                operation=PostingOperation.MONTH_END_CONFIRM,
                idempotency_key=idem_key,
                started_by_user_id=actor_user_id,
            )
            if state == "SUCCESS":
                existing = posting_session.result_json or posting_session.result_ref or {}
                processed.append(
                    {
                        "request_id": int(rid),
                        "result": existing.get("result", "ALREADY_CONFIRMED"),
                        "issue_doc_no": existing.get("issue_doc_no"),
                        "already_done": True,
                        "posting_session_id": posting_session.id,
                    }
                )
                continue
            if state == "IN_PROGRESS":
                failed.append({"request_id": int(rid), "error": "Already in progress", "posting_session_id": posting_session.id})
                continue

            result = await workflow.confirm_request_posting(
                db,
                request_id=int(rid),
                actor_user_id=actor_user_id,
                force_admin_month_end=True,
                audit_action="MONTH_END_CONFIRM",
            )
            await workflow.mark_posting_session_success(
                db,
                posting_session=posting_session,
                result_ref=workflow.confirm_result_ref(result),
            )
            await db.commit()
            processed.append(
                {
                    "request_id": int(rid),
                    "result": result.result,
                    "issue_doc_no": result.issue.issue_doc_no if result.issue else None,
                    "posting_session_id": posting_session.id,
                }
            )
        except Exception as exc:
            await db.rollback()
            posting_logger.exception("MONTH_END_CONFIRM_FAILED request_id=%s error=%s", rid, exc)
            alert_id = None
            session_id = None
            try:
                posting_session, state = await workflow.start_posting_session(
                    db,
                    request_id=int(rid),
                    operation=PostingOperation.MONTH_END_CONFIRM,
                    idempotency_key=idem_key,
                    started_by_user_id=actor_user_id,
                )
                session_id = posting_session.id
                if state != "SUCCESS":
                    await workflow.mark_posting_session_failed(
                        db,
                        posting_session=posting_session,
                        error_code="MONTH_END_CONFIRM_FAILED",
                        error_message=str(exc),
                    )
                alert = await workflow.create_admin_alert(
                    db,
                    alert_type="MONTH_END_CONFIRM_FAILED",
                    severity="HIGH",
                    message=f"Month-end confirm failed for request {rid}: {exc}",
                    request_id=int(rid),
                    posting_session_id=posting_session.id,
                )
                await db.commit()
                alert_id = alert.id
            except Exception:
                await db.rollback()
                logger.exception("Failed to create admin alert for month-end request %s", rid)
                posting_logger.exception("MONTH_END_CONFIRM_ALERT_CREATE_FAILED request_id=%s", rid)
            failed.append({"request_id": int(rid), "error": str(exc), "alert_id": alert_id, "posting_session_id": session_id})

    return {"processed": processed, "failed": failed}


@router.post("/requests/{req_id}/reverse")
async def reverse_request(
    req_id: int,
    data: schema_request.RequestReverseIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    actor_user_id = int(current_user.id)
    idem_key = workflow.normalize_idempotency_key(data.idempotency_key)
    try:
        posting_session, state = await workflow.start_posting_session(
            db,
            request_id=req_id,
            operation=PostingOperation.ADJUSTMENT,
            idempotency_key=idem_key,
            started_by_user_id=actor_user_id,
        )
        if state == "IN_PROGRESS":
            raise HTTPException(status_code=409, detail="Adjustment is already in progress for this Idempotency-Key")
        if state == "SUCCESS":
            existing = posting_session.result_json or posting_session.result_ref or {}
            return {
                "ok": True,
                "already_done": True,
                "posting_session_id": posting_session.id,
                **existing,
            }

        adj = await workflow.reverse_posted_request(
            db,
            request_id=req_id,
            reason=data.reason,
            actor_user_id=actor_user_id,
        )
        await workflow.mark_posting_session_success(
            db,
            posting_session=posting_session,
            result_ref={
                "adjustment_doc_no": adj.adjustment_doc_no,
                "adjustment_id": adj.id,
            },
        )
        await db.commit()
        return {
            "ok": True,
            "adjustment_doc_no": adj.adjustment_doc_no,
            "adjustment_id": adj.id,
            "posting_session_id": posting_session.id,
        }
    except workflow.WorkflowConflictError as e:
        await db.rollback()
        try:
            posting_session, state = await workflow.start_posting_session(
                db,
                request_id=req_id,
                operation=PostingOperation.ADJUSTMENT,
                idempotency_key=idem_key,
                started_by_user_id=actor_user_id,
            )
            if state != "SUCCESS":
                await workflow.mark_posting_session_failed(
                    db,
                    posting_session=posting_session,
                    error_code="ADJUSTMENT_FAILED",
                    error_message=str(e),
                )
                await workflow.create_admin_alert(
                    db,
                    alert_type="ADJUSTMENT_FAILED",
                    severity="HIGH",
                    message=f"Adjustment failed for request {req_id}: {e}",
                    request_id=req_id,
                    posting_session_id=posting_session.id,
                )
                await db.commit()
        except Exception:
            await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/requests/{req_id}/print")
async def print_request(
    req_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "DEPT_USER", "OPERATOR"])),
):
    req_row = (await db.execute(select(Request).where(Request.id == req_id))).scalars().first()
    if not req_row:
        raise HTTPException(status_code=404, detail="Request not found")
    if current_user.role.value == "DEPT_USER" and req_row.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Request belongs to another department")

    result = await pdf_template_service.generate_request_pdf_artifact(
        db,
        request_id=req_id,
        actor_user_id=current_user.id,
        template_id=None,
        force_regenerate=False,
        base_url=settings.frontend_base_url,
    )
    await db.commit()
    artifact = result["artifact"]
    pdf_path = Path(artifact.file_path)
    if not pdf_path.exists():
        raise HTTPException(status_code=500, detail="Artifact file was not generated")
    pdf_bytes = pdf_path.read_bytes()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=request_{req_row.request_number}.pdf"},
    )
