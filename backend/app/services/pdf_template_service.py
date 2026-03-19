from __future__ import annotations

import base64
import hashlib
import io
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import qrcode
from fastapi import HTTPException
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.time import utcnow
from app.crud import department_print_signature as crud_dept_signature
from app.models.department import Department
from app.models.pdf_template import (
    PdfTemplate,
    PdfTemplateScope,
    PdfTemplateVersion,
    PdfTemplateVersionStatus,
    PrintArtifact,
    PrintArtifactType,
    RequestPrintSnapshot,
)
from app.models.request import Request
from app.models.request_item import RequestItem
from app.models.request_snapshot import RequestSnapshot, RequestSnapshotStage
from app.models.stock import FuelType, StockIssue
from app.models.system_meta import SystemMeta
from app.services.barcode_service import build_code39_png_b64, build_unique_barcode_value

try:
    from weasyprint import HTML
except Exception as exc:  # pragma: no cover
    HTML = None
    _WEASYPRINT_IMPORT_ERROR = exc
else:
    _WEASYPRINT_IMPORT_ERROR = None


jinja_env = Environment(
    loader=FileSystemLoader("app/templates"),
    autoescape=select_autoescape(["html", "xml"]),
)


AVAILABLE_FORMATS = ["text", "number_0", "number_2", "date", "datetime"]
AVAILABLE_VISIBILITY_RULES = ["ALWAYS", "IF_STATUS_IN", "IF_DEBT_GT_0", "IF_ROLE_IS_ADMIN"]
AVAILABLE_TEXT_STYLES = ["normal", "bold", "italic"]

AVAILABLE_SOURCES = [
    "request.request_number",
    "request.created_at",
    "request.submitted_at",
    "request.approved_at",
    "request.operator_issued_at",
    "request.dept_confirmed_at",
    "request.stock_posted_at",
    "request.status",
    "request.route_text",
    "request.distance_km_per_trip",
    "request.justification_text",
    "request.period_text",
    "request.persons_involved_count",
    "request.training_days_count",
    "request.coeff_snapshot_ab",
    "request.coeff_snapshot_dp",
    "request.coeff_snapshot_at",
    "request.has_debt",
    "department.name",
    "issue.issue_doc_no",
    "issue.posted_at",
    "system.backend_version",
    "system.frontend_version",
    "system.db_schema_version",
    "computed.row_no",
    "computed.need_10_days_ab",
    "computed.need_10_days_dp",
    "computed.total_ab_liters",
    "computed.total_dp_liters",
    "computed.debt_ab_liters",
    "computed.debt_dp_liters",
    "item.planned_activity_name",
    "item.vehicle_name",
    "item.vehicle_plate",
    "item.vehicle_fuel_type",
    "item.route_text",
    "item.distance_km_per_trip",
    "item.total_km",
    "item.required_liters",
    "item.required_kg",
    "item.consumption_l_per_100km",
    "item.justification_text",
]

DEFAULT_APPROVAL_TITLE = "З розрахунком згоден:"
DEFAULT_AGREED_TITLE = "ПОГОДЖЕНО:"


def _default_layout_json() -> dict[str, Any]:
    return {
        "page": {"size": "A4", "orientation": "landscape", "margin_mm": {"top": 12, "right": 10, "bottom": 14, "left": 10}},
        "blocks": ["header", "table", "totals", "signatures", "footer", "service_block"],
        "typography": {"font_size_pt": 11, "text_style": "normal"},
        "header": {
            "title": "ЗАЯВКА",
            "subtitle": "Прошу, Вас дати вказівку начальнику служби ПММ, що до видачі пального на бойову підготовку",
            "commander_line": "Командиру військової частини A7014",
        },
        "totals": {"show": True},
        "signatures": {
            "show": True,
            "use_department_signatures": True,
            "approval_title": "З розрахунком згоден:",
            "approval_position": "Командир взводу матеріального забезпечення",
            "approval_name": "",
            "agreed_title": "ПОГОДЖЕНО:",
            "agreed_position": "Заступник командира бригади:",
            "agreed_name": "",
        },
        "footer": {"disclaimer": "Документ сформовано автоматично в системі Облік ПММ"},
    }


def _default_columns_json() -> list[dict[str, Any]]:
    return [
        {"id": "row_no", "title": "№", "width": 6, "align": "center", "format": "number_0", "source": "computed.row_no", "visible": True, "rules": {"visibility_rule": "ALWAYS"}},
        {"id": "planned_activity_name", "title": "Заплановані заходи", "width": 22, "align": "left", "format": "text", "source": "item.planned_activity_name", "visible": True, "rules": {"visibility_rule": "ALWAYS"}},
        {"id": "vehicle_name", "title": "Автомобіль", "width": 14, "align": "left", "format": "text", "source": "item.vehicle_name", "visible": True, "rules": {"visibility_rule": "ALWAYS"}},
        {"id": "vehicle_plate", "title": "Номерний знак", "width": 12, "align": "center", "format": "text", "source": "item.vehicle_plate", "visible": True, "rules": {"visibility_rule": "ALWAYS"}},
        {"id": "route_text", "title": "Маршрут", "width": 16, "align": "left", "format": "text", "source": "item.route_text", "visible": True, "rules": {"visibility_rule": "ALWAYS"}},
        {"id": "distance_km_per_trip", "title": "Плече підвезення (км)", "width": 11, "align": "right", "format": "number_2", "source": "item.distance_km_per_trip", "visible": True, "rules": {"visibility_rule": "ALWAYS"}},
        {"id": "total_km", "title": "Пробіг (км)", "width": 10, "align": "right", "format": "number_2", "source": "item.total_km", "visible": True, "rules": {"visibility_rule": "ALWAYS"}},
        {"id": "required_liters", "title": "Потреба (л)", "width": 9, "align": "right", "format": "number_2", "source": "item.required_liters", "visible": True, "rules": {"visibility_rule": "ALWAYS"}},
        {"id": "vehicle_fuel_type", "title": "Пальне", "width": 8, "align": "center", "format": "text", "source": "item.vehicle_fuel_type", "visible": True, "rules": {"visibility_rule": "ALWAYS"}},
        {"id": "justification_text", "title": "Примітка", "width": 12, "align": "left", "format": "text", "source": "item.justification_text", "visible": True, "rules": {"visibility_rule": "ALWAYS"}},
    ]


_LEGACY_REQUEST_SOURCES = {
    "request.request_number",
    "request.status",
    "request.route_text",
    "request.distance_km_per_trip",
    "request.training_days_count",
    "request.persons_involved_count",
    "request.coeff_snapshot_ab",
    "request.coeff_snapshot_dp",
    "request.created_at",
    "request.justification_text",
}


def _is_legacy_request_table(columns: list[dict[str, Any]]) -> bool:
    if len(columns) != len(_LEGACY_REQUEST_SOURCES):
        return False
    sources = {str(c.get("source") or "").strip() for c in columns if isinstance(c, dict)}
    return sources == _LEGACY_REQUEST_SOURCES


def _default_mapping_json() -> dict[str, Any]:
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


def _default_rules_json() -> dict[str, Any]:
    return {"allowed_visibility_rules": AVAILABLE_VISIBILITY_RULES}


def _default_service_block_json() -> dict[str, Any]:
    return {
        "show_request_number": True,
        "show_generated_at": True,
        "show_department": True,
        "show_system_version": True,
        "show_qr": True,
    }


