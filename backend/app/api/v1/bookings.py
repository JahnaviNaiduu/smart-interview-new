from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.config import settings
from app.core.auth import require_staff
from app.models.booking import Booking
from app.models.interview import InterviewRequest
from app.models.availability_slot import AvailabilitySlot
from app.models.panelist import Panelist
from app.schemas.booking import BookingCreate, BookingOut, BookingDetailOut
from app.services.calendar_service import create_calendar_event, delete_calendar_event
from app.services.notification_service import send_booking_confirmation, send_cancellation

router = APIRouter(prefix="/bookings", tags=["bookings"])


def _do_confirm_booking(interview_id: str, slot_id: str, booking_id: str):
    from app.core.database import SessionLocal
    with SessionLocal() as db:
        booking = db.query(Booking).options(
            joinedload(Booking.interview_request).joinedload(InterviewRequest.candidate),
            joinedload(Booking.slot),
        ).filter(Booking.id == booking_id).first()
        if not booking:
            return

        interview = booking.interview_request
        slot = booking.slot
        panelists = db.query(Panelist).filter(Panelist.id.in_(interview.required_panelist_ids)).all()

        all_emails = [interview.candidate.email] + [p.email for p in panelists] + [interview.recruiter_email]
        meet_link = None
        google_event_id = None

        creator_panelist = next((p for p in panelists if p.google_access_token), None)
        if creator_panelist:
            try:
                result = create_calendar_event(
                    access_token=creator_panelist.google_access_token,
                    refresh_token=creator_panelist.google_refresh_token,
                    token_expiry=creator_panelist.token_expiry,
                    summary=f"{interview.round_type.title()} Interview — {interview.job_title}",
                    description=f"Interview with {interview.candidate.name} for {interview.job_title}.\nRound: {interview.round_type.title()}",
                    start_time=slot.start_time,
                    end_time=slot.end_time,
                    attendee_emails=all_emails,
                    timezone=interview.preferred_timezone,
                )
                meet_link = result.get("meet_link")
                google_event_id = result.get("event_id")
            except RuntimeError:
                pass

        booking.meet_link = meet_link
        booking.google_event_id = google_event_id
        db.commit()

        confirm_link = f"{settings.FRONTEND_URL}/confirm/{booking.confirm_token}"

        send_booking_confirmation(db, interview.candidate.email, interview.candidate.name, "candidate",
                                  interview.job_title, interview.round_type, slot.start_time, slot.end_time,
                                  meet_link, confirm_link, booking.id)
        for p in panelists:
            send_booking_confirmation(db, p.email, p.name, "panelist",
                                      interview.job_title, interview.round_type, slot.start_time, slot.end_time,
                                      meet_link, confirm_link, booking.id)
        send_booking_confirmation(db, interview.recruiter_email, "Recruiter", "recruiter",
                                  interview.job_title, interview.round_type, slot.start_time, slot.end_time,
                                  meet_link, confirm_link, booking.id)


@router.post("", response_model=BookingOut, status_code=201)
def create_booking(payload: BookingCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db), _=Depends(require_staff)):
    interview = db.query(InterviewRequest).options(
        joinedload(InterviewRequest.candidate),
    ).filter(InterviewRequest.id == payload.interview_request_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview request not found")

    slot = db.query(AvailabilitySlot).filter(
        AvailabilitySlot.id == payload.slot_id,
        AvailabilitySlot.interview_request_id == payload.interview_request_id,
    ).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found or does not belong to this interview")

    existing = db.query(Booking).filter(
        Booking.interview_request_id == payload.interview_request_id,
        Booking.status == "confirmed",
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="A booking already exists for this interview")

    booking = Booking(
        interview_request_id=interview.id,
        slot_id=slot.id,
        status="confirmed",
    )
    db.add(booking)
    slot.is_selected = True
    interview.status = "booked"
    db.commit()
    db.refresh(booking)

    background_tasks.add_task(_do_confirm_booking, interview.id, slot.id, booking.id)
    return booking


@router.get("/confirm/{token}", response_model=BookingDetailOut)
def get_booking_by_confirm_token(token: str, db: Session = Depends(get_db)):
    booking = db.query(Booking).options(
        joinedload(Booking.interview_request).joinedload(InterviewRequest.candidate),
        joinedload(Booking.slot),
    ).filter(Booking.confirm_token == token).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return _enrich_booking(booking)


@router.get("/{booking_id}", response_model=BookingDetailOut)
def get_booking(booking_id: str, db: Session = Depends(get_db), _=Depends(require_staff)):
    booking = db.query(Booking).options(
        joinedload(Booking.interview_request).joinedload(InterviewRequest.candidate),
        joinedload(Booking.slot),
    ).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return _enrich_booking(booking)


def _enrich_booking(booking: Booking) -> BookingDetailOut:
    detail = BookingDetailOut.model_validate(booking)
    if booking.slot:
        detail.slot_start = booking.slot.start_time
        detail.slot_end = booking.slot.end_time
    if booking.interview_request:
        ir = booking.interview_request
        detail.job_title = ir.job_title
        detail.round_type = ir.round_type
        if ir.candidate:
            detail.candidate_name = ir.candidate.name
            detail.candidate_email = ir.candidate.email
    return detail


@router.post("/{booking_id}/cancel")
def cancel_booking(booking_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db), _=Depends(require_staff)):
    booking = db.query(Booking).options(
        joinedload(Booking.interview_request).joinedload(InterviewRequest.candidate),
        joinedload(Booking.slot),
    ).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status == "cancelled":
        raise HTTPException(status_code=400, detail="Booking is already cancelled")

    ir = booking.interview_request
    booking.status = "cancelled"
    ir.status = "cancelled"
    db.commit()

    panelists = db.query(Panelist).filter(Panelist.id.in_(ir.required_panelist_ids)).all()

    if booking.google_event_id:
        creator = next((p for p in panelists if p.google_access_token), None)
        if creator:
            background_tasks.add_task(
                delete_calendar_event,
                creator.google_access_token,
                creator.google_refresh_token,
                creator.token_expiry,
                booking.google_event_id,
            )

    background_tasks.add_task(
        _send_cancellations,
        booking_id=booking_id,
        candidate_email=ir.candidate.email,
        candidate_name=ir.candidate.name,
        panelist_ids=ir.required_panelist_ids,
        recruiter_email=ir.recruiter_email,
        job_title=ir.job_title,
        round_type=ir.round_type,
    )
    return {"message": "Booking cancelled"}


def _send_cancellations(booking_id, candidate_email, candidate_name, panelist_ids, recruiter_email, job_title, round_type):
    from app.core.database import SessionLocal
    with SessionLocal() as session:
        send_cancellation(session, candidate_email, candidate_name, "candidate", job_title, round_type, booking_id=booking_id)
        panelists = session.query(Panelist).filter(Panelist.id.in_(panelist_ids)).all()
        for p in panelists:
            send_cancellation(session, p.email, p.name, "panelist", job_title, round_type, booking_id=booking_id)
        send_cancellation(session, recruiter_email, "Recruiter", "recruiter", job_title, round_type, booking_id=booking_id)


@router.post("/{booking_id}/reschedule")
def reschedule_booking(booking_id: str, db: Session = Depends(get_db), _=Depends(require_staff)):
    booking = db.query(Booking).options(
        joinedload(Booking.interview_request),
    ).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.status = "rescheduled"
    booking.interview_request.status = "rescheduling"
    db.commit()
    return {"message": "Rescheduling triggered.", "interview_id": booking.interview_request_id}
