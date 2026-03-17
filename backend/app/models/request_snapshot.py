import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship

from app.core.time import utcnow
from app.models.base import Base


class RequestSnapshotStage(str, enum.Enum):
    SUBMIT = "SUBMIT"
    APPROVE = "APPROVE"
    CONFIRM = "CONFIRM"


class RequestSnapshot(Base):
    __tablename__ = "request_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=False, index=True)
    stage = Column(Enum(RequestSnapshotStage), nullable=False)
    payload_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    request = relationship("Request", back_populates="snapshots")
