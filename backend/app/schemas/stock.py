from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
import enum

class FuelType(str, enum.Enum):
    AB = "АБ"
    DP = "ДП"

class UnitEnum(str, enum.Enum):
    L = "L"
    KG = "KG"

class StockReceiptCreate(BaseModel):
    fuel_type: FuelType
    input_unit: UnitEnum
    input_amount: float = Field(..., gt=0)

class StockReceiptOut(StockReceiptCreate):
    id: int
    computed_liters: float
    computed_kg: float
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StockAdjustmentLineIn(BaseModel):
    fuel_type: FuelType
    delta_liters: float
    delta_kg: float
    request_id: Optional[int] = None
    comment: Optional[str] = None


class StockAdjustmentCreateIn(BaseModel):
    reason: str = Field(..., min_length=1)
    lines: list[StockAdjustmentLineIn]
    idempotency_key: Optional[str] = None


class StockAdjustmentOut(BaseModel):
    id: int
    adjustment_doc_no: str
    reason: str
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StockAdjustmentLineOut(BaseModel):
    id: int
    fuel_type: FuelType
    delta_liters: float
    delta_kg: float
    request_id: Optional[int] = None
    comment: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class StockAdjustmentDetailOut(StockAdjustmentOut):
    lines: list[StockAdjustmentLineOut] = []


class StockReconcileRowOut(BaseModel):
    fuel_type: str
    receipts_liters: float
    receipts_kg: float
    issues_liters: float
    issues_kg: float
    adjustments_liters: float
    adjustments_kg: float
    expected_balance_liters: float
    expected_balance_kg: float
    actual_balance_liters: float
    actual_balance_kg: float
    difference_liters: float
    difference_kg: float
    is_consistent: bool


class VehicleReportFilterIn(BaseModel):
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    department_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    fuel_type: Optional[str] = None
    route_contains: Optional[str] = None
