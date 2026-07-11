from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr


class EmployeeCreate(BaseModel):
    employee_code: str
    full_name: str
    department: Optional[str] = None
    designation: Optional[str] = None
    email: Optional[EmailStr] = None


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    employee_code: str
    full_name: str
    department: Optional[str] = None
    designation: Optional[str] = None
    email: Optional[str] = None
    is_active: bool
    created_at: datetime
    registered_faces: int = 0


class RegistrationResult(BaseModel):
    employee_id: str
    accepted_images: int
    rejected_images: list[str]  # reasons for each rejected image
    message: str
