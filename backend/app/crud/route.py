import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError

from app.core.time import utcnow
from app.models.route import Route, RouteChangeRequest, RouteChangeStatus


def _json_points(points: list[str] | None) -> str:
    return json.dumps(points or [], ensure_ascii=False)


async def create_route(
    db: AsyncSession,
    *,
    department_id: int,
    name: str,
    points: list[str],
    distance_km: float,
    created_by: int | None,
    is_approved: bool,
):
    obj = Route(
        department_id=department_id,
        name=name,
        points_json=_json_points(points),
        distance_km=distance_km,
        created_by=created_by,
        is_approved=is_approved,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def list_routes(db: AsyncSession, *, department_id: int | None = None, only_approved: bool | None = None):
    q = select(Route)
    if department_id is not None:
        q = q.where(Route.department_id == department_id)
    if only_approved is True:
        q = q.where(Route.is_approved.is_(True))
    q = q.order_by(Route.created_at.desc())
    res = await db.execute(q)
    return res.scalars().all()


async def get_route(db: AsyncSession, rid: int):
    res = await db.execute(select(Route).where(Route.id == rid))
    return res.scalars().first()


async def set_route_approved(db: AsyncSession, *, route_id: int, is_approved: bool):
    await db.execute(update(Route).where(Route.id == route_id).values(is_approved=is_approved))
    await db.commit()
    return await get_route(db, route_id)


async def create_change_request(
    db: AsyncSession,
    *,
    route_id: int,
    department_id: int,
    requested_by: int,
    name: str | None = None,
    points: list[str] | None = None,
    distance_km: float | None = None,
):
    obj = RouteChangeRequest(
        route_id=route_id,
        department_id=department_id,
        requested_by=requested_by,
        status=RouteChangeStatus.PENDING.value,
        name=name,
        points_json=_json_points(points) if points is not None else None,
        distance_km=distance_km,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def list_change_requests(db: AsyncSession, *, status: str | None = None, department_id: int | None = None):
    q = select(RouteChangeRequest)
    if status is not None:
        q = q.where(RouteChangeRequest.status == status)
    if department_id is not None:
        q = q.where(RouteChangeRequest.department_id == department_id)
    q = q.order_by(RouteChangeRequest.created_at.desc())
    res = await db.execute(q)
    return res.scalars().all()


async def get_change_request(db: AsyncSession, req_id: int):
    res = await db.execute(select(RouteChangeRequest).where(RouteChangeRequest.id == req_id))
    return res.scalars().first()


async def decide_change_request(
    db: AsyncSession,
    *,
    req_id: int,
    status: str,
    decided_by: int,
):
    now = utcnow()
    await db.execute(
        update(RouteChangeRequest)
        .where(RouteChangeRequest.id == req_id)
        .values(status=status, decided_at=now, decided_by=decided_by)
    )
    await db.commit()
    return await get_change_request(db, req_id)


async def apply_change_to_route(db: AsyncSession, *, route_id: int, name: str | None, points_json: str | None, distance_km: float | None):
    vals = {}
    if name is not None:
        vals["name"] = name
    if points_json is not None:
        vals["points_json"] = points_json
    if distance_km is not None:
        vals["distance_km"] = distance_km
    if vals:
        await db.execute(update(Route).where(Route.id == route_id).values(**vals))
        await db.commit()
    return await get_route(db, route_id)


async def delete_route(db: AsyncSession, *, route_id: int):
    route = await get_route(db, route_id)
    if not route:
        return None

    await db.execute(delete(RouteChangeRequest).where(RouteChangeRequest.route_id == route_id))
    await db.delete(route)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    return route
