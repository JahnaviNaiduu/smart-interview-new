"""Problem 2 — a panelist can never have two overlapping confirmed interviews."""
import uuid
from datetime import datetime
import pytest
from app.core.database import SessionLocal
from app.models.candidate import Candidate
from app.models.panelist import Panelist
from app.models.interview import InterviewRequest
from app.models.availability_slot import AvailabilitySlot
from app.services.booking_service import book_slot_atomic, find_panelist_conflict, SlotConflictError


def _mk_interview(db, panelist_id, start, end, status="slots_found"):
    cand = Candidate(name="C", email=f"c-{uuid.uuid4()}@x.com", timezone="UTC")
    db.add(cand)
    db.flush()
    iv = InterviewRequest(
        job_title="Eng", round_type="technical", candidate_id=cand.id,
        required_panelist_ids=[panelist_id], duration_minutes=60, buffer_minutes=0,
        window_start=start, window_end=end, preferred_timezone="UTC",
        recruiter_email="rec@x.com", status=status,
    )
    db.add(iv)
    db.flush()
    slot = AvailabilitySlot(interview_request_id=iv.id, start_time=start, end_time=end, ai_rank=1)
    db.add(slot)
    db.flush()
    return iv, slot


@pytest.fixture()
def booked_panelist(client):
    """Panelist John booked 10:00–11:00. Returns his id.
    Depends on `client` so the app lifespan has created the tables."""
    with SessionLocal() as db:
        p = Panelist(name="John", email=f"john-{uuid.uuid4()}@x.com", skills=["Python"])
        db.add(p)
        db.flush()
        iv, slot = _mk_interview(db, p.id, datetime(2099, 3, 2, 10, 0), datetime(2099, 3, 2, 11, 0))
        book_slot_atomic(db, iv, slot)  # commits
        return p.id


@pytest.mark.parametrize("start,end", [
    (datetime(2099, 3, 2, 10, 0), datetime(2099, 3, 2, 11, 0)),   # exact
    (datetime(2099, 3, 2, 9, 30), datetime(2099, 3, 2, 10, 30)),  # partial front
    (datetime(2099, 3, 2, 10, 30), datetime(2099, 3, 2, 11, 30)), # partial back
    (datetime(2099, 3, 2, 9, 0), datetime(2099, 3, 2, 12, 0)),    # contains
])
def test_overlapping_intervals_rejected(booked_panelist, start, end):
    with SessionLocal() as db:
        conflict = find_panelist_conflict(db, [booked_panelist], start, end)
        assert conflict is not None


@pytest.mark.parametrize("start,end", [
    (datetime(2099, 3, 2, 8, 0), datetime(2099, 3, 2, 9, 0)),     # before
    (datetime(2099, 3, 2, 11, 0), datetime(2099, 3, 2, 12, 0)),   # after (touching)
])
def test_nonoverlapping_intervals_allowed(booked_panelist, start, end):
    with SessionLocal() as db:
        assert find_panelist_conflict(db, [booked_panelist], start, end) is None


def test_second_candidate_cannot_book_same_panelist_time(booked_panelist):
    with SessionLocal() as db:
        iv2, slot2 = _mk_interview(db, booked_panelist,
                                   datetime(2099, 3, 2, 10, 30), datetime(2099, 3, 2, 11, 30))
        with pytest.raises(SlotConflictError):
            book_slot_atomic(db, iv2, slot2)


def test_existing_booking_not_overwritten_and_no_extra_booking(booked_panelist):
    from app.models.booking import Booking
    with SessionLocal() as db:
        before = db.query(Booking).filter(Booking.status == "confirmed").count()
        iv2, slot2 = _mk_interview(db, booked_panelist,
                                   datetime(2099, 3, 2, 10, 0), datetime(2099, 3, 2, 11, 0))
        with pytest.raises(SlotConflictError):
            book_slot_atomic(db, iv2, slot2)
    with SessionLocal() as db:
        after = db.query(Booking).filter(Booking.status == "confirmed").count()
    assert after == before  # no conflicting booking created


def test_non_overlapping_second_booking_succeeds(booked_panelist):
    with SessionLocal() as db:
        iv2, slot2 = _mk_interview(db, booked_panelist,
                                   datetime(2099, 3, 2, 11, 0), datetime(2099, 3, 2, 12, 0))
        booking = book_slot_atomic(db, iv2, slot2)
        assert booking.status == "confirmed"


def test_booking_api_returns_409_on_conflict(client, recruiter_headers):
    """API-level: a slot overlapping an existing confirmed booking → HTTP 409."""
    with SessionLocal() as db:
        p = Panelist(name="Api John", email=f"apijohn-{uuid.uuid4()}@x.com", skills=["Go"])
        db.add(p)
        db.flush()
        iv1, slot1 = _mk_interview(db, p.id, datetime(2099, 4, 1, 10, 0), datetime(2099, 4, 1, 11, 0))
        book_slot_atomic(db, iv1, slot1)
        # Second interview + overlapping slot, not yet booked.
        iv2, slot2 = _mk_interview(db, p.id, datetime(2099, 4, 1, 10, 30), datetime(2099, 4, 1, 11, 30))
        db.commit()
        iv2_id, slot2_id = iv2.id, slot2.id

    res = client.post("/api/v1/bookings",
                      json={"interview_request_id": iv2_id, "slot_id": slot2_id},
                      headers=recruiter_headers)
    assert res.status_code == 409, res.text
    assert "no longer available" in res.json()["detail"].lower()
