from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.time import utcnow
from app.crud import app_settings as crud_app_settings
from app.crud import department_print_signature as crud_dept_signature
from app.crud import settings as crud_settings
from app.services import incident_service
from app.models.admin_alert import AdminAlert
from app.models.posting_session import PostingOperation, PostingSession, PostingSessionStatus
from app.models.request import Request, RequestStatus
from app.models.request_audit import RequestAudit
from app.models.request_item import RequestItem
from app.models.request_snapshot import RequestSnapshot, RequestSnapshotStage
from app.models.issue_doc_sequence import IssueDocSequence
from app.models.pdf_template import PdfTemplate, PdfTemplateScope, PdfTemplateVersion, PdfTemplateVersionStatus
from app.models.stock import (
    DebtStatus,
    FuelDebt,
    FuelType,
    RefType,
    StockAdjustment,
    StockAdjustmentLine,
    StockBalance,
    StockIssue,
    StockIssueLine,
    StockIssueStatus,
    StockLedger,
)
from app.models.stock_reservation import ReservationStatus, StockReservation


ACTIVE_REQUEST_STATUSES = {
    RequestStatus.SUBMITTED,
    RequestStatus.APPROVED,
    RequestStatus.ISSUED_BY_OPERATOR,
}


class WorkflowConflictError(ValueError):
    pass


class MonthEndConfirmRequiredError(WorkflowConflictError):
    pass


@dataclass
class ConfirmResult:
    result: str
    request: Request
    issue: StockIssue | None


def _status_value(status: RequestStatus | str | None) -> str | None:
    if status is None:
        return None
    if isinstance(status, RequestStatus):
        return status.value
    return str(status)


def _fuel_order(ft: FuelType) -> int:
    return 0 if ft == FuelType.AB else 1


async def _next_issue_sequence(db: AsyncSession, scope_key: str) -> int:
    row = (
        await db.execute(
            select(IssueDocSequence)
            .where(IssueDocSequence.scope_key == scope_key)
            .with_for_update()
        )
    ).scalars().first()
    if row is not None:
        seq = int(row.next_value or 1)
        row.next_value = seq + 1
        row.updated_at = utcnow()
        await db.flush()
        return seq

    # Race-safe create: if another transaction inserts the same scope row first,
    # retry by locking the existing row.
    for _ in range(3):
        try:
            async with db.begin_nested():
                db.add(IssueDocSequence(scope_key=scope_key, next_value=2))
                await db.flush()
            return 1
        except IntegrityError:
            row = (
                await db.execute(
                    select(IssueDocSequence)
                    .where(IssueDocSequence.scope_key == scope_key)
                    .with_for_update()
                )
            ).scalars().first()
            if row is not None:
                seq = int(row.next_value or 1)
                row.next_value = seq + 1
                row.updated_at = utcnow()
                await db.flush()
                return seq
    raise WorkflowConflictError("Failed to allocate issue document sequence")


async def _issue_doc_no(db: AsyncSession, now: datetime) -> str:
    scope = now.strftime("%Y%m")
    seq = await _next_issue_sequence(db, scope)
    return f"PMM-{scope}-{seq:06d}"


def _adjustment_doc_no(now: datetime) -> str:
    return f"ADJ-{now.strftime('%Y%m')}-{now.strftime('%d%H%M%S%f')}"


def _is_confirm_expired(req: Request, now: datetime) -> bool:
    marker = req.operator_issued_at or req.approved_at or req.submitted_at
    if marker is None:
        return False
    return (marker.year, marker.month) != (now.year, now.month)


def normalize_idempotency_key(value: str | None) -> str | None:
    if not value:
        return None
    out = str(value).strip()
    if not out:
        return None
    return out[:128]


async def append_request_audit(
    db: AsyncSession,
    *,
    request_id: int,
    actor_user_id: int | None,
    action: str,
    from_status: RequestStatus | str | None = None,
    to_status: RequestStatus | str | None = None,
    message: str | None = None,
) -> RequestAudit:
    row = RequestAudit(
        request_id=request_id,
        actor_user_id=actor_user_id,
        action=action,
        from_status=_status_value(from_status),
        to_status=_status_value(to_status),
        message=message,
    )
    db.add(row)
    await db.flush()
    return row


async def create_admin_alert(
    db: AsyncSession,
    *,
    alert_type: str,
    message: str,
    request_id: int | None = None,
    severity: str = "ERROR",
    posting_session_id: str | None = None,
) -> AdminAlert:
    alert = AdminAlert(
        type=alert_type,
        severity=severity,
        message=message,
        request_id=request_id,
        posting_session_id=posting_session_id,
    )
    db.add(alert)
    await db.flush()
    return alert


