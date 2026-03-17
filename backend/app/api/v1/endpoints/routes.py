import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.crud import route as crud_route
from app.schemas import route as schema_route

router = APIRouter()


def _route_out(r):
    return {
        "id": r.id,
        "department_id": r.department_id,
        "name": r.name,
        "points": r.get_points(),
        "distance_km": getattr(r, 'distance_km', 0.0),
        "is_approved": r.is_approved,
        "created_at": r.created_at,
        "created_by": r.created_by,
    }


def _change_out(r):
    return {
        "id": r.id,
        "route_id": r.route_id,
        "department_id": r.department_id,
        "requested_by": r.requested_by,
        "status": r.status,
        "name": r.name,
        "points": r.get_points() if r.points_json is not None else None,
        "distance_km": getattr(r, 'distance_km', None),
        "created_at": r.created_at,
        "decided_at": r.decided_at,
        "decided_by": r.decided_by,
    }


@router.get("/routes", response_model=List[schema_route.RouteOut])
async def list_routes(
    department_id: Optional[int] = Query(None),
    only_approved: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "DEPT_USER"])),
):
    if current_user.role.value == "DEPT_USER":
        department_id = current_user.department_id
    routes = await crud_route.list_routes(db, department_id=department_id, only_approved=only_approved)
    return [_route_out(r) for r in routes]


@router.post("/routes", response_model=schema_route.RouteOut)
async def create_route(
    data: schema_route.RouteCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "DEPT_USER"])),
):
    if current_user.role.value == "DEPT_USER":
        if current_user.department_id != data.department_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        is_approved = False
    else:
        is_approved = True

    obj = await crud_route.create_route(
        db,
        department_id=data.department_id,
        name=data.name,
        points=data.points,
        distance_km=data.distance_km,
        created_by=current_user.id,
        is_approved=is_approved,
    )
    return _route_out(obj)


@router.post("/routes/{rid}/approve", response_model=schema_route.RouteOut)
async def approve_route(
    rid: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    route = await crud_route.get_route(db, rid)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    updated = await crud_route.set_route_approved(db, route_id=rid, is_approved=True)
    return _route_out(updated)


@router.post("/routes/{rid}/reject", response_model=schema_route.RouteOut)
async def reject_route(
    rid: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    route = await crud_route.get_route(db, rid)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    updated = await crud_route.set_route_approved(db, route_id=rid, is_approved=False)
    return _route_out(updated)


@router.post("/routes/{rid}/change-requests", response_model=schema_route.RouteChangeRequestOut)
async def create_route_change_request(
    rid: int,
    data: schema_route.RouteChangeRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("DEPT_USER")),
):
    route = await crud_route.get_route(db, rid)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    if route.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    obj = await crud_route.create_change_request(
        db,
        route_id=rid,
        department_id=current_user.department_id,
        requested_by=current_user.id,
        name=data.name,
        points=data.points,
        distance_km=data.distance_km,
    )
    return _change_out(obj)


@router.get("/route-change-requests", response_model=List[schema_route.RouteChangeRequestOut])
async def list_route_change_requests(
    status: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "DEPT_USER"])),
):
    if current_user.role.value == "DEPT_USER":
        department_id = current_user.department_id
    reqs = await crud_route.list_change_requests(db, status=status, department_id=department_id)
    return [_change_out(r) for r in reqs]


@router.post("/route-change-requests/{req_id}/approve", response_model=schema_route.RouteChangeRequestOut)
async def approve_route_change_request(
    req_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    user_id = current_user.id
    req = await crud_route.get_change_request(db, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Change request not found")
    if req.status != schema_route.RouteChangeStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Already decided")

    await crud_route.apply_change_to_route(db, route_id=req.route_id, name=req.name, points_json=req.points_json, distance_km=req.distance_km)
    await crud_route.decide_change_request(db, req_id=req_id, status=schema_route.RouteChangeStatus.APPROVED.value, decided_by=user_id)
    updated = await crud_route.get_change_request(db, req_id)
    return _change_out(updated)


@router.post("/route-change-requests/{req_id}/reject", response_model=schema_route.RouteChangeRequestOut)
async def reject_route_change_request(
    req_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    user_id = current_user.id
    req = await crud_route.get_change_request(db, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Change request not found")
    if req.status != schema_route.RouteChangeStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Already decided")

    await crud_route.decide_change_request(db, req_id=req_id, status=schema_route.RouteChangeStatus.REJECTED.value, decided_by=user_id)
    updated = await crud_route.get_change_request(db, req_id)
    return _change_out(updated)
