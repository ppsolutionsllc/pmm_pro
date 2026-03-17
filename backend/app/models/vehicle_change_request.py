from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Float
from sqlalchemy.orm import relationship
import enum

from app.core.time import utcnow
from app.models.base import Base


class VehicleChangeStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class VehicleChangeRequest(Base):
    __tablename__ = "vehicle_change_requests"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    status = Column(Enum(VehicleChangeStatus), nullable=False, default=VehicleChangeStatus.PENDING)

    brand = Column(String, nullable=True)
    identifier = Column(String, nullable=True)
    fuel_type = Column(String, nullable=True)
    consumption_l_per_100km = Column(Float, nullable=True)

    created_at = Column(DateTime, default=utcnow)
    decided_at = Column(DateTime, nullable=True)
    decided_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    vehicle = relationship("Vehicle")
    department = relationship("Department")
    requester = relationship("User", foreign_keys=[requested_by])
    decider = relationship("User", foreign_keys=[decided_by])