async def ensure_single_active_request(
    db: AsyncSession,
    *,
    department_id: int,
    exclude_request_id: int | None = None,
) -> None:
    q = (
        select(Request)
        .where(
            Request.department_id == department_id,
            Request.status.in_(list(ACTIVE_REQUEST_STATUSES)),
        )
        .with_for_update()
    )
    if exclude_request_id is not None:
        q = q.where(Request.id != exclude_request_id)
    existing = (await db.execute(q.limit(1))).scalars().first()
    if existing is not None:
        raise WorkflowConflictError(
            "У підрозділу вже є активна заявка у статусі SUBMITTED/APPROVED/ISSUED."
        )


async def ensure_request_coeff_snapshot(
    db: AsyncSession,
    *,
    req: Request,
    actor_user_id: int | None,
) -> dict[FuelType, float]:
    if req.coeff_snapshot_ab and req.coeff_snapshot_dp:
        return {FuelType.AB: float(req.coeff_snapshot_ab), FuelType.DP: float(req.coeff_snapshot_dp)}
    dens = await crud_settings.get_settings(db)
    if not dens:
        raise WorkflowConflictError("Density settings not configured")
    now = utcnow()
    req.coeff_snapshot_ab = float(dens.density_factor_ab)
    req.coeff_snapshot_dp = float(dens.density_factor_dp)
    req.coeff_snapshot_at = now
    req.coeff_snapshot_by = actor_user_id
    await db.flush()
    return {FuelType.AB: req.coeff_snapshot_ab, FuelType.DP: req.coeff_snapshot_dp}


async def _lock_request_with_items(db: AsyncSession, request_id: int) -> Request | None:
    return (
        await db.execute(
            select(Request)
            .options(
                selectinload(Request.items).selectinload(RequestItem.vehicle),
                selectinload(Request.stock_issue).selectinload(StockIssue.lines),
            )
            .where(Request.id == request_id)
            .with_for_update()
        )
    ).scalars().first()


async def _load_request_for_snapshot(db: AsyncSession, request_id: int) -> Request | None:
    return (
        await db.execute(
            select(Request)
            .options(
                selectinload(Request.items).selectinload(RequestItem.vehicle),
                selectinload(Request.items).selectinload(RequestItem.planned_activity),
                selectinload(Request.stock_issue).selectinload(StockIssue.lines),
            )
            .where(Request.id == request_id)
        )
    ).scalars().first()


async def _lock_existing_issue(db: AsyncSession, request_id: int) -> StockIssue | None:
    return (
        await db.execute(
            select(StockIssue)
            .options(selectinload(StockIssue.lines))
            .where(StockIssue.request_id == request_id)
            .with_for_update()
        )
    ).scalars().first()


async def _lock_balance(db: AsyncSession, fuel_type: FuelType) -> StockBalance:
    bal = (
        await db.execute(
            select(StockBalance).where(StockBalance.fuel_type == fuel_type).with_for_update()
        )
    ).scalars().first()
    if bal is None:
        bal = StockBalance(fuel_type=fuel_type, balance_liters=0.0, balance_kg=0.0)
        db.add(bal)
        await db.flush()
    return bal


def _aggregate_requested_by_fuel(req: Request, coeff: dict[FuelType, float]) -> dict[FuelType, dict[str, float]]:
    out: dict[FuelType, dict[str, float]] = {}
    for item in req.items or []:
        vehicle = getattr(item, "vehicle", None)
        if vehicle is None:
            continue
        fuel_type: FuelType = vehicle.fuel_type
        liters = float(item.required_liters or 0.0)
        if liters <= 0:
            continue
        if fuel_type not in out:
            out[fuel_type] = {
                "requested_liters": 0.0,
                "requested_kg": 0.0,
                "issued_liters": 0.0,
                "issued_kg": 0.0,
                "missing_liters": 0.0,
                "missing_kg": 0.0,
            }
        out[fuel_type]["requested_liters"] += liters

    for ft, agg in out.items():
        c = float(coeff[ft])
        agg["requested_liters"] = round(agg["requested_liters"], 6)
        agg["requested_kg"] = round(agg["requested_liters"] * c, 2)
    return out


