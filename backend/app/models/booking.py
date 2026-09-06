import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    interview_request_id: Mapped[str] = mapped_column(String(36), ForeignKey("interview_requests.id"), nullable=False)
    slot_id: Mapped[str] = mapped_column(String(36), ForeignKey("availability_slots.id"), nullable=False)
    google_event_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    meet_link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="confirmed")
    confirm_token: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    rescheduled_from_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("bookings.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    interview_request: Mapped["InterviewRequest"] = relationship("InterviewRequest", back_populates="booking")
    slot: Mapped["AvailabilitySlot"] = relationship("AvailabilitySlot", back_populates="booking")
    notifications: Mapped[List["NotificationLog"]] = relationship("NotificationLog", back_populates="booking", cascade="all, delete-orphan")
