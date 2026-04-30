from __future__ import annotations

import json
import os
import tarfile
import tempfile
import shutil
import subprocess
import re
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.time import utcnow
from app.crud import app_settings as crud_app


class BackupError(RuntimeError):
    pass


_BACKUP_OP_LOCK_FILE = "backup.operation.lock"
_SCHEDULE_ENABLED_KEY = "backup.schedule_enabled"
_SCHEDULE_INTERVAL_HOURS_KEY = "backup.schedule_interval_hours"
_ROTATION_KEEP_KEY = "backup.rotation_keep"
_LAST_AUTO_BACKUP_AT_KEY = "backup.last_auto_backup_at"
_LAST_AUTO_BACKUP_FILE_KEY = "backup.last_auto_backup_file"
_FULL_BACKUP_MANIFEST_VERSION = 1


def _require_binary(binary: str) -> None:
    if shutil.which(binary):
        return
    raise BackupError(f"{binary} is not available in backend runtime")


def _backup_dir() -> Path:
    p = Path(settings.backup_dir).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def _artifacts_dir() -> Path:
    p = Path(settings.artifacts_dir).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def _logs_dir() -> Path:
    p = Path(settings.posting_error_log_path).expanduser().resolve().parent
    p.mkdir(parents=True, exist_ok=True)
    return p


def _summarize_full_backup_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    app_meta = manifest.get("app") or {}
    return {
        "manifest_version": int(manifest.get("manifest_version") or 0),
        "backup_type": str(manifest.get("backup_type") or ""),
        "created_at": manifest.get("created_at"),
        "backend_version": app_meta.get("backend_version"),
        "frontend_version": app_meta.get("frontend_version"),
        "includes": ["database.dump", "artifacts.tar.gz", "logs.tar.gz"],
    }


def _read_full_backup_manifest_from_path(path: Path) -> dict[str, Any]:
    try:
        with tarfile.open(path, "r:gz") as archive:
            manifest_member = archive.extractfile("manifest.json")
            if not manifest_member:
                raise BackupError("manifest.json is unreadable")
            manifest = json.loads(manifest_member.read().decode("utf-8"))
    except (tarfile.TarError, json.JSONDecodeError, OSError) as exc:
        raise BackupError(f"Failed to read full backup manifest: {exc}") from exc
    if manifest.get("backup_type") != "full":
        raise BackupError("Full backup manifest has invalid backup_type")
    return manifest


def _is_postgres_database() -> bool:
    try:
        url = make_url(settings.database_url)
    except Exception:
        return False
    backend = (url.drivername or "").split("+", 1)[0]
    return backend == "postgresql"


def _pg_conn_params() -> dict[str, Any]:
    url = make_url(settings.database_url)
    backend = (url.drivername or "").split("+", 1)[0]
    if backend != "postgresql":
        raise BackupError("Real pg_dump backups are supported only for PostgreSQL")
    return {
        "host": url.host or "localhost",
        "port": int(url.port or 5432),
        "username": url.username or "",
        "password": url.password or "",
        "database": url.database or "",
    }


