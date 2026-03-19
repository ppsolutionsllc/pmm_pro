from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.department import Department
from app.models.request import Request, RequestStatus
from app.models.request_item import RequestItem
from app.models.stock import DebtStatus, FuelDebt, FuelType, StockAdjustmentLine, StockBalance, StockIssue, StockIssueLine, StockReceipt
from app.models.vehicle import Vehicle


def _fuel_key_order(value: str) -> int:
    return 0 if value == FuelType.AB.value else 1


def _period_label(ts: datetime | None) -> str:
    if ts is None:
        return "unknown"
    return f"{ts.year:04d}-{ts.month:02d}"


async def build_stock_reconcile_rows(db: AsyncSession) -> list[dict[str, Any]]:
    by_fuel: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "receipts_liters": 0.0,
            "receipts_kg": 0.0,
            "issues_liters": 0.0,
            "issues_kg": 0.0,
            "adjustments_liters": 0.0,
            "adjustments_kg": 0.0,
            "balance_liters": 0.0,
            "balance_kg": 0.0,
        }
    )

    receipts = (await db.execute(select(StockReceipt))).scalars().all()
    for rec in receipts:
        fk = rec.fuel_type.value
        by_fuel[fk]["receipts_liters"] += float(rec.computed_liters or 0.0)
        by_fuel[fk]["receipts_kg"] += float(rec.computed_kg or 0.0)

    issue_lines = (
        await db.execute(
            select(StockIssueLine, StockIssue)
            .join(StockIssue, StockIssue.id == StockIssueLine.stock_issue_id)
        )
    ).all()
    for line, _issue in issue_lines:
        fk = line.fuel_type.value
        by_fuel[fk]["issues_liters"] += float(line.issued_liters or 0.0)
        by_fuel[fk]["issues_kg"] += float(line.issued_kg or 0.0)

    adjustment_lines = (await db.execute(select(StockAdjustmentLine))).scalars().all()
    for line in adjustment_lines:
        fk = line.fuel_type.value
        by_fuel[fk]["adjustments_liters"] += float(line.delta_liters or 0.0)
        by_fuel[fk]["adjustments_kg"] += float(line.delta_kg or 0.0)

    balances = (await db.execute(select(StockBalance))).scalars().all()
    for bal in balances:
        fk = bal.fuel_type.value
        by_fuel[fk]["balance_liters"] = float(bal.balance_liters or 0.0)
        by_fuel[fk]["balance_kg"] = float(bal.balance_kg or 0.0)

    rows: list[dict[str, Any]] = []
    for fuel_type in sorted(by_fuel.keys(), key=_fuel_key_order):
        row = by_fuel[fuel_type]
        expected_liters = row["receipts_liters"] - row["issues_liters"] + row["adjustments_liters"]
        expected_kg = row["receipts_kg"] - row["issues_kg"] + row["adjustments_kg"]
        diff_liters = round(expected_liters - row["balance_liters"], 6)
        diff_kg = round(expected_kg - row["balance_kg"], 2)
        rows.append(
            {
                "fuel_type": fuel_type,
                "receipts_liters": round(row["receipts_liters"], 6),
                "receipts_kg": round(row["receipts_kg"], 2),
                "issues_liters": round(row["issues_liters"], 6),
                "issues_kg": round(row["issues_kg"], 2),
                "adjustments_liters": round(row["adjustments_liters"], 6),
                "adjustments_kg": round(row["adjustments_kg"], 2),
                "expected_balance_liters": round(expected_liters, 6),
                "expected_balance_kg": round(expected_kg, 2),
                "actual_balance_liters": round(row["balance_liters"], 6),
                "actual_balance_kg": round(row["balance_kg"], 2),
                "difference_liters": diff_liters,
                "difference_kg": diff_kg,
                "is_consistent": abs(diff_liters) < 1e-6 and abs(diff_kg) < 1e-2,
            }
        )
    return rows


