from typing import Optional
from pydantic import BaseModel, ConfigDict
from enum import Enum

class FuelType(str, Enum):
    AB = "АБ"
    DP = "ДП"

class VehicleBase(BaseModel):
    department_id: int
    brand: str
    identifier: Optional[str] = None
    fuel_type: FuelType
    consumption_l_per_100km: float
    is_active: Optional[bool] = True

class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    department_id: Optional[int] = None
    brand: Optional[str] = None
    identifier: Optional[str] = None
    fuel_type: Optional[FuelType] = None
    consumption_l_per_100km: Optional[float] = None
    is_active: Optional[bool] = None
    is_approved: Optional[bool] = None

class VehicleOut(VehicleBase):
    id: int
    consumption_l_per_km: float
    is_approved: bool
    created_by: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
