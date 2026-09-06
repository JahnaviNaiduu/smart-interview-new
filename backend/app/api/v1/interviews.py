from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, model_validator
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.config import settings
from app.core.auth import require_staff, get_current_user
from app.models.user import User
from app.models.interview import InterviewRequest
from app.models.candidate import Candidate
from app.models.panelist import Panelist
from app.models.availability_slot import AvailabilitySlot
from app.schemas.interview import InterviewRequestCreate, InterviewRequestUpdate, InterviewRequestOut
from app.services.token_service import generate_candidate_token
from app.services.scheduling_service import find_available_slots
from app.services.ai_service import rank_slots, generate_invite_email
from app.services.notification_service import send_candidate_invite

# Every interview endpoint requires an authenticated staff user (recruiter/admin).
router = APIRouter(prefix="/interviews", tags=["interviews"], dependencies=[Depends(require_staff)])


def _upsert_candidate(db: Session, candidate_data) -> Candidate:
    existing = db.query(Candidate).filter(Candidate.email == candidate_data.email).first()
    if existing:
        existing.name = candidate_data.name
        existing.timezone = candidate_data.timezone
        if candidate_data.phone:
            existing.phone = candidate_data.phone
        # Preserve/refresh candidate skills (source of truth for matching).
        if candidate_data.skills:
            existing.skills = candidate_data.skills
        return existing
    candidate = Candidate(**candidate_data.model_dump())
    db.add(candidate)
    db.flush()
    return candidate


def _validate_panelists(db: Session, panelist_ids: list) -> list:
    """Backend-authoritative check: every requested panelist must exist and be active.
    Never trust arbitrary panelist IDs from the frontend."""
    panelists = db.query(Panelist).filter(
        Panelist.id.in_(panelist_ids), Panelist.is_active == True  # noqa: E712
    ).all()
    found = {p.id for p in panelists}
    missing = [pid for pid in panelist_ids if pid not in found]
    if missing:
        raise HTTPException(status_code=400, detail="One or more selected panelists are invalid or inactive")
    return panelists


@router.get("", response_model=List[InterviewRequestOut])
def list_interviews(status: Optional[str] = Query(None), limit: int = Query(50, le=100), db: Session = Depends(get_db)):
    query = db.query(InterviewRequest).options(
        joinedload(InterviewRequest.candidate),
        joinedload(InterviewRequest.slots),
    )
    if status:
        query = query.filter(InterviewRequest.status == status)
    return query.order_by(InterviewRequest.created_at.desc()).limit(limit).all()


