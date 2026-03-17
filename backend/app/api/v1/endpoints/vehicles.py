from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas import vehicle as schema_vehicle
from app.crud import vehicle as crud_vehicle
from app.api import deps

router = APIRouter()

@router.post("/vehicles", response_model=schema_vehicle.VehicleOut)
async def create_vehicle(
    v_in: schema_vehicle.VehicleCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "DEPT_USER"])),
):
    if current_user.role.value == "DEPT_USER":
        if current_user.department_id is None:
            raise HTTPException(status_code=400, detail="User has no department")
        # force department and create pending
        v_in = schema_vehicle.VehicleCreate(
            department_id=current_user.department_id,
            brand=v_in.brand,
            identifier=getattr(v_in, 'identifier', None),
            fuel_type=v_in.fuel_type,
            consumption_l_per_100km=v_in.consumption_l_per_100km,
            is_active=v_in.is_active,
        )
        return await crud_vehicle.create_vehicle(db, v_in, is_approved=False, created_by=current_user.id)
    # admin creates approved by default
    return await crud_vehicle.create_vehicle(db, v_in, is_approved=True, created_by=current_user.id)

@router.get("/vehicles", response_model=List[schema_vehicle.VehicleOut])
async def list_vehicles(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN","DEPT_USER","OPERATOR"])),
):
    if current_user.role.value == "ADMIN":
        return await crud_vehicle.get_vehicles(db)
    if current_user.department_id is None:
        return []
    if current_user.role.value == "OPERATOR":
        # OPERATOR: only approved in own department
        return await crud_vehicle.get_vehicles(db, department_id=current_user.department_id, only_approved=True, only_active=True)

    # DEPT_USER: approved + own pending submissions (still blocked from usage in requests)
    approved = await crud_vehicle.get_vehicles(db, department_id=current_user.department_id, only_approved=True, only_active=True)
    pending_mine = await crud_vehicle.get_vehicles(db, department_id=current_user.department_id, created_by=current_user.id)
    by_id = {v.id: v for v in (approved + pending_mine)}
    return list(by_id.values())

@router.patch("/vehicles/{vid}", response_model=schema_vehicle.VehicleOut)
async def update_vehicle(
    vid: int,
    v_in: schema_vehicle.VehicleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    veh = await crud_vehicle.get_vehicle(db, vid)
    if not veh:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    data = v_in.model_dump(exclude_unset=True)
    return await crud_vehicle.update_vehicle(db, vid, **data)


@router.post("/vehicles/{vid}/approve", response_model=schema_vehicle.VehicleOut)
async def approve_vehicle(
    vid: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    veh = await crud_vehicle.get_vehicle(db, vid)
    if not veh:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return await crud_vehicle.approve_vehicle(db, vid)


@router.delete("/vehicles/{vid}")
async def delete_vehicle(
    vid: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    try:
        ok = await crud_vehicle.delete_vehicle(db, vid)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return {"ok": True}