_SERVICE_BLOCK_ALLOWED_KEYS = (
    "show_request_number",
    "show_generated_at",
    "show_department",
    "show_system_version",
    "show_qr",
)


def _normalize_service_block_json(payload: dict[str, Any] | None) -> dict[str, Any]:
    base = _default_service_block_json()
    incoming = payload if isinstance(payload, dict) else {}
    return {key: bool(incoming.get(key, base[key])) for key in _SERVICE_BLOCK_ALLOWED_KEYS}


@dataclass
class PreparedPrintDocument:
    snapshot: dict[str, Any]
    pdf_bytes: bytes


def default_version_payload() -> dict[str, Any]:
    return {
        "layout_json": _default_layout_json(),
        "table_columns_json": _default_columns_json(),
        "mapping_json": _default_mapping_json(),
        "rules_json": _default_rules_json(),
        "service_block_json": _default_service_block_json(),
    }


def _format_value(value: Any, fmt: str) -> str:
    if value is None:
        return ""
    if fmt == "number_0":
        try:
            return f"{float(value):.0f}"
        except Exception:
            return str(value)
    if fmt == "number_2":
        try:
            return f"{float(value):.2f}"
        except Exception:
            return str(value)
    if fmt == "date":
        try:
            dt = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
            return dt.strftime("%d.%m.%Y")
        except Exception:
            return str(value)
    if fmt == "datetime":
        try:
            dt = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
            return dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            return str(value)
    return str(value)


def _normalize_column(column: dict[str, Any], index: int) -> dict[str, Any]:
    source = str(column.get("source") or "").strip()
    if source not in AVAILABLE_SOURCES:
        raise HTTPException(status_code=400, detail=f"Unsupported column source: {source}")
    fmt = str(column.get("format") or "text")
    if fmt not in AVAILABLE_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unsupported column format: {fmt}")
    align = str(column.get("align") or "left")
    if align not in ("left", "center", "right"):
        raise HTTPException(status_code=400, detail=f"Unsupported column align: {align}")
    text_style = str(column.get("text_style") or "normal").strip().lower()
    if text_style not in AVAILABLE_TEXT_STYLES:
        raise HTTPException(status_code=400, detail=f"Unsupported text style: {text_style}")
    try:
        width = float(column.get("width") or 0)
    except Exception:
        width = 0
    if width <= 0:
        width = 8
    try:
        font_size_pt = float(column.get("font_size_pt") or 11)
    except Exception:
        font_size_pt = 11
    if font_size_pt < 8:
        font_size_pt = 8
    if font_size_pt > 24:
        font_size_pt = 24

    rules = column.get("rules") if isinstance(column.get("rules"), dict) else {}
    visibility_rule = str(rules.get("visibility_rule") or "ALWAYS")
    if visibility_rule not in AVAILABLE_VISIBILITY_RULES:
        raise HTTPException(status_code=400, detail=f"Unsupported visibility rule: {visibility_rule}")

    return {
        "id": str(column.get("id") or f"col_{index + 1}"),
        "title": str(column.get("title") or f"Колонка {index + 1}"),
        "width": round(width, 2),
        "align": align,
        "text_style": text_style,
        "font_size_pt": round(font_size_pt, 1),
        "format": fmt,
        "source": source,
        "visible": bool(column.get("visible", True)),
        "rules": {
            "visibility_rule": visibility_rule,
            "statuses": list(rules.get("statuses") or []),
            "role": str(rules.get("role") or "").upper() if rules.get("role") else None,
        },
    }


def normalize_columns(columns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(columns, list) or not columns:
        raise HTTPException(status_code=400, detail="table_columns_json must be non-empty list")
    out = [_normalize_column(c, i) for i, c in enumerate(columns)]
    if not any(bool(c.get("visible", True)) for c in out):
        raise HTTPException(status_code=400, detail="At least one column must be visible")
    return out


def _normalize_version_name(name: str | None, fallback_version: int) -> str:
    raw = str(name or "").strip()
    if raw:
        return raw[:200]
    return f"Версія v{fallback_version}"


def _rule_match(rule_value: Any, *, status: str, has_debt: bool, role: str | None) -> bool:
    if rule_value is None:
        return True
    if isinstance(rule_value, str):
        if rule_value == "ALWAYS":
            return True
        if rule_value == "IF_DEBT_GT_0":
            return has_debt
        if rule_value == "IF_ROLE_IS_ADMIN":
            return (role or "") == "ADMIN"
        return True
    if not isinstance(rule_value, dict):
        return True
    rule = str(rule_value.get("visibility_rule") or "ALWAYS")
    if rule == "ALWAYS":
        return True
    if rule == "IF_DEBT_GT_0":
        return has_debt
    if rule == "IF_ROLE_IS_ADMIN":
        return (role or "") == "ADMIN"
    if rule == "IF_STATUS_IN":
        statuses = [str(s) for s in (rule_value.get("statuses") or [])]
        return status in statuses if statuses else False
    return True


def _deep_get(data: dict[str, Any], path: str) -> Any:
    cur: Any = data
    for chunk in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(chunk)
        else:
            return None
    return cur


def _resolve_source_value(source: str, *, request_ctx: dict[str, Any], item_ctx: dict[str, Any] | None) -> Any:
    if source == "computed.row_no":
        return (item_ctx or {}).get("row_no")
    if source == "computed.need_10_days_ab":
        return (item_ctx or {}).get("need_10_days_ab")
    if source == "computed.need_10_days_dp":
        return (item_ctx or {}).get("need_10_days_dp")
    if source == "computed.total_ab_liters":
        return _deep_get(request_ctx, "computed.total_ab_liters")
    if source == "computed.total_dp_liters":
        return _deep_get(request_ctx, "computed.total_dp_liters")
    if source == "computed.debt_ab_liters":
        return _deep_get(request_ctx, "computed.debt_ab_liters")
    if source == "computed.debt_dp_liters":
        return _deep_get(request_ctx, "computed.debt_dp_liters")

    if source.startswith("item."):
        return _deep_get(item_ctx or {}, source.split(".", 1)[1])
    if source.startswith("request."):
        return _deep_get(request_ctx.get("request") or {}, source.split(".", 1)[1])
    if source.startswith("department."):
        return _deep_get(request_ctx.get("department") or {}, source.split(".", 1)[1])
    if source.startswith("issue."):
        return _deep_get(request_ctx.get("issue") or {}, source.split(".", 1)[1])
    if source.startswith("system."):
        return _deep_get(request_ctx.get("system") or {}, source.split(".", 1)[1])
    return None


def _source_requires_item_row(source: str) -> bool:
    src = str(source or "").strip()
    if src.startswith("item."):
        return True
    return src in {"computed.row_no", "computed.need_10_days_ab", "computed.need_10_days_dp"}


def _build_qr_b64(url: str) -> str:
    qr = qrcode.make(url, box_size=4)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def _print_storage_dir() -> Path:
    root = Path(settings.artifacts_dir).expanduser().resolve() / "print_artifacts"
    root.mkdir(parents=True, exist_ok=True)
    return root


async def list_templates(db: AsyncSession) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(PdfTemplate)
            .options(selectinload(PdfTemplate.versions))
            .order_by(PdfTemplate.created_at.desc())
        )
    ).scalars().all()

    out: list[dict[str, Any]] = []
    for t in rows:
        published = [v for v in (t.versions or []) if v.status == PdfTemplateVersionStatus.PUBLISHED]
        published.sort(key=lambda v: v.version, reverse=True)
        top = published[0] if published else None
        out.append(
            {
                "id": t.id,
                "name": t.name,
                "scope": t.scope.value if t.scope else None,
                "is_active": bool(t.is_active),
                "created_at": t.created_at,
                "created_by": t.created_by,
                "last_published_version": top.version if top else None,
                "last_published_version_id": top.id if top else None,
            }
        )
    return out


