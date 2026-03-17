from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from app.config import settings
from app.db.session import async_session
from app.models.background_job import BackgroundJob, BackgroundJobStatus, BackgroundJobType
from app.services import job_service

logger = logging.getLogger("app.updater")


async def _next_system_update_job_id() -> str | None:
    async with async_session() as db:
        row = (
            await db.execute(
                select(BackgroundJob.id)
                .where(
                    BackgroundJob.type == BackgroundJobType.SYSTEM_UPDATE,
                    BackgroundJob.status == BackgroundJobStatus.QUEUED,
                )
                .order_by(BackgroundJob.created_at.asc())
                .limit(1)
            )
        ).scalars().first()
        return row


async def run_updater_loop() -> None:
    if not settings.updater_mode:
        raise RuntimeError("Updater loop requires UPDATER_MODE=true")
    interval = max(int(settings.updater_poll_interval_seconds or 5), 1)
    logger.info("Updater loop started; poll interval=%ss", interval)
    while True:
        try:
            job_id = await _next_system_update_job_id()
            if job_id:
                logger.info("Processing SYSTEM_UPDATE job %s", job_id)
                await job_service.run_background_job(job_id)
                continue
        except Exception:
            logger.exception("Updater loop iteration failed")
        await asyncio.sleep(interval)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    asyncio.run(run_updater_loop())
