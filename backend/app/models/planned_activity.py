from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship

from app.core.time import utcnow
from app.models.base import Base


request_planned_activities = Table(
    "request_planned_activities",
    Base.metadata,
    Column("request_id", Integer, ForeignKey("requests.id"), primary_key=True),
    Column("planned_activity_id", Integer, ForeignKey("planned_activities.id"), primary_key=True),
)


class PlannedActivity(Base):
    __tablename__ = "planned_activities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utcnow)

    requests = relationship(
        "Request",
        secondary=request_planned_activities,
        back_populates="planned_activities",
    )
