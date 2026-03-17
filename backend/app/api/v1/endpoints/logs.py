from pathlib import Path
import json

from fastapi import APIRouter, Response, Depends, File, UploadFile, HTTPException, Query, Form
from fastapi.responses import FileResponse
from sqlalchemy import select, text, update
from pydantic import BaseModel, Field

from app import main as app_module
from app.api import deps
from app.config import settings
from app.core.time import utcnow
from app.db.session import async_session
from app import models
from app.services import backup_service
from app.services import incident_service
from app.models.admin_incident import IncidentSeverity, IncidentType

router = APIRouter()


class BackupRuntimeConfigPayload(BaseModel):
    schedule_enabled: bool = False
    schedule_interval_hours: int = Field(24, ge=1, le=720)
    rotation_keep: int = Field(10, ge=1, le=1000)


class BackupRestorePayload(BaseModel):
    confirm: str = ""


async def _record_legacy_json_backup_disabled_attempt(*, user_id: int | None, endpoint: str) -> None:
    async with async_session() as session:
        async with session.begin():
            await incident_service.create_incident(
                session,
                incident_type=IncidentType.SECURITY_ALERT,
                severity=IncidentSeverity.HIGH,
                message="Blocked attempt to use legacy JSON backup endpoint while disabled",
                details_json={"endpoint": endpoint, "reason": "ENABLE_LEGACY_JSON_RESTORE=false"},
                created_by=user_id,
            )


@router.get("/settings/logs")
async def get_logs(current_user=Depends(deps.require_role("ADMIN"))):
    return {"logs": list(app_module.log_history)}


@router.post("/settings/logs/clear")
async def clear_logs(current_user=Depends(deps.require_role("ADMIN"))):
    app_module.log_history.clear()
    return {"ok": True}


@router.get("/settings/logs/export")
async def export_logs(current_user=Depends(deps.require_role("ADMIN"))):
    text_blob = "\n".join(app_module.log_history)
    return Response(
        content=text_blob,
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=logs.txt"},
    )


@router.get("/settings/logs/posting-errors")
async def export_posting_error_logs(current_user=Depends(deps.require_role("ADMIN"))):
    path = Path(app_module.settings.posting_error_log_path)
    if not path.exists():
        return Response(content="", media_type="text/plain")
    return FileResponse(path=str(path), filename=path.name)


@router.get("/settings/alerts")
@router.get("/settings/incidents")
async def list_admin_alerts(
    unresolved_only: bool = Query(False),
    current_user=Depends(deps.require_role("ADMIN")),
):
    async with async_session() as session:
        q = select(models.admin_alert.AdminAlert).order_by(models.admin_alert.AdminAlert.created_at.desc())
        if unresolved_only:
            q = q.where(models.admin_alert.AdminAlert.resolved_at.is_(None))
        res = await session.execute(q)
        rows = res.scalars().all()
    return [
        {
            "id": r.id,
            "type": r.type,
            "severity": getattr(r, "severity", "ERROR"),
            "message": r.message,
            "request_id": r.request_id,
            "posting_session_id": getattr(r, "posting_session_id", None),
            "created_at": str(r.created_at) if r.created_at else None,
            "resolved_at": str(r.resolved_at) if r.resolved_at else None,
            "resolved_by": r.resolved_by,
            "resolution_comment": getattr(r, "resolution_comment", None),
        }
        for r in rows
    ]


@router.post("/settings/alerts/{alert_id}/resolve")
@router.post("/settings/incidents/{alert_id}/resolve")
async def resolve_admin_alert(
    alert_id: int,
    payload: dict | None = None,
    current_user=Depends(deps.require_role("ADMIN")),
):
    payload = payload or {}
    comment = str(payload.get("comment") or "").strip() or None
    async with async_session() as session:
        async with session.begin():
            await session.execute(
                update(models.admin_alert.AdminAlert)
                .where(models.admin_alert.AdminAlert.id == alert_id)
                .values(
                    resolved_at=utcnow(),
                    resolved_by=current_user.id,
                    resolution_comment=comment,
                )
            )
    return {"ok": True}


