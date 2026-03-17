import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, JSON, String, Text

from app.core.time import utcnow
from app.models.base import Base


class UpdateStatus(str, enum.Enum):
    STARTED = "STARTED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"


class UpdatesLog(Base):
    __tablename__ = "updates_log"

    id = Column(Integer, primary_key=True, index=True)
    from_version = Column(String(64), nullable=True)
    to_version = Column(String(64), nullable=False)
    status = Column(Enum(UpdateStatus), nullable=False, default=UpdateStatus.STARTED)
    started_at = Column(DateTime, nullable=False, default=utcnow)
    finished_at = Column(DateTime, nullable=True)
    started_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    job_id = Column(String(36), nullable=True, index=True)
    details_json = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
