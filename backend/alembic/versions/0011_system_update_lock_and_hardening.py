"""system update lock columns for serialized updates

Revision ID: 0011_update_lock_harden
Revises: 0010_system_updates_and_doc_seq
Create Date: 2026-03-05 21:55:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_update_lock_harden"
down_revision = "0010_system_updates_and_doc_seq"
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
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE updatestatus ADD VALUE IF NOT EXISTS 'ROLLED_BACK'")

    if _has_table(inspector, "system_meta"):
        if not _has_column(inspector, "system_meta", "update_lock"):
            op.add_column(
                "system_meta",
                sa.Column("update_lock", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            )
            op.alter_column("system_meta", "update_lock", server_default=None)
        if not _has_column(inspector, "system_meta", "update_lock_job_id"):
            op.add_column("system_meta", sa.Column("update_lock_job_id", sa.String(length=36), nullable=True))
        if not _has_column(inspector, "system_meta", "update_lock_acquired_at"):
            op.add_column("system_meta", sa.Column("update_lock_acquired_at", sa.DateTime(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "system_meta"):
        if _has_column(inspector, "system_meta", "update_lock_acquired_at"):
            op.drop_column("system_meta", "update_lock_acquired_at")
        if _has_column(inspector, "system_meta", "update_lock_job_id"):
            op.drop_column("system_meta", "update_lock_job_id")
        if _has_column(inspector, "system_meta", "update_lock"):
            op.drop_column("system_meta", "update_lock")

    # Postgres enum value removal is intentionally skipped.