async def create_template(
    db: AsyncSession,
    *,
    name: str,
    scope: str,
    is_active: bool,
    created_by: int | None,
) -> PdfTemplate:
    try:
        resolved_scope = PdfTemplateScope(scope)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unsupported scope: {scope}") from exc

    row = PdfTemplate(
        name=name.strip(),
        scope=resolved_scope,
        is_active=bool(is_active),
        created_by=created_by,
        created_at=utcnow(),
    )
    db.add(row)
    await db.flush()

    payload = default_version_payload()
    ver = PdfTemplateVersion(
        template_id=row.id,
        version=1,
        name="Основна форма",
        status=PdfTemplateVersionStatus.PUBLISHED,
        layout_json=payload["layout_json"],
        table_columns_json=payload["table_columns_json"],
        mapping_json=payload["mapping_json"],
        rules_json=payload["rules_json"],
        service_block_json=payload["service_block_json"],
        created_by=created_by,
        created_at=utcnow(),
        published_at=utcnow(),
        published_by=created_by,
    )
    db.add(ver)
    await db.flush()
    return row


async def get_template_detail(db: AsyncSession, template_id: str) -> dict[str, Any]:
    row = (
        await db.execute(
            select(PdfTemplate)
            .options(selectinload(PdfTemplate.versions))
            .where(PdfTemplate.id == template_id)
        )
    ).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="PDF template not found")

    templates = await list_templates(db)
    base = next((x for x in templates if x["id"] == row.id), None)
    versions = sorted(row.versions or [], key=lambda v: v.version, reverse=True)
    return {
        "template": base,
        "versions": [
            {
                "id": v.id,
                "template_id": v.template_id,
                "version": v.version,
                "name": v.name or _normalize_version_name(None, v.version),
                "status": v.status.value if v.status else None,
                "layout_json": v.layout_json,
                "table_columns_json": v.table_columns_json,
                "mapping_json": v.mapping_json,
                "rules_json": v.rules_json,
                "service_block_json": v.service_block_json,
                "created_at": v.created_at,
                "created_by": v.created_by,
                "published_at": v.published_at,
                "published_by": v.published_by,
            }
            for v in versions
        ],
        "available_sources": AVAILABLE_SOURCES,
        "available_formats": AVAILABLE_FORMATS,
        "available_visibility_rules": AVAILABLE_VISIBILITY_RULES,
    }


async def delete_template(db: AsyncSession, *, template_id: str) -> dict[str, Any]:
    template = (
        await db.execute(
            select(PdfTemplate)
            .options(selectinload(PdfTemplate.versions))
            .where(PdfTemplate.id == template_id)
        )
    ).scalars().first()
    if not template:
        raise HTTPException(status_code=404, detail="PDF template not found")

    version_ids = [v.id for v in (template.versions or [])]
    artifacts = []
    if version_ids:
        artifacts = (
            await db.execute(
                select(PrintArtifact).where(PrintArtifact.template_version_id.in_(version_ids))
            )
        ).scalars().all()

    deleted_files = 0
    for art in artifacts:
        try:
            path = Path(str(art.file_path)).expanduser().resolve()
            if path.exists():
                path.unlink()
                deleted_files += 1
        except Exception:
            # DB cleanup should not fail because of filesystem issues.
            pass

    deleted_artifacts = 0
    if version_ids:
        deleted_artifacts = len(artifacts)
        await db.execute(delete(PrintArtifact).where(PrintArtifact.template_version_id.in_(version_ids)))
        await db.execute(
            delete(RequestPrintSnapshot).where(
                or_(
                    RequestPrintSnapshot.template_id == template_id,
                    RequestPrintSnapshot.template_version_id.in_(version_ids),
                )
            )
        )
        await db.execute(delete(PdfTemplateVersion).where(PdfTemplateVersion.id.in_(version_ids)))
    else:
        await db.execute(delete(RequestPrintSnapshot).where(RequestPrintSnapshot.template_id == template_id))

    await db.execute(delete(PdfTemplate).where(PdfTemplate.id == template_id))
    await db.flush()

    remaining = (await db.execute(select(PdfTemplate).order_by(PdfTemplate.created_at.asc()))).scalars().all()
    if not remaining:
        await ensure_default_template(db)
    elif not any(bool(t.is_active) for t in remaining):
        remaining[0].is_active = True
        await db.flush()

    return {
        "ok": True,
        "deleted_template_id": template_id,
        "deleted_versions": len(version_ids),
        "deleted_artifacts": deleted_artifacts,
        "deleted_files": deleted_files,
    }


async def create_template_version(
    db: AsyncSession,
    *,
    template_id: str,
    from_version_id: str | None,
    name: str | None,
    created_by: int | None,
) -> PdfTemplateVersion:
    template = (await db.execute(select(PdfTemplate).where(PdfTemplate.id == template_id))).scalars().first()
    if not template:
        raise HTTPException(status_code=404, detail="PDF template not found")

    versions = (
        await db.execute(
            select(PdfTemplateVersion)
            .where(PdfTemplateVersion.template_id == template_id)
            .order_by(PdfTemplateVersion.version.desc())
        )
    ).scalars().all()
    source = None
    if from_version_id:
        source = next((v for v in versions if v.id == from_version_id), None)
        if not source:
            raise HTTPException(status_code=404, detail="Source version not found")
    elif versions:
        source = versions[0]

    version_no = (versions[0].version if versions else 0) + 1
    if source:
        payload = {
            "layout_json": source.layout_json,
            "table_columns_json": source.table_columns_json,
            "mapping_json": source.mapping_json,
            "rules_json": source.rules_json,
            "service_block_json": _normalize_service_block_json(source.service_block_json),
        }
    else:
        payload = default_version_payload()

    row = PdfTemplateVersion(
        template_id=template_id,
        version=version_no,
        name=_normalize_version_name(name, version_no),
        status=PdfTemplateVersionStatus.DRAFT,
        layout_json=payload["layout_json"],
        table_columns_json=payload["table_columns_json"],
        mapping_json=payload["mapping_json"],
        rules_json=payload["rules_json"],
        service_block_json=payload["service_block_json"],
        created_by=created_by,
        created_at=utcnow(),
    )
    db.add(row)
    await db.flush()
    return row


