"""drop legacy trips_count from request_items

Revision ID: 0017_drop_reqitem_trips
Revises: 0016_drop_trips_field
Create Date: 2026-03-06 22:40:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0017_drop_reqitem_trips"
down_revision = "0016_drop_trips_field"
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
    if _has_column(inspector, "request_items", "trips_count"):
        op.drop_column("request_items", "trips_count")


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _has_column(inspector, "request_items", "trips_count"):
        op.add_column("request_items", sa.Column("trips_count", sa.Integer(), nullable=True))

