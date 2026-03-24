from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.engine import make_url
from sqlalchemy import text

from app.config import settings
from app.crud import user as crud_user
from app.db.session import async_session, engine
from app import models
from app.schemas import user as schema_user
from app.services import backup_service


class ResetError(RuntimeError):
    pass


def _alembic_head() -> str | None:
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    script = ScriptDirectory.from_config(config)
    return script.get_current_head()


def _is_postgres() -> bool:
    try:
        backend = (make_url(settings.database_url).drivername or "").split("+", 1)[0]
    except Exception:
        return False
    return backend == "postgresql"


async def _rebuild_schema() -> None:
    head = _alembic_head()
    async with engine.begin() as conn:
        if _is_postgres():
            await conn.exec_driver_sql("DROP SCHEMA IF EXISTS public CASCADE")
            await conn.exec_driver_sql("CREATE SCHEMA public")
        else:
            await conn.run_sync(models.Base.metadata.drop_all)
            await conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
        await conn.run_sync(models.Base.metadata.create_all)
        if head:
            await conn.exec_driver_sql(
                """
                CREATE TABLE alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
                """
            )
            await conn.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:version_num)"),
                {"version_num": head},
            )


async def reset_database(
    *,
    admin_login: str,
    admin_password: str,
    admin_full_name: str,
    create_backup: bool,
) -> dict[str, Any]:
    login = str(admin_login or "").strip()
    password = str(admin_password or "")
    full_name = str(admin_full_name or "").strip() or "First Administrator"

    if not login:
        raise ResetError("Admin login is required")
    if len(password) < 8:
        raise ResetError("Admin password must be at least 8 characters long")

    backup_meta: dict[str, Any] | None = None
    if create_backup:
        try:
            backup_meta = await asyncio.to_thread(
                backup_service.create_backup,
                name_prefix="pre_reset",
            )
        except backup_service.BackupError as exc:
            raise ResetError(str(exc)) from exc

    await _rebuild_schema()

    async with async_session() as session:
        created = await crud_user.create_user(
            session,
            schema_user.UserCreate(
                login=login,
                password=password,
                full_name=full_name,
                role=schema_user.RoleEnum.ADMIN,
                is_active=True,
                department_id=None,
            ),
        )

    return {
        "ok": True,
        "admin_login": created.login,
        "admin_full_name": created.full_name,
        "backup": backup_meta,
    }
