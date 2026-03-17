"""github source updates, update steps, and system meta extensions

Revision ID: 0015_github_server_build_updates
Revises: 0014_pdf_template_version_name
Create Date: 2026-03-06 14:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0015_github_server_build_updates"
down_revision = "0014_pdf_template_version_name"
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

    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE updatestatus ADD VALUE IF NOT EXISTS 'STARTED'")
        op.execute(
            "DO $$ BEGIN "
            "IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'updatestatus') THEN "
            "UPDATE updates_log SET status = 'STARTED' WHERE status = 'RUNNING'; "
            "END IF; "
            "END $$;"
        )

    if _has_table(inspector, "system_meta"):
        if not _has_column(inspector, "system_meta", "updater_mode"):
            op.add_column(
                "system_meta",
                sa.Column("updater_mode", sa.String(length=32), nullable=False, server_default=sa.text("'server_build'")),
            )
            op.alter_column("system_meta", "updater_mode", server_default=None)
        if not _has_column(inspector, "system_meta", "update_repo"):
            op.add_column("system_meta", sa.Column("update_repo", sa.String(length=256), nullable=True))

    if _has_table(inspector, "updates_log"):
        if not _has_column(inspector, "updates_log", "job_id"):
            op.add_column("updates_log", sa.Column("job_id", sa.String(length=36), nullable=True))
        if not _has_index(inspector, "updates_log", "ix_updates_log_job_id"):
            op.create_index("ix_updates_log_job_id", "updates_log", ["job_id"])

    if not _has_table(inspector, "update_steps"):
        step_status_enum = sa.Enum("RUNNING", "SUCCESS", "FAILED", "SKIPPED", name="updatestepstatus")
        op.create_table(
            "update_steps",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("update_log_id", sa.Integer(), nullable=False),
            sa.Column("job_id", sa.String(length=36), nullable=True),
            sa.Column("step_name", sa.String(length=64), nullable=False),
            sa.Column("status", step_status_enum, nullable=False, server_default=sa.text("'RUNNING'")),
            sa.Column("output_text", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["update_log_id"], ["updates_log.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_index(inspector, "update_steps", "ix_update_steps_update_log_id"):
        op.create_index("ix_update_steps_update_log_id", "update_steps", ["update_log_id"])
    if not _has_index(inspector, "update_steps", "ix_update_steps_job_id"):
        op.create_index("ix_update_steps_job_id", "update_steps", ["job_id"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "update_steps"):
        if _has_index(inspector, "update_steps", "ix_update_steps_job_id"):
            op.drop_index("ix_update_steps_job_id", table_name="update_steps")
        if _has_index(inspector, "update_steps", "ix_update_steps_update_log_id"):
            op.drop_index("ix_update_steps_update_log_id", table_name="update_steps")
        op.drop_table("update_steps")

    if _has_table(inspector, "updates_log"):
        if _has_index(inspector, "updates_log", "ix_updates_log_job_id"):
            op.drop_index("ix_updates_log_job_id", table_name="updates_log")
        if _has_column(inspector, "updates_log", "job_id"):
            op.drop_column("updates_log", "job_id")

    if _has_table(inspector, "system_meta"):
        if _has_column(inspector, "system_meta", "update_repo"):
            op.drop_column("system_meta", "update_repo")
        if _has_column(inspector, "system_meta", "updater_mode"):
            op.drop_column("system_meta", "updater_mode")

    # Enum value removals are intentionally skipped for PostgreSQL.

