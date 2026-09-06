"""Problem 3 — candidate rejects all slots and requests a reschedule."""
from tests.conftest import valid_interview_payload
from app.core.database import SessionLocal
from app.models.notification_log import NotificationLog
from app.models.booking import Booking


def _create(client, headers, panelist_id, **overrides):
    res = client.post("/api/v1/interviews", json=valid_interview_payload(panelist_id, **overrides), headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


def test_candidate_can_request_reschedule_with_reason(client, recruiter_headers, panelist_id):
    iv = _create(client, recruiter_headers, panelist_id,
                 candidate={"name": "Resched One", "email": "resched1@x.com", "timezone": "UTC", "skills": ["Python"]})
    res = client.post("/api/v1/availability/candidate/reschedule",
                      json={"token": iv["candidate_link_token"], "reason": "Traveling that week"})
    assert res.status_code == 200
    assert res.json()["status"] == "rescheduling"

    got = client.get(f"/api/v1/interviews/{iv['id']}", headers=recruiter_headers).json()
    assert got["status"] == "rescheduling"
    assert got["reschedule_reason"] == "Traveling that week"
    # No slot got confirmed as a side effect.
    with SessionLocal() as db:
        assert db.query(Booking).filter(
            Booking.interview_request_id == iv["id"], Booking.status == "confirmed"
        ).count() == 0


def test_candidate_cannot_reschedule_another_interview(client):
    res = client.post("/api/v1/availability/candidate/reschedule",
                      json={"token": "00000000-0000-0000-0000-000000000000", "reason": "x"})
    assert res.status_code == 404


def test_reschedule_notifies_recruiter(client, recruiter_headers, panelist_id):
    iv = _create(client, recruiter_headers, panelist_id,
                 candidate={"name": "Resched Two", "email": "resched2@x.com", "timezone": "UTC"})
    client.post("/api/v1/availability/candidate/reschedule",
                json={"token": iv["candidate_link_token"], "reason": "conflict"})
    with SessionLocal() as db:
        notes = db.query(NotificationLog).filter(
            NotificationLog.notification_type == "reschedule_request",
            NotificationLog.recipient_type == "recruiter",
        ).count()
    assert notes >= 1


def test_recruiter_can_propose_new_slots_preserving_skills_and_type(client, recruiter_headers, panelist_id):
    iv = _create(client, recruiter_headers, panelist_id,
                 candidate={"name": "Resched Three", "email": "resched3@x.com", "timezone": "UTC",
                            "skills": ["Python", "FastAPI"]})
    old_token = iv["candidate_link_token"]
    client.post("/api/v1/availability/candidate/reschedule",
                json={"token": old_token, "reason": "none work"})

    res = client.post(f"/api/v1/interviews/{iv['id']}/propose-slots", json={}, headers=recruiter_headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] in ("slots_found", "pending")
    assert body["candidate_link_token"] != old_token         # fresh link issued
    assert body["round_type"] == "technical"                 # interview type preserved
    assert "Python" in (body["candidate"]["skills"] or [])   # candidate skills preserved
    assert body["reschedule_reason"] is None                 # reason cleared on re-propose
