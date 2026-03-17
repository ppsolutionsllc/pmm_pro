from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

from app.config import settings
from app.core.time import utcnow
from app.db.session import async_session
from app.models.admin_incident import IncidentSeverity, IncidentType
from app.services import backup_service, incident_service


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


async def run_auto_backup_once() -> dict[str, Any]:
    async with async_session() as db:
        config = await backup_service.get_backup_runtime_config(db)

    enabled = bool(config.get("schedule_enabled"))
    if not enabled:
        return {"ok": True, "skipped": "disabled"}

    interval_hours = max(int(config.get("schedule_interval_hours") or 24), 1)
    rotation_keep = max(int(config.get("rotation_keep") or settings.backup_retention_count), 1)
    last_run = _parse_iso(config.get("last_auto_backup_at"))
    now = utcnow()
    if last_run and now - last_run < timedelta(hours=interval_hours):
        return {"ok": True, "skipped": "not_due"}

    try:
        result = await asyncio.to_thread(
            backup_service.create_backup,
            keep_count=rotation_keep,
            name_prefix="pmm_auto",
        )
    except Exception as exc:
        message = str(exc)
        # concurrent manual/auto operation is an expected race, not an incident
        if "already in progress" in message.lower():
            return {"ok": True, "skipped": "busy"}
        async with async_session() as db:
            async with db.begin():
                await incident_service.create_incident(
                    db,
                    incident_type=IncidentType.BACKUP_FAILED,
                    severity=IncidentSeverity.HIGH,
                    message=f"Auto backup failed: {message}",
                    details_json={"operation": "auto_backup", "error": message},
                    created_by=None,
                )
        return {"ok": False, "error": message}

    async with async_session() as db:
        await backup_service.set_last_auto_backup_meta(db, backup_filename=str(result.get("filename") or ""))

    return {"ok": True, "created": result}


async def auto_backup_loop() -> None:
    # Startup grace period so DB/app migrations finish first
    await asyncio.sleep(20)
    while True:
        await run_auto_backup_once()
        await asyncio.sleep(60)
