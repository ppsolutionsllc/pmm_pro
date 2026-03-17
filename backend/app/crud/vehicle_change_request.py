from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update

from app.core.time import utcnow
from app.models.vehicle_change_request import VehicleChangeRequest, VehicleChangeStatus


async def create_change_request(
    db: AsyncSession,
    *,
    vehicle_id: int,
    department_id: int,
    requested_by: int,
    brand: str | None = None,
    identifier: str | None = None,
    fuel_type: str | None = None,
    consumption_l_per_100km: float | None = None,
):
    obj = VehicleChangeRequest(
        vehicle_id=vehicle_id,
        department_id=department_id,
        requested_by=requested_by,
        status=VehicleChangeStatus.PENDING,
        brand=brand,
        identifier=identifier,
        fuel_type=fuel_type,
        consumption_l_per_100km=consumption_l_per_100km,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def list_change_requests(
    db: AsyncSession,
    *,
    status: VehicleChangeStatus | None = None,
    department_id: int | None = None,
):
    q = select(VehicleChangeRequest)
    if status is not None:
        q = q.where(VehicleChangeRequest.status == status)
    if department_id is not None:
        q = q.where(VehicleChangeRequest.department_id == department_id)
    q = q.order_by(VehicleChangeRequest.created_at.desc())
    res = await db.execute(q)
    return res.scalars().all()


async def list_pending_for_vehicle_ids(db: AsyncSession, *, vehicle_ids: list[int]):
    if not vehicle_ids:
        return []
    q = (
        select(VehicleChangeRequest)
        .where(VehicleChangeRequest.vehicle_id.in_(vehicle_ids))
        .where(VehicleChangeRequest.status == VehicleChangeStatus.PENDING)
        .order_by(VehicleChangeRequest.created_at.desc())
    )
    res = await db.execute(q)
    return res.scalars().all()


async def get_change_request(db: AsyncSession, req_id: int):
    res = await db.execute(select(VehicleChangeRequest).where(VehicleChangeRequest.id == req_id))
    return res.scalars().first()


async def set_status(
    db: AsyncSession,
    *,
    req_id: int,
    status: VehicleChangeStatus,
    decided_by: int,
):
    now = utcnow()
    await db.execute(
        update(VehicleChangeRequest)
        .where(VehicleChangeRequest.id == req_id)
        .values(status=status, decided_at=now, decided_by=decided_by)
    )
    await db.commit()
    return await get_change_request(db, req_id)
