from datetime import datetime
from typing import Any

from pydantic import BaseModel


class JobCreateOut(BaseModel):
    job_id: str
    status: str


class JobOut(BaseModel):
    id: str
    type: str
    status: str
    params_json: dict[str, Any] | None = None
    result_json: dict[str, Any] | None = None
    created_at: datetime | None = None
    created_by: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None


class ExportJobIn(BaseModel):
    format: str = "XLSX"
    filters: dict[str, Any] | None = None


class ReconcileJobIn(BaseModel):
    filters: dict[str, Any] | None = None


class MonthEndBatchJobIn(BaseModel):
    request_ids: list[int] | None = None
