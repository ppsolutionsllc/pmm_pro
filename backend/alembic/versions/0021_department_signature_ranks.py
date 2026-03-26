"""add department signature ranks

Revision ID: 0021_department_signature_ranks
Revises: 0020_operator_global_scope
Create Date: 2026-03-26 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0021_department_signature_ranks"
down_revision = "0020_operator_global_scope"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    table_names = inspector.get_table_names()
    if table_name not in table_names:
        return False
    return column_name in {c["name"] for c in inspector.get_columns(table_name)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_column(inspector, "department_print_signatures", "approval_rank"):
        op.add_column(
            "department_print_signatures",
            sa.Column("approval_rank", sa.String(length=255), nullable=False, server_default=""),
        )
        op.alter_column("department_print_signatures", "approval_rank", server_default=None)

    if not _has_column(inspector, "department_print_signatures", "agreed_rank"):
        op.add_column(
            "department_print_signatures",
            sa.Column("agreed_rank", sa.String(length=255), nullable=False, server_default=""),
        )
        op.alter_column("department_print_signatures", "agreed_rank", server_default=None)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_column(inspector, "department_print_signatures", "agreed_rank"):
        op.drop_column("department_print_signatures", "agreed_rank")
    if _has_column(inspector, "department_print_signatures", "approval_rank"):
        op.drop_column("department_print_signatures", "approval_rank")
