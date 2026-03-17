"""add admin incidents table

Revision ID: 0008_admin_incidents
Revises: 0007_posting_sessions_jobs
Create Date: 2026-03-05 16:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_admin_incidents"
down_revision = "0007_posting_sessions_jobs"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    if not _has_table(inspector, table_name):
        return False
    return index_name in {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    incident_type_enum = sa.Enum(
        "POSTING_FAILED",
        "ADJUSTMENT_FAILED",
        "EXPORT_FAILED",
        "BACKUP_FAILED",
        "RECONCILE_FAILED",
        "SYSTEM_UPDATE_FAILED",
        "SECURITY_ALERT",
        name="incidenttype",
    )
    incident_severity_enum = sa.Enum(
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
        name="incidentseverity",
    )
    incident_status_enum = sa.Enum(
        "NEW",
        "IN_PROGRESS",
        "RESOLVED",
        name="incidentstatus",
    )

    if not _has_table(inspector, "admin_incidents"):
        op.create_table(
            "admin_incidents",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("type", incident_type_enum, nullable=False),
            sa.Column("severity", incident_severity_enum, nullable=False, server_default=sa.text("'HIGH'")),
            sa.Column("status", incident_status_enum, nullable=False, server_default=sa.text("'NEW'")),
            sa.Column("message", sa.String(length=512), nullable=False),
            sa.Column("details_json", sa.JSON(), nullable=True),
            sa.Column("request_id", sa.Integer(), nullable=True),
            sa.Column("posting_session_id", sa.String(length=36), nullable=True),
            sa.Column("job_id", sa.String(length=36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.Column("resolved_by", sa.Integer(), nullable=True),
            sa.Column("resolution_comment", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["job_id"], ["background_jobs.id"]),
            sa.ForeignKeyConstraint(["posting_session_id"], ["posting_sessions.id"]),
            sa.ForeignKeyConstraint(["request_id"], ["requests.id"]),
            sa.ForeignKeyConstraint(["resolved_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_index(inspector, "admin_incidents", "ix_admin_incidents_request_id"):
        op.create_index("ix_admin_incidents_request_id", "admin_incidents", ["request_id"])
    if not _has_index(inspector, "admin_incidents", "ix_admin_incidents_posting_session_id"):
        op.create_index("ix_admin_incidents_posting_session_id", "admin_incidents", ["posting_session_id"])
    if not _has_index(inspector, "admin_incidents", "ix_admin_incidents_job_id"):
        op.create_index("ix_admin_incidents_job_id", "admin_incidents", ["job_id"])
    if not _has_index(inspector, "admin_incidents", "ix_admin_incidents_status_created_at"):
        op.create_index("ix_admin_incidents_status_created_at", "admin_incidents", ["status", "created_at"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "admin_incidents"):
        if _has_index(inspector, "admin_incidents", "ix_admin_incidents_status_created_at"):
            op.drop_index("ix_admin_incidents_status_created_at", table_name="admin_incidents")
        if _has_index(inspector, "admin_incidents", "ix_admin_incidents_job_id"):
            op.drop_index("ix_admin_incidents_job_id", table_name="admin_incidents")
        if _has_index(inspector, "admin_incidents", "ix_admin_incidents_posting_session_id"):
            op.drop_index("ix_admin_incidents_posting_session_id", table_name="admin_incidents")
        if _has_index(inspector, "admin_incidents", "ix_admin_incidents_request_id"):
            op.drop_index("ix_admin_incidents_request_id", table_name="admin_incidents")
        op.drop_table("admin_incidents")
