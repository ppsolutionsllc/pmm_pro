"""add pdf template builder tables and default template

Revision ID: 0013_pdf_template_builder
Revises: 0012_remove_user_email
Create Date: 2026-03-06 00:30:00.000000
"""

from __future__ import annotations

import json
import uuid

from alembic import op
import sqlalchemy as sa


revision = "0013_pdf_template_builder"
down_revision = "0012_remove_user_email"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    if not _has_table(inspector, table_name):
        return False
    return index_name in {idx["name"] for idx in inspector.get_indexes(table_name)}


def _default_layout_json() -> dict:
    return {
        "page": {"size": "A4", "orientation": "portrait", "margin_mm": {"top": 12, "right": 10, "bottom": 14, "left": 10}},
        "blocks": ["header", "service_block", "table", "totals", "signatures", "footer"],
        "header": {
            "title": "ЗАЯВКА НА ПММ",
            "subtitle": "Табличний бланк",
        },
        "totals": {"show": True},
        "signatures": {"show": True, "left_label": "Підпис відповідального", "right_label": "Підпис отримувача"},
        "footer": {"disclaimer": "Документ сформовано автоматично в системі Облік ПММ"},
    }


def _default_columns_json() -> list[dict]:
    return [
        {"id": "row_no", "title": "№ з/п", "width": 6, "align": "center", "format": "number_0", "source": "computed.row_no", "visible": True, "rules": {"visibility_rule": "ALWAYS"}},
        {"id": "planned_activity_name", "title": "Заходи", "width": 14, "align": "left", "format": "text", "source": "item.planned_activity_name", "visible": True, "rules": {"visibility_rule": "ALWAYS"}},
        {"id": "vehicle_name", "title": "Марка авто (генератора)", "width": 13, "align": "left", "format": "text", "source": "item.vehicle_name", "visible": True, "rules": {"visibility_rule": "ALWAYS"}},
        {"id": "route_text", "title": "Плече підвезення (км)", "width": 10, "align": "left", "format": "text", "source": "item.route_text", "visible": True, "rules": {"visibility_rule": "ALWAYS"}},
        {"id": "training_days_count", "title": "Кількість навчальних днів", "width": 8, "align": "center", "format": "number_0", "source": "item.training_days_count", "visible": True, "rules": {"visibility_rule": "ALWAYS"}},
        {"id": "norm_l_100km", "title": "Норма витрати (л/100км)", "width": 9, "align": "right", "format": "number_2", "source": "item.consumption_l_per_100km", "visible": True, "rules": {"visibility_rule": "ALWAYS"}},
        {"id": "required_liters", "title": "Загальна витрата (л/год)", "width": 9, "align": "right", "format": "number_2", "source": "item.required_liters", "visible": True, "rules": {"visibility_rule": "ALWAYS"}},
        {"id": "total_km", "title": "Загальна витрата (л/100 км)", "width": 9, "align": "right", "format": "number_2", "source": "item.total_km", "visible": True, "rules": {"visibility_rule": "ALWAYS"}},
        {"id": "need_10_days_ab", "title": "Потреба на 10 днів (АБ)", "width": 8, "align": "right", "format": "number_2", "source": "computed.need_10_days_ab", "visible": True, "rules": {"visibility_rule": "ALWAYS"}},
        {"id": "need_10_days_dp", "title": "Потреба на 10 днів (ДП)", "width": 8, "align": "right", "format": "number_2", "source": "computed.need_10_days_dp", "visible": True, "rules": {"visibility_rule": "ALWAYS"}},
        {"id": "note", "title": "Примітка", "width": 6, "align": "left", "format": "text", "source": "item.justification_text", "visible": True, "rules": {"visibility_rule": "ALWAYS"}},
    ]