# Legacy JSON backup/restore routes (kept for backward compatibility)
@router.get("/settings/backup")
async def get_backup(current_user=Depends(deps.require_role("ADMIN"))):
    if not settings.enable_legacy_json_restore:
        await _record_legacy_json_backup_disabled_attempt(
            user_id=current_user.id,
            endpoint="/settings/backup [GET]",
        )
        raise HTTPException(status_code=404, detail="Not found")
    backup_data = {}
    async with async_session() as session:
        for table in models.Base.metadata.sorted_tables:
            if table.name.startswith("alembic_"):
                continue
            res = await session.execute(select(table))
            rows = [dict(r._mapping) for r in res.fetchall()]
            backup_data[table.name] = rows
    content = json.dumps(backup_data, default=str)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=backup.json"},
    )


@router.post("/settings/backup")
async def restore_backup(
    file: UploadFile = File(...),
    current_user=Depends(deps.require_role("ADMIN")),
):
    if not settings.enable_legacy_json_restore:
        await _record_legacy_json_backup_disabled_attempt(
            user_id=current_user.id,
            endpoint="/settings/backup [POST]",
        )
        raise HTTPException(status_code=404, detail="Not found")
    try:
        data = json.load(file.file)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    async with async_session() as session:
        async with session.begin():
            for table in reversed(models.Base.metadata.sorted_tables):
                if table.name in data:
                    await session.execute(text(f'TRUNCATE TABLE "{table.name}" RESTART IDENTITY CASCADE'))
            for table in models.Base.metadata.sorted_tables:
                if table.name in data:
                    rows = data.get(table.name)
                    if rows:
                        await session.execute(table.insert().values(rows))
    return {"ok": True}


# Real PostgreSQL backups (pg_dump / pg_restore verification)
@router.post("/settings/backups/create")
async def create_real_backup(current_user=Depends(deps.require_role("ADMIN"))):
    try:
        async with async_session() as session:
            runtime_cfg = await backup_service.get_backup_runtime_config(session)
        keep = int(runtime_cfg.get("rotation_keep") or settings.backup_retention_count)
        return backup_service.create_backup(keep_count=keep, name_prefix="pmm")
    except backup_service.BackupError as exc:
        async with async_session() as session:
            async with session.begin():
                await incident_service.create_incident(
                    session,
                    incident_type=IncidentType.BACKUP_FAILED,
                    severity=IncidentSeverity.HIGH,
                    message=f"Backup failed: {exc}",
                    details_json={"operation": "pg_dump", "error": str(exc)},
                    created_by=current_user.id,
                )
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/settings/backups")
async def list_real_backups(current_user=Depends(deps.require_role("ADMIN"))):
    return backup_service.list_backups()


@router.get("/settings/backups/config")
async def get_real_backup_config(current_user=Depends(deps.require_role("ADMIN"))):
    async with async_session() as session:
        return await backup_service.get_backup_runtime_config(session)


@router.post("/settings/backups/config")
async def set_real_backup_config(
    payload: BackupRuntimeConfigPayload,
    current_user=Depends(deps.require_role("ADMIN")),
):
    async with async_session() as session:
        return await backup_service.set_backup_runtime_config(
            session,
            schedule_enabled=payload.schedule_enabled,
            schedule_interval_hours=payload.schedule_interval_hours,
            rotation_keep=payload.rotation_keep,
        )


