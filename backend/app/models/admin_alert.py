from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.core.time import utcnow
from app.models.base import Base


class AdminAlert(Base):
    __tablename__ = "admin_alerts"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)
    severity = Column(String, nullable=False, default="ERROR")
    message = Column(Text, nullable=False)
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=True, index=True)
    posting_session_id = Column(String(36), ForeignKey("posting_sessions.id"), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolution_comment = Column(Text, nullable=True)
