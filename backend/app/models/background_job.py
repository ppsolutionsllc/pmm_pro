import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, JSON, String, Text

from app.core.time import utcnow
from app.models.base import Base


class BackgroundJobType(str, enum.Enum):
    PDF_EXPORT = "PDF_EXPORT"
    XLSX_EXPORT = "XLSX_EXPORT"
    MONTH_END_BATCH = "MONTH_END_BATCH"
    RECONCILE = "RECONCILE"
    SYSTEM_UPDATE = "SYSTEM_UPDATE"
    VEHICLE_REPORT_EXPORT = "VEHICLE_REPORT_EXPORT"
    REQUESTS_EXPORT = "REQUESTS_EXPORT"
    DEBTS_EXPORT = "DEBTS_EXPORT"


class BackgroundJobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(Enum(BackgroundJobType), nullable=False)
    status = Column(Enum(BackgroundJobStatus), nullable=False, default=BackgroundJobStatus.QUEUED)
    params_json = Column(JSON, nullable=True)
    result_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