async def create_request_snapshot(
    db: AsyncSession,
    *,
    request_id: int,
    stage: RequestSnapshotStage,
    actor_user_id: int | None,
) -> RequestSnapshot:
    req = await _load_request_for_snapshot(db, request_id)
    if not req:
        raise WorkflowConflictError("Request not found")

    fuel_breakdown = {
        FuelType.AB: {"requested_liters": 0.0, "requested_kg": 0.0},
        FuelType.DP: {"requested_liters": 0.0, "requested_kg": 0.0},
    }
    items_payload: list[dict[str, Any]] = []
    vehicles_payload: dict[int, dict[str, Any]] = {}

    for item in req.items or []:
        vehicle = getattr(item, "vehicle", None)
        fuel_type = getattr(vehicle, "fuel_type", None)
        liters = float(item.required_liters or 0.0)
        kg = float(item.required_kg or 0.0)
        if fuel_type in fuel_breakdown:
            fuel_breakdown[fuel_type]["requested_liters"] += liters
            fuel_breakdown[fuel_type]["requested_kg"] += kg

        item_payload = {
            "item_id": item.id,
            "planned_activity": getattr(getattr(item, "planned_activity", None), "name", None),
            "vehicle_id": item.vehicle_id,
            "vehicle_identifier": getattr(vehicle, "identifier", None),
            "vehicle_brand": getattr(vehicle, "brand", None),
            "fuel_type": fuel_type.value if fuel_type else None,
            "route_id": item.route_id,
            "route_is_manual": bool(item.route_is_manual),
            "route_text": item.route_text,
            "distance_km_per_trip": item.distance_km_per_trip,
            "total_km": item.total_km,
            "norm_l_per_km": item.consumption_l_per_km_snapshot,
            "required_liters": liters,
            "required_kg": kg,
            "justification": item.justification_text,
        }
        items_payload.append(item_payload)

        if vehicle and vehicle.id not in vehicles_payload:
            vehicles_payload[vehicle.id] = {
                "vehicle_id": vehicle.id,
                "brand": vehicle.brand,
                "identifier": vehicle.identifier,
                "fuel_type": vehicle.fuel_type.value if vehicle.fuel_type else None,
                "consumption_l_per_100km": vehicle.consumption_l_per_100km,
            }

    for ft in (FuelType.AB, FuelType.DP):
        fuel_breakdown[ft]["requested_liters"] = round(fuel_breakdown[ft]["requested_liters"], 6)
        fuel_breakdown[ft]["requested_kg"] = round(fuel_breakdown[ft]["requested_kg"], 2)

    dept_signature = await crud_dept_signature.get_by_department_id(db, req.department_id)
    signature_payload = crud_dept_signature.row_to_payload(dept_signature)

    payload = {
        "stage": stage.value,
        "request": {
            "id": req.id,
            "request_number": req.request_number,
            "department_id": req.department_id,
            "status": req.status.value if req.status else None,
            "route_id": req.route_id,
            "route_is_manual": bool(req.route_is_manual),
            "route_text": req.route_text,
            "distance_km_per_trip": req.distance_km_per_trip,
            "justification_text": req.justification_text,
            "persons_involved_count": req.persons_involved_count,
            "training_days_count": req.training_days_count,
            "has_debt": bool(req.has_debt),
        },
        "items": items_payload,
        "vehicles": list(vehicles_payload.values()),
        "totals": {
            "requested_liters": round(sum(i["required_liters"] for i in items_payload), 6),
            "requested_kg": round(sum(i["required_kg"] for i in items_payload), 2),
        },
        "fuel_breakdown": {
            FuelType.AB.value: fuel_breakdown[FuelType.AB],
            FuelType.DP.value: fuel_breakdown[FuelType.DP],
        },
        "coefficient_snapshot": {
            FuelType.AB.value: float(req.coeff_snapshot_ab) if req.coeff_snapshot_ab is not None else None,
            FuelType.DP.value: float(req.coeff_snapshot_dp) if req.coeff_snapshot_dp is not None else None,
            "snapshot_at": req.coeff_snapshot_at.isoformat() if req.coeff_snapshot_at else None,
            "snapshot_by": req.coeff_snapshot_by,
            "fixed_on": "APPROVE",
        },
        "department_signatures": signature_payload,
        "actor_user_id": actor_user_id,
        "captured_at": utcnow().isoformat(),
    }

    row = RequestSnapshot(
        request_id=req.id,
        stage=stage,
        payload_json=payload,
        created_by=actor_user_id,
    )
    db.add(row)
    await db.flush()
    return row


async def _is_reservation_feature_enabled(db: AsyncSession) -> bool:
    raw = await crud_app_settings.get_setting(db, "features.enable_reservations")
    return str(raw).strip().lower() == "true"


async def _is_department_signature_required_on_submit(db: AsyncSession) -> bool:
    active_template = (
        await db.execute(
            select(PdfTemplate)
            .where(
                PdfTemplate.scope == PdfTemplateScope.REQUEST_FUEL,
                PdfTemplate.is_active.is_(True),
            )
            .order_by(PdfTemplate.created_at.asc())
        )
    ).scalars().first()
    if not active_template:
        return True

    version = (
        await db.execute(
            select(PdfTemplateVersion)
            .where(
                PdfTemplateVersion.template_id == active_template.id,
                PdfTemplateVersion.status == PdfTemplateVersionStatus.PUBLISHED,
            )
            .order_by(PdfTemplateVersion.version.desc())
        )
    ).scalars().first()
    if not version or not isinstance(version.layout_json, dict):
        return True
    signatures = version.layout_json.get("signatures")
    if not isinstance(signatures, dict):
        return True
    return bool(signatures.get("use_department_signatures", True))


