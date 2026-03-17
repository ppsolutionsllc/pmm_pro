from typing import Optional
from pydantic import BaseModel, ConfigDict


class PlannedActivityBase(BaseModel):
    name: str
    is_active: bool = True


class PlannedActivityCreate(PlannedActivityBase):
    pass


class PlannedActivityUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class PlannedActivityOut(PlannedActivityBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
