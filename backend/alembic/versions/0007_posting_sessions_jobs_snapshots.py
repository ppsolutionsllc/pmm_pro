"""posting sessions, snapshots, reservations, jobs, and incidents extension

Revision ID: 0007_posting_sessions_jobs
Revises: 0006_request_posting_consistency
Create Date: 2026-03-05 15:10:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0007_posting_sessions_jobs"
down_revision = "0006_request_posting_consistency"
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


def _has_unique(inspector, table_name: str, name: str) -> bool:
    if not _has_table(inspector, table_name):
        return False
    return name in {u["name"] for u in inspector.get_unique_constraints(table_name)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    posting_operation_enum = sa.Enum(
        "CONFIRM",
        "MONTH_END_CONFIRM",
        "ADJUSTMENT",
        name="postingoperation",
    )
    posting_session_status_enum = sa.Enum(
        "IN_PROGRESS",
        "SUCCESS",
        "FAILED",
        name="postingsessionstatus",
    )
    request_snapshot_stage_enum = sa.Enum(
        "SUBMIT",
        "APPROVE",
        "CONFIRM",
        name="requestsnapshotstage",
    )
    reservation_status_enum = sa.Enum(
        "ACTIVE",
        "RELEASED",
        "CONSUMED",
        name="reservationstatus",
    )
    background_job_type_enum = sa.Enum(
        "PDF_EXPORT",
        "XLSX_EXPORT",
        "MONTH_END_BATCH",
        "RECONCILE",
        "VEHICLE_REPORT_EXPORT",
        "REQUESTS_EXPORT",
        "DEBTS_EXPORT",
        name="backgroundjobtype",
    )
    background_job_status_enum = sa.Enum(
        "QUEUED",
        "RUNNING",
        "SUCCESS",
        "FAILED",
        name="backgroundjobstatus",
    )
    fuel_enum = postgresql.ENUM("АБ", "ДП", name="fueltype", create_type=False)

    if not _has_table(inspector, "posting_sessions"):
        op.create_table(
            "posting_sessions",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("request_id", sa.Integer(), nullable=True),
            sa.Column("operation", posting_operation_enum, nullable=False),
            sa.Column("idempotency_key", sa.String(length=128), nullable=False),
            sa.Column("status", posting_session_status_enum, nullable=False, server_default=sa.text("'IN_PROGRESS'")),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("started_by_user_id", sa.Integer(), nullable=True),
            sa.Column("error_code", sa.String(length=64), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("result_ref", sa.JSON(), nullable=True),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.ForeignKeyConstraint(["request_id"], ["requests.id"]),
            sa.ForeignKeyConstraint(["started_by_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("operation", "idempotency_key", name="uq_posting_sessions_operation_idem_key"),
        )
    if not _has_index(inspector, "posting_sessions", "ix_posting_sessions_request_id"):
        op.create_index("ix_posting_sessions_request_id", "posting_sessions", ["request_id"])

    if not _has_table(inspector, "request_snapshots"):
        op.create_table(
            "request_snapshots",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("request_id", sa.Integer(), nullable=False),
            sa.Column("stage", request_snapshot_stage_enum, nullable=False),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["request_id"], ["requests.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_index(inspector, "request_snapshots", "ix_request_snapshots_request_id"):
        op.create_index("ix_request_snapshots_request_id", "request_snapshots", ["request_id"])

    if not _has_table(inspector, "stock_reservations"):
        op.create_table(
            "stock_reservations",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("request_id", sa.Integer(), nullable=False),
            sa.Column("fuel_type", fuel_enum, nullable=False),
            sa.Column("reserved_liters", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("reserved_kg", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("status", reservation_status_enum, nullable=False, server_default=sa.text("'ACTIVE'")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["request_id"], ["requests.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("request_id", "fuel_type", name="uq_stock_reservations_request_fuel"),
        )
    if not _has_index(inspector, "stock_reservations", "ix_stock_reservations_request_id"):
        op.create_index("ix_stock_reservations_request_id", "stock_reservations", ["request_id"])

    if not _has_table(inspector, "background_jobs"):
        op.create_table(
            "background_jobs",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("type", background_job_type_enum, nullable=False),
            sa.Column("status", background_job_status_enum, nullable=False, server_default=sa.text("'QUEUED'")),
            sa.Column("params_json", sa.JSON(), nullable=True),
            sa.Column("result_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_index(inspector, "background_jobs", "ix_background_jobs_status_created_at"):
        op.create_index("ix_background_jobs_status_created_at", "background_jobs", ["status", "created_at"])

    if _has_table(inspector, "admin_alerts"):
        if not _has_column(inspector, "admin_alerts", "severity"):
            op.add_column(
                "admin_alerts",
                sa.Column("severity", sa.String(), nullable=False, server_default=sa.text("'ERROR'")),
            )
            op.alter_column("admin_alerts", "severity", server_default=None)
        if not _has_column(inspector, "admin_alerts", "posting_session_id"):
            op.add_column("admin_alerts", sa.Column("posting_session_id", sa.String(length=36), nullable=True))
        if not _has_column(inspector, "admin_alerts", "resolution_comment"):
            op.add_column("admin_alerts", sa.Column("resolution_comment", sa.Text(), nullable=True))
        if not _has_index(inspector, "admin_alerts", "ix_admin_alerts_posting_session_id"):
            op.create_index("ix_admin_alerts_posting_session_id", "admin_alerts", ["posting_session_id"])
        try:
            op.create_foreign_key(
                "fk_admin_alerts_posting_session_id",
                "admin_alerts",
                "posting_sessions",
                ["posting_session_id"],
                ["id"],
            )
        except Exception:
            pass

    if _has_table(inspector, "stock_issues") and not _has_column(inspector, "stock_issues", "breakdown_json"):
        op.add_column("stock_issues", sa.Column("breakdown_json", sa.JSON(), nullable=True))

    if _has_table(inspector, "app_settings"):
        cnt = bind.execute(
            sa.text("SELECT COUNT(*) FROM app_settings WHERE key = 'features.enable_reservations'")
        ).scalar() or 0
        if cnt == 0:
            bind.execute(
                sa.text(
                    "INSERT INTO app_settings (key, value) VALUES ('features.enable_reservations', 'false')"
                )
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "stock_issues") and _has_column(inspector, "stock_issues", "breakdown_json"):
        op.drop_column("stock_issues", "breakdown_json")

    if _has_table(inspector, "admin_alerts"):
        if _has_index(inspector, "admin_alerts", "ix_admin_alerts_posting_session_id"):
            op.drop_index("ix_admin_alerts_posting_session_id", table_name="admin_alerts")
        if _has_column(inspector, "admin_alerts", "resolution_comment"):
            op.drop_column("admin_alerts", "resolution_comment")
        if _has_column(inspector, "admin_alerts", "posting_session_id"):
            op.drop_column("admin_alerts", "posting_session_id")
        if _has_column(inspector, "admin_alerts", "severity"):
            op.drop_column("admin_alerts", "severity")

    if _has_table(inspector, "background_jobs"):
        if _has_index(inspector, "background_jobs", "ix_background_jobs_status_created_at"):
            op.drop_index("ix_background_jobs_status_created_at", table_name="background_jobs")
        op.drop_table("background_jobs")

    if _has_table(inspector, "stock_reservations"):
        if _has_index(inspector, "stock_reservations", "ix_stock_reservations_request_id"):
            op.drop_index("ix_stock_reservations_request_id", table_name="stock_reservations")
        op.drop_table("stock_reservations")

    if _has_table(inspector, "request_snapshots"):
        if _has_index(inspector, "request_snapshots", "ix_request_snapshots_request_id"):
            op.drop_index("ix_request_snapshots_request_id", table_name="request_snapshots")
        op.drop_table("request_snapshots")

    if _has_table(inspector, "posting_sessions"):
        if _has_index(inspector, "posting_sessions", "ix_posting_sessions_request_id"):
            op.drop_index("ix_posting_sessions_request_id", table_name="posting_sessions")
        op.drop_table("posting_sessions")
