from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas import department as schema_dept
from app.crud import department as crud_dept
from app.crud import department_print_signature as crud_dept_signature
from app.api import deps

router = APIRouter()

@router.post("/departments", response_model=schema_dept.DepartmentOut)
async def create_department(
    dept_in: schema_dept.DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    return await crud_dept.create_department(db, dept_in)

@router.get("/departments", response_model=List[schema_dept.DepartmentOut])
async def list_departments(
    include_deleted: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN","DEPT_USER","OPERATOR"])),
):
    effective_include_deleted = include_deleted if current_user.role.value == "ADMIN" else False
    return await crud_dept.get_departments(db, include_deleted=effective_include_deleted)


@router.get("/departments/me/print-signatures", response_model=schema_dept.DepartmentPrintSignatureOut)
async def get_my_department_print_signatures(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("DEPT_USER")),
):
    if not current_user.department_id:
        raise HTTPException(status_code=400, detail="Користувач не прив'язаний до підрозділу")
    row = await crud_dept_signature.get_or_create_for_department(
        db,
        department_id=current_user.department_id,
        actor_user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(row)
    return row


@router.put("/departments/me/print-signatures", response_model=schema_dept.DepartmentPrintSignatureOut)
async def set_my_department_print_signatures(
    payload: schema_dept.DepartmentPrintSignatureDeptUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("DEPT_USER")),
):
    if not current_user.department_id:
        raise HTTPException(status_code=400, detail="Користувач не прив'язаний до підрозділу")
    current_row = await crud_dept_signature.get_or_create_for_department(
        db,
        department_id=current_user.department_id,
        actor_user_id=current_user.id,
    )
    row = await crud_dept_signature.upsert_for_department(
        db,
        department_id=current_user.department_id,
        data={
            "approval_title": payload.approval_title,
            "approval_rank": payload.approval_rank,
            "approval_position": payload.approval_position,
            "approval_name": payload.approval_name,
            "agreed_title": current_row.agreed_title,
            "agreed_rank": current_row.agreed_rank,
            "agreed_position": current_row.agreed_position,
            "agreed_name": current_row.agreed_name,
        },
        actor_user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(row)
    return row


@router.get("/departments/{dept_id}", response_model=schema_dept.DepartmentOut)
async def get_department(
    dept_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "DEPT_USER", "OPERATOR"])),
):
    dept = await crud_dept.get_department(db, dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    if current_user.role.value != "ADMIN" and current_user.department_id != dept_id:
        raise HTTPException(status_code=403, detail="Operation not permitted")
    return dept


@router.get("/departments/{dept_id}/print-signatures", response_model=schema_dept.DepartmentPrintSignatureOut)
async def get_department_print_signatures(
    dept_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    dept = await crud_dept.get_department(db, dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    row = await crud_dept_signature.get_or_create_for_department(
        db,
        department_id=dept_id,
        actor_user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(row)
    return row


@router.put("/departments/{dept_id}/print-signatures", response_model=schema_dept.DepartmentPrintSignatureOut)
async def set_department_print_signatures(
    dept_id: int,
    payload: schema_dept.DepartmentPrintSignatureAdminUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    dept = await crud_dept.get_department(db, dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    current_row = await crud_dept_signature.get_or_create_for_department(
        db,
        department_id=dept_id,
        actor_user_id=current_user.id,
    )
    row = await crud_dept_signature.upsert_for_department(
        db,
        department_id=dept_id,
        data={
            "approval_title": current_row.approval_title,
            "approval_rank": current_row.approval_rank,
            "approval_position": current_row.approval_position,
            "approval_name": current_row.approval_name,
            "agreed_title": payload.agreed_title,
            "agreed_rank": payload.agreed_rank,
            "agreed_position": payload.agreed_position,
            "agreed_name": payload.agreed_name,
        },
        actor_user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(row)
    return row


@router.patch("/departments/{dept_id}", response_model=schema_dept.DepartmentOut)
async def update_department(
    dept_id: int,
    dept_in: schema_dept.DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    dept = await crud_dept.get_department(db, dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return await crud_dept.update_department(db, dept_id, **dept_in.model_dump(exclude_none=True))


@router.delete("/departments/{dept_id}", response_model=schema_dept.DepartmentOut)
async def delete_department(
    dept_id: int,
    payload: schema_dept.DepartmentDeleteIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    dept = await crud_dept.get_department(db, dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    if dept.is_deleted:
        return dept
    try:
        return await crud_dept.soft_delete_department(
            db,
            dept_id=dept_id,
            reason=payload.reason,
            actor_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