@router.post("", response_model=InterviewRequestOut, status_code=201)
def create_interview(
    payload: InterviewRequestCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = _upsert_candidate(db, payload.candidate)
    token, expires_at = generate_candidate_token()

    # Backend-authoritative: reject invalid/inactive panelist IDs from the client.
    _validate_panelists(db, payload.required_panelist_ids)

    # The requesting recruiter is the authenticated user, not a client-supplied field.
    recruiter_email = current_user.email
    # The scheduling/working-hours timezone defaults to the candidate's timezone
    # unless explicitly provided.
    preferred_timezone = payload.preferred_timezone or payload.candidate.timezone

    interview = InterviewRequest(
        job_title=payload.job_title,
        round_type=payload.round_type,
        candidate_id=candidate.id,
        required_panelist_ids=payload.required_panelist_ids,
        duration_minutes=payload.duration_minutes,
        buffer_minutes=payload.buffer_minutes,
        window_start=payload.window_start,
        window_end=payload.window_end,
        preferred_timezone=preferred_timezone,
        recruiter_email=recruiter_email,
        candidate_link_token=token,
        token_expires_at=expires_at,
        notes=payload.notes,
        status="pending",
    )
    db.add(interview)
    db.flush()

    raw_slots = find_available_slots(
        db=db,
        panelist_ids=payload.required_panelist_ids,
        window_start=payload.window_start,
        window_end=payload.window_end,
        duration_minutes=payload.duration_minutes,
        buffer_minutes=payload.buffer_minutes,
        preferred_timezone=preferred_timezone,
    )

    ranked_slots = rank_slots(raw_slots, candidate.timezone, {})

    for slot_data in ranked_slots[:10]:
        slot = AvailabilitySlot(
            interview_request_id=interview.id,
            start_time=slot_data["start"],
            end_time=slot_data["end"],
            ai_rank=slot_data.get("ai_rank"),
            ai_score=slot_data.get("ai_score"),
            ai_reasoning=slot_data.get("ai_reasoning"),
        )
        db.add(slot)

    interview.status = "slots_found" if ranked_slots else "pending"
    db.commit()
    db.refresh(interview)

    if ranked_slots:
        background_tasks.add_task(
            _send_invite_email,
            interview_id=interview.id,
            candidate_email=candidate.email,
            candidate_name=candidate.name,
            job_title=payload.job_title,
            round_type=payload.round_type,
            token=token,
            expires_at=expires_at,
            recruiter_email=recruiter_email,
        )

    return db.query(InterviewRequest).options(
        joinedload(InterviewRequest.candidate),
        joinedload(InterviewRequest.slots),
    ).filter(InterviewRequest.id == interview.id).first()


def _send_invite_email(interview_id, candidate_email, candidate_name, job_title, round_type, token, expires_at, recruiter_email):
    from app.core.database import SessionLocal
    with SessionLocal() as session:
        link = f"{settings.FRONTEND_URL}/availability/{token}"
        email_body = generate_invite_email(candidate_name, round_type, job_title, recruiter_email)
        send_candidate_invite(
            db=session,
            to_email=candidate_email,
            candidate_name=candidate_name,
            job_title=job_title,
            round_type=round_type,
            availability_link=link,
            email_body=email_body,
            expires_at=expires_at,
        )
        interview = session.query(InterviewRequest).filter(InterviewRequest.id == interview_id).first()
        if interview:
            interview.status = "candidate_notified"
            session.commit()


@router.get("/{interview_id}", response_model=InterviewRequestOut)
def get_interview(interview_id: str, db: Session = Depends(get_db)):
    interview = db.query(InterviewRequest).options(
        joinedload(InterviewRequest.candidate),
        joinedload(InterviewRequest.slots),
    ).filter(InterviewRequest.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview request not found")
    return interview


@router.patch("/{interview_id}", response_model=InterviewRequestOut)
def update_interview(interview_id: str, payload: InterviewRequestUpdate, db: Session = Depends(get_db)):
    interview = db.query(InterviewRequest).filter(InterviewRequest.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview request not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(interview, field, value)
    db.commit()
    db.refresh(interview)
    return interview


@router.delete("/{interview_id}", status_code=204)
def cancel_interview(interview_id: str, db: Session = Depends(get_db)):
    interview = db.query(InterviewRequest).filter(InterviewRequest.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview request not found")
    interview.status = "cancelled"
    db.commit()


@router.post("/{interview_id}/resend-invite")
def resend_invite(interview_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    interview = db.query(InterviewRequest).options(
        joinedload(InterviewRequest.candidate),
    ).filter(InterviewRequest.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview request not found")
    if not interview.candidate_link_token:
        raise HTTPException(status_code=400, detail="No candidate link exists for this request")
    background_tasks.add_task(
        _send_invite_email,
        interview_id=interview.id,
        candidate_email=interview.candidate.email,
        candidate_name=interview.candidate.name,
        job_title=interview.job_title,
        round_type=interview.round_type,
        token=interview.candidate_link_token,
        expires_at=interview.token_expires_at,
        recruiter_email=interview.recruiter_email,
    )
    return {"message": "Invite resent"}


class ProposeSlotsRequest(BaseModel):
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    required_panelist_ids: Optional[List[str]] = None

    @model_validator(mode="after")
    def validate_window(self):
        if self.window_start and self.window_end and self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        return self


@router.post("/{interview_id}/propose-slots", response_model=InterviewRequestOut)
def propose_new_slots(
    interview_id: str,
    payload: ProposeSlotsRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Recruiter proposes a fresh set of slots (e.g. after a candidate reschedule
    request). Candidate skills, round type and interview identity are preserved."""
    interview = db.query(InterviewRequest).options(
        joinedload(InterviewRequest.candidate),
        joinedload(InterviewRequest.slots),
    ).filter(InterviewRequest.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview request not found")

    if payload.required_panelist_ids:
        _validate_panelists(db, payload.required_panelist_ids)
        interview.required_panelist_ids = payload.required_panelist_ids
    if payload.window_start:
        interview.window_start = payload.window_start
    if payload.window_end:
        interview.window_end = payload.window_end

    # Recompute slots against current calendars; replace the old proposal.
    raw_slots = find_available_slots(
        db=db,
        panelist_ids=interview.required_panelist_ids,
        window_start=interview.window_start,
        window_end=interview.window_end,
        duration_minutes=interview.duration_minutes,
        buffer_minutes=interview.buffer_minutes,
        preferred_timezone=interview.preferred_timezone,
    )
    ranked_slots = rank_slots(raw_slots, interview.candidate.timezone, {})

    for old in list(interview.slots):
        db.delete(old)
    db.flush()

    for slot_data in ranked_slots[:10]:
        db.add(AvailabilitySlot(
            interview_request_id=interview.id,
            start_time=slot_data["start"],
            end_time=slot_data["end"],
            ai_rank=slot_data.get("ai_rank"),
            ai_score=slot_data.get("ai_score"),
            ai_reasoning=slot_data.get("ai_reasoning"),
        ))

    # Refresh the candidate link expiry and re-notify.
    token, expires_at = generate_candidate_token()
    interview.candidate_link_token = token
    interview.token_expires_at = expires_at
    interview.reschedule_reason = None
    interview.status = "slots_found" if ranked_slots else "pending"
    db.commit()
    db.refresh(interview)

    if ranked_slots:
        background_tasks.add_task(
            _send_invite_email,
            interview_id=interview.id,
            candidate_email=interview.candidate.email,
            candidate_name=interview.candidate.name,
            job_title=interview.job_title,
            round_type=interview.round_type,
            token=token,
            expires_at=expires_at,
            recruiter_email=interview.recruiter_email,
        )

    return db.query(InterviewRequest).options(
        joinedload(InterviewRequest.candidate),
        joinedload(InterviewRequest.slots),
    ).filter(InterviewRequest.id == interview.id).first()
