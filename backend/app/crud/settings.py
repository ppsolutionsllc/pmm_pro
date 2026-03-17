from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update

from app.core.time import utcnow
from app.models.fuel_coeff_history import FuelCoeffHistory
from app.models.settings import DensitySettings
from app.models.stock import FuelType
from app.schemas.settings import DensitySettingsBase

async def get_settings(db: AsyncSession):
    result = await db.execute(select(DensitySettings))
    return result.scalars().first()

async def list_coeff_history(db: AsyncSession, limit: int = 200):
    result = await db.execute(
        select(FuelCoeffHistory).order_by(FuelCoeffHistory.changed_at.desc()).limit(limit)
    )
    return result.scalars().all()


async def create_or_update_settings(
    db: AsyncSession,
    data: DensitySettingsBase,
    *,
    changed_by: int | None = None,
    comment: str | None = None,
):
    existing = await get_settings(db)
    old_ab = float(existing.density_factor_ab) if existing else None
    old_dp = float(existing.density_factor_dp) if existing else None
    if existing:
        await db.execute(
            update(DensitySettings)
            .where(DensitySettings.id == existing.id)
            .values(
                density_factor_ab=data.density_factor_ab,
                density_factor_dp=data.density_factor_dp,
            )
        )
        out = await get_settings(db)
    else:
        obj = DensitySettings(
            density_factor_ab=data.density_factor_ab,
            density_factor_dp=data.density_factor_dp,
        )
        db.add(obj)
        await db.flush()
        out = obj

    new_ab = float(data.density_factor_ab)
    new_dp = float(data.density_factor_dp)
    if old_ab is None or old_ab != new_ab:
        db.add(
            FuelCoeffHistory(
                fuel_type=FuelType.AB,
                density_kg_per_l=new_ab,
                changed_by=changed_by,
                changed_at=utcnow(),
                comment=comment,
            )
        )
    if old_dp is None or old_dp != new_dp:
        db.add(
            FuelCoeffHistory(
                fuel_type=FuelType.DP,
                density_kg_per_l=new_dp,
                changed_by=changed_by,
                changed_at=utcnow(),
                comment=comment,
            )
        )

    await db.commit()
    if existing:
        return await get_settings(db)
    await db.refresh(out)
    return out
