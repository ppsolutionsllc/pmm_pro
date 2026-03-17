from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, Text

from app.core.time import utcnow
from app.models.base import Base
from app.models.stock import FuelType


class FuelCoeffHistory(Base):
    __tablename__ = "fuel_coeff_history"

    id = Column(Integer, primary_key=True, index=True)
    fuel_type = Column(Enum(FuelType), nullable=False)
    density_kg_per_l = Column(Float, nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    changed_at = Column(DateTime, nullable=False, default=utcnow)
    comment = Column(Text, nullable=True)
