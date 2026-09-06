from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class BookingCreate(BaseModel):
    interview_request_id: str
    slot_id: str


class BookingOut(BaseModel):
    id: str
    interview_request_id: str
    slot_id: str
    google_event_id: Optional[str]
    meet_link: Optional[str]
    status: str
    confirm_token: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BookingDetailOut(BookingOut):
    slot_start: Optional[datetime] = None
    slot_end: Optional[datetime] = None
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    job_title: Optional[str] = None
    round_type: Optional[str] = None
