from datetime import datetime
from typing import Literal, Optional, List
from pydantic import BaseModel, field_validator, model_validator
from app.schemas.candidate import CandidateCreate, CandidateOut
from app.core.security import sanitize_string

RoundType = Literal["screening", "technical", "managerial", "hr"]
InterviewStatus = Literal["pending", "slots_found", "candidate_notified", "booked", "cancelled", "rescheduling"]


class InterviewRequestCreate(BaseModel):
    job_title: str
    round_type: RoundType
    candidate: CandidateCreate
    required_panelist_ids: List[str]
    duration_minutes: int = 60
    buffer_minutes: int = 15
    window_start: datetime
    window_end: datetime
    # Optional: the timezone used for working-hours/scheduling. Defaults to the
    # candidate's timezone on the server if omitted. Not a required form field.
    preferred_timezone: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("job_title")
    @classmethod
    def sanitize_job_title(cls, v):
        return sanitize_string(v, 255)

    @field_validator("duration_minutes")
    @classmethod
    def validate_duration(cls, v):
        if v not in [30, 45, 60, 90]:
            raise ValueError("Duration must be 30, 45, 60, or 90 minutes")
        return v

    @field_validator("buffer_minutes")
    @classmethod
    def validate_buffer(cls, v):
        if v not in [0, 15, 30]:
            raise ValueError("Buffer must be 0, 15, or 30 minutes")
        return v

    @field_validator("required_panelist_ids")
    @classmethod
    def validate_panelists(cls, v):
        if not v:
            raise ValueError("At least one panelist is required")
        return v

    @model_validator(mode="after")
    def validate_window(self):
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        return self


class InterviewRequestUpdate(BaseModel):
    status: Optional[InterviewStatus] = None
    notes: Optional[str] = None


class SlotOut(BaseModel):
    id: str
    start_time: datetime
    end_time: datetime
    ai_rank: Optional[int]
    ai_score: Optional[float]
    ai_reasoning: Optional[str]
    is_selected: bool

    model_config = {"from_attributes": True}


class InterviewRequestOut(BaseModel):
    id: str
    job_title: str
    round_type: str
    candidate_id: str
    candidate: Optional[CandidateOut] = None
    required_panelist_ids: list
    duration_minutes: int
    buffer_minutes: int
    window_start: datetime
    window_end: datetime
    preferred_timezone: str
    status: str
    recruiter_email: str
    candidate_link_token: Optional[str]
    token_expires_at: Optional[datetime]
    notes: Optional[str]
    slots: List[SlotOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
