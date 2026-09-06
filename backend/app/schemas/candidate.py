from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator
from app.core.security import sanitize_string, sanitize_email


class CandidateCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    timezone: str = "UTC"

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v):
        return sanitize_string(v, 255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        return sanitize_email(str(v))


class CandidateOut(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str]
    timezone: str
    created_at: datetime

    model_config = {"from_attributes": True}
