"""request posting consistency, audit, debt, and adjustments

Revision ID: 0006_request_posting_consistency
Revises: 0005_schema_alignment
Create Date: 2026-03-05 00:00:01.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_request_posting_consistency"
down_revision = "0005_schema_alignment"
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
    dialect = bind.dialect.name

    fuel_enum = sa.Enum("АБ", "ДП", name="fueltype")
    stock_issue_status_enum = sa.Enum("POSTED", "DEBT", "REVERSED", name="stockissuestatus")
    debt_status_enum = sa.Enum("OPEN", "CLOSED", name="debtstatus")

    if _has_table(inspector, "requests"):
        if not _has_column(inspector, "requests", "has_debt"):
            op.add_column("requests", sa.Column("has_debt", sa.Boolean(), nullable=False, server_default=sa.text("false")))
            op.alter_column("requests", "has_debt", server_default=None)
        if not _has_column(inspector, "requests", "coeff_snapshot_ab"):
            op.add_column("requests", sa.Column("coeff_snapshot_ab", sa.Float(), nullable=True))
        if not _has_column(inspector, "requests", "coeff_snapshot_dp"):
            op.add_column("requests", sa.Column("coeff_snapshot_dp", sa.Float(), nullable=True))
        if not _has_column(inspector, "requests", "coeff_snapshot_at"):
            op.add_column("requests", sa.Column("coeff_snapshot_at", sa.DateTime(), nullable=True))
        if not _has_column(inspector, "requests", "coeff_snapshot_by"):
            op.add_column("requests", sa.Column("coeff_snapshot_by", sa.Integer(), nullable=True))

        if not _has_index(inspector, "requests", "uq_requests_one_active_per_department"):
            op.create_index(
                "uq_requests_one_active_per_department",
                "requests",
                ["department_id"],
                unique=True,
                postgresql_where=sa.text("status IN ('SUBMITTED','APPROVED','ISSUED_BY_OPERATOR')"),
                sqlite_where=sa.text("status IN ('SUBMITTED','APPROVED','ISSUED_BY_OPERATOR')"),
            )

    if _has_table(inspector, "stock_issues"):
        if not _has_column(inspector, "stock_issues", "issue_doc_no"):
            op.add_column("stock_issues", sa.Column("issue_doc_no", sa.String(), nullable=True))
        if not _has_column(inspector, "stock_issues", "status"):
            op.add_column(
                "stock_issues",
                sa.Column("status", stock_issue_status_enum, nullable=False, server_default=sa.text("'POSTED'")),
            )
            op.alter_column("stock_issues", "status", server_default=None)
        if not _has_column(inspector, "stock_issues", "posted_by"):
            op.add_column("stock_issues", sa.Column("posted_by", sa.Integer(), nullable=True))
        if not _has_column(inspector, "stock_issues", "posted_at"):
            op.add_column("stock_issues", sa.Column("posted_at", sa.DateTime(), nullable=True))
        if not _has_column(inspector, "stock_issues", "has_debt"):
            op.add_column(
                "stock_issues",
                sa.Column("has_debt", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            )
            op.alter_column("stock_issues", "has_debt", server_default=None)
        if not _has_column(inspector, "stock_issues", "debt_liters"):
            op.add_column(
                "stock_issues",
                sa.Column("debt_liters", sa.Float(), nullable=False, server_default=sa.text("0")),
            )
            op.alter_column("stock_issues", "debt_liters", server_default=None)
        if not _has_column(inspector, "stock_issues", "debt_kg"):
            op.add_column(
                "stock_issues",
                sa.Column("debt_kg", sa.Float(), nullable=False, server_default=sa.text("0")),
            )
            op.alter_column("stock_issues", "debt_kg", server_default=None)

        # backfill doc numbers and posted_at for legacy rows
        op.execute(
            """
            UPDATE stock_issues
            SET issue_doc_no = COALESCE(issue_doc_no, 'PMM-LEGACY-' || CAST(id AS TEXT)),
                posted_at = COALESCE(posted_at, created_at)
            """
        )

        if not _has_index(inspector, "stock_issues", "uq_stock_issues_request_id"):
            op.create_index("uq_stock_issues_request_id", "stock_issues", ["request_id"], unique=True)
        if not _has_index(inspector, "stock_issues", "uq_stock_issues_issue_doc_no"):
            op.create_index("uq_stock_issues_issue_doc_no", "stock_issues", ["issue_doc_no"], unique=True)

        if _has_column(inspector, "stock_issues", "issue_doc_no"):
            op.alter_column("stock_issues", "issue_doc_no", existing_type=sa.String(), nullable=False)
        if _has_column(inspector, "stock_issues", "posted_at"):
            op.alter_column("stock_issues", "posted_at", existing_type=sa.DateTime(), nullable=False)

    if not _has_table(inspector, "stock_issue_lines"):
        op.create_table(
            "stock_issue_lines",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("stock_issue_id", sa.Integer(), nullable=False),
            sa.Column("fuel_type", fuel_enum, nullable=False),
            sa.Column("requested_liters", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("requested_kg", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("issued_liters", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("issued_kg", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("missing_liters", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("missing_kg", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.ForeignKeyConstraint(["stock_issue_id"], ["stock_issues.id"]),
        )
        op.create_index("ix_stock_issue_lines_issue_id", "stock_issue_lines", ["stock_issue_id"])
        op.create_index("uq_stock_issue_lines_issue_fuel", "stock_issue_lines", ["stock_issue_id", "fuel_type"], unique=True)

    if not _has_table(inspector, "fuel_debts"):
        op.create_table(
            "fuel_debts",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("request_id", sa.Integer(), nullable=False),
            sa.Column("fuel_type", fuel_enum, nullable=False),
            sa.Column("missing_liters", sa.Float(), nullable=False),
            sa.Column("missing_kg", sa.Float(), nullable=False),
            sa.Column("status", debt_status_enum, nullable=False, server_default=sa.text("'OPEN'")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("close_comment", sa.Text(), nullable=True),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
            sa.Column("closed_by", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["request_id"], ["requests.id"]),
        )
        op.create_index("ix_fuel_debts_request_id", "fuel_debts", ["request_id"])

    if not _has_table(inspector, "request_audit"):
        op.create_table(
            "request_audit",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("request_id", sa.Integer(), nullable=False),
            sa.Column("actor_user_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("from_status", sa.String(), nullable=True),
            sa.Column("to_status", sa.String(), nullable=True),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["request_id"], ["requests.id"]),
        )
        op.create_index("ix_request_audit_request_id", "request_audit", ["request_id"])

    if not _has_table(inspector, "fuel_coeff_history"):
        op.create_table(
            "fuel_coeff_history",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("fuel_type", fuel_enum, nullable=False),
            sa.Column("density_kg_per_l", sa.Float(), nullable=False),
            sa.Column("changed_by", sa.Integer(), nullable=True),
            sa.Column("changed_at", sa.DateTime(), nullable=False),
            sa.Column("comment", sa.Text(), nullable=True),
        )

    if not _has_table(inspector, "admin_alerts"):
        op.create_table(
            "admin_alerts",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("type", sa.String(), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("request_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.Column("resolved_by", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["request_id"], ["requests.id"]),
        )
        op.create_index("ix_admin_alerts_request_id", "admin_alerts", ["request_id"])

    if not _has_table(inspector, "stock_adjustments"):
        op.create_table(
            "stock_adjustments",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("adjustment_doc_no", sa.String(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("uq_stock_adjustments_doc_no", "stock_adjustments", ["adjustment_doc_no"], unique=True)

    if not _has_table(inspector, "stock_adjustment_lines"):
        op.create_table(
            "stock_adjustment_lines",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("adjustment_id", sa.Integer(), nullable=False),
            sa.Column("fuel_type", fuel_enum, nullable=False),
            sa.Column("delta_liters", sa.Float(), nullable=False),
            sa.Column("delta_kg", sa.Float(), nullable=False),
            sa.Column("request_id", sa.Integer(), nullable=True),
            sa.Column("comment", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["adjustment_id"], ["stock_adjustments.id"]),
            sa.ForeignKeyConstraint(["request_id"], ["requests.id"]),
        )
        op.create_index("ix_stock_adjustment_lines_adjustment_id", "stock_adjustment_lines", ["adjustment_id"])

    # initialize coefficient history from current settings once
    if _has_table(inspector, "fuel_coeff_history") and _has_table(inspector, "density_settings"):
        cnt = bind.execute(sa.text("SELECT COUNT(*) FROM fuel_coeff_history")).scalar() or 0
        if cnt == 0:
            dens = bind.execute(
                sa.text(
                    "SELECT density_factor_ab, density_factor_dp FROM density_settings ORDER BY id LIMIT 1"
                )
            ).fetchone()
            if dens:
                bind.execute(
                    sa.text(
                        "INSERT INTO fuel_coeff_history (fuel_type, density_kg_per_l, changed_by, changed_at, comment) "
                        "VALUES (:ft, :v, NULL, CURRENT_TIMESTAMP, :c)"
                    ),
                    {"ft": "АБ", "v": float(dens[0]), "c": "initial from density_settings"},
                )
                bind.execute(
                    sa.text(
                        "INSERT INTO fuel_coeff_history (fuel_type, density_kg_per_l, changed_by, changed_at, comment) "
                        "VALUES (:ft, :v, NULL, CURRENT_TIMESTAMP, :c)"
                    ),
                    {"ft": "ДП", "v": float(dens[1]), "c": "initial from density_settings"},
                )

    # backfill request snapshots for already active/post-processed requests
    if _has_table(inspector, "requests") and _has_table(inspector, "density_settings"):
        dens = bind.execute(
            sa.text("SELECT density_factor_ab, density_factor_dp FROM density_settings ORDER BY id LIMIT 1")
        ).fetchone()
        if dens:
            bind.execute(
                sa.text(
                    "UPDATE requests SET coeff_snapshot_ab = :ab, coeff_snapshot_dp = :dp, "
                    "coeff_snapshot_at = COALESCE(coeff_snapshot_at, created_at) "
                    "WHERE coeff_snapshot_ab IS NULL OR coeff_snapshot_dp IS NULL"
                ),
                {"ab": float(dens[0]), "dp": float(dens[1])},
            )

    # SQLite doesn't support altering enum types; nothing else required.
    if dialect == "sqlite":
        pass


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "stock_adjustment_lines"):
        if _has_index(inspector, "stock_adjustment_lines", "ix_stock_adjustment_lines_adjustment_id"):
            op.drop_index("ix_stock_adjustment_lines_adjustment_id", table_name="stock_adjustment_lines")
        op.drop_table("stock_adjustment_lines")
    if _has_table(inspector, "stock_adjustments"):
        if _has_index(inspector, "stock_adjustments", "uq_stock_adjustments_doc_no"):
            op.drop_index("uq_stock_adjustments_doc_no", table_name="stock_adjustments")
        op.drop_table("stock_adjustments")
    if _has_table(inspector, "admin_alerts"):
        if _has_index(inspector, "admin_alerts", "ix_admin_alerts_request_id"):
            op.drop_index("ix_admin_alerts_request_id", table_name="admin_alerts")
        op.drop_table("admin_alerts")
    if _has_table(inspector, "fuel_coeff_history"):
        op.drop_table("fuel_coeff_history")
    if _has_table(inspector, "request_audit"):
        if _has_index(inspector, "request_audit", "ix_request_audit_request_id"):
            op.drop_index("ix_request_audit_request_id", table_name="request_audit")
        op.drop_table("request_audit")
    if _has_table(inspector, "fuel_debts"):
        if _has_index(inspector, "fuel_debts", "ix_fuel_debts_request_id"):
            op.drop_index("ix_fuel_debts_request_id", table_name="fuel_debts")
        op.drop_table("fuel_debts")
    if _has_table(inspector, "stock_issue_lines"):
        if _has_index(inspector, "stock_issue_lines", "uq_stock_issue_lines_issue_fuel"):
            op.drop_index("uq_stock_issue_lines_issue_fuel", table_name="stock_issue_lines")
        if _has_index(inspector, "stock_issue_lines", "ix_stock_issue_lines_issue_id"):
            op.drop_index("ix_stock_issue_lines_issue_id", table_name="stock_issue_lines")
        op.drop_table("stock_issue_lines")
    if _has_table(inspector, "stock_issues"):
        if _has_index(inspector, "stock_issues", "uq_stock_issues_issue_doc_no"):
            op.drop_index("uq_stock_issues_issue_doc_no", table_name="stock_issues")
        if _has_index(inspector, "stock_issues", "uq_stock_issues_request_id"):
            op.drop_index("uq_stock_issues_request_id", table_name="stock_issues")
    if _has_table(inspector, "requests"):
        if _has_index(inspector, "requests", "uq_requests_one_active_per_department"):
            op.drop_index("uq_requests_one_active_per_department", table_name="requests")
