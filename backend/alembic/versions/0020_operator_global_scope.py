"""make operators global (department_id null)

Revision ID: 0020_operator_global_scope
Revises: 0019_soft_delete_departments
Create Date: 2026-03-17 12:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0020_operator_global_scope"
down_revision = "0019_soft_delete_departments"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    if not _has_table(inspector, table_name):
        return False
    return column_name in {c["name"] for c in inspector.get_columns(table_name)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _has_table(inspector, "users"):
        return
    if not _has_column(inspector, "users", "role") or not _has_column(inspector, "users", "department_id"):
        return

    bind.execute(
        sa.text(
            """
            UPDATE users
            SET department_id = NULL
            WHERE role = 'OPERATOR' AND department_id IS NOT NULL
            """
        )
    )


def downgrade():
    # no-op: previous department binding for operators is intentionally not restored
    return
