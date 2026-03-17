from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete

from app.models.planned_activity import PlannedActivity


async def list_activities(db: AsyncSession, *, only_active: bool | None = None):
    q = select(PlannedActivity)
    if only_active is True:
        q = q.where(PlannedActivity.is_active == True)  # noqa: E712
    q = q.order_by(PlannedActivity.id.desc())
    res = await db.execute(q)
    return res.scalars().all()


async def get_activity(db: AsyncSession, activity_id: int):
    res = await db.execute(select(PlannedActivity).where(PlannedActivity.id == activity_id))
    return res.scalars().first()


async def create_activity(db: AsyncSession, *, name: str, is_active: bool = True):
    obj = PlannedActivity(name=name, is_active=is_active)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def update_activity(db: AsyncSession, activity_id: int, *, name: str | None = None, is_active: bool | None = None):
    values = {}
    if name is not None:
        values["name"] = name
    if is_active is not None:
        values["is_active"] = is_active
    if values:
        await db.execute(update(PlannedActivity).where(PlannedActivity.id == activity_id).values(**values))
        await db.commit()
    return await get_activity(db, activity_id)


async def delete_activity(db: AsyncSession, activity_id: int):
    await db.execute(delete(PlannedActivity).where(PlannedActivity.id == activity_id))
    await db.commit()
    return True
