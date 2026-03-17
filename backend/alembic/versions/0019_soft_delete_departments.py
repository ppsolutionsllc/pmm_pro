"""soft delete fields for departments

Revision ID: 0019_soft_delete_departments
Revises: 0018_department_print_signatures
Create Date: 2026-03-08 10:45:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0019_soft_delete_departments"
down_revision = "0018_department_print_signatures"
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
    table = "departments"
    if not _has_table(inspector, table):
        return
    if not _has_column(inspector, table, "is_deleted"):
        op.add_column(table, sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    if not _has_column(inspector, table, "deleted_at"):
        op.add_column(table, sa.Column("deleted_at", sa.DateTime(), nullable=True))
    if not _has_column(inspector, table, "deleted_by"):
        op.add_column(table, sa.Column("deleted_by", sa.Integer(), nullable=True))
    if not _has_column(inspector, table, "deletion_reason"):
        op.add_column(table, sa.Column("deletion_reason", sa.Text(), nullable=True))
    if not _has_column(inspector, table, "updated_at"):
        op.add_column(table, sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")))

    fk_names = {fk["name"] for fk in inspector.get_foreign_keys(table)}
    if "fk_departments_deleted_by_users" not in fk_names:
        op.create_foreign_key(
            "fk_departments_deleted_by_users",
            table,
            "users",
            ["deleted_by"],
            ["id"],
        )

    op.alter_column(table, "is_deleted", server_default=None)
    op.alter_column(table, "updated_at", server_default=None)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table = "departments"
    if not _has_table(inspector, table):
        return
    fk_names = {fk["name"] for fk in inspector.get_foreign_keys(table)}
    if "fk_departments_deleted_by_users" in fk_names:
        op.drop_constraint("fk_departments_deleted_by_users", table, type_="foreignkey")
    if _has_column(inspector, table, "updated_at"):
        op.drop_column(table, "updated_at")
    if _has_column(inspector, table, "deletion_reason"):
        op.drop_column(table, "deletion_reason")
    if _has_column(inspector, table, "deleted_by"):
        op.drop_column(table, "deleted_by")
    if _has_column(inspector, table, "deleted_at"):
        op.drop_column(table, "deleted_at")
    if _has_column(inspector, table, "is_deleted"):
        op.drop_column(table, "is_deleted")
