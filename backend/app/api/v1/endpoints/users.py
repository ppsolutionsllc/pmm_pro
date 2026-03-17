from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas import user as schema_user
from app.crud import user as crud_user
from app.crud import department as crud_department
from app.api import deps
from sqlalchemy.future import select
from app.models.user import User

router = APIRouter()

@router.post("/users", response_model=schema_user.UserOut)
async def create_user(
    user_in: schema_user.UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    if user_in.role == schema_user.RoleEnum.OPERATOR:
        # Operator is global by business rule and must not be tied to a department.
        user_in.department_id = None
    existing = await crud_user.get_user_by_login(db, user_in.login)
    if existing:
        raise HTTPException(status_code=400, detail="Login already registered")
    if user_in.department_id is not None:
        dept = await crud_department.get_department(db, user_in.department_id)
        if not dept or dept.is_deleted or not dept.is_active:
            raise HTTPException(status_code=400, detail="Підрозділ деактивовано або видалено")
    return await crud_user.create_user(db, user_in)

@router.get("/users", response_model=List[schema_user.UserOut])
async def list_users(
    role: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    q = select(User)
    if role:
        q = q.where(User.role == role)
    if department_id is not None:
        q = q.where(User.department_id == department_id)
    result = await db.execute(q)
    return result.scalars().all()

@router.get("/users/{user_id}", response_model=schema_user.UserOut)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    user = await crud_user.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.patch("/users/{user_id}", response_model=schema_user.UserOut)
async def update_user(
    user_id: int,
    user_in: schema_user.UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    user = await crud_user.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    update_data = user_in.model_dump(exclude_none=True)
    if "password" in update_data and update_data["password"]:
        from app.core.security import get_password_hash
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    else:
        update_data.pop("password", None)
    return await crud_user.update_user(db, user_id, **update_data)
