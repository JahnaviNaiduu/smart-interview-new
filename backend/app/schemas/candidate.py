from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator
from app.core.security import sanitize_string, sanitize_email


class CandidateCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    timezone: str = "UTC"
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
        return [sanitize_string(s, 100) for s in (v or []) if s and s.strip()]


class CandidateOut(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str]
    timezone: str
    skills: Optional[list] = []
    created_at: datetime

    model_config = {"from_attributes": True}