async def patch_template_version(
    db: AsyncSession,
    *,
    version_id: str,
    name: str | None,
    layout_json: dict[str, Any] | None,
    table_columns_json: list[dict[str, Any]] | None,
    mapping_json: dict[str, Any] | None,
    rules_json: dict[str, Any] | None,
    service_block_json: dict[str, Any] | None,
) -> PdfTemplateVersion:
    row = (await db.execute(select(PdfTemplateVersion).where(PdfTemplateVersion.id == version_id))).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Template version not found")

    updated = False
    if name is not None:
        row.name = _normalize_version_name(name, row.version)
        updated = True
    if layout_json is not None:
        row.layout_json = layout_json
        updated = True
    if table_columns_json is not None:
        row.table_columns_json = normalize_columns(table_columns_json)
        updated = True
    if mapping_json is not None:
        row.mapping_json = mapping_json
        updated = True
    if rules_json is not None:
        row.rules_json = rules_json
        updated = True
    if service_block_json is not None:
        row.service_block_json = _normalize_service_block_json(service_block_json)
        updated = True

    if updated:
        cached_artifacts = (
            await db.execute(
                select(PrintArtifact).where(
                    and_(
                        PrintArtifact.template_version_id == version_id,
                        PrintArtifact.artifact_type == PrintArtifactType.PDF_REQUEST_FORM,
                    )
                )
            )
        ).scalars().all()
        for artifact in cached_artifacts:
            try:
                path = Path(str(artifact.file_path)).expanduser().resolve()
                if path.exists():
                    path.unlink()
            except Exception:
                pass
        if cached_artifacts:
            await db.execute(delete(PrintArtifact).where(PrintArtifact.template_version_id == version_id))
        await db.execute(delete(RequestPrintSnapshot).where(RequestPrintSnapshot.template_version_id == version_id))

    await db.flush()
    return row


async def delete_template_version(db: AsyncSession, *, version_id: str) -> dict[str, Any]:
    version = (
        await db.execute(
            select(PdfTemplateVersion).where(PdfTemplateVersion.id == version_id)
        )
    ).scalars().first()
    if not version:
        raise HTTPException(status_code=404, detail="Template version not found")

    siblings = (
        await db.execute(
            select(PdfTemplateVersion)
            .where(PdfTemplateVersion.template_id == version.template_id)
            .order_by(PdfTemplateVersion.version.desc())
        )
    ).scalars().all()
    if len(siblings) <= 1:
        raise HTTPException(status_code=409, detail="Cannot delete the last template version")

    if version.status == PdfTemplateVersionStatus.PUBLISHED:
        replacement = next((v for v in siblings if v.id != version.id), None)
        if not replacement:
            raise HTTPException(status_code=409, detail="Cannot delete the last published version")
        replacement.status = PdfTemplateVersionStatus.PUBLISHED
        replacement.published_at = utcnow()

    artifacts = (
        await db.execute(
            select(PrintArtifact).where(PrintArtifact.template_version_id == version_id)
        )
    ).scalars().all()
    deleted_files = 0
    for art in artifacts:
        try:
            path = Path(str(art.file_path)).expanduser().resolve()
            if path.exists():
                path.unlink()
                deleted_files += 1
        except Exception:
            pass

    await db.execute(delete(PrintArtifact).where(PrintArtifact.template_version_id == version_id))
    await db.execute(delete(RequestPrintSnapshot).where(RequestPrintSnapshot.template_version_id == version_id))
    await db.execute(delete(PdfTemplateVersion).where(PdfTemplateVersion.id == version_id))
    await db.flush()

    remaining = (
        await db.execute(
            select(PdfTemplateVersion)
            .where(PdfTemplateVersion.template_id == version.template_id)
            .order_by(PdfTemplateVersion.version.desc())
        )
    ).scalars().all()
    next_version = remaining[0] if remaining else None
    return {
        "ok": True,
        "deleted_version_id": version_id,
        "deleted_artifacts": len(artifacts),
        "deleted_files": deleted_files,
        "template_id": version.template_id,
        "remaining_version_id": next_version.id if next_version else None,
    }


async def publish_template_version(db: AsyncSession, *, version_id: str, published_by: int | None) -> PdfTemplateVersion:
    row = (
        await db.execute(
            select(PdfTemplateVersion).where(PdfTemplateVersion.id == version_id)
        )
    ).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Template version not found")

    all_rows = (
        await db.execute(
            select(PdfTemplateVersion)
            .where(PdfTemplateVersion.template_id == row.template_id)
            .order_by(PdfTemplateVersion.version.desc())
        )
    ).scalars().all()
    for v in all_rows:
        if v.id == row.id:
            continue
        if v.status == PdfTemplateVersionStatus.PUBLISHED:
            v.status = PdfTemplateVersionStatus.ARCHIVED

    row.status = PdfTemplateVersionStatus.PUBLISHED
    row.published_at = utcnow()
    row.published_by = published_by
    await db.flush()
    return row


async def _resolve_published_version(
    db: AsyncSession,
    *,
    template_id: str | None,
) -> tuple[PdfTemplate, PdfTemplateVersion]:
    if template_id:
        template = (await db.execute(select(PdfTemplate).where(PdfTemplate.id == template_id))).scalars().first()
        if not template:
            raise HTTPException(status_code=404, detail="PDF template not found")
    else:
        template = (
            await db.execute(
                select(PdfTemplate)
                .where(and_(PdfTemplate.scope == PdfTemplateScope.REQUEST_FUEL, PdfTemplate.is_active.is_(True)))
                .order_by(PdfTemplate.created_at.asc())
            )
        ).scalars().first()
        if not template:
            raise HTTPException(status_code=404, detail="Active REQUEST_FUEL template not found")

    version = (
        await db.execute(
            select(PdfTemplateVersion)
            .where(
                and_(
                    PdfTemplateVersion.template_id == template.id,
                    PdfTemplateVersion.status == PdfTemplateVersionStatus.PUBLISHED,
                )
            )
            .order_by(PdfTemplateVersion.version.desc())
        )
    ).scalars().first()
    if not version:
        raise HTTPException(status_code=409, detail="No published template version found")
    return template, version


async def _load_request_for_print(db: AsyncSession, request_id: int) -> Request:
    row = (
        await db.execute(
            select(Request)
            .options(
                selectinload(Request.department),
                selectinload(Request.items).selectinload(RequestItem.vehicle),
                selectinload(Request.items).selectinload(RequestItem.planned_activity),
                selectinload(Request.stock_issue).selectinload(StockIssue.lines),
                selectinload(Request.audits),
            )
            .where(Request.id == request_id)
        )
    ).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Request not found")
    return row


async def _load_system_meta(db: AsyncSession) -> dict[str, Any]:
    meta = (await db.execute(select(SystemMeta).order_by(SystemMeta.id.asc()))).scalars().first()
    if not meta:
        return {
            "backend_version": settings.backend_version,
            "frontend_version": settings.frontend_version,
            "db_schema_version": None,
        }
    return {
        "backend_version": meta.backend_version,
        "frontend_version": meta.frontend_version,
        "db_schema_version": meta.db_schema_version,
    }