def _default_mapping_json() -> dict:
    return {
        "header_fields": [
            {"label": "Номер заявки", "source": "request.request_number"},
            {"label": "Підрозділ", "source": "department.name"},
            {"label": "Дата створення", "source": "request.created_at"},
            {"label": "Період", "source": "request.period_text"},
        ],
        "table_rows_source": "request.items",
        "totals_fields": [
            {"label": "Усього АБ", "source": "computed.total_ab_liters"},
            {"label": "Усього ДП", "source": "computed.total_dp_liters"},
            {"label": "Заборгованість АБ", "source": "computed.debt_ab_liters"},
            {"label": "Заборгованість ДП", "source": "computed.debt_dp_liters"},
        ],
        "service_fields": [
            {"label": "Статус", "source": "request.status"},
            {"label": "Номер акта", "source": "issue.issue_doc_no"},
            {"label": "Версія системи", "source": "system.backend_version"},
        ],
    }


def _default_rules_json() -> dict:
    return {
        "allowed_visibility_rules": ["ALWAYS", "IF_STATUS_IN", "IF_DEBT_GT_0", "IF_ROLE_IS_ADMIN"],
    }


def _default_service_block_json() -> dict:
    return {
        "show_request_number": True,
        "show_generated_at": True,
        "show_department": True,
        "show_status": True,
        "show_audit_users": True,
        "show_issue_doc_no": True,
        "show_system_version": True,
        "show_qr": True,
        "rules": {
            "issue_doc_no": "IF_STATUS_IN",
            "debt_section": "IF_DEBT_GT_0",
        },
    }


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    scope_enum = sa.Enum("REQUEST_FUEL", name="pdf_template_scope_enum")
    version_status_enum = sa.Enum("DRAFT", "PUBLISHED", "ARCHIVED", name="pdf_template_version_status_enum")
    artifact_type_enum = sa.Enum("PDF_REQUEST_FORM", name="print_artifact_type_enum")

    if not _has_table(inspector, "pdf_templates"):
        op.create_table(
            "pdf_templates",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("scope", scope_enum, nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)
    if not _has_table(inspector, "pdf_template_versions"):
        op.create_table(
            "pdf_template_versions",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("template_id", sa.String(length=36), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("status", version_status_enum, nullable=False),
            sa.Column("layout_json", sa.JSON(), nullable=False),
            sa.Column("table_columns_json", sa.JSON(), nullable=False),
            sa.Column("mapping_json", sa.JSON(), nullable=False),
            sa.Column("rules_json", sa.JSON(), nullable=False),
            sa.Column("service_block_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("published_at", sa.DateTime(), nullable=True),
            sa.Column("published_by", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["published_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["template_id"], ["pdf_templates.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("template_id", "version", name="uq_pdf_template_versions_template_version"),
        )
        op.create_index("ix_pdf_template_versions_template_id", "pdf_template_versions", ["template_id"], unique=False)

    inspector = sa.inspect(bind)
    if not _has_table(inspector, "request_print_snapshots"):
        op.create_table(
            "request_print_snapshots",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("request_id", sa.Integer(), nullable=False),
            sa.Column("template_id", sa.String(length=36), nullable=False),
            sa.Column("template_version_id", sa.String(length=36), nullable=False),
            sa.Column("snapshot_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["request_id"], ["requests.id"]),
            sa.ForeignKeyConstraint(["template_id"], ["pdf_templates.id"]),
            sa.ForeignKeyConstraint(["template_version_id"], ["pdf_template_versions.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("request_id", "template_version_id", name="uq_request_print_snapshot_req_tplver"),
        )
        op.create_index("ix_request_print_snapshots_request_id", "request_print_snapshots", ["request_id"], unique=False)

    inspector = sa.inspect(bind)
    if not _has_table(inspector, "print_artifacts"):
        op.create_table(
            "print_artifacts",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("request_id", sa.Integer(), nullable=False),
            sa.Column("artifact_type", artifact_type_enum, nullable=False),
            sa.Column("template_version_id", sa.String(length=36), nullable=False),
            sa.Column("file_path", sa.Text(), nullable=False),
            sa.Column("sha256", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["request_id"], ["requests.id"]),
            sa.ForeignKeyConstraint(["template_version_id"], ["pdf_template_versions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_print_artifacts_request_id", "print_artifacts", ["request_id"], unique=False)
        op.create_index("ix_print_artifacts_template_version_id", "print_artifacts", ["template_version_id"], unique=False)

    inspector = sa.inspect(bind)
    if _has_table(inspector, "pdf_templates") and _has_table(inspector, "pdf_template_versions"):
        existing = bind.execute(sa.text("SELECT id FROM pdf_templates WHERE scope = 'REQUEST_FUEL' ORDER BY created_at ASC LIMIT 1")).fetchone()
        if not existing:
            template_id = str(uuid.uuid4())
            version_id = str(uuid.uuid4())
            bind.execute(
                sa.text(
                    """
                    INSERT INTO pdf_templates (id, name, scope, is_active, created_at, created_by)
                    VALUES (:id, :name, 'REQUEST_FUEL', true, NOW(), NULL)
                    """
                ),
                {"id": template_id, "name": "Заявка ПММ (Стандарт)"},
            )
            version_cols = {c["name"] for c in inspector.get_columns("pdf_template_versions")}
            version_values = {
                "id": version_id,
                "template_id": template_id,
                "version": 1,
                "name": "Версія v1",
                "status": "PUBLISHED",
                "layout_json": json.dumps(_default_layout_json(), ensure_ascii=False),
                "table_columns_json": json.dumps(_default_columns_json(), ensure_ascii=False),
                "mapping_json": json.dumps(_default_mapping_json(), ensure_ascii=False),
                "rules_json": json.dumps(_default_rules_json(), ensure_ascii=False),
                "service_block_json": json.dumps(_default_service_block_json(), ensure_ascii=False),
                "created_at": sa.text("NOW()"),
                "created_by": None,
                "published_at": sa.text("NOW()"),
                "published_by": None,
            }

            insert_cols: list[str] = []
            sql_values: list[str] = []
            params: dict[str, object] = {}
            for key, value in version_values.items():
                if key not in version_cols:
                    continue
                insert_cols.append(key)
                if isinstance(value, sa.sql.elements.TextClause):
                    sql_values.append(str(value))
                elif key in {"layout_json", "table_columns_json", "mapping_json", "rules_json", "service_block_json"}:
                    sql_values.append(f"CAST(:{key} AS JSON)")
                    params[key] = value
                else:
                    sql_values.append(f":{key}")
                    params[key] = value

            bind.execute(
                sa.text(
                    f"INSERT INTO pdf_template_versions ({', '.join(insert_cols)}) "
                    f"VALUES ({', '.join(sql_values)})"
                ),
                params,
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_index(inspector, "print_artifacts", "ix_print_artifacts_template_version_id"):
        op.drop_index("ix_print_artifacts_template_version_id", table_name="print_artifacts")
    if _has_index(inspector, "print_artifacts", "ix_print_artifacts_request_id"):
        op.drop_index("ix_print_artifacts_request_id", table_name="print_artifacts")
    if _has_table(inspector, "print_artifacts"):
        op.drop_table("print_artifacts")

    inspector = sa.inspect(bind)
    if _has_index(inspector, "request_print_snapshots", "ix_request_print_snapshots_request_id"):
        op.drop_index("ix_request_print_snapshots_request_id", table_name="request_print_snapshots")
    if _has_table(inspector, "request_print_snapshots"):
        op.drop_table("request_print_snapshots")

    inspector = sa.inspect(bind)
    if _has_index(inspector, "pdf_template_versions", "ix_pdf_template_versions_template_id"):
        op.drop_index("ix_pdf_template_versions_template_id", table_name="pdf_template_versions")
    if _has_table(inspector, "pdf_template_versions"):
        op.drop_table("pdf_template_versions")

    inspector = sa.inspect(bind)
    if _has_table(inspector, "pdf_templates"):
        op.drop_table("pdf_templates")

    for enum_name in (
        "print_artifact_type_enum",
        "pdf_template_version_status_enum",
        "pdf_template_scope_enum",
    ):
        try:
            op.execute(f"DROP TYPE IF EXISTS {enum_name}")
        except Exception:
            pass
