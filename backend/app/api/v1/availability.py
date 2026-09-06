from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.models.interview import InterviewRequest
from app.models.availability_slot import AvailabilitySlot
from app.models.booking import Booking
from app.schemas.availability import CandidateAvailabilitySubmit, CandidateLinkData, SlotInfo
from app.services.token_service import is_expired

router = APIRouter(prefix="/availability", tags=["availability"])


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

    # Mark selected slots
    selected_slots = db.query(AvailabilitySlot).filter(
        AvailabilitySlot.id.in_(payload.selected_slot_ids),
        AvailabilitySlot.interview_request_id == interview.id,
    ).all()

    if not selected_slots:
        raise HTTPException(status_code=400, detail="No valid slots found")

    for slot in selected_slots:
        slot.is_selected = True

    # Book the best-ranked slot
    best_slot = sorted(selected_slots, key=lambda s: s.ai_rank or 999)[0]

    interview.status = "booked"
    db.flush()

    return {"interview_id": str(interview.id), "best_slot_id": str(best_slot.id)}