def _build_item_rows(req: Request) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, item in enumerate(req.items or [], start=1):
        fuel_type = item.vehicle.fuel_type.value if getattr(item, "vehicle", None) and item.vehicle and item.vehicle.fuel_type else None
        required_liters = float(item.required_liters or 0.0)
        row = {
            "row_no": idx,
            "planned_activity_name": item.planned_activity.name if getattr(item, "planned_activity", None) else None,
            "vehicle_name": item.vehicle.brand if getattr(item, "vehicle", None) else None,
            "vehicle_plate": item.vehicle.identifier if getattr(item, "vehicle", None) else None,
            "vehicle_fuel_type": fuel_type,
            "route_text": item.route_text or req.route_text,
            "distance_km_per_trip": item.distance_km_per_trip if item.distance_km_per_trip is not None else req.distance_km_per_trip,
            "total_km": float(item.total_km or 0.0),
            "required_liters": required_liters,
            "required_kg": float(item.required_kg or 0.0),
            "consumption_l_per_100km": float(item.vehicle.consumption_l_per_100km or 0.0) if getattr(item, "vehicle", None) else 0.0,
            "justification_text": item.justification_text or req.justification_text,
            "need_10_days_ab": required_liters if fuel_type == FuelType.AB.value else 0.0,
            "need_10_days_dp": required_liters if fuel_type == FuelType.DP.value else 0.0,
        }
        rows.append(row)
    return rows


def _build_totals(req: Request, rows: list[dict[str, Any]]) -> dict[str, float]:
    total_ab = round(sum(float(r.get("required_liters") or 0.0) for r in rows if r.get("vehicle_fuel_type") == FuelType.AB.value), 2)
    total_dp = round(sum(float(r.get("required_liters") or 0.0) for r in rows if r.get("vehicle_fuel_type") == FuelType.DP.value), 2)

    debt_ab = 0.0
    debt_dp = 0.0
    issue = req.stock_issue
    if issue and issue.lines:
        for line in issue.lines:
            if line.fuel_type == FuelType.AB:
                debt_ab += float(line.missing_liters or 0.0)
            elif line.fuel_type == FuelType.DP:
                debt_dp += float(line.missing_liters or 0.0)
    return {
        "total_ab_liters": round(total_ab, 2),
        "total_dp_liters": round(total_dp, 2),
        "debt_ab_liters": round(debt_ab, 2),
        "debt_dp_liters": round(debt_dp, 2),
    }


def _build_audit_people(req: Request) -> dict[str, Any]:
    out = {
        "approved_by": None,
        "issued_by": None,
        "confirmed_by": None,
        "approved_at": req.approved_at.isoformat() if req.approved_at else None,
        "issued_at": req.operator_issued_at.isoformat() if req.operator_issued_at else None,
        "confirmed_at": req.dept_confirmed_at.isoformat() if req.dept_confirmed_at else None,
    }
    for a in (req.audits or []):
        if a.action == "APPROVE" and not out["approved_by"]:
            out["approved_by"] = a.actor_user_id
        elif a.action == "ISSUE" and not out["issued_by"]:
            out["issued_by"] = a.actor_user_id
        elif a.action in ("CONFIRM", "MONTH_END_CONFIRM") and not out["confirmed_by"]:
            out["confirmed_by"] = a.actor_user_id
    return out


def _normalize_signature_payload(payload: dict[str, Any] | None) -> dict[str, str]:
    data = payload or {}
    return {
        "approval_title": str(data.get("approval_title") or DEFAULT_APPROVAL_TITLE).strip() or DEFAULT_APPROVAL_TITLE,
        "approval_position": str(data.get("approval_position") or "").strip(),
        "approval_name": str(data.get("approval_name") or "").strip(),
        "agreed_title": str(data.get("agreed_title") or DEFAULT_AGREED_TITLE).strip() or DEFAULT_AGREED_TITLE,
        "agreed_position": str(data.get("agreed_position") or "").strip(),
        "agreed_name": str(data.get("agreed_name") or "").strip(),
    }


async def _load_department_signatures(db: AsyncSession, req: Request) -> dict[str, str]:
    snapshot = (
        await db.execute(
            select(RequestSnapshot)
            .where(
                RequestSnapshot.request_id == req.id,
                RequestSnapshot.stage.in_(
                    [
                        RequestSnapshotStage.SUBMIT,
                        RequestSnapshotStage.APPROVE,
                        RequestSnapshotStage.CONFIRM,
                    ]
                ),
            )
            .order_by(RequestSnapshot.created_at.desc())
        )
    ).scalars().first()
    if snapshot and isinstance(snapshot.payload_json, dict):
        snap_signatures = snapshot.payload_json.get("department_signatures")
        if isinstance(snap_signatures, dict):
            return _normalize_signature_payload(snap_signatures)

    row = await crud_dept_signature.get_by_department_id(db, req.department_id)
    if row is not None:
        return _normalize_signature_payload(
            {
                "approval_title": row.approval_title,
                "approval_position": row.approval_position,
                "approval_name": row.approval_name,
                "agreed_title": row.agreed_title,
                "agreed_position": row.agreed_position,
                "agreed_name": row.agreed_name,
            }
        )
    return _normalize_signature_payload(None)


async def build_request_print_context(db: AsyncSession, request_id: int) -> dict[str, Any]:
    req = await _load_request_for_print(db, request_id)
    sys_meta = await _load_system_meta(db)
    items = _build_item_rows(req)
    totals = _build_totals(req, items)

    status = req.status.value if req.status else ""
    has_debt = bool(getattr(req, "has_debt", False)) or totals["debt_ab_liters"] > 0 or totals["debt_dp_liters"] > 0
    period_text = f"{req.training_days_count or 0} днів / {req.persons_involved_count or 0} осіб"

    issue = req.stock_issue
    signatures = await _load_department_signatures(db, req)
    issue_payload = {
        "id": issue.id if issue else None,
        "issue_doc_no": issue.issue_doc_no if issue else None,
        "posted_at": issue.posted_at.isoformat() if issue and issue.posted_at else None,
    }

    context = {
        "request": {
            "id": req.id,
            "request_number": req.request_number,
            "created_at": req.created_at.isoformat() if req.created_at else None,
            "submitted_at": req.submitted_at.isoformat() if req.submitted_at else None,
            "approved_at": req.approved_at.isoformat() if req.approved_at else None,
            "operator_issued_at": req.operator_issued_at.isoformat() if req.operator_issued_at else None,
            "dept_confirmed_at": req.dept_confirmed_at.isoformat() if req.dept_confirmed_at else None,
            "stock_posted_at": req.stock_posted_at.isoformat() if req.stock_posted_at else None,
            "status": status,
            "route_text": req.route_text,
            "distance_km_per_trip": req.distance_km_per_trip,
            "justification_text": req.justification_text,
            "period_text": period_text,
            "persons_involved_count": req.persons_involved_count,
            "training_days_count": req.training_days_count,
            "coeff_snapshot_ab": req.coeff_snapshot_ab,
            "coeff_snapshot_dp": req.coeff_snapshot_dp,
            "coeff_snapshot_at": req.coeff_snapshot_at.isoformat() if req.coeff_snapshot_at else None,
            "has_debt": has_debt,
        },
        "department": {
            "id": req.department_id,
            "name": req.department.name if isinstance(req.department, Department) and req.department else f"Підрозділ #{req.department_id}",
        },
        "issue": issue_payload,
        "system": sys_meta,
        "computed": totals,
        "audit": _build_audit_people(req),
        "items": items,
        "signatures": signatures,
    }
    return context