async def build_vehicle_consumption_rows(
    db: AsyncSession,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    department_id: int | None = None,
    vehicle_id: int | None = None,
    fuel_type: str | None = None,
    route_contains: str | None = None,
) -> list[dict[str, Any]]:
    q = (
        select(RequestItem, Request, Vehicle)
        .join(Request, Request.id == RequestItem.request_id)
        .join(Vehicle, Vehicle.id == RequestItem.vehicle_id)
        .where(Request.status == RequestStatus.POSTED)
    )
    if department_id is not None:
        q = q.where(Request.department_id == department_id)
    if vehicle_id is not None:
        q = q.where(RequestItem.vehicle_id == vehicle_id)
    if fuel_type:
        q = q.where(Vehicle.fuel_type == FuelType(fuel_type))
    if date_from is not None:
        q = q.where(Request.stock_posted_at >= date_from)
    if date_to is not None:
        q = q.where(Request.stock_posted_at <= date_to)
    if route_contains:
        like = f"%{route_contains}%"
        q = q.where(
            and_(
                RequestItem.route_text.is_not(None),
                RequestItem.route_text.ilike(like),
            )
        )

    rows = (await db.execute(q)).all()
    agg: dict[tuple[Any, ...], dict[str, Any]] = {}
    for item, req, vehicle in rows:
        period = _period_label(req.stock_posted_at or req.dept_confirmed_at or req.created_at)
        route_label = item.route_text or req.route_text or "-"
        key = (period, vehicle.id, route_label)
        if key not in agg:
            agg[key] = {
                "period": period,
                "vehicle_id": vehicle.id,
                "vehicle_brand": vehicle.brand,
                "vehicle_identifier": vehicle.identifier,
                "fuel_type": vehicle.fuel_type.value if vehicle.fuel_type else None,
                "route": route_label,
                "total_km": 0.0,
                "requested_liters": 0.0,
                "requested_kg": 0.0,
                "requests_count": set(),
            }
        bucket = agg[key]
        bucket["total_km"] += float(item.total_km or 0.0)
        bucket["requested_liters"] += float(item.required_liters or 0.0)
        bucket["requested_kg"] += float(item.required_kg or 0.0)
        bucket["requests_count"].add(req.id)

    out = []
    for row in agg.values():
        out.append(
            {
                **row,
                "total_km": round(float(row["total_km"]), 3),
                "requested_liters": round(float(row["requested_liters"]), 3),
                "requested_kg": round(float(row["requested_kg"]), 2),
                "requests_count": len(row["requests_count"]),
            }
        )
    out.sort(key=lambda r: (r["period"], r["vehicle_brand"] or "", r["vehicle_identifier"] or ""))
    return out


async def build_debts_rows(
    db: AsyncSession,
    *,
    department_id: int | None = None,
    only_open: bool = False,
) -> list[dict[str, Any]]:
    q = (
        select(FuelDebt, Request)
        .join(Request, Request.id == FuelDebt.request_id)
        .order_by(FuelDebt.created_at.desc())
    )
    if department_id is not None:
        q = q.where(Request.department_id == department_id)
    if only_open:
        q = q.where(FuelDebt.status == DebtStatus.OPEN)

    rows = (await db.execute(q)).all()
    out = []
    for debt, req in rows:
        out.append(
            {
                "debt_id": debt.id,
                "request_id": req.id,
                "request_number": req.request_number,
                "department_id": req.department_id,
                "fuel_type": debt.fuel_type.value if debt.fuel_type else None,
                "missing_liters": float(debt.missing_liters or 0.0),
                "missing_kg": float(debt.missing_kg or 0.0),
                "status": debt.status.value if getattr(debt, "status", None) else str(debt.status),
                "created_at": debt.created_at.isoformat() if debt.created_at else None,
                "closed_at": debt.closed_at.isoformat() if debt.closed_at else None,
                "close_comment": debt.close_comment,
            }
        )
    return out


