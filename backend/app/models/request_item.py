from sqlalchemy import Column, Integer, ForeignKey, Float, Text, Boolean
from sqlalchemy.orm import relationship

from app.models.base import Base

class RequestItem(Base):
    __tablename__ = "request_items"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=False)
    planned_activity_id = Column(Integer, ForeignKey("planned_activities.id"), nullable=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    people_count = Column(Integer, nullable=True)

    route_id = Column(Integer, ForeignKey("routes.id"), nullable=True)
    route_is_manual = Column(Boolean, nullable=False, default=False)
    route_text = Column(Text, nullable=True)
    distance_km_per_trip = Column(Float, nullable=True)
    justification_text = Column(Text, nullable=True)
    persons_involved_count = Column(Integer, nullable=True)
    training_days_count = Column(Integer, nullable=True)

    consumption_l_per_km_snapshot = Column(Float, nullable=False)
    total_km = Column(Float, nullable=False)
    required_liters = Column(Float, nullable=False)
    required_kg = Column(Float, nullable=False)

    request = relationship("Request", back_populates="items")
    planned_activity = relationship("PlannedActivity")
    vehicle = relationship("Vehicle")
    route = relationship("Route")
