from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.models.base import Base
from app.core.time import utcnow


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    deletion_reason = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=utcnow)

    users = relationship("User", back_populates="department", foreign_keys="User.department_id")
    vehicles = relationship("Vehicle", back_populates="department")
    deleter = relationship("User", foreign_keys=[deleted_by])
    print_signature = relationship(
        "DepartmentPrintSignature",
        back_populates="department",
        uselist=False,
        cascade="all, delete-orphan",
    )
