import argparse
import asyncio
from typing import Optional

from sqlalchemy import select

from app.config import settings
from app.crud import user as crud_user
from app.db.session import async_session
from app.models.user import RoleEnum as UserRoleEnum
from app.models.user import User
from app.schemas import user as schema_user
from app.services import reset_service


def _resolve_value(cli_value: Optional[str], env_value: Optional[str]) -> str:
    return (cli_value or env_value or "").strip()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PMM management CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser(
        "create-first-admin",
        help="Create first administrator if none exists",
    )
    create.add_argument("--login", default="", help="Admin login")
    create.add_argument("--password", default="", help="Admin password (min 8 chars)")
    create.add_argument("--full-name", default="", help="Admin full name")

    reset = sub.add_parser(
        "reset-database",
        help="Drop all application data and bootstrap a new administrator",
    )
    reset.add_argument("--confirm", default="", help="Confirmation word RESET")
    reset.add_argument("--admin-login", default="", help="New admin login")
    reset.add_argument("--admin-password", default="", help="New admin password (min 8 chars)")
    reset.add_argument("--admin-full-name", default="", help="New admin full name")
    reset.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating a backup before reset",
    )
    return parser


async def _has_admin() -> bool:
    async with async_session() as session:
        row = (
            await session.execute(
                select(User.id).where(User.role == UserRoleEnum.ADMIN).limit(1)
            )
        ).first()
        return bool(row)


async def _create_first_admin(login: str, password: str, full_name: str) -> int:
    if await _has_admin():
        print("First admin bootstrap skipped: ADMIN user already exists.")
        return 2

    async with async_session() as session:
        existing = await crud_user.get_user_by_login(session, login)
        if existing:
            print(f"Cannot create first admin: login '{login}' already exists.")
            return 2

        created = await crud_user.create_user(
            session,
            schema_user.UserCreate(
                login=login,
                password=password,
                full_name=full_name or "First Administrator",
                role=schema_user.RoleEnum.ADMIN,
                is_active=True,
                department_id=None,
            ),
        )
        print(f"First admin created successfully: id={created.id}, login={created.login}")
        return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "create-first-admin":
        login = _resolve_value(args.login, settings.first_admin_login)
        password = _resolve_value(args.password, settings.first_admin_password)
        full_name = _resolve_value(args.full_name, settings.first_admin_full_name)

        if not login:
            parser.error("Login is required: pass --login or set FIRST_ADMIN_LOGIN")
        if not password:
            parser.error("Password is required: pass --password or set FIRST_ADMIN_PASSWORD")
        if len(password) < 8:
            parser.error("Password must be at least 8 characters long")

        return asyncio.run(_create_first_admin(login=login, password=password, full_name=full_name))

    if args.command == "reset-database":
        login = _resolve_value(args.admin_login, settings.first_admin_login)
        password = _resolve_value(args.admin_password, settings.first_admin_password)
        full_name = _resolve_value(args.admin_full_name, settings.first_admin_full_name) or "First Administrator"

        if (args.confirm or "").strip().upper() != "RESET":
            parser.error("Pass --confirm RESET to allow full database reset")
        if not login:
            parser.error("Admin login is required: pass --admin-login or set FIRST_ADMIN_LOGIN")
        if not password:
            parser.error("Admin password is required: pass --admin-password or set FIRST_ADMIN_PASSWORD")
        if len(password) < 8:
            parser.error("Admin password must be at least 8 characters long")

        result = asyncio.run(
            reset_service.reset_database(
                admin_login=login,
                admin_password=password,
                admin_full_name=full_name,
                create_backup=not bool(args.no_backup),
            )
        )
        print(
            f"Database reset complete. New admin: login={result['admin_login']}, "
            f"backup={result.get('backup', {}).get('filename') if result.get('backup') else 'skipped'}"
        )
        return 0

    parser.error("Unknown command")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
