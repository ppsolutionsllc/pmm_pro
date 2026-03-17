from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.crud import vehicle as crud_vehicle
from app.crud import vehicle_change_request as crud_vcr
from app.db.session import get_db
from app.schemas import vehicle_change_request as schema_vcr
from app.models.vehicle_change_request import VehicleChangeStatus as ModelVehicleChangeStatus

router = APIRouter()


@router.post(
    "/vehicles/{vid}/change-requests",
    response_model=schema_vcr.VehicleChangeRequestOut,
)
async def create_vehicle_change_request(
    vid: int,
    data: schema_vcr.VehicleChangeRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("DEPT_USER")),
):
    if current_user.department_id is None:
        raise HTTPException(status_code=400, detail="User has no department")

    veh = await crud_vehicle.get_vehicle(db, vid)
    if not veh:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if veh.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return await crud_vcr.create_change_request(
        db,
        vehicle_id=vid,
        department_id=current_user.department_id,
        requested_by=current_user.id,
        brand=data.brand,
        identifier=data.identifier,
        fuel_type=data.fuel_type,
        consumption_l_per_100km=data.consumption_l_per_100km,
    )


@router.get(
    "/vehicle-change-requests",
    response_model=List[schema_vcr.VehicleChangeRequestOut],
)
async def list_vehicle_change_requests(
    status: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "DEPT_USER"])),
):
    st = None
    if status:
        try:
            st = ModelVehicleChangeStatus(status)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid status")

    if current_user.role.value == "DEPT_USER":
        if current_user.department_id is None:
            return []
        department_id = current_user.department_id

    return await crud_vcr.list_change_requests(db, status=st, department_id=department_id)


@router.post(
    "/vehicle-change-requests/{req_id}/approve",
    response_model=schema_vcr.VehicleChangeRequestOut,
)
async def approve_vehicle_change_request(
    req_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    user_id = current_user.id
    req = await crud_vcr.get_change_request(db, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Change request not found")
    if req.status != ModelVehicleChangeStatus.PENDING:
        raise HTTPException(status_code=400, detail="Already decided")

    updates = {}
    if req.brand is not None:
        updates["brand"] = req.brand
    if req.identifier is not None:
        updates["identifier"] = req.identifier
    if req.fuel_type is not None:
        updates["fuel_type"] = req.fuel_type
    if req.consumption_l_per_100km is not None:
        updates["consumption_l_per_100km"] = req.consumption_l_per_100km

    if updates:
        await crud_vehicle.update_vehicle(db, req.vehicle_id, **updates)

    await crud_vcr.set_status(db, req_id=req_id, status=ModelVehicleChangeStatus.APPROVED, decided_by=user_id)
    return await crud_vcr.get_change_request(db, req_id)


@router.post(
    "/vehicle-change-requests/{req_id}/reject",
    response_model=schema_vcr.VehicleChangeRequestOut,
)
async def reject_vehicle_change_request(
    req_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    user_id = current_user.id
    req = await crud_vcr.get_change_request(db, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Change request not found")
    if req.status != ModelVehicleChangeStatus.PENDING:
        raise HTTPException(status_code=400, detail="Already decided")

    await crud_vcr.set_status(db, req_id=req_id, status=ModelVehicleChangeStatus.REJECTED, decided_by=user_id)
    return await crud_vcr.get_change_request(db, req_id)
