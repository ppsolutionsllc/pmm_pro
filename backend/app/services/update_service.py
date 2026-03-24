from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
from datetime import timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest, urlopen

from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.time import utcnow
from app.models.app_settings import AppSettings
from app.models.background_job import BackgroundJob, BackgroundJobStatus, BackgroundJobType
from app.models.system_meta import SystemMeta
from app.models.update_step import UpdateStep, UpdateStepStatus
from app.models.updates_log import UpdateStatus, UpdatesLog
from app.services import backup_service


class UpdateError(RuntimeError):
    pass


CONFIG_DEFAULT_WITH_BACKUP = "updates.default_with_backup"

_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
_TAG_RE = re.compile(r"^v\d+\.\d+\.\d+$")

_GITHUB_CACHE: dict[str, Any] = {
    "repo": None,
    "fetched_at": None,
    "payload": None,
}


def _strtobool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


async def _get_setting(db: AsyncSession, key: str) -> str | None:
    row = (await db.execute(select(AppSettings).where(AppSettings.key == key))).scalars().first()
    return row.value if row else None


async def _set_setting(db: AsyncSession, key: str, value: str | None) -> None:
    row = (await db.execute(select(AppSettings).where(AppSettings.key == key))).scalars().first()
    if row:
        row.value = value
    else:
        db.add(AppSettings(key=key, value=value))
    await db.flush()


async def get_update_config(db: AsyncSession) -> dict[str, Any]:
    default_with_backup_raw = await _get_setting(db, CONFIG_DEFAULT_WITH_BACKUP)
    return {
        "update_repo": _normalize_repo(settings.update_github_repo) if settings.update_github_repo else None,
        "updater_mode": "server_build",
        "require_signed_tags": bool(settings.require_signed_tags),
        "default_with_backup": _strtobool(default_with_backup_raw, default=True),
    }


async def set_update_config(
    db: AsyncSession,
    *,
    default_with_backup: bool | None = None,
) -> dict[str, Any]:
    if default_with_backup is not None:
        await _set_setting(db, CONFIG_DEFAULT_WITH_BACKUP, "true" if default_with_backup else "false")
    await db.commit()
    return await get_update_config(db)


async def current_db_schema_version(db: AsyncSession) -> str | None:
    try:
        row = (await db.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))).first()
        return str(row[0]) if row and row[0] else None
    except Exception:
        return None


async def get_or_create_system_meta(db: AsyncSession) -> SystemMeta:
    row = (await db.execute(select(SystemMeta).where(SystemMeta.id == 1))).scalars().first()
    if row:
        changed = False
        if not row.updater_mode:
            row.updater_mode = "server_build"
            changed = True
        normalized_repo = _normalize_repo(settings.update_github_repo) if settings.update_github_repo else None
        if normalized_repo and row.update_repo != normalized_repo:
            row.update_repo = normalized_repo
            changed = True
        if changed:
            await db.flush()
        return row

    row = SystemMeta(
        id=1,
        backend_version=settings.backend_version,
        frontend_version=settings.frontend_version,
        db_schema_version=await current_db_schema_version(db),
        last_update_at=utcnow(),
        last_update_by=None,
        updater_mode="server_build",
        update_repo=_normalize_repo(settings.update_github_repo) if settings.update_github_repo else None,
    )
    db.add(row)
    await db.flush()
    return row


async def list_updates_logs(db: AsyncSession, *, limit: int = 50) -> list[UpdatesLog]:
    rows = (
        await db.execute(
            select(UpdatesLog)
            .order_by(desc(UpdatesLog.started_at), desc(UpdatesLog.id))
            .limit(max(int(limit), 1))
        )
    ).scalars().all()
    return list(rows)


async def get_update_log_by_job_id(db: AsyncSession, *, job_id: str) -> UpdatesLog | None:
    row = (
        await db.execute(
            select(UpdatesLog)
            .where(UpdatesLog.job_id == job_id)
            .order_by(desc(UpdatesLog.id))
            .limit(1)
        )
    ).scalars().first()
    if row:
        return row

    # Backward-compat fallback for old rows without job_id column value.
    rows = await list_updates_logs(db, limit=200)
    for candidate in rows:
        details = candidate.details_json or {}
        if str(details.get("job_id") or "") == job_id:
            return candidate
    return None


async def ensure_no_update_in_progress(db: AsyncSession) -> None:
    meta = (
        await db.execute(select(SystemMeta).where(SystemMeta.id == 1).with_for_update())
    ).scalars().first()
    if meta and bool(meta.update_lock):
        raise UpdateError("Update in progress")

    running = (
        await db.execute(
            select(BackgroundJob.id).where(
                BackgroundJob.type == BackgroundJobType.SYSTEM_UPDATE,
                BackgroundJob.status.in_([BackgroundJobStatus.QUEUED, BackgroundJobStatus.RUNNING]),
            )
        )
    ).scalars().first()
    if running:
        raise UpdateError("Update in progress")


async def _acquire_update_lock(db: AsyncSession, *, job_id: str) -> None:
    meta = (
        await db.execute(select(SystemMeta).where(SystemMeta.id == 1).with_for_update())
    ).scalars().first()
    if meta is None:
        meta = await get_or_create_system_meta(db)
        await db.flush()
        meta = (
            await db.execute(select(SystemMeta).where(SystemMeta.id == 1).with_for_update())
        ).scalars().first()
    assert meta is not None

    if meta.update_lock and meta.update_lock_job_id not in (None, job_id):
        raise UpdateError("Update in progress")

    meta.update_lock = True
    meta.update_lock_job_id = job_id
    meta.update_lock_acquired_at = utcnow()
    await db.flush()


