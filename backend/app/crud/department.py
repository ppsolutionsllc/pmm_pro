from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from sqlalchemy.orm import selectinload

from app.core.time import utcnow
from app.models.department import Department
from app.models.route import Route
from app.models.user import RoleEnum, User
from app.models.vehicle import Vehicle
from app.schemas.department import DepartmentCreate

DELETED_PREFIX = "[ВИДАЛЕНО] "


async def get_department(db: AsyncSession, dept_id: int):
    result = await db.execute(
        select(Department)
        .options(selectinload(Department.users), selectinload(Department.vehicles))
        .where(Department.id == dept_id)
    )
    return result.scalars().first()


async def get_departments(db: AsyncSession, *, include_deleted: bool = True):
    q = select(Department)
    if not include_deleted:
        q = q.where(Department.is_deleted.is_(False))
    result = await db.execute(q.order_by(Department.id.asc()))
    return result.scalars().all()


async def create_department(db: AsyncSession, dept_in: DepartmentCreate):
    dept = Department(name=dept_in.name, is_active=dept_in.is_active)
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return dept


async def update_department(db: AsyncSession, dept_id: int, **kwargs):
    await db.execute(update(Department).where(Department.id == dept_id).values(**kwargs))
    await db.commit()
    return await get_department(db, dept_id)


async def soft_delete_department(
    db: AsyncSession,
    *,
    dept_id: int,
    reason: str,
    actor_user_id: int,
) -> Department:
    dept = (
        await db.execute(
            select(Department)
            .options(selectinload(Department.users), selectinload(Department.vehicles))
            .where(Department.id == dept_id)
            .with_for_update()
        )
    ).scalars().first()
    if not dept:
        raise ValueError("Department not found")
    if dept.is_deleted:
        return dept

    now = utcnow()
    clean_reason = str(reason or "").strip()
    if not clean_reason:
        raise ValueError("Reason is required")

    if not str(dept.name).startswith(DELETED_PREFIX):
        dept.name = f"{DELETED_PREFIX}{dept.name}"
    dept.is_deleted = True
    dept.is_active = False
    dept.deleted_at = now
    dept.deleted_by = actor_user_id
    dept.deletion_reason = clean_reason
    dept.updated_at = now

    await db.execute(
        update(User)
        .where(
            User.department_id == dept_id,
            User.role == RoleEnum.DEPT_USER,
        )
        .values(is_active=False)
    )
    await db.execute(
        update(Vehicle)
        .where(Vehicle.department_id == dept_id)
        .values(is_active=False)
    )
    await db.execute(
        update(Route)
        .where(Route.department_id == dept_id)
        .values(is_approved=False)
    )

    await db.commit()
    await db.refresh(dept)
    return dept
