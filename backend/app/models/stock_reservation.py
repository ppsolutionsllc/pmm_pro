import enum

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.time import utcnow
from app.models.base import Base
from app.models.stock import FuelType


class ReservationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    CONSUMED = "CONSUMED"


class StockReservation(Base):
    __tablename__ = "stock_reservations"
    __table_args__ = (
        UniqueConstraint("request_id", "fuel_type", name="uq_stock_reservations_request_fuel"),
    )

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=False, index=True)
    fuel_type = Column(Enum(FuelType), nullable=False)
    reserved_liters = Column(Float, nullable=False, default=0.0)
    reserved_kg = Column(Float, nullable=False, default=0.0)
    status = Column(Enum(ReservationStatus), nullable=False, default=ReservationStatus.ACTIVE)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    request = relationship("Request", back_populates="stock_reservations")
