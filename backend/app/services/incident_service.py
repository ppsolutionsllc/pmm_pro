from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utcnow
from app.models.admin_incident import (
    AdminIncident,
    IncidentSeverity,
    IncidentStatus,
    IncidentType,
)
from app.models.background_job import BackgroundJobType
from app.models.posting_session import PostingOperation, PostingSession


def posting_incident_type(operation: PostingOperation | None) -> IncidentType:
    if operation == PostingOperation.ADJUSTMENT:
        return IncidentType.ADJUSTMENT_FAILED
    return IncidentType.POSTING_FAILED


def posting_incident_severity(operation: PostingOperation | None) -> IncidentSeverity:
    if operation == PostingOperation.ADJUSTMENT:
        return IncidentSeverity.HIGH
    return IncidentSeverity.CRITICAL


def job_incident_type(job_type: BackgroundJobType) -> IncidentType:
    if job_type == BackgroundJobType.RECONCILE:
        return IncidentType.RECONCILE_FAILED
    if job_type in (
        BackgroundJobType.REQUESTS_EXPORT,
        BackgroundJobType.DEBTS_EXPORT,
        BackgroundJobType.VEHICLE_REPORT_EXPORT,
        BackgroundJobType.PDF_EXPORT,
        BackgroundJobType.XLSX_EXPORT,
    ):
        return IncidentType.EXPORT_FAILED
    if job_type == BackgroundJobType.SYSTEM_UPDATE:
        return IncidentType.SYSTEM_UPDATE_FAILED
    return IncidentType.SYSTEM_UPDATE_FAILED


def job_incident_severity(job_type: BackgroundJobType) -> IncidentSeverity:
    if job_type == BackgroundJobType.RECONCILE:
        return IncidentSeverity.HIGH
    if job_type in (
        BackgroundJobType.REQUESTS_EXPORT,
        BackgroundJobType.DEBTS_EXPORT,
        BackgroundJobType.VEHICLE_REPORT_EXPORT,
        BackgroundJobType.PDF_EXPORT,
        BackgroundJobType.XLSX_EXPORT,
    ):
        return IncidentSeverity.MEDIUM
    if job_type == BackgroundJobType.SYSTEM_UPDATE:
        return IncidentSeverity.HIGH
    return IncidentSeverity.HIGH


async def create_incident(
    db: AsyncSession,
    *,
    incident_type: IncidentType,
    severity: IncidentSeverity,
    message: str,
    details_json: dict[str, Any] | None = None,
    request_id: int | None = None,
    posting_session_id: str | None = None,
    job_id: str | None = None,
    created_by: int | None = None,
) -> AdminIncident:
    row = AdminIncident(
        type=incident_type,
        severity=severity,
        status=IncidentStatus.NEW,
        message=(message or "")[:512],
        details_json=details_json,
        request_id=request_id,
        posting_session_id=posting_session_id,
        job_id=job_id,
        created_by=created_by,
        created_at=utcnow(),
    )
    db.add(row)
    await db.flush()
    return row


async def create_incident_for_failed_posting_session(
    db: AsyncSession,
    *,
    posting_session: PostingSession,
    error_code: str,
    error_message: str,
) -> AdminIncident:
    return await create_incident(
        db,
        incident_type=posting_incident_type(posting_session.operation),
        severity=posting_incident_severity(posting_session.operation),
        message=f"{posting_session.operation.value} failed: {error_message}"[:512],
        details_json={
            "error_code": error_code,
            "error_message": error_message[:4000],
            "operation": posting_session.operation.value if posting_session.operation else None,
            "idempotency_key": posting_session.idempotency_key,
            "retry_count": int(posting_session.retry_count or 0),
        },
        request_id=posting_session.request_id,
        posting_session_id=posting_session.id,
        created_by=posting_session.started_by_user_id,
    )
