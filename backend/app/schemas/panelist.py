from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator
from app.core.security import sanitize_string, sanitize_email


class PanelistCreate(BaseModel):
    name: str
    email: EmailStr
    role: Optional[str] = None
    skills: List[str] = []

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v):
        return sanitize_string(v, 255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        return sanitize_email(str(v))

    @field_validator("skills")
    @classmethod
    def sanitize_skills(cls, v):
        return [sanitize_string(s, 100) for s in v if s]


class PanelistUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    skills: Optional[List[str]] = None
    is_active: Optional[bool] = None


class PanelistOut(BaseModel):
    id: str
    name: str
    email: str
    role: Optional[str]
    skills: Optional[list]
    google_calendar_id: Optional[str]
    is_active: bool
    calendar_connected: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_calendar(cls, panelist):
        data = cls.model_validate(panelist)
        data.calendar_connected = bool(panelist.google_access_token)
        return data
