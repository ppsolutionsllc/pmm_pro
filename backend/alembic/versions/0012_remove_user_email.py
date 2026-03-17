"""remove email field from users

Revision ID: 0012_remove_user_email
Revises: 0011_update_lock_harden
Create Date: 2026-03-05 23:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0012_remove_user_email"
down_revision = "0011_update_lock_harden"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    if not _has_table(inspector, table_name):
        return False
    return column_name in {c["name"] for c in inspector.get_columns(table_name)}


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    if not _has_table(inspector, table_name):
        return False
    return index_name in {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_column(inspector, "users", "email"):
        op.drop_column("users", "email")


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "users") and not _has_column(inspector, "users", "email"):
        op.add_column("users", sa.Column("email", sa.String(), nullable=True))

    inspector = sa.inspect(bind)
    if _has_column(inspector, "users", "email") and not _has_index(inspector, "users", "ix_users_email"):
        op.create_index("ix_users_email", "users", ["email"], unique=True)
