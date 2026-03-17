from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime
import enum


class RouteCreate(BaseModel):
    department_id: int
    name: str
    points: List[str]
    distance_km: float


class RouteOut(BaseModel):
    id: int
    department_id: int
    name: str
    points: List[str]
    distance_km: float
    is_approved: bool
    created_at: Optional[datetime] = None
    created_by: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class RouteChangeStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RouteChangeRequestCreate(BaseModel):
    name: Optional[str] = None
    points: Optional[List[str]] = None
    distance_km: Optional[float] = None


class RouteChangeRequestOut(BaseModel):
    id: int
    route_id: int
    department_id: int
    requested_by: int
    status: str
    name: Optional[str] = None
    points: Optional[List[str]] = None
    distance_km: Optional[float] = None
    created_at: Optional[datetime] = None
    decided_at: Optional[datetime] = None
    decided_by: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