async def _release_active_reservations(
    db: AsyncSession,
    *,
    request_id: int,
) -> None:
    rows = (
        await db.execute(
            select(StockReservation)
            .where(
                StockReservation.request_id == request_id,
                StockReservation.status == ReservationStatus.ACTIVE,
            )
            .with_for_update()
        )
    ).scalars().all()
    for row in rows:
        row.status = ReservationStatus.RELEASED
    await db.flush()


async def _upsert_reservations_for_request(
    db: AsyncSession,
    *,
    request_id: int,
    actor_user_id: int,
) -> None:
    req = await _lock_request_with_items(db, request_id)
    if not req:
        raise WorkflowConflictError("Request not found")
    coeff = await ensure_request_coeff_snapshot(db, req=req, actor_user_id=actor_user_id)
    breakdown = _aggregate_requested_by_fuel(req, coeff)

    existing = (
        await db.execute(
            select(StockReservation)
            .where(StockReservation.request_id == req.id)
            .with_for_update()
        )
    ).scalars().all()
    by_fuel = {r.fuel_type: r for r in existing}

    for ft, agg in breakdown.items():
        liters = float(agg["requested_liters"])
        kg = float(agg["requested_kg"])
        if liters <= 0:
            continue
        row = by_fuel.get(ft)
        if row is None:
            row = StockReservation(
                request_id=req.id,
                fuel_type=ft,
                reserved_liters=liters,
                reserved_kg=kg,
                status=ReservationStatus.ACTIVE,
                created_by=actor_user_id,
            )
            db.add(row)
        else:
            row.reserved_liters = liters
            row.reserved_kg = kg
            row.status = ReservationStatus.ACTIVE

    for ft, row in by_fuel.items():
        if ft not in breakdown:
            row.status = ReservationStatus.RELEASED

    await db.flush()


async def transition_request_status(
    db: AsyncSession,
    *,
    request_id: int,
    actor_user_id: int,
    to_status: RequestStatus,
    action: str,
    message: str | None = None,
) -> Request:
    req = (
        await db.execute(
            select(Request).where(Request.id == request_id).with_for_update()
        )
    ).scalars().first()
    if not req:
        raise WorkflowConflictError("Request not found")

    from_status = req.status
    if to_status in ACTIVE_REQUEST_STATUSES:
        await ensure_single_active_request(
            db,
            department_id=req.department_id,
            exclude_request_id=req.id,
        )
    if to_status == RequestStatus.APPROVED:
        await ensure_request_coeff_snapshot(db, req=req, actor_user_id=actor_user_id)
    if to_status == RequestStatus.SUBMITTED:
        if await _is_department_signature_required_on_submit(db):
            dept_signature = await crud_dept_signature.get_by_department_id(db, req.department_id)
            if not crud_dept_signature.is_department_approval_complete(dept_signature):
                raise WorkflowConflictError(
                    "Перед поданням заявки заповніть блок «З розрахунком згоден» у профілі підрозділу."
                )

    now = utcnow()
    req.status = to_status
    if to_status == RequestStatus.SUBMITTED:
        req.submitted_at = now
        req.submitted_by = actor_user_id
        req.is_rejected = False
        req.rejection_comment = None
        req.rejected_at = None
        req.rejected_by = None
    elif to_status == RequestStatus.APPROVED:
        req.approved_at = now
        req.approved_by = actor_user_id
    elif to_status == RequestStatus.ISSUED_BY_OPERATOR:
        req.operator_issued_at = now
        req.operator_issued_by = actor_user_id
    elif to_status == RequestStatus.CANCELED:
        pass

    await append_request_audit(
        db,
        request_id=req.id,
        actor_user_id=actor_user_id,
        action=action,
        from_status=from_status,
        to_status=to_status,
        message=message,
    )

    if to_status == RequestStatus.SUBMITTED:
        await create_request_snapshot(
            db,
            request_id=req.id,
            stage=RequestSnapshotStage.SUBMIT,
            actor_user_id=actor_user_id,
        )
    elif to_status == RequestStatus.APPROVED:
        if await _is_reservation_feature_enabled(db):
            await _upsert_reservations_for_request(
                db,
                request_id=req.id,
                actor_user_id=actor_user_id,
            )
            await append_request_audit(
                db,
                request_id=req.id,
                actor_user_id=actor_user_id,
                action="RESERVE",
                from_status=to_status,
                to_status=to_status,
                message="Stock reservation activated by feature flag",
            )
        await create_request_snapshot(
            db,
            request_id=req.id,
            stage=RequestSnapshotStage.APPROVE,
            actor_user_id=actor_user_id,
        )

    await db.flush()
    return req


