from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PdfTemplateCreateIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    scope: Literal["REQUEST_FUEL"] = "REQUEST_FUEL"
    is_active: bool = True


class PdfTemplateVersionCreateIn(BaseModel):
    from_version_id: str | None = None
    name: str | None = None


class PdfTemplateVersionPatchIn(BaseModel):
    name: str | None = None
    layout_json: dict[str, Any] | None = None
    table_columns_json: list[dict[str, Any]] | None = None
    mapping_json: dict[str, Any] | None = None
    rules_json: dict[str, Any] | None = None
    service_block_json: dict[str, Any] | None = None


class PdfTemplatePreviewIn(BaseModel):
    request_id: int
    layout_json: dict[str, Any] | None = None
    table_columns_json: list[dict[str, Any]] | None = None
    mapping_json: dict[str, Any] | None = None
    rules_json: dict[str, Any] | None = None
    service_block_json: dict[str, Any] | None = None


class RequestPrintPdfIn(BaseModel):
    template_id: str | None = None
    force_regenerate: bool = False


class PdfTemplateOut(BaseModel):
    id: str
    name: str
    scope: str
    is_active: bool
    created_at: datetime | None = None
    created_by: int | None = None
    last_published_version: int | None = None
    last_published_version_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PdfTemplateVersionOut(BaseModel):
    id: str
    template_id: str
    version: int
    name: str
    status: str
    layout_json: dict[str, Any]
    table_columns_json: list[dict[str, Any]]
    mapping_json: dict[str, Any]
    rules_json: dict[str, Any]
    service_block_json: dict[str, Any]
    created_at: datetime | None = None
    created_by: int | None = None
    published_at: datetime | None = None
    published_by: int | None = None


class PdfTemplateDetailOut(BaseModel):
    template: PdfTemplateOut
    versions: list[PdfTemplateVersionOut]
    available_sources: list[str]
    available_formats: list[str]
    available_visibility_rules: list[str]


class RequestPrintPdfOut(BaseModel):
    artifact_id: str
    request_id: int
    template_version_id: str
    download_url: str
    from_cache: bool
