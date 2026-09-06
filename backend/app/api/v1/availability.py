from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.models.interview import InterviewRequest
from app.models.availability_slot import AvailabilitySlot
from app.models.booking import Booking
from app.models.panelist import Panelist
from app.schemas.availability import CandidateAvailabilitySubmit, CandidateLinkData, SlotInfo
from app.services.token_service import is_expired
from app.services.booking_service import book_slot_atomic, SlotConflictError
from app.services.notification_service import send_reschedule_request_notice

router = APIRouter(prefix="/availability", tags=["availability"])


class CandidateRescheduleRequest(BaseModel):
    token: str
    reason: str = ""


@router.get("/candidate/{token}", response_model=CandidateLinkData)
def get_candidate_link_data(token: str, db: Session = Depends(get_db)):
    if not token or len(token) != 36:
        raise HTTPException(status_code=400, detail="Invalid token format")

    interview = db.query(InterviewRequest).options(
        joinedload(InterviewRequest.candidate),
        joinedload(InterviewRequest.slots),
    ).filter(InterviewRequest.candidate_link_token == token).first()

    if not interview:
        raise HTTPException(status_code=404, detail="Link not found")

    existing_booking = db.query(Booking).filter(
        Booking.interview_request_id == interview.id,
        Booking.status == "confirmed",
    ).first()

    if existing_booking:
        return CandidateLinkData(
            interview_id=interview.id,
            candidate_name=interview.candidate.name,
            job_title=interview.job_title,
            round_type=interview.round_type,
            duration_minutes=interview.duration_minutes,
            recruiter_email=interview.recruiter_email,
            slots=[],
            candidate_timezone=interview.candidate.timezone,
            already_submitted=True,
        )

    if interview.token_expires_at and is_expired(interview.token_expires_at):
        return CandidateLinkData(
            interview_id=interview.id,
            candidate_name=interview.candidate.name,
            job_title=interview.job_title,
            round_type=interview.round_type,
            duration_minutes=interview.duration_minutes,
            recruiter_email=interview.recruiter_email,
            slots=[],
            candidate_timezone=interview.candidate.timezone,
            is_expired=True,
        )

    sorted_slots = sorted(
        [s for s in interview.slots if not s.is_selected],
        key=lambda x: (x.ai_rank or 999, x.start_time),
    )

    return CandidateLinkData(
        interview_id=interview.id,
        candidate_name=interview.candidate.name,
        job_title=interview.job_title,
        round_type=interview.round_type,
        duration_minutes=interview.duration_minutes,
        recruiter_email=interview.recruiter_email,
        slots=[SlotInfo.model_validate(s) for s in sorted_slots],
        candidate_timezone=interview.candidate.timezone,
    )


@router.post("/candidate/submit")
def submit_candidate_availability(
    payload: CandidateAvailabilitySubmit,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if not payload.token or len(payload.token) != 36:
        raise HTTPException(status_code=400, detail="Invalid token")

    interview = db.query(InterviewRequest).options(
        joinedload(InterviewRequest.candidate),
    ).filter(InterviewRequest.candidate_link_token == payload.token).first()

    if not interview:
        raise HTTPException(status_code=404, detail="Link not found")

    if interview.token_expires_at and is_expired(interview.token_expires_at):
        raise HTTPException(status_code=410, detail="This link has expired")

    existing = db.query(Booking).filter(
        Booking.interview_request_id == interview.id,
        Booking.status == "confirmed",
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Availability already submitted")

    # Mark selected slots (scoped to this interview via its token — a candidate
    # can only ever act on their own interview).
    selected_slots = db.query(AvailabilitySlot).filter(
        AvailabilitySlot.id.in_(payload.selected_slot_ids),
        AvailabilitySlot.interview_request_id == interview.id,
    ).all()

    if not selected_slots:
        raise HTTPException(status_code=400, detail="No valid slots found")

    for slot in selected_slots:
        slot.is_selected = True

    # Book the best-ranked selected slot atomically (authoritative conflict check).
    best_slot = sorted(selected_slots, key=lambda s: s.ai_rank or 999)[0]
    try:
        booking = book_slot_atomic(db, interview, best_slot)
    except SlotConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # Calendar event + confirmation emails happen only AFTER the booking is secured.
    from app.api.v1.bookings import _do_confirm_booking
    background_tasks.add_task(_do_confirm_booking, interview.id, best_slot.id, booking.id)

    return {
        "interview_id": str(interview.id),
        "booking_id": str(booking.id),
        "confirm_token": booking.confirm_token,
        "best_slot_id": str(best_slot.id),
    }


@router.post("/candidate/reschedule")
def request_candidate_reschedule(
    payload: CandidateRescheduleRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Candidate rejects all proposed slots and asks for a reschedule.
    Token-scoped: a candidate can only reschedule their own interview."""
    if not payload.token or len(payload.token) != 36:
        raise HTTPException(status_code=400, detail="Invalid token")

    interview = db.query(InterviewRequest).options(
        joinedload(InterviewRequest.candidate),
    ).filter(InterviewRequest.candidate_link_token == payload.token).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Link not found")

    confirmed = db.query(Booking).filter(
        Booking.interview_request_id == interview.id,
        Booking.status == "confirmed",
    ).first()
    if confirmed:
        raise HTTPException(status_code=409, detail="This interview is already booked.")

    # No proposed slot is confirmed; interview simply awaits new slots.
    interview.status = "rescheduling"
    interview.reschedule_reason = (payload.reason or "").strip() or None
    for slot in interview.slots:
        slot.is_selected = False
    db.commit()

    background_tasks.add_task(
        _notify_reschedule_requested,
        interview_id=interview.id,
        candidate_name=interview.candidate.name,
        recruiter_email=interview.recruiter_email,
        panelist_ids=interview.required_panelist_ids,
        job_title=interview.job_title,
        round_type=interview.round_type,
        reason=interview.reschedule_reason or "",
    )
    return {"message": "Reschedule requested", "interview_id": str(interview.id), "status": interview.status}


def _notify_reschedule_requested(interview_id, candidate_name, recruiter_email, panelist_ids,
                                 job_title, round_type, reason):
    from app.core.database import SessionLocal
    with SessionLocal() as session:
        send_reschedule_request_notice(session, recruiter_email, "Recruiter", "recruiter",
                                       candidate_name, job_title, round_type, reason)
        panelists = session.query(Panelist).filter(Panelist.id.in_(panelist_ids or [])).all()
        for p in panelists:
            send_reschedule_request_notice(session, p.email, p.name, "panelist",
                                           candidate_name, job_title, round_type, reason)
