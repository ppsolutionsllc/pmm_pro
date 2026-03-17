from typing import Optional
from pydantic import BaseModel, ConfigDict
import enum
from datetime import datetime


class VehicleChangeStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class VehicleChangeRequestCreate(BaseModel):
    brand: Optional[str] = None
    identifier: Optional[str] = None
    fuel_type: Optional[str] = None
    consumption_l_per_100km: Optional[float] = None


class VehicleChangeRequestOut(BaseModel):
    id: int
    vehicle_id: int
    department_id: int
    requested_by: int
    status: VehicleChangeStatus

    brand: Optional[str] = None
    identifier: Optional[str] = None
    fuel_type: Optional[str] = None
    consumption_l_per_100km: Optional[float] = None

    created_at: Optional[datetime] = None
    decided_at: Optional[datetime] = None
    decided_by: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
