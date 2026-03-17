import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, JSON, String, Text

from app.core.time import utcnow
from app.models.base import Base


class IncidentType(str, enum.Enum):
    POSTING_FAILED = "POSTING_FAILED"
    ADJUSTMENT_FAILED = "ADJUSTMENT_FAILED"
    EXPORT_FAILED = "EXPORT_FAILED"
    BACKUP_FAILED = "BACKUP_FAILED"
    RECONCILE_FAILED = "RECONCILE_FAILED"
    SYSTEM_UPDATE_FAILED = "SYSTEM_UPDATE_FAILED"
    SECURITY_ALERT = "SECURITY_ALERT"


class IncidentSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentStatus(str, enum.Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"


class AdminIncident(Base):
    __tablename__ = "admin_incidents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(Enum(IncidentType), nullable=False)
    severity = Column(Enum(IncidentSeverity), nullable=False, default=IncidentSeverity.HIGH)
    status = Column(Enum(IncidentStatus), nullable=False, default=IncidentStatus.NEW)
    message = Column(String(512), nullable=False)
    details_json = Column(JSON, nullable=True)
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=True, index=True)
    posting_session_id = Column(String(36), ForeignKey("posting_sessions.id"), nullable=True, index=True)
    job_id = Column(String(36), ForeignKey("background_jobs.id"), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolution_comment = Column(Text, nullable=True)