async def build_requests_rows(
    db: AsyncSession,
    *,
    department_id: int | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    q = select(Request).order_by(Request.created_at.desc())
    if department_id is not None:
        q = q.where(Request.department_id == department_id)
    if status:
        q = q.where(Request.status == status)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": r.id,
            "request_number": r.request_number,
            "department_id": r.department_id,
            "status": r.status.value if r.status else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
            "approved_at": r.approved_at.isoformat() if r.approved_at else None,
            "operator_issued_at": r.operator_issued_at.isoformat() if r.operator_issued_at else None,
            "stock_posted_at": r.stock_posted_at.isoformat() if r.stock_posted_at else None,
            "has_debt": bool(r.has_debt),
            "is_rejected": bool(r.is_rejected),
            "issue_doc_no": r.issue_doc_no,
        }
        for r in rows
    ]


async def build_department_consumption_rows(
    db: AsyncSession,
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    department_id: int | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    q = (
        select(Request)
        .options(
            selectinload(Request.department),
            selectinload(Request.items).selectinload(RequestItem.vehicle),
            selectinload(Request.stock_issue).selectinload(StockIssue.lines),
        )
    )
    if department_id is not None:
        q = q.where(Request.department_id == department_id)
    if status:
        try:
            q = q.where(Request.status == RequestStatus(status))
        except ValueError:
            return []
    if date_from is not None:
        q = q.where(Request.created_at >= date_from)
    if date_to is not None:
        q = q.where(Request.created_at <= date_to)

    reqs = (await db.execute(q)).scalars().all()
    agg: dict[int, dict[str, Any]] = {}
    for req in reqs:
        dep_id = int(req.department_id)
        dep_name = (
            req.department.name
            if isinstance(req.department, Department) and req.department and req.department.name
            else f"Підрозділ #{dep_id}"
        )
        if dep_id not in agg:
            agg[dep_id] = {
                "department_id": dep_id,
                "department_name": dep_name,
                "requests_count": 0,
                "posted_count": 0,
                "debt_requests_count": 0,
                "requested_ab_liters": 0.0,
                "requested_dp_liters": 0.0,
                "issued_ab_liters": 0.0,
                "issued_dp_liters": 0.0,
                "debt_ab_liters": 0.0,
                "debt_dp_liters": 0.0,
            }
        bucket = agg[dep_id]
        bucket["requests_count"] += 1
        if req.status == RequestStatus.POSTED:
            bucket["posted_count"] += 1
        if bool(req.has_debt):
            bucket["debt_requests_count"] += 1

        for item in req.items or []:
            vehicle = item.vehicle
            if not vehicle or not vehicle.fuel_type:
                continue
            liters = float(item.required_liters or 0.0)
            if vehicle.fuel_type == FuelType.AB:
                bucket["requested_ab_liters"] += liters
            elif vehicle.fuel_type == FuelType.DP:
                bucket["requested_dp_liters"] += liters

        issue = req.stock_issue
        for ln in (issue.lines if issue else []) or []:
            issued = float(ln.issued_liters or 0.0)
            debt = float(ln.missing_liters or 0.0)
            if ln.fuel_type == FuelType.AB:
                bucket["issued_ab_liters"] += issued
                bucket["debt_ab_liters"] += debt
            elif ln.fuel_type == FuelType.DP:
                bucket["issued_dp_liters"] += issued
                bucket["debt_dp_liters"] += debt

    out = []
    for row in agg.values():
        out.append(
            {
                **row,
                "requested_ab_liters": round(float(row["requested_ab_liters"]), 3),
                "requested_dp_liters": round(float(row["requested_dp_liters"]), 3),
                "issued_ab_liters": round(float(row["issued_ab_liters"]), 3),
                "issued_dp_liters": round(float(row["issued_dp_liters"]), 3),
                "debt_ab_liters": round(float(row["debt_ab_liters"]), 3),
                "debt_dp_liters": round(float(row["debt_dp_liters"]), 3),
            }
        )
    out.sort(key=lambda r: (r["department_name"] or "").lower())
    return out
