import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.time import utcnow
from app.models.base import Base


class PostingOperation(str, enum.Enum):
    CONFIRM = "CONFIRM"
    MONTH_END_CONFIRM = "MONTH_END_CONFIRM"
    ADJUSTMENT = "ADJUSTMENT"
    EXPORT = "EXPORT"
    RECONCILE = "RECONCILE"
    UPDATE = "UPDATE"


class PostingSessionStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class PostingSession(Base):
    __tablename__ = "posting_sessions"
    __table_args__ = (
        UniqueConstraint("operation", "idempotency_key", name="uq_posting_sessions_operation_idem_key"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=True, index=True)
    operation = Column(Enum(PostingOperation), nullable=False)
    idempotency_key = Column(String(128), nullable=False)
    status = Column(Enum(PostingSessionStatus), nullable=False, default=PostingSessionStatus.IN_PROGRESS)
    started_at = Column(DateTime, nullable=False, default=utcnow)
    finished_at = Column(DateTime, nullable=True)
    started_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    result_json = Column(JSON, nullable=True)
    result_ref = Column(JSON, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)

    request = relationship("Request", back_populates="posting_sessions")