@router.post("/settings/backups/{filename}/verify")
async def verify_real_backup(filename: str, current_user=Depends(deps.require_role("ADMIN"))):
    try:
        return backup_service.verify_backup(filename)
    except backup_service.BackupError as exc:
        async with async_session() as session:
            async with session.begin():
                await incident_service.create_incident(
                    session,
                    incident_type=IncidentType.BACKUP_FAILED,
                    severity=IncidentSeverity.MEDIUM,
                    message=f"Backup verify failed: {exc}",
                    details_json={"operation": "pg_restore --list", "filename": filename, "error": str(exc)},
                    created_by=current_user.id,
                )
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/settings/backups/{filename}/restore")
async def restore_real_backup(
    filename: str,
    payload: BackupRestorePayload,
    current_user=Depends(deps.require_role("ADMIN")),
):
    if payload.confirm.strip().upper() != "RESTORE":
        raise HTTPException(status_code=400, detail="Для відновлення введіть confirm=RESTORE")
    try:
        return backup_service.restore_backup(filename)
    except backup_service.BackupError as exc:
        async with async_session() as session:
            async with session.begin():
                await incident_service.create_incident(
                    session,
                    incident_type=IncidentType.BACKUP_FAILED,
                    severity=IncidentSeverity.HIGH,
                    message=f"Backup restore failed: {exc}",
                    details_json={"operation": "pg_restore", "filename": filename, "error": str(exc)},
                    created_by=current_user.id,
                )
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/settings/backups/upload")
async def upload_real_backup(
    file: UploadFile = File(...),
    current_user=Depends(deps.require_role("ADMIN")),
):
    try:
        async with async_session() as session:
            runtime_cfg = await backup_service.get_backup_runtime_config(session)
        keep = int(runtime_cfg.get("rotation_keep") or settings.backup_retention_count)
        return backup_service.save_uploaded_backup(
            file.file,
            file.filename,
            keep_count=keep,
            name_prefix="pmm_import",
        )
    except backup_service.BackupError as exc:
        async with async_session() as session:
            async with session.begin():
                await incident_service.create_incident(
                    session,
                    incident_type=IncidentType.BACKUP_FAILED,
                    severity=IncidentSeverity.HIGH,
                    message=f"Backup upload failed: {exc}",
                    details_json={"operation": "upload_dump", "filename": file.filename, "error": str(exc)},
                    created_by=current_user.id,
                )
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/settings/backups/upload-and-restore")
async def upload_and_restore_real_backup(
    file: UploadFile = File(...),
    confirm: str = Form(""),
    current_user=Depends(deps.require_role("ADMIN")),
):
    if confirm.strip().upper() != "RESTORE":
        raise HTTPException(status_code=400, detail="Для відновлення введіть confirm=RESTORE")
    try:
        async with async_session() as session:
            runtime_cfg = await backup_service.get_backup_runtime_config(session)
        keep = int(runtime_cfg.get("rotation_keep") or settings.backup_retention_count)
        uploaded = backup_service.save_uploaded_backup(
            file.file,
            file.filename,
            keep_count=keep,
            name_prefix="pmm_import",
        )
        restored = backup_service.restore_backup(str(uploaded.get("filename")))
        return {"uploaded": uploaded, "restored": restored}
    except backup_service.BackupError as exc:
        async with async_session() as session:
            async with session.begin():
                await incident_service.create_incident(
                    session,
                    incident_type=IncidentType.BACKUP_FAILED,
                    severity=IncidentSeverity.HIGH,
                    message=f"Backup upload+restore failed: {exc}",
                    details_json={"operation": "upload_and_restore_dump", "filename": file.filename, "error": str(exc)},
                    created_by=current_user.id,
                )
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/settings/backups/{filename}")
async def delete_real_backup(filename: str, current_user=Depends(deps.require_role("ADMIN"))):
    try:
        return backup_service.delete_backup(filename)
    except backup_service.BackupError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/settings/backups/{filename}/download")
async def download_real_backup(filename: str, current_user=Depends(deps.require_role("ADMIN"))):
    try:
        path = backup_service.resolve_backup_path(filename)
    except backup_service.BackupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return FileResponse(path=str(path), filename=path.name)