async def _release_update_lock(db: AsyncSession, *, job_id: str) -> None:
    meta = (
        await db.execute(select(SystemMeta).where(SystemMeta.id == 1).with_for_update())
    ).scalars().first()
    if not meta:
        return
    if meta.update_lock_job_id and meta.update_lock_job_id != job_id:
        return
    meta.update_lock = False
    meta.update_lock_job_id = None
    meta.update_lock_acquired_at = None
    await db.flush()


def _normalize_repo(value: str) -> str:
    s = str(value or "").strip()
    if not s:
        raise UpdateError("UPDATE_GITHUB_REPO is not configured")

    for prefix in ("https://", "http://"):
        if s.startswith(prefix):
            s = s[len(prefix) :]
    if s.startswith("github.com/"):
        s = s[len("github.com/") :]
    if s.endswith(".git"):
        s = s[:-4]
    s = s.strip("/")

    if not re.match(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", s):
        raise UpdateError("UPDATE_GITHUB_REPO must be in format '<ORG>/<REPO>'")
    return s


def _repo_git_url(repo: str) -> str:
    return f"https://github.com/{repo}.git"


def _github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "pmm-updater",
    }
    token = str(settings.update_github_token or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _http_get_json(url: str) -> Any:
    req = UrlRequest(url, headers=_github_headers())
    with urlopen(req, timeout=20) as resp:  # nosec B310 - admin-configured GitHub endpoint
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def _parse_notes(body: str | None) -> list[str]:
    text = str(body or "").strip()
    if not text:
        return []
    lines = [ln.strip("- ").strip() for ln in text.splitlines() if ln.strip()]
    return lines[:20]


def _semver_key(version: str) -> tuple[int, int, int]:
    major, minor, patch = version.split(".")
    return (int(major), int(minor), int(patch))


def _tag_to_version(tag: str) -> str:
    if not _TAG_RE.match(tag):
        raise UpdateError(f"Unsupported tag format: {tag}")
    return tag[1:]


def _version_to_tag(version: str) -> str:
    value = str(version or "").strip()
    if value.startswith("v"):
        if not _TAG_RE.match(value):
            raise UpdateError("Version must match vX.Y.Z")
        return value
    if not _VERSION_RE.match(value):
        raise UpdateError("Version must match X.Y.Z")
    return f"v{value}"


def _sorted_versions(values: list[str], *, limit: int) -> list[str]:
    uniq = sorted({v for v in values if _VERSION_RE.match(v)}, key=_semver_key, reverse=True)
    return uniq[: max(1, int(limit))]


def _fetch_versions_from_github(repo: str, *, limit: int) -> dict[str, Any]:
    changelog: list[dict[str, Any]] = []
    versions_from_releases: list[str] = []
    try:
        releases_url = f"https://api.github.com/repos/{repo}/releases?per_page={max(10, int(limit) * 2)}"
        releases = _http_get_json(releases_url)
        if isinstance(releases, list):
            for rel in releases:
                tag = str((rel or {}).get("tag_name") or "").strip()
                if not _TAG_RE.match(tag):
                    continue
                version = tag[1:]
                versions_from_releases.append(version)
                changelog.append(
                    {
                        "version": version,
                        "date": str((rel or {}).get("published_at") or "")[:10] or None,
                        "notes": _parse_notes((rel or {}).get("body")),
                    }
                )
    except Exception:
        # fallback below
        pass

    tags_url = f"https://api.github.com/repos/{repo}/tags?per_page={max(10, int(limit) * 3)}"
    tags_payload = _http_get_json(tags_url)
    tag_versions: list[str] = []
    if isinstance(tags_payload, list):
        for node in tags_payload:
            tag = str((node or {}).get("name") or "").strip()
            if _TAG_RE.match(tag):
                tag_versions.append(tag[1:])

    versions = _sorted_versions(versions_from_releases + tag_versions, limit=limit)
    changelog = [x for x in changelog if x.get("version") in set(versions)]
    changelog.sort(key=lambda x: _semver_key(str(x.get("version"))), reverse=True)

    return {
        "source": f"github:{repo}",
        "available_versions": versions,
        "latest_version": versions[0] if versions else None,
        "changelog": changelog,
    }


def _fetch_versions_from_git(repo: str, *, limit: int) -> dict[str, Any]:
    cmd = ["git", "ls-remote", "--tags", "--refs", _repo_git_url(repo)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=30)
    if proc.returncode != 0:
        raise UpdateError((proc.stderr or proc.stdout or "Failed to query git tags")[-1000:])

    versions: list[str] = []
    for line in (proc.stdout or "").splitlines():
        if "refs/tags/" not in line:
            continue
        tag = line.split("refs/tags/")[-1].strip()
        if _TAG_RE.match(tag):
            versions.append(tag[1:])

    versions = _sorted_versions(versions, limit=limit)
    return {
        "source": f"git:{repo}",
        "available_versions": versions,
        "latest_version": versions[0] if versions else None,
        "changelog": [],
    }


async def _load_available_versions(*, force: bool = False) -> dict[str, Any]:
    repo = _normalize_repo(settings.update_github_repo)
    ttl = max(int(settings.update_check_cache_ttl_seconds or 300), 60)
    now = utcnow()

    cached_repo = _GITHUB_CACHE.get("repo")
    cached_at = _GITHUB_CACHE.get("fetched_at")
    cached_payload = _GITHUB_CACHE.get("payload")
    if (
        not force
        and cached_repo == repo
        and cached_payload is not None
        and cached_at is not None
        and now - cached_at <= timedelta(seconds=ttl)
    ):
        return dict(cached_payload)

    limit = max(int(settings.update_releases_limit or 10), 1)
    payload: dict[str, Any]
    try:
        payload = _fetch_versions_from_github(repo, limit=limit)
    except (HTTPError, URLError, TimeoutError, UpdateError, json.JSONDecodeError, ValueError):
        payload = _fetch_versions_from_git(repo, limit=limit)

    _GITHUB_CACHE["repo"] = repo
    _GITHUB_CACHE["fetched_at"] = now
    _GITHUB_CACHE["payload"] = dict(payload)
    return payload


async def load_update_manifest(db: AsyncSession) -> dict[str, Any]:
    # Backward-compat endpoint kept for old UI/clients.
    payload = await _load_available_versions(force=False)
    return {
        "app_name": "PMM_ONLINE",
        "latest_version": payload.get("latest_version"),
        "available_versions": payload.get("available_versions") or [],
        "changelog": payload.get("changelog") or [],
        "source": payload.get("source"),
        "mode": "github_server_build",
    }


async def check_for_update(db: AsyncSession) -> dict[str, Any]:
    versions_payload = await _load_available_versions(force=True)
    meta = await get_or_create_system_meta(db)
    db_schema = await current_db_schema_version(db)

    latest = str(versions_payload.get("latest_version") or "")
    current_version = (meta.backend_version or "").strip() or None

    return {
        "source": versions_payload.get("source") or f"github:{_normalize_repo(settings.update_github_repo)}",
        "app_name": "PMM_ONLINE",
        "current_version": current_version,
        "latest_version": latest,
        "update_available": bool(latest and current_version != latest),
        "current_db_schema": db_schema,
        "available_versions": versions_payload.get("available_versions") or [],
        "changelog": versions_payload.get("changelog") or [],
    }


def _run_cmd(
    args: list[str],
    *,
    cwd: str,
    timeout: int = 900,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
    except FileNotFoundError as exc:
        raise UpdateError(f"Command not found: {args[0]}") from exc

    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode != 0:
        raise UpdateError(f"Command failed ({' '.join(args)}): {(err or out)[-2000:]}")

    return {
        "cmd": args,
        "stdout_tail": out[-2000:] if out else "",
        "stderr_tail": err[-2000:] if err else "",
    }


def _compose_command_base(*, compose_files: list[Path], env_file: Path) -> list[str]:
    if shutil.which("docker"):
        probe = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True, check=False)
        if probe.returncode == 0:
            cmd = ["docker", "compose", "--env-file", str(env_file)]
            for compose_file in compose_files:
                cmd.extend(["-f", str(compose_file)])
            return cmd
    if shutil.which("docker-compose"):
        cmd = ["docker-compose", "--env-file", str(env_file)]
        for compose_file in compose_files:
            cmd.extend(["-f", str(compose_file)])
        return cmd
    raise UpdateError("Neither 'docker compose' nor 'docker-compose' is available")


def _read_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def _upsert_env(path: Path, updates: dict[str, str]) -> None:
    lines: list[str] = []
    found: set[str] = set()
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()

    rendered: list[str] = []
    for line in lines:
        raw = line
        s = raw.strip()
        if not s or s.startswith("#") or "=" not in raw:
            rendered.append(raw)
            continue
        k, _ = raw.split("=", 1)
        key = k.strip()
        if key in updates:
            rendered.append(f"{key}={updates[key]}")
            found.add(key)
        else:
            rendered.append(raw)

    for key, value in updates.items():
        if key not in found:
            rendered.append(f"{key}={value}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rendered).rstrip() + "\n", encoding="utf-8")


def _update_root() -> Path:
    return Path(settings.update_project_dir).expanduser().resolve()


def _releases_dir(root: Path) -> Path:
    return (root / "releases").resolve()


def _current_link(root: Path) -> Path:
    return (root / "current").resolve(strict=False)


def _compose_files_from_overlay(overlay_file: Path) -> list[Path]:
    overlay = overlay_file.resolve()
    base = (overlay.parent / "docker-compose.yml").resolve()
    files: list[Path] = []
    if base.exists() and base != overlay:
        files.append(base)
    files.append(overlay)
    return files


def _compose_files_for_release(release_dir: Path) -> list[Path]:
    return _compose_files_from_overlay(release_dir / "docker-compose.prod.yml")


def _compose_files_current(root: Path) -> list[Path]:
    configured = str(settings.update_compose_file or "").strip()
    if configured:
        return _compose_files_from_overlay(Path(configured).expanduser().resolve())
    return _compose_files_from_overlay(root / "current" / "docker-compose.prod.yml")


def _env_file_path() -> Path:
    return Path(settings.update_env_file).expanduser().resolve()


def _log_file_path() -> Path:
    p = Path(settings.update_logs_dir).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p / "updates.log"


def _append_file_log(message: str) -> None:
    try:
        path = _log_file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        line = f"{utcnow().isoformat()} {message}\n"
        with path.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        # File logging is optional and must not break updates.
        pass


async def _run_precheck(db: AsyncSession, *, root: Path, repo: str) -> dict[str, Any]:
    if shutil.which("git") is None:
        raise UpdateError("Precheck failed: git is not installed")
    if shutil.which("docker") is None:
        raise UpdateError("Precheck failed: docker is not installed")
    if shutil.which("pg_dump") is None or shutil.which("pg_restore") is None:
        raise UpdateError("Precheck failed: pg_dump/pg_restore are required")

    # docker compose availability
    _compose_command_base(compose_files=_compose_files_current(root), env_file=_env_file_path())

    if not root.exists() or not root.is_dir():
        raise UpdateError(f"Precheck failed: update root directory does not exist: {root}")

    compose_current = _compose_files_current(root)
    for compose_file in compose_current:
        if not compose_file.exists():
            raise UpdateError(f"Precheck failed: compose file not found: {compose_file}")

    env_file = _env_file_path()
    if not env_file.exists():
        raise UpdateError(f"Precheck failed: env file not found: {env_file}")

    free_bytes = shutil.disk_usage(str(root)).free
    free_gb = free_bytes / (1024 ** 3)
    min_gb = float(settings.update_min_free_gb or 2)
    if free_gb < min_gb:
        raise UpdateError(f"Precheck failed: low disk space ({free_gb:.2f} GB), required >= {min_gb:.2f} GB")

    await db.execute(text("SELECT 1"))
    versions_payload = await _load_available_versions(force=True)
    if not (versions_payload.get("available_versions") or []):
        raise UpdateError(f"Precheck failed: no release tags available for repo {repo}")

    return {
        "repo": repo,
        "compose_file": ",".join(str(item) for item in compose_current),
        "env_file": str(env_file),
        "disk_free_gb": round(free_gb, 2),
        "versions": versions_payload.get("available_versions") or [],
    }


def _resolve_target_version(target_version: str | None, *, available_versions: list[str]) -> str:
    if not available_versions:
        raise UpdateError("No available versions found")

    if target_version:
        raw = str(target_version).strip()
        if raw.startswith("v"):
            raw = _tag_to_version(raw)
        if not _VERSION_RE.match(raw):
            raise UpdateError("target_version must be X.Y.Z")
        if raw not in set(available_versions):
            raise UpdateError(f"Target version {raw} is not available in GitHub releases/tags")
        return raw

    return str(available_versions[0])


def _fetch_release_code(*, repo: str, version: str, release_dir: Path) -> dict[str, Any]:
    tag = _version_to_tag(version)
    remote = _repo_git_url(repo)
    release_dir.parent.mkdir(parents=True, exist_ok=True)

    if (release_dir / ".git").exists():
        _run_cmd(["git", "fetch", "--tags", "--force"], cwd=str(release_dir))
        _run_cmd(["git", "checkout", "-f", tag], cwd=str(release_dir))
    else:
        if release_dir.exists():
            shutil.rmtree(release_dir)
        _run_cmd(["git", "clone", "--depth", "1", "--branch", tag, remote, str(release_dir)], cwd=str(release_dir.parent))

    if settings.require_signed_tags:
        _run_cmd(["git", "tag", "-v", tag], cwd=str(release_dir))

    rev = _run_cmd(["git", "rev-parse", "HEAD"], cwd=str(release_dir))["stdout_tail"].strip().splitlines()
    commit_sha = rev[-1] if rev else ""

    return {
        "release_dir": str(release_dir),
        "tag": tag,
        "git_commit_sha": commit_sha,
    }


def _build_local_images(*, release_dir: Path, version: str) -> dict[str, Any]:
    backend_image = f"pmm-backend:{version}"
    frontend_image = f"pmm-frontend:{version}"
    worker_image = f"pmm-worker:{version}"

    backend_dir = (release_dir / "backend").resolve()
    frontend_dir = (release_dir / "frontend").resolve()

    _run_cmd(
        ["docker", "build", "--target", "prod", "-t", backend_image, "-f", str(backend_dir / "Dockerfile"), str(backend_dir)],
        cwd=str(release_dir),
        timeout=3600,
    )
    _run_cmd(
        ["docker", "build", "--target", "prod", "-t", frontend_image, "-f", str(frontend_dir / "Dockerfile"), str(frontend_dir)],
        cwd=str(release_dir),
        timeout=3600,
    )
    _run_cmd(
        ["docker", "build", "--target", "prod", "-t", worker_image, "-f", str(backend_dir / "Dockerfile"), str(backend_dir)],
        cwd=str(release_dir),
        timeout=3600,
    )

    return {
        "backend": backend_image,
        "frontend": frontend_image,
        "worker": worker_image,
    }


def _env_updates_for_version(version: str, images: dict[str, str]) -> dict[str, str]:
    return {
        "APP_VERSION": version,
        "PMM_BACKEND_IMAGE": str(images.get("backend") or f"pmm-backend:{version}"),
        "PMM_FRONTEND_IMAGE": str(images.get("frontend") or f"pmm-frontend:{version}"),
        "PMM_WORKER_IMAGE": str(images.get("worker") or f"pmm-worker:{version}"),
    }


def _run_migrations(*, release_dir: Path, env_file: Path, env_updates: dict[str, str]) -> dict[str, Any]:
    compose_files = _compose_files_for_release(release_dir)
    for compose_file in compose_files:
        if not compose_file.exists():
            raise UpdateError(f"Compose file not found in release: {compose_file}")

    compose_base = _compose_command_base(compose_files=compose_files, env_file=env_file)
    runtime_env = os.environ.copy()
    runtime_env.update(env_updates)

    return _run_cmd(
        compose_base + ["run", "--rm", "backend", "alembic", "upgrade", "head"],
        cwd=str(release_dir),
        timeout=3600,
        env=runtime_env,
    )


def _switch_current_symlink(*, root: Path, target_release_dir: Path) -> str | None:
    current = root / "current"
    previous_target: str | None = None

    if current.exists() or current.is_symlink():
        if current.is_symlink():
            try:
                previous_target = str(current.resolve())
            except Exception:
                previous_target = None
            current.unlink()
        elif current.is_dir():
            raise UpdateError(f"Expected symlink at {current}, found directory")
        else:
            current.unlink()

    current.symlink_to(target_release_dir, target_is_directory=True)
    return previous_target


def _deploy_services(*, root: Path, env_file: Path) -> dict[str, Any]:
    compose_files = _compose_files_current(root)
    compose_base = _compose_command_base(compose_files=compose_files, env_file=env_file)
    return _run_cmd(compose_base + ["up", "-d", "backend", "frontend"], cwd=str(root), timeout=1800)


def _healthcheck_backend_ready(*, root: Path, env_file: Path) -> dict[str, Any]:
    compose_files = _compose_files_current(root)
    compose_base = _compose_command_base(compose_files=compose_files, env_file=env_file)
    return _run_cmd(
        compose_base
        + [
            "exec",
            "-T",
            "backend",
            "python",
            "-c",
            "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=10)",
        ],
        cwd=str(root),
        timeout=120,
    )


def _cleanup_old_releases(*, root: Path, keep: int) -> dict[str, Any]:
    releases = _releases_dir(root)
    releases.mkdir(parents=True, exist_ok=True)

    keep_count = max(int(keep), 1)
    current = root / "current"
    current_resolved = None
    if current.exists() and current.is_symlink():
        try:
            current_resolved = current.resolve()
        except Exception:
            current_resolved = None

    dirs = [p for p in releases.iterdir() if p.is_dir()]
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    removed: list[str] = []
    retained = 0
    for d in dirs:
        if current_resolved and d.resolve() == current_resolved:
            retained += 1
            continue
        if retained < keep_count:
            retained += 1
            continue
        shutil.rmtree(d, ignore_errors=True)
        removed.append(d.name)

    return {"removed": removed, "kept": keep_count}


def _step_output(result: Any) -> str | None:
    if result is None:
        return None
    if isinstance(result, dict):
        if result.get("stderr_tail"):
            return str(result.get("stderr_tail"))[:4000]
        if result.get("stdout_tail"):
            return str(result.get("stdout_tail"))[:4000]
        return json.dumps(result, ensure_ascii=False)[:4000]
    return str(result)[:4000]


async def _job_progress(
    db: AsyncSession,
    *,
    job_id: str,
    operation: str,
    phase: str,
    progress_pct: int,
    steps: list[dict[str, Any]],
    message: str | None = None,
) -> None:
    job = (await db.execute(select(BackgroundJob).where(BackgroundJob.id == job_id))).scalars().first()
    if not job:
        return
    payload = dict(job.result_json or {})
    payload.update(
        {
            "operation": operation,
            "phase": phase,
            "progress_pct": max(0, min(int(progress_pct), 100)),
            "steps": steps,
            "updated_at": utcnow().isoformat(),
        }
    )
    if message:
        payload["message"] = message
    job.result_json = payload
    await db.flush()
    await db.commit()


async def _create_step_row(
    db: AsyncSession,
    *,
    update_log_id: int,
    job_id: str,
    step_name: str,
) -> UpdateStep:
    row = UpdateStep(
        update_log_id=update_log_id,
        job_id=job_id,
        step_name=step_name,
        status=UpdateStepStatus.RUNNING,
        started_at=utcnow(),
    )
    db.add(row)
    await db.flush()
    return row


async def _finish_step_row(
    db: AsyncSession,
    *,
    row: UpdateStep,
    status: UpdateStepStatus,
    output_text: str | None,
) -> None:
    row.status = status
    row.finished_at = utcnow()
    row.output_text = output_text[:4000] if output_text else None
    await db.flush()


async def _append_step(
    db: AsyncSession,
    *,
    update_log_id: int,
    job_id: str,
    operation: str,
    steps: list[dict[str, Any]],
    name: str,
    progress_pct: int,
    phase: str,
    fn,
) -> dict[str, Any]:
    step = {
        "name": name,
        "status": "RUNNING",
        "started_at": utcnow().isoformat(),
    }
    steps.append(step)

    step_row = await _create_step_row(db, update_log_id=update_log_id, job_id=job_id, step_name=name)
    await _job_progress(db, job_id=job_id, operation=operation, phase=phase, progress_pct=progress_pct, steps=steps)

    try:
        result = fn()
        if asyncio.iscoroutine(result):
            result = await result
    except Exception as exc:
        step["status"] = "FAILED"
        step["finished_at"] = utcnow().isoformat()
        step["error"] = str(exc)
        await _finish_step_row(db, row=step_row, status=UpdateStepStatus.FAILED, output_text=str(exc))
        await _job_progress(
            db,
            job_id=job_id,
            operation=operation,
            phase=f"{phase}_FAILED",
            progress_pct=progress_pct,
            steps=steps,
            message=str(exc),
        )
        raise

    step["status"] = "SUCCESS"
    step["finished_at"] = utcnow().isoformat()
    output = _step_output(result)
    if output:
        step["output"] = output
    await _finish_step_row(db, row=step_row, status=UpdateStepStatus.SUCCESS, output_text=output)
    await _job_progress(db, job_id=job_id, operation=operation, phase=phase, progress_pct=progress_pct, steps=steps)
    return result if isinstance(result, dict) else {"value": result}


async def _append_skipped_step(
    db: AsyncSession,
    *,
    update_log_id: int,
    job_id: str,
    operation: str,
    steps: list[dict[str, Any]],
    name: str,
    progress_pct: int,
    phase: str,
    reason: str,
) -> None:
    step = {
        "name": name,
        "status": "SKIPPED",
        "started_at": utcnow().isoformat(),
        "finished_at": utcnow().isoformat(),
        "output": reason,
    }
    steps.append(step)

    row = UpdateStep(
        update_log_id=update_log_id,
        job_id=job_id,
        step_name=name,
        status=UpdateStepStatus.SKIPPED,
        started_at=utcnow(),
        finished_at=utcnow(),
        output_text=reason[:4000],
    )
    db.add(row)
    await db.flush()
    await _job_progress(db, job_id=job_id, operation=operation, phase=phase, progress_pct=progress_pct, steps=steps)


def _find_last_successful_update(logs: list[UpdatesLog], update_log_id: int | None) -> UpdatesLog | None:
    if update_log_id is not None:
        for row in logs:
            if int(row.id) == int(update_log_id):
                return row
        return None

    for row in logs:
        details = row.details_json or {}
        op = str(details.get("operation") or "UPDATE").upper()
        if op == "UPDATE" and row.status in (UpdateStatus.SUCCESS, UpdateStatus.ROLLED_BACK):
            return row
    return None


async def run_system_update_job(
    db: AsyncSession,
    *,
    job_id: str,
    mode: str,
    target_version: str | None,
    with_backup: bool | None,
    started_by: int | None,
    update_log_id: int | None = None,
    to_version: str | None = None,
) -> dict[str, Any]:
    operation = "ROLLBACK" if str(mode).upper() == "ROLLBACK" else "UPDATE"
    steps: list[dict[str, Any]] = []
    await _job_progress(db, job_id=job_id, operation=operation, phase="INIT", progress_pct=1, steps=steps)

    lock_acquired = False
    update_row: UpdatesLog | None = None
    previous_release_dir: str | None = None
    root = _update_root()
    env_file = _env_file_path()

    try:
        await _acquire_update_lock(db, job_id=job_id)
        await db.commit()
        lock_acquired = True

        meta = await get_or_create_system_meta(db)
        schema_before = await current_db_schema_version(db)
        repo = _normalize_repo(settings.update_github_repo)

        versions_payload = await _load_available_versions(force=True)
        available_versions = list(versions_payload.get("available_versions") or [])

        if operation == "UPDATE":
            target = _resolve_target_version(target_version, available_versions=available_versions)
            require_backup = bool(with_backup) if with_backup is not None else bool((await get_update_config(db)).get("default_with_backup", True))
            update_row = UpdatesLog(
                from_version=meta.backend_version,
                to_version=target,
                status=UpdateStatus.STARTED,
                started_at=utcnow(),
                started_by=started_by,
                job_id=job_id,
                details_json={
                    "operation": "UPDATE",
                    "job_id": job_id,
                    "repo": repo,
                    "source": versions_payload.get("source"),
                    "available_versions": available_versions,
                    "require_backup": require_backup,
                },
            )
            db.add(update_row)
            await db.flush()
            await db.commit()

            await _append_step(
                db,
                update_log_id=update_row.id,
                job_id=job_id,
                operation=operation,
                steps=steps,
                name="LOCK",
                progress_pct=5,
                phase="LOCK",
                fn=lambda: {"lock": "acquired"},
            )

            await _append_step(
                db,
                update_log_id=update_row.id,
                job_id=job_id,
                operation=operation,
                steps=steps,
                name="PRECHECK",
                progress_pct=12,
                phase="PRECHECK",
                fn=lambda: _run_precheck(db, root=root, repo=repo),
            )

            backup_result: dict[str, Any] | None = None
            backup_verify: dict[str, Any] | None = None
            if require_backup:
                backup_result = await _append_step(
                    db,
                    update_log_id=update_row.id,
                    job_id=job_id,
                    operation=operation,
                    steps=steps,
                    name="BACKUP",
                    progress_pct=20,
                    phase="BACKUP",
                    fn=lambda: backup_service.create_backup(),
                )
                backup_verify = await _append_step(
                    db,
                    update_log_id=update_row.id,
                    job_id=job_id,
                    operation=operation,
                    steps=steps,
                    name="BACKUP_VERIFY",
                    progress_pct=25,
                    phase="BACKUP_VERIFY",
                    fn=lambda: backup_service.verify_backup(str((backup_result or {}).get("filename") or "")),
                )
                if not backup_verify.get("ok"):
                    raise UpdateError(f"Backup verify failed: {backup_verify.get('reason') or 'unknown reason'}")
            else:
                await _append_skipped_step(
                    db,
                    update_log_id=update_row.id,
                    job_id=job_id,
                    operation=operation,
                    steps=steps,
                    name="BACKUP",
                    progress_pct=20,
                    phase="BACKUP",
                    reason="Skipped by request",
                )

            release_dir = (_releases_dir(root) / target).resolve()
            fetch_result = await _append_step(
                db,
                update_log_id=update_row.id,
                job_id=job_id,
                operation=operation,
                steps=steps,
                name="FETCH_CODE",
                progress_pct=38,
                phase="FETCH_CODE",
                fn=lambda: _fetch_release_code(repo=repo, version=target, release_dir=release_dir),
            )

            images = await _append_step(
                db,
                update_log_id=update_row.id,
                job_id=job_id,
                operation=operation,
                steps=steps,
                name="BUILD",
                progress_pct=55,
                phase="BUILD",
                fn=lambda: _build_local_images(release_dir=release_dir, version=target),
            )
            env_updates = _env_updates_for_version(target, images)

            await _append_step(
                db,
                update_log_id=update_row.id,
                job_id=job_id,
                operation=operation,
                steps=steps,
                name="MIGRATE",
                progress_pct=68,
                phase="MIGRATE",
                fn=lambda: _run_migrations(release_dir=release_dir, env_file=env_file, env_updates=env_updates),
            )

            previous_release_dir = _switch_current_symlink(root=root, target_release_dir=release_dir)
            _upsert_env(env_file, env_updates)
            await _append_step(
                db,
                update_log_id=update_row.id,
                job_id=job_id,
                operation=operation,
                steps=steps,
                name="DEPLOY",
                progress_pct=80,
                phase="DEPLOY",
                fn=lambda: _deploy_services(root=root, env_file=env_file),
            )

            await _append_step(
                db,
                update_log_id=update_row.id,
                job_id=job_id,
                operation=operation,
                steps=steps,
                name="HEALTHCHECK",
                progress_pct=90,
                phase="HEALTHCHECK",
                fn=lambda: _healthcheck_backend_ready(root=root, env_file=env_file),
            )

            cleanup_result = await _append_step(
                db,
                update_log_id=update_row.id,
                job_id=job_id,
                operation=operation,
                steps=steps,
                name="FINALIZE",
                progress_pct=96,
                phase="FINALIZE",
                fn=lambda: _cleanup_old_releases(root=root, keep=int(settings.update_releases_keep or 5)),
            )

            db_schema_after = await current_db_schema_version(db)
            meta.backend_version = target
            meta.frontend_version = target
            meta.db_schema_version = db_schema_after
            meta.last_update_at = utcnow()
            meta.last_update_by = started_by
            meta.updater_mode = "server_build"
            meta.update_repo = repo

            update_row.status = UpdateStatus.SUCCESS
            update_row.finished_at = utcnow()
            details = dict(update_row.details_json or {})
            details.update(
                {
                    "steps": steps,
                    "target_version": target,
                    "fetch": fetch_result,
                    "images": images,
                    "backup": backup_result,
                    "backup_verify": backup_verify,
                    "cleanup": cleanup_result,
                    "db_schema_before": schema_before,
                    "db_schema_after": db_schema_after,
                    "job_id": job_id,
                    "compose_file": ",".join(str(item) for item in _compose_files_current(root)),
                    "env_file": str(env_file),
                    "release_dir": str(release_dir),
                    "previous_release_dir": previous_release_dir,
                }
            )
            update_row.details_json = details
            await db.flush()

            final = {
                "operation": "UPDATE",
                "update_log_id": update_row.id,
                "from_version": update_row.from_version,
                "to_version": update_row.to_version,
                "repo": repo,
                "db_schema_before": schema_before,
                "db_schema_after": db_schema_after,
                "steps": steps,
                "rollback_available": True,
            }
            await _job_progress(db, job_id=job_id, operation=operation, phase="DONE", progress_pct=100, steps=steps)
            await db.commit()
            _append_file_log(f"update success job={job_id} from={update_row.from_version} to={update_row.to_version}")
            return final

        # Explicit rollback mode
        logs = await list_updates_logs(db, limit=300)
        src = _find_last_successful_update(logs, update_log_id=update_log_id)
        if not src:
            raise UpdateError("No successful update log found for rollback")

        target = str(to_version or src.from_version or "").strip()
        if not target:
            raise UpdateError("Rollback target version is missing")
        if target.startswith("v"):
            target = _tag_to_version(target)
        if not _VERSION_RE.match(target):
            raise UpdateError("Rollback target version must be X.Y.Z")

        update_row = UpdatesLog(
            from_version=meta.backend_version,
            to_version=target,
            status=UpdateStatus.STARTED,
            started_at=utcnow(),
            started_by=started_by,
            job_id=job_id,
            details_json={
                "operation": "ROLLBACK",
                "job_id": job_id,
                "rollback_of_update_log_id": src.id,
                "repo": repo,
            },
        )
        db.add(update_row)
        await db.flush()
        await db.commit()

        await _append_step(
            db,
            update_log_id=update_row.id,
            job_id=job_id,
            operation=operation,
            steps=steps,
            name="LOCK",
            progress_pct=5,
            phase="LOCK",
            fn=lambda: {"lock": "acquired"},
        )

        await _append_step(
            db,
            update_log_id=update_row.id,
            job_id=job_id,
            operation=operation,
            steps=steps,
            name="PRECHECK",
            progress_pct=15,
            phase="PRECHECK",
            fn=lambda: _run_precheck(db, root=root, repo=repo),
        )

        release_dir = (_releases_dir(root) / target).resolve()
        if not release_dir.exists():
            await _append_step(
                db,
                update_log_id=update_row.id,
                job_id=job_id,
                operation=operation,
                steps=steps,
                name="FETCH_CODE",
                progress_pct=30,
                phase="FETCH_CODE",
                fn=lambda: _fetch_release_code(repo=repo, version=target, release_dir=release_dir),
            )
            images = await _append_step(
                db,
                update_log_id=update_row.id,
                job_id=job_id,
                operation=operation,
                steps=steps,
                name="BUILD",
                progress_pct=50,
                phase="BUILD",
                fn=lambda: _build_local_images(release_dir=release_dir, version=target),
            )
        else:
            await _append_skipped_step(
                db,
                update_log_id=update_row.id,
                job_id=job_id,
                operation=operation,
                steps=steps,
                name="FETCH_CODE",
                progress_pct=30,
                phase="FETCH_CODE",
                reason="Release directory already exists",
            )
            await _append_skipped_step(
                db,
                update_log_id=update_row.id,
                job_id=job_id,
                operation=operation,
                steps=steps,
                name="BUILD",
                progress_pct=50,
                phase="BUILD",
                reason="Images assumed to be available locally",
            )
            images = {
                "backend": f"pmm-backend:{target}",
                "frontend": f"pmm-frontend:{target}",
                "worker": f"pmm-worker:{target}",
            }

        env_updates = _env_updates_for_version(target, images)
        previous_release_dir = _switch_current_symlink(root=root, target_release_dir=release_dir)
        _upsert_env(env_file, env_updates)

        await _append_step(
            db,
            update_log_id=update_row.id,
            job_id=job_id,
            operation=operation,
            steps=steps,
            name="DEPLOY",
            progress_pct=75,
            phase="DEPLOY",
            fn=lambda: _deploy_services(root=root, env_file=env_file),
        )

        await _append_step(
            db,
            update_log_id=update_row.id,
            job_id=job_id,
            operation=operation,
            steps=steps,
            name="HEALTHCHECK",
            progress_pct=90,
            phase="HEALTHCHECK",
            fn=lambda: _healthcheck_backend_ready(root=root, env_file=env_file),
        )

        await _append_step(
            db,
            update_log_id=update_row.id,
            job_id=job_id,
            operation=operation,
            steps=steps,
            name="FINALIZE",
            progress_pct=96,
            phase="FINALIZE",
            fn=lambda: {"rolled_back_to": target},
        )

        db_schema_after = await current_db_schema_version(db)
        meta.backend_version = target
        meta.frontend_version = target
        meta.db_schema_version = db_schema_after
        meta.last_update_at = utcnow()
        meta.last_update_by = started_by
        meta.updater_mode = "server_build"
        meta.update_repo = repo

        update_row.status = UpdateStatus.ROLLED_BACK
        update_row.finished_at = utcnow()
        details = dict(update_row.details_json or {})
        details.update(
            {
                "steps": steps,
                "rollback_of_update_log_id": src.id,
                "db_schema_before": schema_before,
                "db_schema_after": db_schema_after,
                "previous_release_dir": previous_release_dir,
                "release_dir": str(release_dir),
            }
        )
        update_row.details_json = details
        await db.flush()

        final = {
            "operation": "ROLLBACK",
            "update_log_id": update_row.id,
            "from_version": update_row.from_version,
            "to_version": update_row.to_version,
            "steps": steps,
            "db_schema_before": schema_before,
            "db_schema_after": db_schema_after,
            "rollback_of_update_log_id": src.id,
        }
        await _job_progress(db, job_id=job_id, operation=operation, phase="DONE", progress_pct=100, steps=steps)
        await db.commit()
        _append_file_log(f"rollback success job={job_id} from={update_row.from_version} to={update_row.to_version}")
        return final

    except Exception as exc:
        if update_row is not None and operation == "UPDATE" and previous_release_dir:
            # Best effort automatic container rollback to previous release path.
            try:
                previous_path = Path(previous_release_dir).resolve()
                if previous_path.exists():
                    _switch_current_symlink(root=root, target_release_dir=previous_path)
                    env_before = _read_env(env_file)
                    from_version = str(update_row.from_version or env_before.get("APP_VERSION") or "").strip()
                    if _VERSION_RE.match(from_version):
                        _upsert_env(
                            env_file,
                            {
                                "APP_VERSION": from_version,
                                "PMM_BACKEND_IMAGE": f"pmm-backend:{from_version}",
                                "PMM_FRONTEND_IMAGE": f"pmm-frontend:{from_version}",
                                "PMM_WORKER_IMAGE": f"pmm-worker:{from_version}",
                            },
                        )
                    _deploy_services(root=root, env_file=env_file)
                    _healthcheck_backend_ready(root=root, env_file=env_file)
                    rollback_message = f"Automatic rollback applied to {previous_release_dir}"
                    await _append_skipped_step(
                        db,
                        update_log_id=update_row.id,
                        job_id=job_id,
                        operation=operation,
                        steps=steps,
                        name="ROLLBACK",
                        progress_pct=96,
                        phase="ROLLBACK",
                        reason=rollback_message,
                    )
                    update_row.status = UpdateStatus.ROLLED_BACK
                    details = dict(update_row.details_json or {})
                    details["auto_rollback"] = {
                        "ok": True,
                        "target": previous_release_dir,
                    }
                    update_row.details_json = details
                    _append_file_log(f"update failed but rolled back job={job_id}: {exc}")
                else:
                    update_row.status = UpdateStatus.FAILED
            except Exception as rollback_exc:
                update_row.status = UpdateStatus.FAILED
                details = dict(update_row.details_json or {})
                details["auto_rollback"] = {
                    "ok": False,
                    "error": str(rollback_exc),
                }
                update_row.details_json = details
                _append_file_log(f"update failed and rollback failed job={job_id}: {rollback_exc}")
        elif update_row is not None:
            update_row.status = UpdateStatus.FAILED

        if update_row is not None:
            update_row.finished_at = utcnow()
            update_row.error_message = str(exc)[:4000]
            details = dict(update_row.details_json or {})
            details["steps"] = steps
            details["failed_at"] = utcnow().isoformat()
            details["job_id"] = job_id
            update_row.details_json = details
            await db.flush()

        await _job_progress(
            db,
            job_id=job_id,
            operation=operation,
            phase="FAILED",
            progress_pct=95,
            steps=steps,
            message=str(exc),
        )
        await db.commit()
        raise

    finally:
        if lock_acquired:
            try:
                await _release_update_lock(db, job_id=job_id)
                await db.commit()
            except Exception:
                await db.rollback()
