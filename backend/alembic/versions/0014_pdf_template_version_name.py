"""add name to pdf_template_versions

Revision ID: 0014_pdf_template_version_name
Revises: 0013_pdf_template_builder
Create Date: 2026-03-06 11:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0014_pdf_template_version_name"
down_revision = "0013_pdf_template_builder"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    if not _has_table(inspector, table_name):
        return False
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _has_table(inspector, "pdf_template_versions"):
        return

    if not _has_column(inspector, "pdf_template_versions", "name"):
        op.add_column(
            "pdf_template_versions",
            sa.Column("name", sa.String(length=200), nullable=True),
        )

    bind.execute(
        sa.text(
            """
            UPDATE pdf_template_versions
            SET name = CONCAT('Версія v', version)
            WHERE name IS NULL OR BTRIM(name) = ''
            """
        )
    )
    op.alter_column("pdf_template_versions", "name", existing_type=sa.String(length=200), nullable=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _has_column(inspector, "pdf_template_versions", "name"):
        op.drop_column("pdf_template_versions", "name")

