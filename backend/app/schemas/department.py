from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class DepartmentBase(BaseModel):
    name: str
    is_active: Optional[bool] = True

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None

class DepartmentOut(DepartmentBase):
    id: int
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[int] = None
    deletion_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DepartmentPrintSignatureBase(BaseModel):
    approval_title: str = "З розрахунком згоден:"
    approval_rank: str = ""
    approval_position: str = ""
    approval_name: str = ""
    agreed_title: str = "ПОГОДЖЕНО:"
    agreed_rank: str = ""
    agreed_position: str = ""
    agreed_name: str = ""


class DepartmentPrintSignatureUpdate(DepartmentPrintSignatureBase):
    pass


class DepartmentPrintSignatureDeptUpdate(BaseModel):
    approval_title: str = "З розрахунком згоден:"
    approval_rank: str = ""
    approval_position: str = ""
    approval_name: str = ""


class DepartmentPrintSignatureAdminUpdate(BaseModel):
    agreed_title: str = "ПОГОДЖЕНО:"
    agreed_rank: str = ""
    agreed_position: str = ""
    agreed_name: str = ""


class DepartmentPrintSignatureOut(DepartmentPrintSignatureBase):
    id: int
    department_id: int
    updated_at: Optional[datetime] = None
    updated_by: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class DepartmentDeleteIn(BaseModel):
    reason: str