async def reject_request_to_draft(
    db: AsyncSession,
    *,
    request_id: int,
    comment: str,
    admin_user_id: int,
) -> Request:
    req = (
        await db.execute(select(Request).where(Request.id == request_id).with_for_update())
    ).scalars().first()
    if not req:
        raise WorkflowConflictError("Request not found")
    if req.status != RequestStatus.SUBMITTED:
        raise WorkflowConflictError("Can only reject submitted requests")
    c = (comment or "").strip()
    if not c:
        raise WorkflowConflictError("Rejection comment required")

    now = utcnow()
    from_status = req.status
    req.status = RequestStatus.DRAFT
    req.is_rejected = True
    req.rejection_comment = c
    req.rejected_at = now
    req.rejected_by = admin_user_id

    await _release_active_reservations(db, request_id=req.id)

    await append_request_audit(
        db,
        request_id=req.id,
        actor_user_id=admin_user_id,
        action="REJECT",
        from_status=from_status,
        to_status=RequestStatus.DRAFT,
        message=c,
    )
    await db.flush()
    return req


async def start_posting_session(
    db: AsyncSession,
    *,
    request_id: int | None,
    operation: PostingOperation,
    idempotency_key: str | None,
    started_by_user_id: int | None,
) -> tuple[PostingSession, str]:
    key = normalize_idempotency_key(idempotency_key)
    if not key:
        key = f"auto:{operation.value}:{request_id or 'global'}:{uuid.uuid4()}"

    session = (
        await db.execute(
            select(PostingSession)
            .where(
                PostingSession.operation == operation,
                PostingSession.idempotency_key == key,
            )
            .with_for_update()
        )
    ).scalars().first()

    if session:
        if request_id is not None and session.request_id not in (None, request_id):
            raise WorkflowConflictError("Idempotency-Key already used for another request")
        if session.status == PostingSessionStatus.SUCCESS:
            return session, "SUCCESS"
        if session.status == PostingSessionStatus.IN_PROGRESS:
            return session, "IN_PROGRESS"

        session.status = PostingSessionStatus.IN_PROGRESS
        session.started_at = utcnow()
        session.finished_at = None
        session.started_by_user_id = started_by_user_id
        session.error_code = None
        session.error_message = None
        session.retry_count = int(session.retry_count or 0) + 1
        await db.flush()
        return session, "PROCEED"

    session = PostingSession(
        request_id=request_id,
        operation=operation,
        idempotency_key=key,
        status=PostingSessionStatus.IN_PROGRESS,
        started_at=utcnow(),
        started_by_user_id=started_by_user_id,
        retry_count=0,
    )
    db.add(session)
    await db.flush()
    return session, "PROCEED"


async def mark_posting_session_success(
    db: AsyncSession,
    *,
    posting_session: PostingSession,
    result_ref: dict[str, Any] | None,
) -> PostingSession:
    posting_session.status = PostingSessionStatus.SUCCESS
    posting_session.finished_at = utcnow()
    posting_session.error_code = None
    posting_session.error_message = None
    posting_session.result_json = result_ref
    posting_session.result_ref = result_ref
    await db.flush()
    return posting_session


async def mark_posting_session_failed(
    db: AsyncSession,
    *,
    posting_session: PostingSession,
    error_code: str,
    error_message: str,
) -> PostingSession:
    posting_session.status = PostingSessionStatus.FAILED
    posting_session.finished_at = utcnow()
    posting_session.error_code = error_code[:64]
    posting_session.error_message = error_message[:4000]
    posting_session.result_json = None
    await incident_service.create_incident_for_failed_posting_session(
        db,
        posting_session=posting_session,
        error_code=posting_session.error_code,
        error_message=posting_session.error_message or "Unknown posting error",
    )
    await db.flush()
    return posting_session


