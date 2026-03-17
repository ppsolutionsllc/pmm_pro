from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from sqlalchemy.orm import selectinload

from app.core.time import utcnow
from app.models.request import Request, RequestStatus
from app.models.request_item import RequestItem
from app.models.vehicle import Vehicle
from app.models.stock import FuelType as StockFuelType
from app.models.planned_activity import PlannedActivity
from app.crud import route as crud_route

async def create_request(
    db: AsyncSession,
    dept_id: int,
    created_by: int,
    *,
    route_id: int | None = None,
    route_is_manual: bool = False,
    route_text: str | None = None,
    distance_km_per_trip: float | None = None,
    justification_text: str | None = None,
    persons_involved_count: int = 0,
    training_days_count: int = 0,
):
    num = f"REQ-{utcnow().strftime('%Y%m%d%H%M%S%f')}"
    req = Request(
        request_number=num,
        department_id=dept_id,
        status=RequestStatus.DRAFT,
        route_id=route_id,
        route_is_manual=route_is_manual,
        route_text=route_text,
        distance_km_per_trip=distance_km_per_trip,
        justification_text=justification_text,
        persons_involved_count=persons_involved_count,
        training_days_count=training_days_count,
        created_by=created_by,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req

async def get_request(db: AsyncSession, request_id: int):
    result = await db.execute(
        select(Request)
        .options(selectinload(Request.planned_activities))
        .where(Request.id == request_id)
    )
    return result.scalars().first()

async def get_requests(db: AsyncSession):
    result = await db.execute(select(Request))
    return result.scalars().all()

async def add_item(
    db: AsyncSession,
    request_id: int,
    *,
    planned_activity_id: int | None = None,
    vehicle_id: int,
    route_id: int | None = None,
    route_is_manual: bool = False,
    route_text: str | None = None,
    distance_km_per_trip: float | None = None,
    justification_text: str | None = None,
    persons_involved_count: int | None = None,
    training_days_count: int | None = None,
):
    req = await get_request(db, request_id)
    if not req:
        raise ValueError("Request not found")

    effective_training_days = int(
        training_days_count if training_days_count is not None else (req.training_days_count or 0)
    )
    if effective_training_days <= 0:
        raise ValueError("Training days count must be > 0")

    # Resolve route (pending routes allowed, only department ownership is checked)
    if route_id is not None:
        route = await crud_route.get_route(db, route_id)
        if not route:
            raise ValueError("Route not found")
        if route.department_id != req.department_id:
            raise ValueError("Route belongs to another department")
        route_is_manual = False
        pts = route.get_points()
        route_text = " — ".join([p for p in pts if p]) or route.name
        if distance_km_per_trip is None and getattr(route, 'distance_km', None) is not None:
            distance_km_per_trip = route.distance_km
    elif route_is_manual:
        if not route_text:
            raise ValueError("Manual route text required")

    if distance_km_per_trip is None:
        raise ValueError("Distance must be set")
    if distance_km_per_trip <= 0:
        raise ValueError("Distance must be > 0")

    if planned_activity_id is None:
        raise ValueError("Planned activity must be selected")
    res_pa = await db.execute(select(PlannedActivity).where(PlannedActivity.id == planned_activity_id))
    pa = res_pa.scalars().first()
    if not pa:
        raise ValueError("Planned activity not found")

    res = await db.execute(select(Vehicle).where(Vehicle.id == vehicle_id))
    vehicle = res.scalars().first()
    if not vehicle:
        raise ValueError("Vehicle not found")
    if not vehicle.is_active:
        raise ValueError("Vehicle is inactive")
    if not getattr(vehicle, 'is_approved', True):
        raise ValueError("Vehicle is not approved")
    if vehicle.department_id != req.department_id:
        raise ValueError("Vehicle belongs to another department")

    total_km = distance_km_per_trip * effective_training_days
    liters = total_km * vehicle.consumption_l_per_km
    # compute kg snapshot using density settings
    from app.crud import settings as crud_settings
    dens = await crud_settings.get_settings(db)
    if not dens:
        raise ValueError("Density settings not configured")
    factor = dens.density_factor_ab if vehicle.fuel_type == StockFuelType.AB else dens.density_factor_dp
    kg = round(liters * factor, 2)

    item = RequestItem(
        request_id=request_id,
        planned_activity_id=planned_activity_id,
        vehicle_id=vehicle_id,
        route_id=route_id,
        route_is_manual=bool(route_is_manual),
        route_text=route_text,
        distance_km_per_trip=distance_km_per_trip,
        justification_text=justification_text,
        persons_involved_count=persons_involved_count,
        training_days_count=effective_training_days,
        consumption_l_per_km_snapshot=vehicle.consumption_l_per_km,
        total_km=total_km,
        required_liters=liters,
        required_kg=kg,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

async def update_status(
    db: AsyncSession,
    request_id: int,
    status: RequestStatus,
    user_id: int,
    *,
    commit: bool = True,
):
    values = {"status": status}
    now = utcnow()
    if status == RequestStatus.SUBMITTED:
        values.update({"submitted_at": now, "submitted_by": user_id, "is_rejected": False, "rejection_comment": None, "rejected_at": None, "rejected_by": None})
    elif status == RequestStatus.APPROVED:
        values.update({"approved_at": now, "approved_by": user_id})
    elif status == RequestStatus.ISSUED_BY_OPERATOR:
        values.update({"operator_issued_at": now, "operator_issued_by": user_id})
    elif status == RequestStatus.POSTED:
        values.update({"dept_confirmed_at": now, "dept_confirmed_by": user_id, "stock_posted_at": now, "stock_posted_by": user_id})
    await db.execute(update(Request).where(Request.id == request_id).values(**values))
    if commit:
        await db.commit()
    return await get_request(db, request_id)


async def reject_request(db: AsyncSession, request_id: int, comment: str, admin_user_id: int):
    req = await get_request(db, request_id)
    if not req:
        raise ValueError("Request not found")
    if req.status != RequestStatus.SUBMITTED:
        raise ValueError("Can only reject submitted requests")
    if not comment or not str(comment).strip():
        raise ValueError("Rejection comment required")

    now = utcnow()
    await db.execute(
        update(Request)
        .where(Request.id == request_id)
        .values(
            status=RequestStatus.DRAFT,
            is_rejected=True,
            rejection_comment=str(comment).strip(),
            rejected_at=now,
            rejected_by=admin_user_id,
        )
    )
    await db.commit()
    return await get_request(db, request_id)


async def set_planned_activities(db: AsyncSession, request_id: int, activity_ids: list[int]):
    req = await get_request(db, request_id)
    if not req:
        raise ValueError("Request not found")

    ids = [int(x) for x in (activity_ids or [])]
    if len(set(ids)) != len(ids):
        ids = list(dict.fromkeys(ids))

    activities = []
    if ids:
        res = await db.execute(select(PlannedActivity).where(PlannedActivity.id.in_(ids)))
        activities = res.scalars().all()
        if len(activities) != len(ids):
            found = {a.id for a in activities}
            missing = [i for i in ids if i not in found]
            raise ValueError(f"Planned activity not found: {missing}")

    req.planned_activities = activities
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req
