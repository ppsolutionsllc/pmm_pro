from datetime import datetime, timedelta
from typing import List
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.schemas import stock as schema_stock
from app.crud import stock as crud_stock
from app.core.quantities import round_up_quantity, round_up_signed_quantity
from app.models.posting_session import PostingOperation
from app.models.request import Request
from app.models.stock import StockAdjustment, StockBalance, StockLedger, StockReceipt
from app.api import deps
from app.services import request_workflow as workflow

router = APIRouter()
posting_logger = logging.getLogger("app.posting")


def _parse_yyyy_mm_dd(value: str | None, *, field: str) -> datetime | None:
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field} format. Use YYYY-MM-DD")

@router.post("/stock/receipts", response_model=schema_stock.StockReceiptOut)
async def create_receipt(
    data: schema_stock.StockReceiptCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    try:
        rec = await crud_stock.create_stock_receipt(
            db,
            fuel_type=data.fuel_type,
            input_unit=data.input_unit,
            input_amount=data.input_amount,
            created_by=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return rec


@router.get("/stock/receipts", response_model=List[schema_stock.StockReceiptOut])
async def list_receipts(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    dt_from = _parse_yyyy_mm_dd(date_from, field="date_from")
    dt_to = _parse_yyyy_mm_dd(date_to, field="date_to")
    if dt_from and dt_to and dt_to < dt_from:
        raise HTTPException(status_code=400, detail="date_to must be greater than or equal to date_from")

    q = select(StockReceipt)
    if dt_from:
        q = q.where(StockReceipt.created_at >= dt_from)
    if dt_to:
        q = q.where(StockReceipt.created_at < (dt_to + timedelta(days=1)))
    q = q.order_by(StockReceipt.created_at.desc())
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/stock/balance")
async def get_balance(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "OPERATOR"])),
):
    result = await db.execute(select(StockBalance))
    rows = result.scalars().all()
    return [
        {
                "id": r.id,
                "fuel_type": r.fuel_type.value if r.fuel_type else None,
                "balance_liters": float(round_up_quantity(r.balance_liters)),
                "balance_kg": float(round_up_quantity(r.balance_kg)),
            }
        for r in rows
    ]


