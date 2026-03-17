from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

class RequestStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    ISSUED_BY_OPERATOR = "ISSUED_BY_OPERATOR"
    POSTED = "POSTED"
    REJECTED = "REJECTED"
    CANCELED = "CANCELED"

class RequestBase(BaseModel):
    department_id: int
    route_id: Optional[int] = None
    route_is_manual: Optional[bool] = False
    route_text: Optional[str] = None
    distance_km_per_trip: Optional[float] = None
    justification_text: Optional[str] = None

    persons_involved_count: Optional[int] = 0
    training_days_count: Optional[int] = 0
    planned_activity_ids: Optional[List[int]] = None

class RequestCreate(RequestBase):
    pass

class RequestOut(RequestBase):
    id: int
    request_number: str
    status: RequestStatus
    created_at: Optional[datetime]
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    operator_issued_at: Optional[datetime] = None
    dept_confirmed_at: Optional[datetime] = None
    stock_posted_at: Optional[datetime] = None
    has_debt: bool = False
    issue_doc_no: Optional[str] = None
    coeff_snapshot_ab: Optional[float] = None
    coeff_snapshot_dp: Optional[float] = None
    coeff_snapshot_at: Optional[datetime] = None

    is_rejected: bool = False
    rejection_comment: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejected_by: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class RequestRejectIn(BaseModel):
    comment: str = Field(..., min_length=1)

# items
class RequestItemBase(BaseModel):
    planned_activity_id: Optional[int] = None
    vehicle_id: int

    route_id: Optional[int] = None
    route_is_manual: Optional[bool] = False
    route_text: Optional[str] = None
    distance_km_per_trip: Optional[float] = None
    justification_text: Optional[str] = None
    persons_involved_count: Optional[int] = None
    training_days_count: Optional[int] = None

class RequestItemCreate(RequestItemBase):
    pass

class RequestItemOut(RequestItemBase):
    id: int
    consumption_l_per_km_snapshot: float
    total_km: float
    required_liters: float
    required_kg: float

    model_config = ConfigDict(from_attributes=True)


class RequestAuditOut(BaseModel):
    id: int
    actor_user_id: Optional[int] = None
    action: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    message: Optional[str] = None
    created_at: Optional[str] = None


class RequestFuelSummaryOut(BaseModel):
    fuel_type: str
    requested_liters: float
    requested_kg: float
    issued_liters: float
    issued_kg: float
    missing_liters: float
    missing_kg: float


class RequestConfirmOut(RequestOut):
    result: str
    state: Optional[str] = None
    already_confirmed: bool = False
    posting_session_id: Optional[str] = None
    issue_id: Optional[int] = None
    fuel_summary: list[RequestFuelSummaryOut] = []
    debts: list[RequestFuelSummaryOut] = []
    request: Optional[dict] = None
    posting_session: Optional[dict] = None
    issue: Optional[dict] = None
    breakdown: Optional[dict] = None
    message: Optional[str] = None


class AdminMonthEndConfirmIn(BaseModel):
    request_ids: Optional[List[int]] = None
    async_mode: bool = False
    idempotency_key: Optional[str] = None


class RequestReverseIn(BaseModel):
    reason: str = Field(..., min_length=1)
    idempotency_key: Optional[str] = None


class RequestConfirmIn(BaseModel):
    idempotency_key: Optional[str] = None


class PostingSessionOut(BaseModel):
    id: str
    request_id: Optional[int] = None
    operation: str
    idempotency_key: str
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    started_by_user_id: Optional[int] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    result_json: Optional[dict] = None
    result_ref: Optional[dict] = None
    retry_count: int = 0