def _retention_cleanup() -> None:
    keep = max(int(settings.backup_retention_count), 1)
    files = sorted(_backup_dir().glob("pmm_*.dump"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[keep:]:
        try:
            old.unlink(missing_ok=True)
        except Exception:
            continue


def _retention_cleanup_with_keep(keep_count: int) -> None:
    keep = max(int(keep_count), 1)
    files = sorted(_backup_dir().glob("pmm_*.dump"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[keep:]:
        try:
            old.unlink(missing_ok=True)
        except Exception:
            continue


def _retention_cleanup_for_pattern(pattern: str, keep_count: int) -> None:
    keep = max(int(keep_count), 1)
    files = sorted(_backup_dir().glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[keep:]:
        try:
            old.unlink(missing_ok=True)
        except Exception:
            continue


@contextmanager
def _backup_operation_lock(*, stale_seconds: int = 3600):
    lock_path = _backup_dir() / _BACKUP_OP_LOCK_FILE
    now = utcnow()
    if lock_path.exists():
        try:
            age = now.timestamp() - lock_path.stat().st_mtime
            if age > stale_seconds:
                lock_path.unlink(missing_ok=True)
        except Exception:
            pass
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise BackupError("Backup operation is already in progress") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(now.isoformat())
        yield
    finally:
        try:
            lock_path.unlink(missing_ok=True)
        except Exception:
            pass


def create_backup(*, keep_count: int | None = None, name_prefix: str = "pmm") -> dict[str, Any]:
    params = _pg_conn_params()
    _require_binary("pg_dump")
    with _backup_operation_lock():
        ts = utcnow().strftime("%Y%m%d_%H%M%S")
        safe_prefix = "".join(ch for ch in (name_prefix or "pmm") if ch.isalnum() or ch in ("_", "-")).strip("_-") or "pmm"
        path = _backup_dir() / f"{safe_prefix}_{ts}.dump"
        env = os.environ.copy()
        if params["password"]:
            env["PGPASSWORD"] = params["password"]
        cmd = [
            "pg_dump",
            "--format=custom",
            "--no-owner",
            "--no-privileges",
            "--host",
            params["host"],
            "--port",
            str(params["port"]),
            "--username",
            params["username"],
            "--file",
            str(path),
            params["database"],
        ]
        try:
            proc = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)
        except OSError as exc:
            raise BackupError(f"pg_dump failed to start: {exc}") from exc
        if proc.returncode != 0:
            raise BackupError(f"pg_dump failed: {(proc.stderr or proc.stdout or '').strip()}")
        if keep_count is None:
            _retention_cleanup()
        else:
            _retention_cleanup_with_keep(keep_count)
        return {
            "filename": path.name,
            "path": str(path),
            "size": path.stat().st_size if path.exists() else 0,
            "created_at": utcnow().isoformat(),
        }


def _create_pg_dump_to_path(target_path: Path, *, params: dict[str, Any] | None = None) -> None:
    params = params or _pg_conn_params()
    _require_binary("pg_dump")
    env = os.environ.copy()
    if params["password"]:
        env["PGPASSWORD"] = params["password"]
    cmd = [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        "--host",
        params["host"],
        "--port",
        str(params["port"]),
        "--username",
        params["username"],
        "--file",
        str(target_path),
        params["database"],
    ]
    try:
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise BackupError(f"pg_dump failed to start: {exc}") from exc
    if proc.returncode != 0:
        raise BackupError(f"pg_dump failed: {(proc.stderr or proc.stdout or '').strip()}")


def _restore_pg_dump_from_path(source_path: Path, *, params: dict[str, Any] | None = None) -> None:
    params = params or _pg_conn_params()
    _require_binary("pg_restore")
    env = os.environ.copy()
    if params["password"]:
        env["PGPASSWORD"] = params["password"]
    cmd = [
        "pg_restore",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        "--host",
        params["host"],
        "--port",
        str(params["port"]),
        "--username",
        params["username"],
        "--dbname",
        params["database"],
        str(source_path),
    ]
    try:
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise BackupError(f"pg_restore failed to start: {exc}") from exc
    if proc.returncode != 0:
        raise BackupError(f"pg_restore failed: {(proc.stderr or proc.stdout or '').strip()}")


def _write_directory_archive(source_dir: Path, target_archive: Path, *, root_name: str) -> None:
    source_dir = source_dir.resolve()
    with tarfile.open(target_archive, "w:gz") as archive:
        root_info = tarfile.TarInfo(f"{root_name}/")
        root_info.type = tarfile.DIRTYPE
        root_info.mtime = int(utcnow().timestamp())
        archive.addfile(root_info)
        if not source_dir.exists():
            return
        for child in sorted(source_dir.iterdir(), key=lambda p: p.name):
            archive.add(child, arcname=f"{root_name}/{child.name}")


def _clear_directory_contents(target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for child in target_dir.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink(missing_ok=True)


def _restore_directory_archive(source_archive: Path, target_dir: Path, *, root_name: str) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pmm_restore_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        with tarfile.open(source_archive, "r:gz") as archive:
            archive.extractall(tmp_path)
        extracted_root = tmp_path / root_name
        if not extracted_root.exists() or not extracted_root.is_dir():
            raise BackupError(f"Archive is missing required directory: {root_name}")
        _clear_directory_contents(target_dir)
        for child in sorted(extracted_root.iterdir(), key=lambda p: p.name):
            destination = target_dir / child.name
            if child.is_dir() and not child.is_symlink():
                shutil.copytree(child, destination)
            else:
                shutil.copy2(child, destination)


def create_full_backup(*, keep_count: int | None = None, name_prefix: str = "pmm_full") -> dict[str, Any]:
    params = _pg_conn_params()
    _require_binary("pg_dump")
    with _backup_operation_lock():
        ts = utcnow().strftime("%Y%m%d_%H%M%S")
        safe_prefix = "".join(ch for ch in (name_prefix or "pmm_full") if ch.isalnum() or ch in ("_", "-")).strip("_-") or "pmm_full"
        target = _backup_dir() / f"{safe_prefix}_{ts}.tar.gz"

        with tempfile.TemporaryDirectory(prefix="pmm_full_backup_") as tmp_dir:
            tmp_path = Path(tmp_dir)
            dump_path = tmp_path / "database.dump"
            artifacts_archive = tmp_path / "artifacts.tar.gz"
            logs_archive = tmp_path / "logs.tar.gz"
            manifest_path = tmp_path / "manifest.json"

            _create_pg_dump_to_path(dump_path, params=params)
            _write_directory_archive(_artifacts_dir(), artifacts_archive, root_name="artifacts")
            _write_directory_archive(_logs_dir(), logs_archive, root_name="logs")

            manifest = {
                "manifest_version": _FULL_BACKUP_MANIFEST_VERSION,
                "backup_type": "full",
                "created_at": utcnow().isoformat(),
                "database": {
                    "engine": "postgresql",
                    "filename": dump_path.name,
                    "size": dump_path.stat().st_size if dump_path.exists() else 0,
                },
                "artifacts": {
                    "filename": artifacts_archive.name,
                    "size": artifacts_archive.stat().st_size if artifacts_archive.exists() else 0,
                },
                "logs": {
                    "filename": logs_archive.name,
                    "size": logs_archive.stat().st_size if logs_archive.exists() else 0,
                },
                "app": {
                    "backend_version": settings.backend_version,
                    "frontend_version": settings.frontend_version,
                },
            }
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

            with tarfile.open(target, "w:gz") as full_archive:
                full_archive.add(dump_path, arcname=dump_path.name)
                full_archive.add(artifacts_archive, arcname=artifacts_archive.name)
                full_archive.add(logs_archive, arcname=logs_archive.name)
                full_archive.add(manifest_path, arcname=manifest_path.name)

        _retention_cleanup_for_pattern("pmm_full_*.tar.gz", keep_count or int(settings.backup_retention_count))
        return {
            "filename": target.name,
            "path": str(target),
            "size": target.stat().st_size if target.exists() else 0,
            "created_at": utcnow().isoformat(),
            "type": "full",
        }


def delete_backup(filename: str) -> dict[str, Any]:
    with _backup_operation_lock():
        path = resolve_backup_path(filename)
        path.unlink(missing_ok=True)
        return {"ok": True, "filename": filename}


def _slug_name(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return "dump"
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "_", raw)
    return slug[:80].strip("._-") or "dump"


def save_uploaded_backup(
    file_obj,
    original_filename: str | None,
    *,
    keep_count: int | None = None,
    name_prefix: str = "pmm_import",
) -> dict[str, Any]:
    _require_binary("pg_restore")
    with _backup_operation_lock():
        ts = utcnow().strftime("%Y%m%d_%H%M%S")
        safe_name = _slug_name(Path(original_filename or "dump").stem)
        safe_prefix = "".join(ch for ch in (name_prefix or "pmm_import") if ch.isalnum() or ch in ("_", "-")).strip("_-") or "pmm_import"
        target = _backup_dir() / f"{safe_prefix}_{ts}_{safe_name}.dump"
        try:
            with open(target, "wb") as out:
                shutil.copyfileobj(file_obj, out)
        except Exception as exc:
            raise BackupError(f"Failed to save uploaded dump: {exc}") from exc
        if not target.exists() or target.stat().st_size <= 0:
            target.unlink(missing_ok=True)
            raise BackupError("Uploaded dump file is empty")
        verification = verify_backup(target.name)
        if not verification.get("ok"):
            target.unlink(missing_ok=True)
            raise BackupError(f"Uploaded dump verification failed: {verification.get('reason') or 'unknown error'}")

        if keep_count is None:
            _retention_cleanup()
        else:
            _retention_cleanup_with_keep(keep_count)

        return {
            "filename": target.name,
            "path": str(target),
            "size": int(target.stat().st_size),
            "created_at": utcnow().isoformat(),
            "verified": True,
        }


def resolve_full_backup_path(filename: str) -> Path:
    safe_name = Path(filename).name
    p = (_backup_dir() / safe_name).resolve()
    if p.parent != _backup_dir():
        raise BackupError("Invalid backup filename")
    if not p.exists():
        raise BackupError("Full backup file not found")
    return p


def verify_full_backup(filename: str) -> dict[str, Any]:
    path = resolve_full_backup_path(filename)
    if path.stat().st_size <= 0:
        return {"ok": False, "reason": "file is empty", "filename": filename}
    try:
        with tarfile.open(path, "r:gz") as archive:
            names = set(archive.getnames())
            required = {"manifest.json", "database.dump", "artifacts.tar.gz", "logs.tar.gz"}
            missing = sorted(required - names)
            if missing:
                return {
                    "ok": False,
                    "reason": f"archive is missing required files: {', '.join(missing)}",
                    "filename": filename,
                }
            manifest_member = archive.extractfile("manifest.json")
            if not manifest_member:
                return {"ok": False, "reason": "manifest.json is unreadable", "filename": filename}
            manifest = json.loads(manifest_member.read().decode("utf-8"))
            if manifest.get("backup_type") != "full":
                return {"ok": False, "reason": "invalid backup_type in manifest", "filename": filename}
            if int(manifest.get("manifest_version") or 0) != _FULL_BACKUP_MANIFEST_VERSION:
                return {"ok": False, "reason": "unsupported manifest version", "filename": filename}
    except (tarfile.TarError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "reason": str(exc), "filename": filename}
    return {
        "ok": True,
        "filename": filename,
        "size": path.stat().st_size,
        "type": "full",
        "manifest": _summarize_full_backup_manifest(manifest),
    }


def save_uploaded_full_backup(
    file_obj,
    original_filename: str | None,
    *,
    keep_count: int | None = None,
    name_prefix: str = "pmm_full_import",
) -> dict[str, Any]:
    with _backup_operation_lock():
        ts = utcnow().strftime("%Y%m%d_%H%M%S")
        safe_name = _slug_name(Path(original_filename or "backup").stem)
        safe_prefix = "".join(ch for ch in (name_prefix or "pmm_full_import") if ch.isalnum() or ch in ("_", "-")).strip("_-") or "pmm_full_import"
        target = _backup_dir() / f"{safe_prefix}_{ts}_{safe_name}.tar.gz"
        try:
            with open(target, "wb") as out:
                shutil.copyfileobj(file_obj, out)
        except Exception as exc:
            raise BackupError(f"Failed to save uploaded full backup: {exc}") from exc
        if not target.exists() or target.stat().st_size <= 0:
            target.unlink(missing_ok=True)
            raise BackupError("Uploaded full backup file is empty")
        verification = verify_full_backup(target.name)
        if not verification.get("ok"):
            target.unlink(missing_ok=True)
            raise BackupError(f"Uploaded full backup verification failed: {verification.get('reason') or 'unknown error'}")

        _retention_cleanup_for_pattern("pmm_full_*.tar.gz", keep_count or int(settings.backup_retention_count))
        return {
            "filename": target.name,
            "path": str(target),
            "size": int(target.stat().st_size),
            "created_at": utcnow().isoformat(),
            "verified": True,
            "type": "full",
        }


def restore_full_backup(filename: str) -> dict[str, Any]:
    params = _pg_conn_params()
    path = resolve_full_backup_path(filename)
    with _backup_operation_lock():
        with tempfile.TemporaryDirectory(prefix="pmm_full_restore_") as tmp_dir:
            tmp_path = Path(tmp_dir)
            try:
                with tarfile.open(path, "r:gz") as archive:
                    archive.extractall(tmp_path)
            except (tarfile.TarError, OSError) as exc:
                raise BackupError(f"Failed to extract full backup archive: {exc}") from exc

            manifest_path = tmp_path / "manifest.json"
            dump_path = tmp_path / "database.dump"
            artifacts_archive = tmp_path / "artifacts.tar.gz"
            logs_archive = tmp_path / "logs.tar.gz"
            if not manifest_path.exists() or not dump_path.exists() or not artifacts_archive.exists() or not logs_archive.exists():
                raise BackupError("Full backup archive is incomplete")
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise BackupError(f"Full backup manifest is invalid: {exc}") from exc
            if manifest.get("backup_type") != "full":
                raise BackupError("Full backup manifest has invalid backup_type")

            _restore_pg_dump_from_path(dump_path, params=params)
            _restore_directory_archive(artifacts_archive, _artifacts_dir(), root_name="artifacts")
            _restore_directory_archive(logs_archive, _logs_dir(), root_name="logs")
        return {"ok": True, "filename": filename, "restored_at": utcnow().isoformat(), "type": "full"}


def restore_backup(filename: str) -> dict[str, Any]:
    with _backup_operation_lock():
        _restore_pg_dump_from_path(resolve_backup_path(filename))
        return {"ok": True, "filename": filename, "restored_at": utcnow().isoformat()}


def list_backups() -> list[dict[str, Any]]:
    files = sorted(_backup_dir().glob("pmm_*.dump"), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for p in files:
        st = p.stat()
        out.append(
            {
                "filename": p.name,
                "path": str(p),
                "size": int(st.st_size),
                "mtime": int(st.st_mtime),
                "created_at": datetime.fromtimestamp(st.st_mtime).isoformat(),
            }
        )
    return out


def list_full_backups() -> list[dict[str, Any]]:
    files = sorted(_backup_dir().glob("pmm_full_*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for p in files:
        st = p.stat()
        manifest_summary: dict[str, Any] | None = None
        manifest_error: str | None = None
        try:
            manifest_summary = _summarize_full_backup_manifest(_read_full_backup_manifest_from_path(p))
        except BackupError as exc:
            manifest_error = str(exc)
        out.append(
            {
                "filename": p.name,
                "path": str(p),
                "size": int(st.st_size),
                "mtime": int(st.st_mtime),
                "created_at": datetime.fromtimestamp(st.st_mtime).isoformat(),
                "type": "full",
                "manifest": manifest_summary,
                "manifest_error": manifest_error,
            }
        )
    return out


def resolve_backup_path(filename: str) -> Path:
    safe_name = Path(filename).name
    p = (_backup_dir() / safe_name).resolve()
    if p.parent != _backup_dir():
        raise BackupError("Invalid backup filename")
    if not p.exists():
        raise BackupError("Backup file not found")
    return p


def verify_backup(filename: str) -> dict[str, Any]:
    if not _is_postgres_database():
        raise BackupError("Real pg_restore verification is available only for PostgreSQL")
    _require_binary("pg_restore")
    path = resolve_backup_path(filename)
    if path.stat().st_size <= 0:
        return {"ok": False, "reason": "file is empty", "filename": filename}
    cmd = ["pg_restore", "--list", str(path)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise BackupError(f"pg_restore failed to start: {exc}") from exc
    if proc.returncode != 0:
        return {
            "ok": False,
            "reason": (proc.stderr or proc.stdout or "pg_restore failed").strip(),
            "filename": filename,
        }
    return {"ok": True, "filename": filename, "size": path.stat().st_size}


def _to_bool(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _to_int(raw: str | None, default: int, minimum: int) -> int:
    if raw is None:
        return default
    try:
        value = int(str(raw).strip())
    except Exception:
        return default
    return value if value >= minimum else minimum


async def get_backup_runtime_config(db: AsyncSession) -> dict[str, Any]:
    enabled_raw = await crud_app.get_setting(db, _SCHEDULE_ENABLED_KEY)
    interval_raw = await crud_app.get_setting(db, _SCHEDULE_INTERVAL_HOURS_KEY)
    keep_raw = await crud_app.get_setting(db, _ROTATION_KEEP_KEY)
    last_auto_backup_at = await crud_app.get_setting(db, _LAST_AUTO_BACKUP_AT_KEY)
    last_auto_backup_file = await crud_app.get_setting(db, _LAST_AUTO_BACKUP_FILE_KEY)

    return {
        "schedule_enabled": _to_bool(enabled_raw, False),
        "schedule_interval_hours": _to_int(interval_raw, 24, 1),
        "rotation_keep": _to_int(keep_raw, int(settings.backup_retention_count), 1),
        "last_auto_backup_at": last_auto_backup_at or None,
        "last_auto_backup_file": last_auto_backup_file or None,
    }


async def set_backup_runtime_config(
    db: AsyncSession,
    *,
    schedule_enabled: bool,
    schedule_interval_hours: int,
    rotation_keep: int,
) -> dict[str, Any]:
    await crud_app.set_setting(db, _SCHEDULE_ENABLED_KEY, str(bool(schedule_enabled)).lower())
    await crud_app.set_setting(db, _SCHEDULE_INTERVAL_HOURS_KEY, str(max(int(schedule_interval_hours), 1)))
    await crud_app.set_setting(db, _ROTATION_KEEP_KEY, str(max(int(rotation_keep), 1)))
    return await get_backup_runtime_config(db)


async def set_last_auto_backup_meta(db: AsyncSession, *, backup_filename: str) -> None:
    now = utcnow().isoformat()
    await crud_app.set_setting(db, _LAST_AUTO_BACKUP_AT_KEY, now)
    await crud_app.set_setting(db, _LAST_AUTO_BACKUP_FILE_KEY, backup_filename)