def confirm_result_ref(result: ConfirmResult) -> dict[str, Any]:
    issue = result.issue
    breakdown = {"AB": {"requested": {"liters": 0.0, "kg": 0.0}, "posted": {"liters": 0.0, "kg": 0.0}, "debt": {"liters": 0.0, "kg": 0.0}},
                 "DP": {"requested": {"liters": 0.0, "kg": 0.0}, "posted": {"liters": 0.0, "kg": 0.0}, "debt": {"liters": 0.0, "kg": 0.0}}}
    if issue and issue.breakdown_json:
        for row in (issue.breakdown_json.get("lines") or []):
            ft = str(row.get("fuel_type") or "")
            key = "AB" if ft == FuelType.AB.value else "DP" if ft == FuelType.DP.value else None
            if not key:
                continue
            breakdown[key] = {
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
    return {
        "result": result.result,
        "request_id": result.request.id,
        "issue_id": issue.id if issue else None,
        "issue_doc_no": issue.issue_doc_no if issue else None,
        "issue_status": issue.status.value if issue and issue.status else None,
        "has_debt": bool(result.request.has_debt),
        "totals": issue.breakdown_json.get("totals") if issue and issue.breakdown_json else None,
        "breakdown": breakdown,
    }


async def confirm_request_posting(
    db: AsyncSession,
    *,
    request_id: int,
    actor_user_id: int,
    force_admin_month_end: bool = False,
    audit_action: str = "CONFIRM",
) -> ConfirmResult:
    now = utcnow()
    req = await _lock_request_with_items(db, request_id)
    if not req:
        raise WorkflowConflictError("Request not found")

    existing_issue = await _lock_existing_issue(db, request_id)
    if existing_issue and req.status == RequestStatus.POSTED:
        return ConfirmResult(result="ALREADY_CONFIRMED", request=req, issue=existing_issue)

    if req.status != RequestStatus.ISSUED_BY_OPERATOR:
        raise WorkflowConflictError("Cannot confirm in current status")

    if not force_admin_month_end and _is_confirm_expired(req, now):
        raise MonthEndConfirmRequiredError(
            "Підтвердження після завершення місяця виконує тільки адміністратор вручну."
        )

    coeff = await ensure_request_coeff_snapshot(db, req=req, actor_user_id=actor_user_id)
    requested_by_fuel = _aggregate_requested_by_fuel(req, coeff)
    if not requested_by_fuel:
        raise WorkflowConflictError("Request has no items to post")

    if existing_issue:
        req.status = RequestStatus.POSTED
        req.has_debt = bool(existing_issue.has_debt)
        req.dept_confirmed_at = req.dept_confirmed_at or existing_issue.posted_at or now
        req.dept_confirmed_by = req.dept_confirmed_by or actor_user_id
        req.stock_posted_at = req.stock_posted_at or existing_issue.posted_at or now
        req.stock_posted_by = req.stock_posted_by or existing_issue.posted_by or actor_user_id
        await append_request_audit(
            db,
            request_id=req.id,
            actor_user_id=actor_user_id,
            action=audit_action,
            from_status=RequestStatus.ISSUED_BY_OPERATOR,
            to_status=RequestStatus.POSTED,
            message=f"Recovered from existing issue document {existing_issue.issue_doc_no}",
        )
        await create_request_snapshot(
            db,
            request_id=req.id,
            stage=RequestSnapshotStage.CONFIRM,
            actor_user_id=actor_user_id,
        )
        return ConfirmResult(result="ALREADY_CONFIRMED", request=req, issue=existing_issue)

    reservation_enabled = await _is_reservation_feature_enabled(db)

    fuel_keys = sorted(requested_by_fuel.keys(), key=_fuel_order)
    primary_fuel = fuel_keys[0]
    issue = StockIssue(
        request_id=req.id,
        issue_doc_no=await _issue_doc_no(db, now),
        status=StockIssueStatus.POSTED,
        posted_by=actor_user_id,
        posted_at=now,
        has_debt=False,
        debt_liters=0.0,
        debt_kg=0.0,
        fuel_type=primary_fuel,
        issue_liters=0.0,
        issue_kg=0.0,
        created_by=actor_user_id,
    )
    db.add(issue)
    await db.flush()

    has_debt = False
    breakdown_rows: list[dict[str, Any]] = []

    for ft in fuel_keys:
        agg = requested_by_fuel[ft]
        bal = await _lock_balance(db, ft)

        requested_liters = float(agg["requested_liters"])
        available_liters = max(float(bal.balance_liters or 0.0), 0.0)

        own_reservation = 0.0
        own_reservation_row: StockReservation | None = None
        if reservation_enabled:
            reservations = (
                await db.execute(
                    select(StockReservation)
                    .where(
                        StockReservation.fuel_type == ft,
                        StockReservation.status == ReservationStatus.ACTIVE,
                    )
                    .with_for_update()
                )
            ).scalars().all()
            total_reserved = 0.0
            for res in reservations:
                total_reserved += float(res.reserved_liters or 0.0)
                if res.request_id == req.id:
                    own_reservation = float(res.reserved_liters or 0.0)
                    own_reservation_row = res
            free_unreserved = max(available_liters - total_reserved, 0.0)
            available_liters = min(available_liters, own_reservation + free_unreserved)

        issued_liters = min(requested_liters, available_liters)
        missing_liters = round(requested_liters - issued_liters, 6)

        c = float(coeff[ft])
        issued_kg = round(issued_liters * c, 2)
        missing_kg = round(missing_liters * c, 2)

        if issued_liters > 0:
            bal.balance_liters = round(float(bal.balance_liters) - issued_liters, 6)
            bal.balance_kg = round(float(bal.balance_kg) - issued_kg, 2)
            if bal.balance_liters < -1e-6 or bal.balance_kg < -1e-6:
                raise WorkflowConflictError("Posting would lead to negative stock balance")
            db.add(
                StockLedger(
                    fuel_type=ft,
                    delta_liters=-issued_liters,
                    delta_kg=-issued_kg,
                    ref_type=RefType.ISSUE,
                    ref_id=req.id,
                )
            )

        if missing_liters > 0:
            has_debt = True
            db.add(
                FuelDebt(
                    request_id=req.id,
                    fuel_type=ft,
                    missing_liters=missing_liters,
                    missing_kg=missing_kg,
                    status=DebtStatus.OPEN,
                    created_by=None,
                )
            )

        db.add(
            StockIssueLine(
                stock_issue_id=issue.id,
                fuel_type=ft,
                requested_liters=requested_liters,
                requested_kg=float(agg["requested_kg"]),
                issued_liters=issued_liters,
                issued_kg=issued_kg,
                missing_liters=missing_liters,
                missing_kg=missing_kg,
            )
        )

        if reservation_enabled and own_reservation_row is not None:
            own_reservation_row.status = ReservationStatus.CONSUMED

        issue.issue_liters = round(issue.issue_liters + issued_liters, 6)
        issue.issue_kg = round(issue.issue_kg + issued_kg, 2)
        issue.debt_liters = round(issue.debt_liters + missing_liters, 6)
        issue.debt_kg = round(issue.debt_kg + missing_kg, 2)

        breakdown_rows.append(
            {
                "fuel_type": ft.value,
                "requested_liters": requested_liters,
                "requested_kg": float(agg["requested_kg"]),
                "issued_liters": issued_liters,
                "issued_kg": issued_kg,
                "missing_liters": missing_liters,
                "missing_kg": missing_kg,
                "reservation_enabled": reservation_enabled,
                "reserved_liters": own_reservation,
            }
        )

    issue.has_debt = has_debt
    issue.status = StockIssueStatus.DEBT if has_debt else StockIssueStatus.POSTED
    issue.breakdown_json = {
        "lines": breakdown_rows,
        "totals": {
            "issued_liters": issue.issue_liters,
            "issued_kg": issue.issue_kg,
            "debt_liters": issue.debt_liters,
            "debt_kg": issue.debt_kg,
        },
    }

    req.status = RequestStatus.POSTED
    req.has_debt = has_debt
    req.dept_confirmed_at = now
    req.dept_confirmed_by = actor_user_id
    req.stock_posted_at = now
    req.stock_posted_by = actor_user_id

    action_msg = f"Issue document {issue.issue_doc_no} posted by system"
    if force_admin_month_end:
        action_msg += " (admin month-end confirm)"
    if has_debt:
        action_msg += f"; debt recorded: {issue.debt_liters:.2f} L / {issue.debt_kg:.2f} kg"

    await append_request_audit(
        db,
        request_id=req.id,
        actor_user_id=actor_user_id,
        action=audit_action,
        from_status=RequestStatus.ISSUED_BY_OPERATOR,
        to_status=RequestStatus.POSTED,
        message=action_msg,
    )
    if has_debt:
        await append_request_audit(
            db,
            request_id=req.id,
            actor_user_id=None,
            action="DEBT",
            from_status=RequestStatus.POSTED,
            to_status=RequestStatus.POSTED,
            message="Created fuel debt due to insufficient stock",
        )

    await create_request_snapshot(
        db,
        request_id=req.id,
        stage=RequestSnapshotStage.CONFIRM,
        actor_user_id=actor_user_id,
    )

    if reservation_enabled:
        await _release_active_reservations(db, request_id=req.id)

    return ConfirmResult(
        result="POSTED_WITH_DEBT" if has_debt else "POSTED",
        request=req,
        issue=issue,
    )


async def create_adjustment(
    db: AsyncSession,
    *,
    reason: str,
    created_by: int,
    lines: list[dict[str, Any]],
) -> StockAdjustment:
    reason_clean = (reason or "").strip()
    if not reason_clean:
        raise WorkflowConflictError("Adjustment reason is required")
    if not lines:
        raise WorkflowConflictError("Adjustment lines are required")

    now = utcnow()
    adj = StockAdjustment(
        adjustment_doc_no=_adjustment_doc_no(now),
        reason=reason_clean,
        created_by=created_by,
        created_at=now,
    )
    db.add(adj)
    await db.flush()

    request_ids_to_release: set[int] = set()

    for ln in lines:
        fuel_type = ln.get("fuel_type")
        if isinstance(fuel_type, str):
            fuel_type = FuelType(fuel_type)
        delta_liters = float(ln.get("delta_liters", 0.0))
        delta_kg = float(ln.get("delta_kg", 0.0))
        request_id = ln.get("request_id")
        comment = ln.get("comment")

        if abs(delta_liters) < 1e-9 and abs(delta_kg) < 1e-9:
            continue

        bal = await _lock_balance(db, fuel_type)
        new_l = round(float(bal.balance_liters) + delta_liters, 6)
        new_kg = round(float(bal.balance_kg) + delta_kg, 2)
        if new_l < -1e-6 or new_kg < -1e-6:
            raise WorkflowConflictError("Adjustment would lead to negative stock balance")
        bal.balance_liters = new_l
        bal.balance_kg = new_kg

        db.add(
            StockLedger(
                fuel_type=fuel_type,
                delta_liters=delta_liters,
                delta_kg=delta_kg,
                ref_type=RefType.RECEIPT if delta_liters >= 0 else RefType.ISSUE,
                ref_id=adj.id,
            )
        )
        db.add(
            StockAdjustmentLine(
                adjustment_id=adj.id,
                fuel_type=fuel_type,
                delta_liters=delta_liters,
                delta_kg=delta_kg,
                request_id=request_id,
                comment=comment,
            )
        )
        if request_id:
            request_ids_to_release.add(int(request_id))
            await append_request_audit(
                db,
                request_id=int(request_id),
                actor_user_id=created_by,
                action="ADJUST",
                message=f"Adjustment {adj.adjustment_doc_no}: {reason_clean}",
            )

    for request_id in request_ids_to_release:
        await _release_active_reservations(db, request_id=request_id)

    await db.flush()
    return adj


async def reverse_posted_request(
    db: AsyncSession,
    *,
    request_id: int,
    reason: str,
    actor_user_id: int,
) -> StockAdjustment:
    req = await _lock_request_with_items(db, request_id)
    if not req:
        raise WorkflowConflictError("Request not found")

    issue = await _lock_existing_issue(db, request_id)
    if not issue:
        raise WorkflowConflictError("Posted stock issue not found")
    if issue.status == StockIssueStatus.REVERSED:
        raise WorkflowConflictError("Request already reversed")

    lines_payload: list[dict[str, Any]] = []
    for ln in issue.lines:
        if float(ln.issued_liters or 0) <= 0 and float(ln.issued_kg or 0) <= 0:
            continue
        lines_payload.append(
            {
                "fuel_type": ln.fuel_type,
                "delta_liters": float(ln.issued_liters or 0.0),
                "delta_kg": float(ln.issued_kg or 0.0),
                "request_id": req.id,
                "comment": f"Reverse issue {issue.issue_doc_no}",
            }
        )

    if not lines_payload:
        raise WorkflowConflictError("No issued fuel lines found for reversal")

    adj = await create_adjustment(
        db,
        reason=reason,
        created_by=actor_user_id,
        lines=lines_payload,
    )

    issue.status = StockIssueStatus.REVERSED
    req.status = RequestStatus.CANCELED
    req.has_debt = False
    await _release_active_reservations(db, request_id=req.id)

    await append_request_audit(
        db,
        request_id=req.id,
        actor_user_id=actor_user_id,
        action="CANCEL",
        from_status=RequestStatus.POSTED,
        to_status=RequestStatus.CANCELED,
        message=f"Reversed by adjustment {adj.adjustment_doc_no}",
    )

    debts = (
        await db.execute(
            select(FuelDebt)
            .where(
                and_(
                    FuelDebt.request_id == req.id,
                    FuelDebt.status == DebtStatus.OPEN,
                )
            )
            .with_for_update()
        )
    ).scalars().all()
    now = utcnow()
    for debt in debts:
        debt.status = DebtStatus.CLOSED
        debt.closed_at = now
        debt.closed_by = actor_user_id
        debt.close_comment = f"Closed by request reversal {adj.adjustment_doc_no}"

    await db.flush()
    return adj


async def month_end_pending_request_ids(
    db: AsyncSession,
    *,
    request_ids: list[int] | None = None,
) -> list[int]:
    if request_ids:
        rows = (
            await db.execute(
                select(Request.id)
                .where(
                    Request.id.in_(request_ids),
                    Request.status == RequestStatus.ISSUED_BY_OPERATOR,
                )
                .order_by(Request.id)
            )
        ).scalars().all()
        return [int(x) for x in rows]

    now = utcnow()
    month_start = datetime(now.year, now.month, 1)
    rows = (
        await db.execute(
            select(Request.id)
            .where(
                Request.status == RequestStatus.ISSUED_BY_OPERATOR,
                Request.operator_issued_at.is_not(None),
                Request.operator_issued_at < month_start,
            )
            .order_by(Request.id)
        )
    ).scalars().all()
    return [int(x) for x in rows]
