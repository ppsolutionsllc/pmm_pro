from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utcnow
from app.models.department_print_signature import DepartmentPrintSignature


DEFAULT_APPROVAL_TITLE = "З розрахунком згоден:"
DEFAULT_AGREED_TITLE = "ПОГОДЖЕНО:"


def _normalize_payload(data: dict[str, Any]) -> dict[str, str]:
    return {
        "approval_title": str(data.get("approval_title") or DEFAULT_APPROVAL_TITLE).strip() or DEFAULT_APPROVAL_TITLE,
        "approval_position": str(data.get("approval_position") or "").strip(),
        "approval_name": str(data.get("approval_name") or "").strip(),
        "agreed_title": str(data.get("agreed_title") or DEFAULT_AGREED_TITLE).strip() or DEFAULT_AGREED_TITLE,
        "agreed_position": str(data.get("agreed_position") or "").strip(),
        "agreed_name": str(data.get("agreed_name") or "").strip(),
    }


async def get_by_department_id(db: AsyncSession, department_id: int) -> DepartmentPrintSignature | None:
    return (
        await db.execute(
            select(DepartmentPrintSignature).where(DepartmentPrintSignature.department_id == department_id)
        )
    ).scalars().first()


async def get_or_create_for_department(
    db: AsyncSession,
    *,
    department_id: int,
    actor_user_id: int | None,
) -> DepartmentPrintSignature:
    row = await get_by_department_id(db, department_id)
    if row is not None:
        return row
    now = utcnow()
    row = DepartmentPrintSignature(
        department_id=department_id,
        approval_title=DEFAULT_APPROVAL_TITLE,
        approval_position="",
        approval_name="",
        agreed_title=DEFAULT_AGREED_TITLE,
        agreed_position="",
        agreed_name="",
        created_at=now,
        created_by=actor_user_id,
        updated_at=now,
        updated_by=actor_user_id,
    )
    db.add(row)
    await db.flush()
    return row


async def upsert_for_department(
    db: AsyncSession,
    *,
    department_id: int,
    data: dict[str, Any],
    actor_user_id: int | None,
) -> DepartmentPrintSignature:
    row = await get_or_create_for_department(
        db,
        department_id=department_id,
        actor_user_id=actor_user_id,
    )
    payload = _normalize_payload(data)
    row.approval_title = payload["approval_title"]
    row.approval_position = payload["approval_position"]
    row.approval_name = payload["approval_name"]
    row.agreed_title = payload["agreed_title"]
    row.agreed_position = payload["agreed_position"]
    row.agreed_name = payload["agreed_name"]
    row.updated_at = utcnow()
    row.updated_by = actor_user_id
    await db.flush()
    return row


def is_signature_complete(row: DepartmentPrintSignature | None) -> bool:
    if row is None:
        return False
    return bool(
        str(row.approval_position or "").strip()
        and str(row.approval_name or "").strip()
        and str(row.agreed_position or "").strip()
        and str(row.agreed_name or "").strip()
    )


def row_to_payload(row: DepartmentPrintSignature | None) -> dict[str, str]:
    if row is None:
        return {
            "approval_title": DEFAULT_APPROVAL_TITLE,
            "approval_position": "",
            "approval_name": "",
            "agreed_title": DEFAULT_AGREED_TITLE,
            "agreed_position": "",
            "agreed_name": "",
        }
    return _normalize_payload(
        {
            "approval_title": row.approval_title,
            "approval_position": row.approval_position,
            "approval_name": row.approval_name,
            "agreed_title": row.agreed_title,
            "agreed_position": row.agreed_position,
            "agreed_name": row.agreed_name,
        }
    )