def _build_render_rows(columns: list[dict[str, Any]], request_ctx: dict[str, Any]) -> list[dict[str, Any]]:
    req_status = str(_deep_get(request_ctx, "request.status") or "")
    has_debt = bool(_deep_get(request_ctx, "request.has_debt"))

    active_columns: list[dict[str, Any]] = []
    for col in columns:
        if not bool(col.get("visible", True)):
            continue
        if not _rule_match(col.get("rules"), status=req_status, has_debt=has_debt, role=None):
            continue
        active_columns.append(col)

    rows: list[dict[str, Any]] = []
    use_item_rows = any(_source_requires_item_row(str(c.get("source") or "")) for c in active_columns)
    row_sources = (request_ctx.get("items") or []) if use_item_rows else [None]
    for item in row_sources:
        row_cells = []
        for col in active_columns:
            raw = _resolve_source_value(col["source"], request_ctx=request_ctx, item_ctx=item)
            row_cells.append(
                {
                    "id": col["id"],
                    "align": col.get("align") or "left",
                    "text_style": col.get("text_style") or "normal",
                    "font_size_pt": col.get("font_size_pt") or 11,
                    "value": _format_value(raw, col.get("format") or "text"),
                }
            )
        rows.append({"cells": row_cells})

    raw_widths: list[float] = []
    for c in active_columns:
        try:
            width = float(c.get("width") or 0)
        except Exception:
            width = 0
        raw_widths.append(width if width > 0 else 8.0)

    total_width = sum(raw_widths) or (len(raw_widths) * 8.0) or 1.0
    normalized_widths: list[float] = []
    consumed = 0.0
    for idx, width in enumerate(raw_widths):
        if idx == len(raw_widths) - 1:
            normalized = round(max(0.1, 100.0 - consumed), 2)
        else:
            normalized = round((width / total_width) * 100.0, 2)
            consumed += normalized
        normalized_widths.append(normalized)

    rendered_columns = []
    for idx, c in enumerate(active_columns):
        rendered_columns.append(
            {
                "id": c["id"],
                "title": c.get("title") or c["id"],
                "width": normalized_widths[idx],
                "align": c.get("align") or "left",
                "text_style": c.get("text_style") or "normal",
                "font_size_pt": c.get("font_size_pt") or 11,
            }
        )
    return [{"columns": rendered_columns, "rows": rows}]


def _build_doc_view(snapshot: dict[str, Any], *, base_url: str) -> dict[str, Any]:
    template_version = snapshot.get("template_version") or {}
    request_ctx = snapshot.get("request_context") or {}
    render_data = _build_render_rows(template_version.get("table_columns_json") or [], request_ctx)
    table = render_data[0] if render_data else {"columns": [], "rows": []}

    header_fields = []
    for node in (template_version.get("mapping_json") or {}).get("header_fields") or []:
        source = str(node.get("source") or "")
        label = str(node.get("label") or source)
        value = _resolve_source_value(source, request_ctx=request_ctx, item_ctx=None)
        header_fields.append({"label": label, "value": _format_value(value, "text")})

    totals_fields = []
    for node in (template_version.get("mapping_json") or {}).get("totals_fields") or []:
        source = str(node.get("source") or "")
        label = str(node.get("label") or source)
        value = _resolve_source_value(source, request_ctx=request_ctx, item_ctx=None)
        totals_fields.append({"label": label, "value": _format_value(value, "number_2")})

    service_fields = []
    for node in (template_version.get("mapping_json") or {}).get("service_fields") or []:
        source = str(node.get("source") or "")
        label = str(node.get("label") or source)
        value = _resolve_source_value(source, request_ctx=request_ctx, item_ctx=None)
        service_fields.append({"label": label, "value": _format_value(value, "text")})

    raw_qr_url = str(settings.print_qr_target_url or "").strip() or str(base_url or "").strip()
    if raw_qr_url and not raw_qr_url.startswith(("http://", "https://")):
        raw_qr_url = f"https://{raw_qr_url}"
    qr_url = raw_qr_url or str(base_url or "").strip()
    qr_b64 = _build_qr_b64(qr_url)
    auto_sign_date = _format_value(
        _deep_get(request_ctx, "request.submitted_at") or _deep_get(request_ctx, "request.created_at"),
        "date",
    )
    layout_signatures = (
        _deep_get(template_version, "layout_json.signatures")
        if isinstance(template_version, dict)
        else {}
    ) or {}
    use_department_signatures = bool(layout_signatures.get("use_department_signatures", True))
    ctx_signatures = _normalize_signature_payload(request_ctx.get("signatures") if isinstance(request_ctx, dict) else None)
    if use_department_signatures:
        resolved_signatures = {
            "approval_title": ctx_signatures.get("approval_title")
            or str(layout_signatures.get("approval_title") or DEFAULT_APPROVAL_TITLE),
            "approval_position": ctx_signatures.get("approval_position")
            or str(layout_signatures.get("approval_position") or ""),
            "approval_name": ctx_signatures.get("approval_name")
            or str(layout_signatures.get("approval_name") or ""),
            "agreed_title": ctx_signatures.get("agreed_title")
            or str(layout_signatures.get("agreed_title") or DEFAULT_AGREED_TITLE),
            "agreed_position": ctx_signatures.get("agreed_position")
            or str(layout_signatures.get("agreed_position") or ""),
            "agreed_name": ctx_signatures.get("agreed_name")
            or str(layout_signatures.get("agreed_name") or ""),
        }
    else:
        resolved_signatures = {
            "approval_title": str(layout_signatures.get("approval_title") or DEFAULT_APPROVAL_TITLE),
            "approval_position": str(layout_signatures.get("approval_position") or ""),
            "approval_name": str(layout_signatures.get("approval_name") or ""),
            "agreed_title": str(layout_signatures.get("agreed_title") or DEFAULT_AGREED_TITLE),
            "agreed_position": str(layout_signatures.get("agreed_position") or ""),
            "agreed_name": str(layout_signatures.get("agreed_name") or ""),
        }

    generated_at = utcnow().isoformat()
    barcode_value = build_unique_barcode_value(
        [
            "PMM",
            "REQ",
            _deep_get(request_ctx, "request.request_number") or _deep_get(request_ctx, "request.id"),
            generated_at,
        ]
    )
    barcode_b64 = build_code39_png_b64(barcode_value)

    return {
        "layout": template_version.get("layout_json") or _default_layout_json(),
        "service": _normalize_service_block_json(template_version.get("service_block_json")),
        "request": request_ctx.get("request") or {},
        "department": request_ctx.get("department") or {},
        "issue": request_ctx.get("issue") or {},
        "system": request_ctx.get("system") or {},
        "audit": request_ctx.get("audit") or {},
        "items": request_ctx.get("items") or [],
        "computed": request_ctx.get("computed") or {},
        "table": table,
        "header_fields": header_fields,
        "totals_fields": totals_fields,
        "service_fields": service_fields,
        "generated_at": generated_at,
        "auto_sign_date": auto_sign_date,
        "use_department_signatures": use_department_signatures,
        "signatures": resolved_signatures,
        "qr_url": qr_url,
        "qr_b64": qr_b64,
        "barcode_value": barcode_value,
        "barcode_b64": barcode_b64,
        "has_debt": bool(_deep_get(request_ctx, "request.has_debt")),
        "debt_ab_liters": float(_deep_get(request_ctx, "computed.debt_ab_liters") or 0.0),
        "debt_dp_liters": float(_deep_get(request_ctx, "computed.debt_dp_liters") or 0.0),
    }


