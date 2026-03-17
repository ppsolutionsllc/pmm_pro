from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from sqlalchemy import func

from app.models.vehicle import Vehicle, FuelType
from app.models.request_item import RequestItem
from app.schemas.vehicle import VehicleCreate, VehicleUpdate

async def create_vehicle(
    db: AsyncSession,
    v_in: VehicleCreate,
    *,
    is_approved: bool = True,
    created_by: int | None = None,
):
    per_km = round(v_in.consumption_l_per_100km / 100.0, 6)
    v = Vehicle(
        department_id=v_in.department_id,
        name=v_in.brand,
        brand=v_in.brand,
        identifier=getattr(v_in, 'identifier', None),
        fuel_type=v_in.fuel_type,
        consumption_l_per_100km=v_in.consumption_l_per_100km,
        consumption_l_per_km=per_km,
        is_active=v_in.is_active,
        is_approved=is_approved,
        created_by=created_by,
    )
    db.add(v)
    await db.commit()
    await db.refresh(v)
    return v

async def get_vehicles(
    db: AsyncSession,
    *,
    department_id: int | None = None,
    only_approved: bool | None = None,
    only_active: bool | None = None,
    created_by: int | None = None,
):
    q = select(Vehicle)
    if department_id is not None:
        q = q.where(Vehicle.department_id == department_id)
    if only_approved is True:
        q = q.where(Vehicle.is_approved.is_(True))
    if only_active is True:
        q = q.where(Vehicle.is_active.is_(True))
    if created_by is not None:
        q = q.where(Vehicle.created_by == created_by)
    result = await db.execute(q)
    return result.scalars().all()

async def get_vehicle(db: AsyncSession, vid: int):
    result = await db.execute(select(Vehicle).where(Vehicle.id == vid))
    return result.scalars().first()

async def update_vehicle(db: AsyncSession, v_id: int, **kwargs):
    vals = dict(kwargs)
    if "fuel_type" in vals and vals.get("fuel_type") is not None:
        ft = vals.get("fuel_type")
        if isinstance(ft, str):
            try:
                vals["fuel_type"] = FuelType(ft)
            except Exception:
                # let DB validation handle if unknown
                pass
    if "consumption_l_per_100km" in vals and vals["consumption_l_per_100km"] is not None:
        vals["consumption_l_per_km"] = round(vals["consumption_l_per_100km"] / 100.0, 6)
    if "brand" in vals and vals.get("brand") is not None:
        vals["name"] = vals.get("brand")
    await db.execute(update(Vehicle).where(Vehicle.id == v_id).values(**vals))
    await db.commit()
    return await get_vehicle(db, v_id)


async def approve_vehicle(db: AsyncSession, vid: int):
    await db.execute(update(Vehicle).where(Vehicle.id == vid).values(is_approved=True))
    await db.commit()
    return await get_vehicle(db, vid)


async def delete_vehicle(db: AsyncSession, vid: int):
    res = await db.execute(select(Vehicle).where(Vehicle.id == vid))
    veh = res.scalars().first()
    if not veh:
        return None

    used_res = await db.execute(select(func.count(RequestItem.id)).where(RequestItem.vehicle_id == vid))
    used_count = used_res.scalar_one()
    if used_count and used_count > 0:
        raise ValueError("Vehicle is used in requests")

    await db.delete(veh)
    await db.commit()
    return True
