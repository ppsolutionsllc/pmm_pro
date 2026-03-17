"""add department print signatures

Revision ID: 0018_department_print_signatures
Revises: 0017_drop_reqitem_trips
Create Date: 2026-03-07 10:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


revision = "0018_department_print_signatures"
down_revision = "0017_drop_reqitem_trips"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _has_table(inspector, "department_print_signatures"):
        op.create_table(
            "department_print_signatures",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("department_id", sa.Integer(), nullable=False),
            sa.Column("approval_title", sa.String(length=255), nullable=False, server_default="З розрахунком згоден:"),
            sa.Column("approval_position", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("approval_name", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("agreed_title", sa.String(length=255), nullable=False, server_default="ПОГОДЖЕНО:"),
            sa.Column("agreed_position", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("agreed_name", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("updated_by", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        )
        op.create_index(
            "ix_department_print_signatures_department_id",
            "department_print_signatures",
            ["department_id"],
            unique=True,
        )

    # bootstrap one row per existing department
    bind.execute(
        text(
            """
            INSERT INTO department_print_signatures (
                department_id,
                approval_title,
                approval_position,
                approval_name,
                agreed_title,
                agreed_position,
                agreed_name,
                created_at,
                updated_at
            )
            SELECT d.id, 'З розрахунком згоден:', '', '', 'ПОГОДЖЕНО:', '', '', NOW(), NOW()
            FROM departments d
            WHERE NOT EXISTS (
                SELECT 1 FROM department_print_signatures s WHERE s.department_id = d.id
            )
            """
        )
    )

    op.alter_column("department_print_signatures", "approval_title", server_default=None)
    op.alter_column("department_print_signatures", "approval_position", server_default=None)
    op.alter_column("department_print_signatures", "approval_name", server_default=None)
    op.alter_column("department_print_signatures", "agreed_title", server_default=None)
    op.alter_column("department_print_signatures", "agreed_position", server_default=None)
    op.alter_column("department_print_signatures", "agreed_name", server_default=None)
    op.alter_column("department_print_signatures", "created_at", server_default=None)
    op.alter_column("department_print_signatures", "updated_at", server_default=None)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _has_table(inspector, "department_print_signatures"):
        op.drop_index("ix_department_print_signatures_department_id", table_name="department_print_signatures")
        op.drop_table("department_print_signatures")