def render_pdf_from_snapshot(snapshot: dict[str, Any], *, base_url: str) -> bytes:
    if HTML is None:
        raise HTTPException(status_code=503, detail=f"PDF service is unavailable: {_WEASYPRINT_IMPORT_ERROR}")
    doc = _build_doc_view(snapshot, base_url=base_url)
    html = jinja_env.get_template("request_form_builder.html").render(doc=doc)
    return HTML(string=html).write_pdf()


def _request_status_label(status: str | None) -> str:
    mapping = {
        "DRAFT": "Чернетка",
        "SUBMITTED": "Подано",
        "APPROVED": "Затверджено",
        "ISSUED_BY_OPERATOR": "Видано оператором",
        "POSTED": "Проведено",
        "REJECTED": "Відхилено",
        "CANCELED": "Скасовано",
    }
    key = str(status or "").strip().upper()
    return mapping.get(key, key or "—")


async def build_request_issue_act_pdf(
    db: AsyncSession,
    *,
    request_id: int,
) -> bytes:
    if HTML is None:
        raise HTTPException(status_code=503, detail=f"PDF service is unavailable: {_WEASYPRINT_IMPORT_ERROR}")

    req = await _load_request_for_print(db, request_id)
    issue = req.stock_issue
    if issue is None:
        raise HTTPException(
            status_code=409,
            detail="Акт ще не сформовано. Підтвердіть отримання підрозділом.",
        )

    line_rows: list[dict[str, Any]] = []
    for idx, line in enumerate(issue.lines or [], start=1):
        line_rows.append(
            {
                "row_no": idx,
                "fuel_type": line.fuel_type.value if line.fuel_type else "—",
                "requested_liters": float(line.requested_liters or 0.0),
                "requested_kg": float(line.requested_kg or 0.0),
                "issued_liters": float(line.issued_liters or 0.0),
                "issued_kg": float(line.issued_kg or 0.0),
                "missing_liters": float(line.missing_liters or 0.0),
                "missing_kg": float(line.missing_kg or 0.0),
            }
        )

    if not line_rows:
        line_rows.append(
            {
                "row_no": 1,
                "fuel_type": issue.fuel_type.value if issue.fuel_type else "—",
                "requested_liters": float(issue.issue_liters or 0.0),
                "requested_kg": float(issue.issue_kg or 0.0),
                "issued_liters": float(issue.issue_liters or 0.0),
                "issued_kg": float(issue.issue_kg or 0.0),
                "missing_liters": float(issue.debt_liters or 0.0),
                "missing_kg": float(issue.debt_kg or 0.0),
            }
        )

    requested_liters_total = round(sum(float(r["requested_liters"]) for r in line_rows), 2)
    requested_kg_total = round(sum(float(r["requested_kg"]) for r in line_rows), 2)
    issued_liters_total = round(sum(float(r["issued_liters"]) for r in line_rows), 2)
    issued_kg_total = round(sum(float(r["issued_kg"]) for r in line_rows), 2)
    missing_liters_total = round(sum(float(r["missing_liters"]) for r in line_rows), 2)
    missing_kg_total = round(sum(float(r["missing_kg"]) for r in line_rows), 2)

    generated_at = utcnow().isoformat()
    barcode_value = build_unique_barcode_value(
        [
            "PMM",
            "ACT",
            issue.issue_doc_no or req.request_number or request_id,
            generated_at,
        ]
    )
    barcode_b64 = build_code39_png_b64(barcode_value)

    doc = {
        "request_number": req.request_number,
        "department_name": req.department.name if req.department else f"Підрозділ #{req.department_id}",
        "issue_doc_no": issue.issue_doc_no,
        "issue_status": _request_status_label(req.status.value if req.status else None),
        "posted_at": issue.posted_at.isoformat() if issue.posted_at else None,
        "generated_at": generated_at,
        "barcode_value": barcode_value,
        "barcode_b64": barcode_b64,
        "rows": line_rows,
        "totals": {
            "requested_liters": requested_liters_total,
            "requested_kg": requested_kg_total,
            "issued_liters": issued_liters_total,
            "issued_kg": issued_kg_total,
            "missing_liters": missing_liters_total,
            "missing_kg": missing_kg_total,
        },
    }
    html = jinja_env.get_template("request_issue_act.html").render(doc=doc)
    return HTML(string=html).write_pdf()


async def build_preview_pdf(
    db: AsyncSession,
    *,
    version_id: str,
    request_id: int,
    base_url: str,
    layout_json: dict[str, Any] | None = None,
    table_columns_json: list[dict[str, Any]] | None = None,
    mapping_json: dict[str, Any] | None = None,
    rules_json: dict[str, Any] | None = None,
    service_block_json: dict[str, Any] | None = None,
) -> bytes:
    await ensure_default_template(db)
    version = (await db.execute(select(PdfTemplateVersion).where(PdfTemplateVersion.id == version_id))).scalars().first()
    if not version:
        raise HTTPException(status_code=404, detail="Template version not found")

    context = await build_request_print_context(db, request_id)
    effective_columns = normalize_columns(table_columns_json) if table_columns_json is not None else version.table_columns_json

    snapshot = {
        "request_id": request_id,
        "template_id": version.template_id,
        "template_version_id": version.id,
        "template_version": {
            "layout_json": layout_json if layout_json is not None else version.layout_json,
            "table_columns_json": effective_columns,
            "mapping_json": mapping_json if mapping_json is not None else version.mapping_json,
            "rules_json": rules_json if rules_json is not None else version.rules_json,
            "service_block_json": service_block_json if service_block_json is not None else version.service_block_json,
        },
        "request_context": context,
        "created_at": utcnow().isoformat(),
        "created_by": None,
    }
    return render_pdf_from_snapshot(snapshot, base_url=base_url)


async def generate_request_pdf_artifact(
    db: AsyncSession,
    *,
    request_id: int,
    actor_user_id: int | None,
    template_id: str | None,
    force_regenerate: bool,
    base_url: str,
) -> dict[str, Any]:
    await ensure_default_template(db)
    template, version = await _resolve_published_version(db, template_id=template_id)

    if not force_regenerate:
        existing_artifact = (
            await db.execute(
                select(PrintArtifact)
                .where(
                    and_(
                        PrintArtifact.request_id == request_id,
                        PrintArtifact.template_version_id == version.id,
                        PrintArtifact.artifact_type == PrintArtifactType.PDF_REQUEST_FORM,
                    )
                )
                .order_by(PrintArtifact.created_at.desc())
            )
        ).scalars().first()
        if existing_artifact and Path(existing_artifact.file_path).exists():
            return {
                "artifact": existing_artifact,
                "from_cache": True,
                "template_version": version,
            }

    snapshot = (
        await db.execute(
            select(RequestPrintSnapshot).where(
                and_(
                    RequestPrintSnapshot.request_id == request_id,
                    RequestPrintSnapshot.template_version_id == version.id,
                )
            )
        )
    ).scalars().first()

    if snapshot:
        snapshot_json = snapshot.snapshot_json
    else:
        context = await build_request_print_context(db, request_id)
        snapshot_json = {
            "request_id": request_id,
            "template_id": template.id,
            "template_version_id": version.id,
            "template_version": {
                "layout_json": version.layout_json,
                "table_columns_json": version.table_columns_json,
                "mapping_json": version.mapping_json,
                "rules_json": version.rules_json,
                "service_block_json": version.service_block_json,
            },
            "request_context": context,
            "created_at": utcnow().isoformat(),
            "created_by": actor_user_id,
        }
        snapshot = RequestPrintSnapshot(
            request_id=request_id,
            template_id=template.id,
            template_version_id=version.id,
            snapshot_json=snapshot_json,
            created_by=actor_user_id,
            created_at=utcnow(),
        )
        db.add(snapshot)
        await db.flush()

    pdf_bytes = render_pdf_from_snapshot(snapshot_json, base_url=base_url)
    digest = hashlib.sha256(pdf_bytes).hexdigest()

    out_dir = _print_storage_dir()
    stamp = utcnow().strftime("%Y%m%d%H%M%S")
    file_path = out_dir / f"request_{request_id}_tpl_{version.version}_{stamp}.pdf"
    file_path.write_bytes(pdf_bytes)

    artifact = PrintArtifact(
        request_id=request_id,
        artifact_type=PrintArtifactType.PDF_REQUEST_FORM,
        template_version_id=version.id,
        file_path=str(file_path),
        sha256=digest,
        created_by=actor_user_id,
        created_at=utcnow(),
    )
    db.add(artifact)
    await db.flush()
    return {
        "artifact": artifact,
        "from_cache": False,
        "template_version": version,
    }


