from sqlalchemy import Column, Integer, String, Text, Enum, ForeignKey, DateTime, Float, Boolean
from sqlalchemy.orm import relationship
import enum

from app.core.time import utcnow
from app.models.base import Base
from app.models.planned_activity import request_planned_activities

class RequestStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    ISSUED_BY_OPERATOR = "ISSUED_BY_OPERATOR"
    POSTED = "POSTED"
    REJECTED = "REJECTED"
    CANCELED = "CANCELED"

class Request(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, index=True)
    request_number = Column(String, unique=True, index=True, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    status = Column(Enum(RequestStatus), nullable=False, default=RequestStatus.DRAFT)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=True)
    route_is_manual = Column(Boolean, nullable=False, default=False)
    route_text = Column(Text, nullable=True)
    distance_km_per_trip = Column(Float, nullable=True)
    justification_text = Column(Text, nullable=True)

    persons_involved_count = Column(Integer, nullable=False, default=0)
    training_days_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    operator_issued_at = Column(DateTime, nullable=True)
    operator_issued_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    dept_confirmed_at = Column(DateTime, nullable=True)
    dept_confirmed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    stock_posted_at = Column(DateTime, nullable=True)
    stock_posted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    has_debt = Column(Boolean, nullable=False, default=False)

    coeff_snapshot_ab = Column(Float, nullable=True)
    coeff_snapshot_dp = Column(Float, nullable=True)
    coeff_snapshot_at = Column(DateTime, nullable=True)
    coeff_snapshot_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    is_rejected = Column(Boolean, nullable=False, default=False)
    rejection_comment = Column(Text, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejected_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    items = relationship("RequestItem", back_populates="request", cascade="all, delete-orphan")
    audits = relationship("RequestAudit", back_populates="request", cascade="all, delete-orphan")
    fuel_debts = relationship("FuelDebt", back_populates="request", cascade="all, delete-orphan")
    snapshots = relationship("RequestSnapshot", back_populates="request", cascade="all, delete-orphan")
    print_snapshots = relationship("RequestPrintSnapshot", back_populates="request", cascade="all, delete-orphan")
    print_artifacts = relationship("PrintArtifact", back_populates="request", cascade="all, delete-orphan")
    posting_sessions = relationship("PostingSession", back_populates="request", cascade="all, delete-orphan")
    stock_reservations = relationship("StockReservation", back_populates="request", cascade="all, delete-orphan")
    stock_issue = relationship("StockIssue", back_populates="request", uselist=False)
    department = relationship("Department")

    planned_activities = relationship(
        "PlannedActivity",
        secondary=request_planned_activities,
        back_populates="requests",
    )

    @property
    def planned_activity_ids(self):
        try:
            return [a.id for a in (self.planned_activities or []) if getattr(a, 'id', None) is not None]
        except Exception:
            return []

    @property
    def issue_doc_no(self):
        try:
            return self.stock_issue.issue_doc_no if self.stock_issue else None
        except Exception:
            return None
