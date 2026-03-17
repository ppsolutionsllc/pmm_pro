import enum
import json

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship

from app.core.time import utcnow
from app.models.base import Base


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)

    name = Column(String, nullable=False)
    points_json = Column(Text, nullable=False, default="[]")
    distance_km = Column(Float, nullable=False, default=0.0)

    is_approved = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    department = relationship("Department")
    creator = relationship("User")

    def get_points(self):
        try:
            v = json.loads(self.points_json or "[]")
            return v if isinstance(v, list) else []
        except Exception:
            return []


class RouteChangeStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RouteChangeRequest(Base):
    __tablename__ = "route_change_requests"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    status = Column(String, nullable=False, default=RouteChangeStatus.PENDING.value)

    name = Column(String, nullable=True)
    points_json = Column(Text, nullable=True)
    distance_km = Column(Float, nullable=True)

    created_at = Column(DateTime, default=utcnow)
    decided_at = Column(DateTime, nullable=True)
    decided_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    route = relationship("Route")
    department = relationship("Department")
    requester = relationship("User", foreign_keys=[requested_by])
    decider = relationship("User", foreign_keys=[decided_by])

    def get_points(self):
        try:
            v = json.loads(self.points_json or "[]")
            return v if isinstance(v, list) else []
        except Exception:
            return []
