import enum

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.time import utcnow
from app.models.base import Base


class FuelType(str, enum.Enum):
    AB = "АБ"
    DP = "ДП"


class RefType(str, enum.Enum):
    RECEIPT = "receipt"
    ISSUE = "issue"


class StockIssueStatus(str, enum.Enum):
    POSTED = "POSTED"
    DEBT = "DEBT"
    REVERSED = "REVERSED"


class DebtStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class StockReceipt(Base):
    __tablename__ = "stock_receipts"
    id = Column(Integer, primary_key=True, index=True)
    fuel_type = Column(Enum(FuelType), nullable=False)
    input_unit = Column(Enum("L", "KG", name="unit_enum"), nullable=False)
    input_amount = Column(Float, nullable=False)
    computed_liters = Column(Float, nullable=False)
    computed_kg = Column(Float, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)


class StockIssue(Base):
    __tablename__ = "stock_issues"
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=False, unique=True)
    issue_doc_no = Column(String, nullable=False, unique=True)
    status = Column(Enum(StockIssueStatus), nullable=False, default=StockIssueStatus.POSTED)
    posted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    posted_at = Column(DateTime, nullable=False, default=utcnow)
    breakdown_json = Column(JSON, nullable=True)
    has_debt = Column(Boolean, nullable=False, default=False)
    debt_liters = Column(Float, nullable=False, default=0.0)
    debt_kg = Column(Float, nullable=False, default=0.0)
    # legacy aggregate totals
    fuel_type = Column(Enum(FuelType), nullable=False)
    issue_liters = Column(Float, nullable=False)
    issue_kg = Column(Float, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    request = relationship("Request", back_populates="stock_issue")
    lines = relationship("StockIssueLine", back_populates="stock_issue", cascade="all, delete-orphan")


class StockIssueLine(Base):
    __tablename__ = "stock_issue_lines"
    id = Column(Integer, primary_key=True, index=True)
    stock_issue_id = Column(Integer, ForeignKey("stock_issues.id"), nullable=False, index=True)
    fuel_type = Column(Enum(FuelType), nullable=False)
    requested_liters = Column(Float, nullable=False, default=0.0)
    requested_kg = Column(Float, nullable=False, default=0.0)
    issued_liters = Column(Float, nullable=False, default=0.0)
    issued_kg = Column(Float, nullable=False, default=0.0)
    missing_liters = Column(Float, nullable=False, default=0.0)
    missing_kg = Column(Float, nullable=False, default=0.0)
    stock_issue = relationship("StockIssue", back_populates="lines")


class FuelDebt(Base):
    __tablename__ = "fuel_debts"
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=False, index=True)
    fuel_type = Column(Enum(FuelType), nullable=False)
    missing_liters = Column(Float, nullable=False)
    missing_kg = Column(Float, nullable=False)
    status = Column(Enum(DebtStatus), nullable=False, default=DebtStatus.OPEN)
    created_at = Column(DateTime, default=utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    close_comment = Column(Text, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    closed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    request = relationship("Request", back_populates="fuel_debts")


class StockLedger(Base):
    __tablename__ = "stock_ledger"
    id = Column(Integer, primary_key=True, index=True)
    fuel_type = Column(Enum(FuelType), nullable=False)
    delta_liters = Column(Float, nullable=False)
    delta_kg = Column(Float, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    ref_type = Column(Enum(RefType), nullable=False)
    ref_id = Column(Integer, nullable=False)


class StockBalance(Base):
    __tablename__ = "stock_balance"
    id = Column(Integer, primary_key=True, index=True)
    fuel_type = Column(Enum(FuelType), unique=True, nullable=False)
    balance_liters = Column(Float, nullable=False, default=0.0)
    balance_kg = Column(Float, nullable=False, default=0.0)


class StockAdjustment(Base):
    __tablename__ = "stock_adjustments"
    id = Column(Integer, primary_key=True, index=True)
    adjustment_doc_no = Column(String, nullable=False, unique=True)
    reason = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    lines = relationship("StockAdjustmentLine", back_populates="adjustment", cascade="all, delete-orphan")


class StockAdjustmentLine(Base):
    __tablename__ = "stock_adjustment_lines"
    id = Column(Integer, primary_key=True, index=True)
    adjustment_id = Column(Integer, ForeignKey("stock_adjustments.id"), nullable=False, index=True)
    fuel_type = Column(Enum(FuelType), nullable=False)
    delta_liters = Column(Float, nullable=False)
    delta_kg = Column(Float, nullable=False)
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=True)
    comment = Column(Text, nullable=True)
    adjustment = relationship("StockAdjustment", back_populates="lines")
