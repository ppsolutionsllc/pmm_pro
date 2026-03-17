from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class IncidentListItem(BaseModel):
    id: str
    type: str
    severity: str
    status: str
    message: str
    request_id: Optional[int] = None
    posting_session_id: Optional[str] = None
    job_id: Optional[str] = None
    created_at: Optional[datetime] = None
    created_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[int] = None


class IncidentListOut(BaseModel):
    items: list[IncidentListItem]
    page: int
    page_size: int
    total: int
    unresolved_count: int


class IncidentRequestSummary(BaseModel):
    id: int
    request_number: str
    status: str
    department_id: int
    department_name: Optional[str] = None


class IncidentPostingSessionSummary(BaseModel):
    id: str
    operation: Optional[str] = None
    status: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class IncidentJobSummary(BaseModel):
    id: str
    type: str
    status: str
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None


class IncidentDetailOut(BaseModel):
    id: str
    type: str
    severity: str
    status: str
    message: str
    details_json: Optional[dict[str, Any]] = None
    request_id: Optional[int] = None
    posting_session_id: Optional[str] = None
    job_id: Optional[str] = None
    created_at: Optional[datetime] = None
    created_by: Optional[int] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[int] = None
    resolution_comment: Optional[str] = None
    request_summary: Optional[IncidentRequestSummary] = None
    posting_session_summary: Optional[IncidentPostingSessionSummary] = None
    job_summary: Optional[IncidentJobSummary] = None


class IncidentPatchIn(BaseModel):
    status: Optional[str] = None
    resolution_comment: Optional[str] = None
    message: Optional[str] = None


class IncidentRetryOut(BaseModel):
    ok: bool = True
    incident_id: str
    status: str
    session_id: Optional[str] = None
    job_id: Optional[str] = None