async def ensure_default_template(db: AsyncSession) -> None:
    template = (
        await db.execute(
            select(PdfTemplate)
            .options(selectinload(PdfTemplate.versions))
            .where(PdfTemplate.scope == PdfTemplateScope.REQUEST_FUEL)
            .order_by(PdfTemplate.created_at.asc())
            .limit(1)
        )
    ).scalars().first()
    if template:
        changed = False
        invalidated_version_ids: set[str] = set()
        for v in template.versions or []:
            cols = v.table_columns_json if isinstance(v.table_columns_json, list) else []
            default_cols = _default_columns_json()
            normalized_default = [_normalize_column(dict(c), idx) for idx, c in enumerate(default_cols)]
            if not cols:
                v.table_columns_json = normalized_default
                changed = True
                invalidated_version_ids.add(v.id)
            else:
                cols_changed = False
                normalized_cols: list[dict[str, Any]] = []
                for idx, col in enumerate(cols):
                    if not isinstance(col, dict):
                        fallback = dict(default_cols[idx]) if idx < len(default_cols) else dict(default_cols[-1])
                        fallback["id"] = f"col_{idx + 1}"
                        normalized_cols.append(_normalize_column(fallback, idx))
                        cols_changed = True
                        continue
                    patched = dict(col)
                    patched.setdefault("text_style", "normal")
                    patched.setdefault("font_size_pt", 11)
                    try:
                        normalized = _normalize_column(patched, idx)
                    except HTTPException:
                        fallback = dict(default_cols[idx]) if idx < len(default_cols) else dict(default_cols[-1])
                        fallback["id"] = str(col.get("id") or f"col_{idx + 1}")
                        normalized = _normalize_column(fallback, idx)
                        cols_changed = True
                    normalized_cols.append(normalized)
                    if normalized != col:
                        cols_changed = True

                if _is_legacy_request_table(normalized_cols):
                    if normalized_cols != normalized_default:
                        v.table_columns_json = normalized_default
                        changed = True
                        invalidated_version_ids.add(v.id)
                elif cols_changed:
                    v.table_columns_json = normalized_cols
                    changed = True
                    invalidated_version_ids.add(v.id)
            normalized_service_block = _normalize_service_block_json(v.service_block_json)
            if normalized_service_block != (v.service_block_json or {}):
                v.service_block_json = normalized_service_block
                changed = True
                invalidated_version_ids.add(v.id)
            layout = v.layout_json or {}
            page = layout.get("page") if isinstance(layout, dict) else {}
            orientation = str((page or {}).get("orientation") or "").lower()
            if orientation != "landscape":
                layout = dict(layout or {})
                page = dict(layout.get("page") or {})
                page["orientation"] = "landscape"
                layout["page"] = page
                v.layout_json = layout
                changed = True
                invalidated_version_ids.add(v.id)
            if isinstance(v.layout_json, dict):
                layout = dict(v.layout_json)
                typography = dict(layout.get("typography") or {})
                header = dict(layout.get("header") or {})
                signatures = dict(layout.get("signatures") or {})
                hdr_changed = False
                sig_changed = False
                if "font_size_pt" not in typography:
                    typography["font_size_pt"] = 11
                    hdr_changed = True
                if str(typography.get("text_style") or "").lower() not in AVAILABLE_TEXT_STYLES:
                    typography["text_style"] = "normal"
                    hdr_changed = True
                if not header.get("commander_line"):
                    header["commander_line"] = "Командиру військової частини A7014"
                    hdr_changed = True
                if not header.get("title"):
                    header["title"] = "ЗАЯВКА"
                    hdr_changed = True
                if not header.get("subtitle"):
                    header["subtitle"] = "Прошу, Вас дати вказівку начальнику служби ПММ, що до видачі пального на бойову підготовку"
                    hdr_changed = True
                if "approval_title" not in signatures:
                    signatures["approval_title"] = "З розрахунком згоден:"
                    sig_changed = True
                if "use_department_signatures" not in signatures:
                    signatures["use_department_signatures"] = True
                    sig_changed = True
                if "approval_position" not in signatures:
                    signatures["approval_position"] = "Командир взводу матеріального забезпечення"
                    sig_changed = True
                if "approval_name" not in signatures:
                    signatures["approval_name"] = ""
                    sig_changed = True
                if "agreed_title" not in signatures:
                    signatures["agreed_title"] = "ПОГОДЖЕНО:"
                    sig_changed = True
                if "agreed_position" not in signatures:
                    signatures["agreed_position"] = "Заступник командира бригади:"
                    sig_changed = True
                if "agreed_name" not in signatures:
                    signatures["agreed_name"] = ""
                    sig_changed = True
                if hdr_changed or sig_changed:
                    layout["typography"] = typography
                    layout["header"] = header
                    layout["signatures"] = signatures
                    v.layout_json = layout
                    changed = True
                    invalidated_version_ids.add(v.id)
        if invalidated_version_ids:
            cached_artifacts = (
                await db.execute(
                    select(PrintArtifact).where(PrintArtifact.template_version_id.in_(list(invalidated_version_ids)))
                )
            ).scalars().all()
            for artifact in cached_artifacts:
                try:
                    path = Path(str(artifact.file_path)).expanduser().resolve()
                    if path.exists():
                        path.unlink()
                except Exception:
                    pass
            await db.execute(delete(PrintArtifact).where(PrintArtifact.template_version_id.in_(list(invalidated_version_ids))))
            await db.execute(delete(RequestPrintSnapshot).where(RequestPrintSnapshot.template_version_id.in_(list(invalidated_version_ids))))
        if changed:
            await db.flush()
        return

    row = await create_template(
        db,
        name="Заявка ПММ (Стандарт)",
        scope=PdfTemplateScope.REQUEST_FUEL.value,
        is_active=True,
        created_by=None,
    )
    ver = (
        await db.execute(
            select(PdfTemplateVersion)
            .where(PdfTemplateVersion.template_id == row.id)
            .order_by(PdfTemplateVersion.version.desc())
        )
    ).scalars().first()
    if ver:
        ver.status = PdfTemplateVersionStatus.PUBLISHED
        ver.published_at = utcnow()
        ver.published_by = None
    await db.flush()
