"""request item form fields

Revision ID: 0002_request_item_form_fields
Revises: 0001_initial
Create Date: 2026-02-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002_request_item_form_fields'
down_revision = '0001_initial'
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

    if not _has_column(inspector, 'request_items', 'route_id'):
        op.add_column('request_items', sa.Column('route_id', sa.Integer(), nullable=True))
    if _has_table(inspector, "routes") and not _has_fk(inspector, 'request_items', 'fk_request_items_route_id_routes'):
        op.create_foreign_key('fk_request_items_route_id_routes', 'request_items', 'routes', ['route_id'], ['id'])

    if not _has_column(inspector, 'request_items', 'route_is_manual'):
        op.add_column('request_items', sa.Column('route_is_manual', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    if not _has_column(inspector, 'request_items', 'route_text'):
        op.add_column('request_items', sa.Column('route_text', sa.Text(), nullable=True))
    if not _has_column(inspector, 'request_items', 'distance_km_per_trip'):
        op.add_column('request_items', sa.Column('distance_km_per_trip', sa.Float(), nullable=True))
    if not _has_column(inspector, 'request_items', 'justification_text'):
        op.add_column('request_items', sa.Column('justification_text', sa.Text(), nullable=True))
    if not _has_column(inspector, 'request_items', 'persons_involved_count'):
        op.add_column('request_items', sa.Column('persons_involved_count', sa.Integer(), nullable=True))
    if not _has_column(inspector, 'request_items', 'training_days_count'):
        op.add_column('request_items', sa.Column('training_days_count', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('request_items', 'training_days_count')
    op.drop_column('request_items', 'persons_involved_count')
    op.drop_column('request_items', 'justification_text')
    op.drop_column('request_items', 'distance_km_per_trip')
    op.drop_column('request_items', 'route_text')
    op.drop_column('request_items', 'route_is_manual')

    op.drop_constraint('fk_request_items_route_id_routes', 'request_items', type_='foreignkey')
    op.drop_column('request_items', 'route_id')
