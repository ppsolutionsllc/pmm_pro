from sqlalchemy import Column, Integer, String, Boolean, Float, Enum, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base
import enum

class FuelType(str, enum.Enum):
    AB = "АБ"
    DP = "ДП"


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    name = Column(String, nullable=True)
    brand = Column(String, nullable=False)
    identifier = Column(String, nullable=True)
    fuel_type = Column(Enum(FuelType), nullable=False)
    consumption_l_per_100km = Column(Float, nullable=False)
    consumption_l_per_km = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    is_approved = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    department = relationship("Department", back_populates="vehicles")
    creator = relationship("User")
