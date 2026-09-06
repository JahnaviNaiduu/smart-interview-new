"""Deterministic, explainable interviewer matching (no LLM/ML).

Ranks panelists for a candidate by:
  1. eligibility (active, interview-type compatible),
  2. skill overlap with the candidate (normalized),
  3. availability within the requested window (availability overrides skill).
"""
import re
from typing import Optional
from sqlalchemy.orm import Session
from app.models.panelist import Panelist

# Canonical aliases so "React", "ReactJS", "React.js" match as one skill.
_SKILL_ALIASES = {
    "reactjs": "react",
    "react.js": "react",
    "js": "javascript",
    "node": "nodejs",
    "node.js": "nodejs",
    "postgres": "postgresql",
    "postgre": "postgresql",
    "ml": "machine learning",
    "py": "python",
    "golang": "go",
    "k8s": "kubernetes",
    "fast api": "fastapi",
}


def normalize_skill(skill: str) -> str:
    """Lowercase, strip punctuation/extra spaces, and apply alias mapping."""
    if not skill:
        return ""
    s = skill.strip().lower()
    s = re.sub(r"[._/]", " ", s)          # react.js -> react js
    s = re.sub(r"\s+", " ", s).strip()
    s = _SKILL_ALIASES.get(s, s)
    s = _SKILL_ALIASES.get(s.replace(" ", ""), s)  # catch "react js" collapses
    return s


def normalize_skills(skills) -> set:
    return {normalize_skill(s) for s in (skills or []) if s and s.strip()}


# Round types where skill overlap is the dominant selection factor.
SKILL_DRIVEN_ROUNDS = {"technical"}


def score_panelist(candidate_skills, panelist_skills) -> tuple:
    """Return (score in [0,1], matched_skills list). Score = matched / total candidate skills."""
    cand = normalize_skills(candidate_skills)
    pan = normalize_skills(panelist_skills)
    if not cand:
        # No candidate skills to match on → neutral score, no false ranking.
        return 0.0, []
    matched_norm = cand & pan
    # Report matched skills using the candidate's original casing where possible.
    matched_display = sorted(
        {s for s in (candidate_skills or []) if normalize_skill(s) in matched_norm}
    )
    return round(len(matched_norm) / len(cand), 3), matched_display


def _has_availability(db: Session, panelist_id, window_start, window_end,
                      duration_minutes, buffer_minutes, preferred_timezone) -> bool:
    # Imported lazily to avoid a circular import at module load.
    from app.services.scheduling_service import find_available_slots
    slots = find_available_slots(
        db=db,
        panelist_ids=[panelist_id],
        window_start=window_start,
        window_end=window_end,
        duration_minutes=duration_minutes,
        buffer_minutes=buffer_minutes,
        preferred_timezone=preferred_timezone,
    )
    return len(slots) > 0


def recommend_panelists(
    db: Session,
    candidate_skills,
    round_type: str,
    window_start,
    window_end,
    duration_minutes: int = 60,
    buffer_minutes: int = 15,
    preferred_timezone: str = "UTC",
    limit: int = 10,
    check_availability: bool = True,
) -> list[dict]:
    """Rank eligible, available panelists by candidate-skill match. Availability
    overrides skill: an unavailable panelist ranks below every available one."""
    panelists = db.query(Panelist).filter(Panelist.is_active == True).all()  # noqa: E712
    results = []
    for p in panelists:
        score, matched = score_panelist(candidate_skills, p.skills)
        available = True
        if check_availability:
            available = _has_availability(
                db, p.id, window_start, window_end,
                duration_minutes, buffer_minutes, preferred_timezone,
            )
        total = len(normalize_skills(candidate_skills))
        if total and round_type in SKILL_DRIVEN_ROUNDS:
            reason = (f"Matches {len(matched)} of {total} candidate skills"
                      f"{'' if available else ' (currently unavailable)'} for the {round_type} interview.")
        else:
            reason = (f"Eligible for the {round_type} interview"
                      + (f"; matches {len(matched)} of {total} candidate skills" if total else "")
                      + ("" if available else "; currently unavailable") + ".")
        results.append({
            "panelist_id": p.id,
            "panelist_name": p.name,
            "role": p.role,
            "match_score": score,
            "matched_skills": matched,
            "available": available,
            "reason": reason,
        })

    # Available first, then higher skill score, then name for deterministic ties.
    results.sort(key=lambda r: (0 if r["available"] else 1, -r["match_score"], r["panelist_name"]))
    return results[:limit]
