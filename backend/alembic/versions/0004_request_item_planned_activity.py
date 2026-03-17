"""request item planned activity

Revision ID: 0004_item_planned_activity
Revises: 0003_request_rejection_fields
Create Date: 2026-02-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0004_item_planned_activity'
down_revision = '0003_request_rejection_fields'
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    if not _has_table(inspector, table_name):
        return False
    return column_name in {c["name"] for c in inspector.get_columns(table_name)}


def _has_fk(inspector, table_name: str, fk_name: str) -> bool:
    if not _has_table(inspector, table_name):
        return False
    return fk_name in {fk.get("name") for fk in inspector.get_foreign_keys(table_name)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _has_table(inspector, "request_items"):
        return

    if not _has_column(inspector, 'request_items', 'planned_activity_id'):
        op.add_column('request_items', sa.Column('planned_activity_id', sa.Integer(), nullable=True))
    if (
        _has_table(inspector, "planned_activities")
        and not _has_fk(inspector, "request_items", "fk_request_items_planned_activity_id_planned_activities")
    ):
        op.create_foreign_key(
            'fk_request_items_planned_activity_id_planned_activities',
            'request_items',
            'planned_activities',
            ['planned_activity_id'],
            ['id'],
        )


def downgrade():
    op.drop_constraint('fk_request_items_planned_activity_id_planned_activities', 'request_items', type_='foreignkey')
    op.drop_column('request_items', 'planned_activity_id')
