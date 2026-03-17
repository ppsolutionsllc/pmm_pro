from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update

from app.models.stock import (
    StockReceipt,
    StockIssue,
    StockIssueStatus,
    StockLedger,
    StockBalance,
    FuelType as StockFuelType,
    RefType,
)
from app.models.request_item import RequestItem
from app.crud import settings as crud_settings
from app.core.time import utcnow


def _convert(fuel_type: StockFuelType, liters: float = None, kg: float = None):
    # helper to convert using density settings, not currently used
    raise NotImplementedError

async def create_stock_receipt(db: AsyncSession, fuel_type: StockFuelType, input_unit: str, input_amount: float, created_by: int = None):
    # compute other unit using density
    dens = await crud_settings.get_settings(db)
    if not dens:
        raise ValueError("Density settings not configured")
    if input_unit == "L":
        liters = input_amount
        factor = dens.density_factor_ab if fuel_type == StockFuelType.AB else dens.density_factor_dp
        kg = round(liters * factor, 2)
    else:
        kg = input_amount
        factor = dens.density_factor_ab if fuel_type == StockFuelType.AB else dens.density_factor_dp
        liters = round(kg / factor, 2)
    # record receipt
    receipt = StockReceipt(
        fuel_type=fuel_type,
        input_unit=input_unit,
        input_amount=input_amount,
        computed_liters=liters,
        computed_kg=kg,
        created_by=created_by,
    )
    db.add(receipt)
    # ledger plus
    ledger = StockLedger(
        fuel_type=fuel_type,
        delta_liters=liters,
        delta_kg=kg,
        ref_type=RefType.RECEIPT,
        ref_id=0,  # will update after flush
    )
    db.add(ledger)
    await db.commit()
    await db.refresh(receipt)
    # update the ledger ref_id now that receipt.id exists
    ledger.ref_id = receipt.id
    # update or create balance
    bal = await db.execute(select(StockBalance).where(StockBalance.fuel_type == fuel_type))
    bal = bal.scalars().first()
    if not bal:
        bal = StockBalance(fuel_type=fuel_type, balance_liters=liters, balance_kg=kg)
        db.add(bal)
    else:
        bal.balance_liters += liters
        bal.balance_kg += kg
    await db.commit()
    await db.refresh(receipt)
    return receipt

from sqlalchemy.orm import selectinload

async def create_issue_from_request(db: AsyncSession, req, *, commit: bool = True):
    # load items with vehicles to ensure data
    fresh = await db.execute(
        select(req.__class__).options(
            selectinload(req.__class__.items).selectinload(RequestItem.vehicle)
        ).where(req.__class__.id == req.id)
    )
    fresh_req = fresh.scalars().first()
    if not fresh_req or not fresh_req.items:
        raise ValueError("Request has no items")
    fuel_type = None
    total_liters = 0.0
    for item in fresh_req.items:
        if fuel_type is None:
            fuel_type = item.vehicle.fuel_type
        total_liters += item.required_liters
    if fuel_type is None:
        raise ValueError("Cannot determine fuel type")
    dens = await crud_settings.get_settings(db)
    if not dens:
        raise ValueError("Density settings not configured")
    factor = dens.density_factor_ab if fuel_type == StockFuelType.AB else dens.density_factor_dp
    issue_kg = round(total_liters * factor, 2)
    issue = StockIssue(
        request_id=req.id,
        issue_doc_no=f"PMM-LEGACY-{req.id}",
        status=StockIssueStatus.POSTED,
        posted_by=req.dept_confirmed_by,
        posted_at=utcnow(),
        has_debt=False,
        debt_liters=0.0,
        debt_kg=0.0,
        fuel_type=fuel_type,
        issue_liters=total_liters,
        issue_kg=issue_kg,
        created_by=req.dept_confirmed_by,
    )
    db.add(issue)
    # ledger minus
    ledger = StockLedger(
        fuel_type=fuel_type,
        delta_liters=-total_liters,
        delta_kg=-issue_kg,
        ref_type=RefType.ISSUE,
        ref_id=req.id,
    )
    db.add(ledger)
    # update balance
    bal = await db.execute(select(StockBalance).where(StockBalance.fuel_type == fuel_type))
    bal = bal.scalars().first()
    if not bal:
        bal = StockBalance(fuel_type=fuel_type, balance_liters=-total_liters, balance_kg=-issue_kg)
        db.add(bal)
    else:
        bal.balance_liters += -total_liters
        bal.balance_kg += -issue_kg
    if commit:
        await db.commit()
    return issue
