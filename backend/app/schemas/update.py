from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UpdateConfigIn(BaseModel):
    default_with_backup: bool | None = None


class UpdateConfigOut(BaseModel):
    update_repo: str | None = None
    updater_mode: str = "server_build"
    require_signed_tags: bool = False
    default_with_backup: bool = True


class SystemUpdateApplyIn(BaseModel):
    target_version: str | None = None
    backup: bool = True
    with_backup: bool | None = None


class SystemRollbackIn(BaseModel):
    update_log_id: int | None = None
    to_version: str | None = None


class SystemUpdateMetaOut(BaseModel):
    backend_version: str
    frontend_version: str
    db_schema_version: str | None = None
    last_update_at: datetime | None = None
    last_update_by: int | None = None


class SystemUpdateCheckOut(BaseModel):
    source: str
    app_name: str | None = None
    current_version: str | None = None
    latest_version: str
    update_available: bool
    current_db_schema: str | None = None
    available_versions: list[str] = Field(default_factory=list)
    changelog: list[dict[str, Any]] = Field(default_factory=list)


class UpdatesLogOut(BaseModel):
    id: int
    from_version: str | None = None
    to_version: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    started_by: int | None = None
    job_id: str | None = None
    details_json: dict[str, Any] | None = None
    error_message: str | None = None


class UpdateStepOut(BaseModel):
    id: int
    update_log_id: int
    job_id: str | None = None
    step_name: str
    status: str
    output_text: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class UpdatesLogListOut(BaseModel):
    items: list[UpdatesLogOut]


class SystemUpdateStatusOut(BaseModel):
    job_id: str
    job_status: str | None = None
    phase: str | None = None
    progress_pct: int | None = None
    message: str | None = None
    update_log: UpdatesLogOut | None = None
    steps: list[UpdateStepOut] = Field(default_factory=list)
