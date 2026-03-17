"""initial

Revision ID: 0001_initial
Revises: 
Create Date: 2026-02-24 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

from app.models import Base

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    # use metadata to create all tables
    Base.metadata.create_all(bind=bind)


def downgrade():
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
