"""posting session result_json and stock issue unique request safeguard

Revision ID: 0009_posting_session_result_json
Revises: 0008_admin_incidents
Create Date: 2026-03-05 19:35:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_posting_session_result_json"
down_revision = "0008_admin_incidents"
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

    if _has_table(inspector, "posting_sessions") and not _has_column(inspector, "posting_sessions", "result_json"):
        op.add_column("posting_sessions", sa.Column("result_json", sa.JSON(), nullable=True))
        if _has_column(inspector, "posting_sessions", "result_ref"):
            bind.execute(
                sa.text(
                    "UPDATE posting_sessions SET result_json = result_ref WHERE result_json IS NULL AND result_ref IS NOT NULL"
                )
            )

    if _has_table(inspector, "stock_issues") and not _has_index(inspector, "stock_issues", "uq_stock_issues_request_id"):
        op.create_index("uq_stock_issues_request_id", "stock_issues", ["request_id"], unique=True)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _has_table(inspector, "posting_sessions") and _has_column(inspector, "posting_sessions", "result_json"):
        op.drop_column("posting_sessions", "result_json")
