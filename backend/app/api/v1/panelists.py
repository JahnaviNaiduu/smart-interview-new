from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import require_staff, require_admin
from app.models.panelist import Panelist
from app.schemas.panelist import PanelistCreate, PanelistUpdate, PanelistOut
from app.services.calendar_service import get_oauth_url, exchange_code_for_tokens
from app.services.matching_service import recommend_panelists
from app.core.config import settings

router = APIRouter(prefix="/panelists", tags=["panelists"])


class RecommendRequest(BaseModel):
    candidate_skills: List[str] = []
    round_type: str
    window_start: datetime
    window_end: datetime
    duration_minutes: int = 60
    buffer_minutes: int = 15
    preferred_timezone: str = "UTC"


@router.get("", response_model=List[PanelistOut])
def list_panelists(active_only: bool = Query(True), db: Session = Depends(get_db), _=Depends(require_staff)):
    query = db.query(Panelist)
    if active_only:
        query = query.filter(Panelist.is_active == True)
    panelists = query.order_by(Panelist.name).all()
    return [PanelistOut.from_orm_with_calendar(p) for p in panelists]


@router.post("", response_model=PanelistOut, status_code=201)
def create_panelist(payload: PanelistCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    existing = db.query(Panelist).filter(Panelist.email == payload.email).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            existing.name = payload.name
            existing.role = payload.role
            existing.skills = payload.skills
            db.commit()
            db.refresh(existing)
            return PanelistOut.from_orm_with_calendar(existing)
        raise HTTPException(status_code=409, detail="A panelist with this email already exists")
    panelist = Panelist(**payload.model_dump())
    db.add(panelist)
    db.commit()
    db.refresh(panelist)
    return PanelistOut.from_orm_with_calendar(panelist)


@router.post("/recommend")
def recommend(payload: RecommendRequest, db: Session = Depends(get_db), _=Depends(require_staff)):
    """Rank eligible, available panelists by candidate-skill match for this round.
    Deterministic and explainable; availability overrides skill ranking."""
    if payload.window_end <= payload.window_start:
        raise HTTPException(status_code=422, detail="window_end must be after window_start")
    return recommend_panelists(
        db=db,
        candidate_skills=payload.candidate_skills,
        round_type=payload.round_type,
        window_start=payload.window_start,
        window_end=payload.window_end,
        duration_minutes=payload.duration_minutes,
        buffer_minutes=payload.buffer_minutes,
        preferred_timezone=payload.preferred_timezone,
    )


# IMPORTANT: /calendar-callback must be declared BEFORE /{panelist_id}
# so FastAPI doesn't treat "calendar-callback" as a panelist_id value
@router.get("/calendar-callback")
def calendar_oauth_callback(code: str, state: str, db: Session = Depends(get_db)):
    panelist = db.query(Panelist).filter(Panelist.id == state).first()
    if not panelist:
        raise HTTPException(status_code=404, detail="Panelist not found")
    try:
        tokens = exchange_code_for_tokens(code, state)
        panelist.google_access_token = tokens["access_token"]
        panelist.google_refresh_token = tokens["refresh_token"]
        panelist.token_expiry = tokens["token_expiry"]
        panelist.google_calendar_id = panelist.email
        db.commit()
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/panelists?connected=true", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/panelists?error=calendar_failed", status_code=302)


@router.get("/{panelist_id}", response_model=PanelistOut)
def get_panelist(panelist_id: str, db: Session = Depends(get_db), _=Depends(require_staff)):
    panelist = db.query(Panelist).filter(Panelist.id == panelist_id).first()
    if not panelist:
        raise HTTPException(status_code=404, detail="Panelist not found")
    return PanelistOut.from_orm_with_calendar(panelist)


@router.patch("/{panelist_id}", response_model=PanelistOut)
def update_panelist(panelist_id: str, payload: PanelistUpdate, db: Session = Depends(get_db), _=Depends(require_admin)):
    panelist = db.query(Panelist).filter(Panelist.id == panelist_id).first()
    if not panelist:
        raise HTTPException(status_code=404, detail="Panelist not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(panelist, field, value)
    db.commit()
    db.refresh(panelist)
    return PanelistOut.from_orm_with_calendar(panelist)


@router.delete("/{panelist_id}", status_code=204)
def deactivate_panelist(panelist_id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    panelist = db.query(Panelist).filter(Panelist.id == panelist_id).first()
    if not panelist:
        raise HTTPException(status_code=404, detail="Panelist not found")
    panelist.is_active = False
    db.commit()


@router.get("/{panelist_id}/calendar-auth-url")
def get_calendar_auth_url(panelist_id: str, db: Session = Depends(get_db), _=Depends(require_admin)):
    panelist = db.query(Panelist).filter(Panelist.id == panelist_id).first()
    if not panelist:
        raise HTTPException(status_code=404, detail="Panelist not found")
    url = get_oauth_url(state=panelist_id)
    return {"auth_url": url, "panelist_id": panelist_id}
