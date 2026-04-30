from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete, update
from sqlalchemy import func

from app.models.user import User
from app.core.security import get_password_hash, verify_password, needs_password_rehash
from app.schemas.user import UserCreate, RoleEnum

async def get_user_by_login(db: AsyncSession, login: str):
    normalized = str(login or "").strip().lower()
    result = await db.execute(select(User).where(func.lower(User.login) == normalized))
    return result.scalars().first()


async def get_user(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()

async def create_user(db: AsyncSession, user_in: UserCreate):
    hashed = get_password_hash(user_in.password)
    db_obj = User(
        login=user_in.login,
        hashed_password=hashed,
        full_name=user_in.full_name,
        phone=user_in.phone,
        rank=getattr(user_in, 'rank', None),
        position=getattr(user_in, 'position', None),
        is_active=user_in.is_active,
        role=user_in.role,
        department_id=user_in.department_id,
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def authenticate(db: AsyncSession, login: str, password: str):
    user = await get_user_by_login(db, login)
    if not user or not verify_password(password, user.hashed_password):
        return None
    if needs_password_rehash(user.hashed_password):
        user.hashed_password = get_password_hash(password)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user

async def update_user(db: AsyncSession, user_id: int, **kwargs):
    await db.execute(update(User).where(User.id == user_id).values(**kwargs))
    await db.commit()
    return await get_user(db, user_id)


async def delete_user(db: AsyncSession, user_id: int):
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()
