from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship

from app.models.base import Base
import enum

class RoleEnum(str, enum.Enum):
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    DEPT_USER = "DEPT_USER"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    login = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    rank = Column(String, nullable=True)
    position = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    role = Column(Enum(RoleEnum), nullable=False)

    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    department = relationship("Department", back_populates="users", foreign_keys=[department_id])
