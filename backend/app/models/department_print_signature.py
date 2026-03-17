from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.time import utcnow
from app.models.base import Base


class DepartmentPrintSignature(Base):
    __tablename__ = "department_print_signatures"

    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    approval_title = Column(String(255), nullable=False, default="З розрахунком згоден:")
    approval_position = Column(String(255), nullable=False, default="")
    approval_name = Column(String(255), nullable=False, default="")

    agreed_title = Column(String(255), nullable=False, default="ПОГОДЖЕНО:")
    agreed_position = Column(String(255), nullable=False, default="")
    agreed_name = Column(String(255), nullable=False, default="")

    created_at = Column(DateTime, nullable=False, default=utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=utcnow)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    department = relationship("Department", back_populates="print_signature")
