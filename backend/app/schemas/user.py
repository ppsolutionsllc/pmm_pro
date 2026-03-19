from typing import Optional
from pydantic import BaseModel, ConfigDict
import enum

class RoleEnum(str, enum.Enum):
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    DEPT_USER = "DEPT_USER"

class UserBase(BaseModel):
    login: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    rank: Optional[str] = None
    position: Optional[str] = None
    is_active: Optional[bool] = True
    role: RoleEnum
    department_id: Optional[int] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    login: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    rank: Optional[str] = None
    position: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class UserOut(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
