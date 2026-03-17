from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update

from app.models.app_settings import AppSettings


async def get_setting(db: AsyncSession, key: str) -> str | None:
    result = await db.execute(select(AppSettings).where(AppSettings.key == key))
    row = result.scalars().first()
    return row.value if row else None


async def set_setting(db: AsyncSession, key: str, value: str | None):
    result = await db.execute(select(AppSettings).where(AppSettings.key == key))
    existing = result.scalars().first()
    if existing:
        existing.value = value
    else:
        db.add(AppSettings(key=key, value=value))
    await db.commit()


async def get_settings_dict(db: AsyncSession, prefix: str) -> dict:
    result = await db.execute(select(AppSettings).where(AppSettings.key.like(f"{prefix}%")))
    rows = result.scalars().all()
    return {r.key.replace(f"{prefix}.", ""): r.value for r in rows}


async def set_settings_dict(db: AsyncSession, prefix: str, data: dict):
    for k, v in data.items():
        full_key = f"{prefix}.{k}"
        await set_setting(db, full_key, str(v) if v is not None else None)
