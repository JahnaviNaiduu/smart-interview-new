"""Problem 4 — intelligent, deterministic interviewer selection."""
import uuid
from datetime import datetime
import app.services.matching_service as ms
from app.services.matching_service import normalize_skill, score_panelist, recommend_panelists
from app.core.database import SessionLocal
from app.models.panelist import Panelist
from tests.conftest import valid_interview_payload

WIN_START = datetime(2099, 6, 1, 9, 0)
WIN_END = datetime(2099, 6, 5, 18, 0)


def test_skill_normalization_treats_aliases_as_same():
    assert normalize_skill("ReactJS") == normalize_skill("React.js") == normalize_skill("react")
    assert normalize_skill("ML") == normalize_skill("machine learning")


def test_score_full_and_zero_overlap():
    full, matched = score_panelist(["Python", "FastAPI", "Machine Learning"],
                                   ["Python", "FastAPI", "Machine Learning"])
    assert full == 1.0 and len(matched) == 3
    none, _ = score_panelist(["Python", "FastAPI", "Machine Learning"], ["Java", "Spring Boot"])
    assert none == 0.0


def _mk_panelists(db):
    a = Panelist(name="AAA", email=f"a-{uuid.uuid4()}@x.com", skills=["Python", "FastAPI", "Machine Learning"])
    b = Panelist(name="BBB", email=f"b-{uuid.uuid4()}@x.com", skills=["Java", "Spring Boot"])
    c = Panelist(name="CCC", email=f"c-{uuid.uuid4()}@x.com", skills=["Python", "SQL"])
    db.add_all([a, b, c])
    db.flush()
    return a.id, b.id, c.id


def test_ranking_A_over_C_over_B(client):
    with SessionLocal() as db:
        a_id, b_id, c_id = _mk_panelists(db)
        recs = recommend_panelists(
            db, candidate_skills=["Python", "FastAPI", "Machine Learning"],
            round_type="technical", window_start=WIN_START, window_end=WIN_END,
            check_availability=False, limit=1000,
        )
    order = {r["panelist_id"]: i for i, r in enumerate(recs)}
    assert order[a_id] < order[c_id] < order[b_id]
    by_id = {r["panelist_id"]: r for r in recs}
    assert by_id[a_id]["match_score"] == 1.0
    assert by_id[b_id]["match_score"] == 0.0
    assert "Python" in by_id[a_id]["matched_skills"]


def test_availability_overrides_skill(client, monkeypatch):
    with SessionLocal() as db:
        a_id, b_id, c_id = _mk_panelists(db)
        # Best skill match (A) is unavailable; others available.
        monkeypatch.setattr(ms, "_has_availability", lambda db, pid, *a, **k: pid != a_id)
        recs = recommend_panelists(
            db, candidate_skills=["Python", "FastAPI", "Machine Learning"],
            round_type="technical", window_start=WIN_START, window_end=WIN_END,
            check_availability=True, limit=1000,
        )
    by_id = {r["panelist_id"]: r for r in recs}
    assert by_id[a_id]["available"] is False
    # An available (lower-scoring) panelist outranks the unavailable top scorer.
    assert recs[0]["available"] is True
    assert recs[0]["panelist_id"] != a_id
    assert order_index(recs, c_id) < order_index(recs, a_id)


def order_index(recs, pid):
    return next(i for i, r in enumerate(recs) if r["panelist_id"] == pid)


def test_recommend_api_returns_scores_and_reason(client, recruiter_headers):
    res = client.post("/api/v1/panelists/recommend", json={
        "candidate_skills": ["Python", "FastAPI"],
        "round_type": "technical",
        "window_start": "2099-06-01T09:00:00+00:00",
        "window_end": "2099-06-05T18:00:00+00:00",
    }, headers=recruiter_headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert isinstance(data, list) and len(data) >= 1
    top = data[0]
    assert {"panelist_id", "panelist_name", "match_score", "matched_skills", "reason", "available"} <= set(top)
    # All returned panelists are distinct (no duplicate selection).
    ids = [r["panelist_id"] for r in data]
    assert len(ids) == len(set(ids))


def test_recommend_api_requires_auth(client):
    res = client.post("/api/v1/panelists/recommend", json={
        "candidate_skills": ["Python"], "round_type": "technical",
        "window_start": "2099-06-01T09:00:00+00:00", "window_end": "2099-06-05T18:00:00+00:00",
    })
    assert res.status_code == 401


def test_backend_rejects_invalid_panelist_on_create(client, recruiter_headers):
    res = client.post("/api/v1/interviews",
                      json=valid_interview_payload("nonexistent-panelist-id"),
                      headers=recruiter_headers)
    assert res.status_code == 400