@router.get("/stock/ledger")
async def list_ledger(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    dt_from = _parse_yyyy_mm_dd(date_from, field="date_from")
    dt_to = _parse_yyyy_mm_dd(date_to, field="date_to")
    if dt_from and dt_to and dt_to < dt_from:
        raise HTTPException(status_code=400, detail="date_to must be greater than or equal to date_from")

    q = select(StockLedger)
    if dt_from:
        q = q.where(StockLedger.created_at >= dt_from)
    if dt_to:
        q = q.where(StockLedger.created_at < (dt_to + timedelta(days=1)))
    q = q.order_by(StockLedger.created_at.desc())
    result = await db.execute(q)
    rows = result.scalars().all()

    receipt_candidate_ids = {int(r.ref_id) for r in rows if r.ref_type and r.ref_type.value == "receipt" and int(r.ref_id or 0) > 0}
    issue_candidate_ids = {int(r.ref_id) for r in rows if r.ref_type and r.ref_type.value == "issue" and int(r.ref_id or 0) > 0}
    adjustment_candidate_ids = receipt_candidate_ids.union(issue_candidate_ids)

    receipt_ids: set[int] = set()
    request_ids: set[int] = set()
    adjustment_ids: set[int] = set()

    if receipt_candidate_ids:
        receipt_ids = set(
            (await db.execute(select(StockReceipt.id).where(StockReceipt.id.in_(list(receipt_candidate_ids))))).scalars().all()
        )
    if issue_candidate_ids:
        request_ids = set(
            (await db.execute(select(Request.id).where(Request.id.in_(list(issue_candidate_ids))))).scalars().all()
        )
    if adjustment_candidate_ids:
        adjustment_ids = set(
            (await db.execute(select(StockAdjustment.id).where(StockAdjustment.id.in_(list(adjustment_candidate_ids))))).scalars().all()
        )

    return [
        (
            lambda ref_type, ref_id: {
                "id": r.id,
                "fuel_type": r.fuel_type.value if r.fuel_type else None,
                "delta_liters": float(round_up_signed_quantity(r.delta_liters)),
                "delta_kg": float(round_up_signed_quantity(r.delta_kg)),
                "ref_type": ref_type,
                "ref_id": ref_id,
                "ref_doc_type": (
                    "STOCK_RECEIPT"
                    if ref_type == "receipt" and ref_id in receipt_ids
                    else "REQUEST"
                    if ref_type == "issue" and ref_id in request_ids
                    else "STOCK_ADJUSTMENT"
                    if ref_id in adjustment_ids
                    else None
                ),
                "ref_doc_url": (
                    f"/admin/stock/receipts?receipt_id={ref_id}"
                    if ref_type == "receipt" and ref_id in receipt_ids
                    else f"/admin/requests/{ref_id}"
                    if ref_type == "issue" and ref_id in request_ids
                    else f"/admin/stock/adjustments/{ref_id}"
                    if ref_id in adjustment_ids
                    else None
                ),
                "ref_doc_label": (
                    f"Прихід №{ref_id}"
                    if ref_type == "receipt" and ref_id in receipt_ids
                    else f"Заявка №{ref_id}"
                    if ref_type == "issue" and ref_id in request_ids
                    else f"Акт коригування №{ref_id}"
                    if ref_id in adjustment_ids
                    else (f"Документ №{ref_id}" if ref_id else "—")
                ),
                "created_at": str(r.created_at) if r.created_at else None,
            }
        )(r.ref_type.value if r.ref_type else None, int(r.ref_id or 0))
        for r in rows
    ]


@router.post("/stock/adjustments", response_model=schema_stock.StockAdjustmentOut)
async def create_adjustment(
    data: schema_stock.StockAdjustmentCreateIn,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    actor_user_id = int(current_user.id)
    idem_key = workflow.normalize_idempotency_key(idempotency_key or data.idempotency_key)
    try:
        posting_session, state = await workflow.start_posting_session(
            db,
            request_id=None,
            operation=PostingOperation.ADJUSTMENT,
            idempotency_key=idem_key,
            started_by_user_id=actor_user_id,
        )
        if state == "IN_PROGRESS":
            raise HTTPException(status_code=409, detail="Adjustment is already in progress for this Idempotency-Key")
        if state == "SUCCESS":
            result_ref = posting_session.result_json or posting_session.result_ref or {}
            return {
                "id": int(result_ref.get("adjustment_id", 0)),
                "adjustment_doc_no": result_ref.get("adjustment_doc_no", "ALREADY_DONE"),
                "reason": data.reason,
                "created_by": current_user.id,
                "created_at": None,
            }

        adj = await workflow.create_adjustment(
            db,
            reason=data.reason,
            created_by=actor_user_id,
            lines=[ln.model_dump() for ln in data.lines],
        )
        await workflow.mark_posting_session_success(
            db,
            posting_session=posting_session,
            result_ref={"adjustment_id": adj.id, "adjustment_doc_no": adj.adjustment_doc_no},
        )
        await db.commit()
        return adj
    except workflow.WorkflowConflictError as e:
        await db.rollback()
        posting_logger.exception("ADJUSTMENT_FAILED error=%s", e)
        try:
            posting_session, state = await workflow.start_posting_session(
                db,
                request_id=None,
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
                    message=f"Manual adjustment failed: {e}",
                    posting_session_id=posting_session.id,
                )
                await db.commit()
        except Exception:
            await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        posting_logger.exception("ADJUSTMENT_EXCEPTION error=%s", e)
        try:
            posting_session, state = await workflow.start_posting_session(
                db,
                request_id=None,
                operation=PostingOperation.ADJUSTMENT,
                idempotency_key=idem_key,
                started_by_user_id=actor_user_id,
            )
            if state != "SUCCESS":
                await workflow.mark_posting_session_failed(
                    db,
                    posting_session=posting_session,
                    error_code="ADJUSTMENT_EXCEPTION",
                    error_message=str(e),
                )
                await workflow.create_admin_alert(
                    db,
                    alert_type="ADJUSTMENT_FAILED",
                    severity="HIGH",
                    message=f"Manual adjustment exception: {e}",
                    posting_session_id=posting_session.id,
                )
                await db.commit()
        except Exception:
            await db.rollback()
        raise HTTPException(status_code=500, detail="Adjustment failed")


@router.get("/stock/adjustments", response_model=List[schema_stock.StockAdjustmentOut])
async def list_adjustments(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    result = await db.execute(select(StockAdjustment).order_by(StockAdjustment.created_at.desc()))
    return result.scalars().all()


@router.get("/stock/adjustments/{adjustment_id}", response_model=schema_stock.StockAdjustmentDetailOut)
async def get_adjustment_detail(
    adjustment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    row = (
        await db.execute(
            select(StockAdjustment)
            .options(selectinload(StockAdjustment.lines))
            .where(StockAdjustment.id == adjustment_id)
        )
    ).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Adjustment not found")
    return row
