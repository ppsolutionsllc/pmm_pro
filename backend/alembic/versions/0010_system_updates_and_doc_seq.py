"""system update metadata/logs and issue doc sequence

Revision ID: 0010_system_updates_and_doc_seq
Revises: 0009_posting_session_result_json
Create Date: 2026-03-05 21:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_system_updates_and_doc_seq"
down_revision = "0009_posting_session_result_json"
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

    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE backgroundjobtype ADD VALUE IF NOT EXISTS 'SYSTEM_UPDATE'")
        op.execute("ALTER TYPE postingoperation ADD VALUE IF NOT EXISTS 'EXPORT'")
        op.execute("ALTER TYPE postingoperation ADD VALUE IF NOT EXISTS 'RECONCILE'")
        op.execute("ALTER TYPE postingoperation ADD VALUE IF NOT EXISTS 'UPDATE'")

    if not _has_table(inspector, "issue_doc_sequences"):
        op.create_table(
            "issue_doc_sequences",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("scope_key", sa.String(length=16), nullable=False),
            sa.Column("next_value", sa.Integer(), nullable=False, server_default=sa.text("1")),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("scope_key", name="uq_issue_doc_sequences_scope_key"),
        )
    if not _has_index(inspector, "issue_doc_sequences", "ix_issue_doc_sequences_scope_key"):
        op.create_index("ix_issue_doc_sequences_scope_key", "issue_doc_sequences", ["scope_key"])

    if not _has_table(inspector, "system_meta"):
        op.create_table(
            "system_meta",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("backend_version", sa.String(length=64), nullable=False, server_default=sa.text("'dev'")),
            sa.Column("frontend_version", sa.String(length=64), nullable=False, server_default=sa.text("'dev'")),
            sa.Column("db_schema_version", sa.String(length=128), nullable=True),
            sa.Column("last_update_at", sa.DateTime(), nullable=False),
            sa.Column("last_update_by", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["last_update_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    update_status_enum = sa.Enum("RUNNING", "SUCCESS", "FAILED", name="updatestatus")
    if not _has_table(inspector, "updates_log"):
        op.create_table(
            "updates_log",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("from_version", sa.String(length=64), nullable=True),
            sa.Column("to_version", sa.String(length=64), nullable=False),
            sa.Column("status", update_status_enum, nullable=False, server_default=sa.text("'RUNNING'")),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("started_by", sa.Integer(), nullable=True),
            sa.Column("details_json", sa.JSON(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["started_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_index(inspector, "updates_log", "ix_updates_log_started_at"):
        op.create_index("ix_updates_log_started_at", "updates_log", ["started_at"])

    if _has_table(inspector, "system_meta"):
        count = bind.execute(sa.text("SELECT COUNT(*) FROM system_meta WHERE id = 1")).scalar() or 0
        if count == 0:
            cols = {c["name"] for c in inspector.get_columns("system_meta")}
            values = {
                "id": 1,
                "backend_version": "dev",
                "frontend_version": "dev",
                "last_update_at": sa.func.now(),
            }
            if "update_lock" in cols:
                values["update_lock"] = False
            if "updater_mode" in cols:
                values["updater_mode"] = "server_build"

            insert_cols = []
            insert_params = {}
            for key, value in values.items():
                if key not in cols:
                    continue
                insert_cols.append(key)
                if hasattr(value, "compile"):
                    continue
                insert_params[key] = value

            sql_values = []
            for col in insert_cols:
                if col == "last_update_at":
                    sql_values.append("CURRENT_TIMESTAMP")
                else:
                    sql_values.append(f":{col}")
            bind.execute(
                sa.text(
                    f"INSERT INTO system_meta ({', '.join(insert_cols)}) "
                    f"VALUES ({', '.join(sql_values)})"
                ),
                insert_params,
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "updates_log"):
        if _has_index(inspector, "updates_log", "ix_updates_log_started_at"):
            op.drop_index("ix_updates_log_started_at", table_name="updates_log")
        op.drop_table("updates_log")

    if _has_table(inspector, "system_meta"):
        op.drop_table("system_meta")

    if _has_table(inspector, "issue_doc_sequences"):
        if _has_index(inspector, "issue_doc_sequences", "ix_issue_doc_sequences_scope_key"):
            op.drop_index("ix_issue_doc_sequences_scope_key", table_name="issue_doc_sequences")
        op.drop_table("issue_doc_sequences")

    # Enum value downgrades for PostgreSQL are intentionally skipped.
