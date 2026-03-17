import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text

from app.core.time import utcnow
from app.models.base import Base


class UpdateStepStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class UpdateStep(Base):
    __tablename__ = "update_steps"

    id = Column(Integer, primary_key=True, index=True)
    update_log_id = Column(Integer, ForeignKey("updates_log.id"), nullable=False, index=True)
    job_id = Column(String(36), nullable=True, index=True)
    step_name = Column(String(64), nullable=False)
    status = Column(Enum(UpdateStepStatus), nullable=False, default=UpdateStepStatus.RUNNING)
    output_text = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False, default=utcnow)
    finished_at = Column(DateTime, nullable=True)

