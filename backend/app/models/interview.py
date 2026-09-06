import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, DateTime, Integer, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class InterviewRequest(Base):
    __tablename__ = "interview_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    round_type: Mapped[str] = mapped_column(String(50), nullable=False)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"), nullable=False)
    required_panelist_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    buffer_minutes: Mapped[int] = mapped_column(Integer, default=15)
    window_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    preferred_timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    status: Mapped[str] = mapped_column(String(50), default="pending")
    recruiter_email: Mapped[str] = mapped_column(String(255), nullable=False)
    candidate_link_token: Mapped[Optional[str]] = mapped_column(String(36), unique=True, nullable=True)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reschedule_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="interviews")
    slots: Mapped[List["AvailabilitySlot"]] = relationship("AvailabilitySlot", back_populates="interview_request", cascade="all, delete-orphan")
    booking: Mapped[Optional["Booking"]] = relationship("Booking", back_populates="interview_request", uselist=False)
