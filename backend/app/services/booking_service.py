"""Authoritative booking logic: panelist conflict detection + atomic reservation.

A panelist must never hold two overlapping confirmed interviews. Because a
panelist relates to a booking only indirectly (interview.required_panelist_ids
is a JSON list and slot times live on AvailabilitySlot), we cannot express this
as a single DB exclusion constraint portably. Instead we:
  1. lock the panelist rows (SELECT ... FOR UPDATE on Postgres; SQLite
     serializes writers anyway), which serializes concurrent bookings for the
     same panelist,
  2. re-validate overlap against live data inside that transaction,
  3. insert the booking and commit.
Two concurrent requests for the same panelist/time therefore cannot both win.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models.booking import Booking
from app.models.interview import InterviewRequest
from app.models.availability_slot import AvailabilitySlot
from app.models.panelist import Panelist


class SlotConflictError(Exception):
    """Raised when the requested panelist/time overlaps an existing confirmed booking."""


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    # Standard half-open interval overlap: a_start < b_end AND a_end > b_start.
    return a_start < b_end and a_end > b_start


def find_panelist_conflict(
    db: Session,
    panelist_ids: list[str],
    start: datetime,
    end: datetime,
    exclude_interview_id: Optional[str] = None,
) -> Optional[dict]:
    """Return conflict info if any panelist already has an overlapping confirmed
    booking, else None."""
    if not panelist_ids:
        return None
    wanted = set(panelist_ids)

    q = (
        db.query(Booking)
        .join(AvailabilitySlot, Booking.slot_id == AvailabilitySlot.id)
        .join(InterviewRequest, Booking.interview_request_id == InterviewRequest.id)
        .filter(
            Booking.status == "confirmed",
            AvailabilitySlot.start_time < end,
            AvailabilitySlot.end_time > start,
        )
    )
    if exclude_interview_id:
        q = q.filter(InterviewRequest.id != exclude_interview_id)

    for booking in q.all():
        other_panelists = set(booking.interview_request.required_panelist_ids or [])
        clash = other_panelists & wanted
        if clash and _overlaps(start, end, booking.slot.start_time, booking.slot.end_time):
            return {"booking_id": booking.id, "panelist_ids": sorted(clash)}
    return None


def book_slot_atomic(db: Session, interview: InterviewRequest, slot: AvailabilitySlot) -> Booking:
    """Reserve `slot` for `interview` atomically. Raises SlotConflictError on
    an existing booking for this interview or a panelist time overlap."""
    panelist_ids = list(interview.required_panelist_ids or [])

    # (1) Serialize concurrent bookings that share any panelist.
    if panelist_ids:
        db.query(Panelist).filter(Panelist.id.in_(panelist_ids)).with_for_update().all()

    # (2) Re-validate under the lock — never trust an earlier check.
    existing = (
        db.query(Booking)
        .filter(Booking.interview_request_id == interview.id, Booking.status == "confirmed")
        .first()
    )
    if existing:
        raise SlotConflictError("A booking already exists for this interview.")

    if find_panelist_conflict(db, panelist_ids, slot.start_time, slot.end_time,
                              exclude_interview_id=interview.id):
        raise SlotConflictError("The selected time slot is no longer available for this panelist.")

    # (3) Reserve + commit.
    booking = Booking(interview_request_id=interview.id, slot_id=slot.id, status="confirmed")
    db.add(booking)
    slot.is_selected = True
    interview.status = "booked"
    db.commit()
    db.refresh(booking)
    return booking
