"""request rejection fields

Revision ID: 0003_request_rejection_fields
Revises: 0002_request_item_form_fields
Create Date: 2026-02-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0003_request_rejection_fields'
down_revision = '0002_request_item_form_fields'
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
    if not _has_table(inspector, "requests"):
        return

    if not _has_column(inspector, 'requests', 'is_rejected'):
        op.add_column('requests', sa.Column('is_rejected', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    if not _has_column(inspector, 'requests', 'rejection_comment'):
        op.add_column('requests', sa.Column('rejection_comment', sa.Text(), nullable=True))
    if not _has_column(inspector, 'requests', 'rejected_at'):
        op.add_column('requests', sa.Column('rejected_at', sa.DateTime(), nullable=True))
    if not _has_column(inspector, 'requests', 'rejected_by'):
        op.add_column('requests', sa.Column('rejected_by', sa.Integer(), nullable=True))
    if _has_table(inspector, "users") and not _has_fk(inspector, 'requests', 'fk_requests_rejected_by_users'):
        op.create_foreign_key('fk_requests_rejected_by_users', 'requests', 'users', ['rejected_by'], ['id'])


def downgrade():
    op.drop_constraint('fk_requests_rejected_by_users', 'requests', type_='foreignkey')
    op.drop_column('requests', 'rejected_by')
    op.drop_column('requests', 'rejected_at')
    op.drop_column('requests', 'rejection_comment')
    op.drop_column('requests', 'is_rejected')
