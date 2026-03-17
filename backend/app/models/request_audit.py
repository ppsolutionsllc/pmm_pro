from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.time import utcnow
from app.models.base import Base


class RequestAudit(Base):
    __tablename__ = "request_audit"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=False, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    from_status = Column(String, nullable=True)
    to_status = Column(String, nullable=True)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    request = relationship("Request", back_populates="audits")
