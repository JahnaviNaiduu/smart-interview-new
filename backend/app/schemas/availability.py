from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, field_validator,ConfigDict
from app.core.security import sanitize_string


class AvailabilityCheckRequest(BaseModel):
    interview_request_id: str
    panelist_ids: List[str]


class CandidateAvailabilitySubmit(BaseModel):
    token: str
    selected_slot_ids: List[str]
    candidate_timezone: str = "UTC"

    @field_validator("selected_slot_ids")
    @classmethod
    def validate_slots(cls, v):
        if not v:
            raise ValueError("Please select at least one slot")
        if len(v) > 5:
            raise ValueError("Please select at most 5 slots")
        return v

    @field_validator("candidate_timezone")
    @classmethod
    def sanitize_tz(cls, v):
        return sanitize_string(v, 50)


class SlotInfo(BaseModel):
    id: str
    start_time: datetime
    end_time: datetime
    ai_rank: Optional[int]
    ai_score: Optional[float]
    ai_reasoning: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class CandidateLinkData(BaseModel):
    interview_id: str
    candidate_name: str
    job_title: str
    round_type: str
    duration_minutes: int
    recruiter_email: str
    slots: List[SlotInfo]
    candidate_timezone: str
    is_expired: bool = False
    already_submitted: bool = False
