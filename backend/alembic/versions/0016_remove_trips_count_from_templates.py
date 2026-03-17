"""replace trips_count print column with training_days_count

Revision ID: 0016_drop_trips_field
Revises: 0015_github_server_build_updates
Create Date: 2026-03-06 22:15:00.000000
"""

from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa


revision = "0016_drop_trips_field"
down_revision = "0015_github_server_build_updates"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    if not _has_table(inspector, table_name):
        return False
    return column_name in {c["name"] for c in inspector.get_columns(table_name)}


def _normalize_columns(columns_raw):
    if isinstance(columns_raw, list):
        return columns_raw
    if isinstance(columns_raw, str):
        try:
            parsed = json.loads(columns_raw)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            return None
    return None


def _convert_column(col: dict, *, reverse: bool = False) -> tuple[dict, bool]:
    src = str(col.get("source") or "")
    cid = str(col.get("id") or "")
    if reverse:
        if src != "item.training_days_count" and cid != "training_days_count":
            return col, False
        updated = dict(col)
        updated["id"] = "trips_count"
        updated["title"] = "Кількість рейсів"
        updated["source"] = "item.trips_count"
        return updated, True

    if src != "item.trips_count" and cid != "trips_count":
        return col, False
    updated = dict(col)
    updated["id"] = "training_days_count"
    updated["title"] = "Кількість навчальних днів"
    updated["source"] = "item.training_days_count"
    return updated, True


def _migrate_columns(reverse: bool = False):
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _has_table(inspector, "pdf_template_versions"):
        return
    if not _has_column(inspector, "pdf_template_versions", "table_columns_json"):
        return

    rows = bind.execute(sa.text("SELECT id, table_columns_json FROM pdf_template_versions")).fetchall()
    for row in rows:
        row_id = row[0]
        columns = _normalize_columns(row[1])
        if not columns:
            continue
        changed = False
        converted = []
        for col in columns:
            if not isinstance(col, dict):
                converted.append(col)
                continue
            upd, did_change = _convert_column(col, reverse=reverse)
            converted.append(upd)
            changed = changed or did_change
        if not changed:
            continue
        bind.execute(
            sa.text(
                "UPDATE pdf_template_versions "
                "SET table_columns_json = CAST(:payload AS JSON) "
                "WHERE id = :row_id"
            ),
            {"payload": json.dumps(converted, ensure_ascii=False), "row_id": row_id},
        )


def upgrade():
    _migrate_columns(reverse=False)


def downgrade():
    _migrate_columns(reverse=True)
