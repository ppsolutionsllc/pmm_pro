from sqlalchemy import Column, DateTime, Integer, String

from app.core.time import utcnow
from app.models.base import Base


class IssueDocSequence(Base):
    __tablename__ = "issue_doc_sequences"

    id = Column(Integer, primary_key=True, index=True)
    scope_key = Column(String(16), nullable=False, unique=True, index=True)
    next_value = Column(Integer, nullable=False, default=1)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
