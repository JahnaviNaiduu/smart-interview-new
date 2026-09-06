"""Request Interview creation tests (validation + auth + field derivation)."""
from tests.conftest import valid_interview_payload


def test_create_interview_requires_auth(client, panelist_id):
    res = client.post("/api/v1/interviews", json=valid_interview_payload(panelist_id))
    assert res.status_code == 401


def test_create_interview_success(client, recruiter_headers, panelist_id):
    res = client.post("/api/v1/interviews", json=valid_interview_payload(panelist_id), headers=recruiter_headers)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["job_title"] == "Senior Engineer"
    # recruiter_email is derived from the authenticated user, not the request body.
    assert body["recruiter_email"] == "recruiter@demo.com"
    # preferred_timezone defaults to the candidate timezone when omitted.
    assert body["preferred_timezone"] == "Asia/Kolkata"


def test_recruiter_email_cannot_be_spoofed_via_body(client, recruiter_headers, panelist_id):
    payload = valid_interview_payload(panelist_id, recruiter_email="ceo@evil.com")
    res = client.post("/api/v1/interviews", json=payload, headers=recruiter_headers)
    assert res.status_code == 201
    # The spoofed value is ignored; identity comes from the token.
    assert res.json()["recruiter_email"] == "recruiter@demo.com"


def test_create_interview_missing_required_fields(client, recruiter_headers):
    res = client.post("/api/v1/interviews", json={"round_type": "technical"}, headers=recruiter_headers)
    assert res.status_code == 422


def test_create_interview_invalid_duration(client, recruiter_headers, panelist_id):
    res = client.post(
        "/api/v1/interviews",
        json=valid_interview_payload(panelist_id, duration_minutes=17),
        headers=recruiter_headers,
    )
    assert res.status_code == 422


def test_create_interview_invalid_window(client, recruiter_headers, panelist_id):
    res = client.post(
        "/api/v1/interviews",
        json=valid_interview_payload(
            panelist_id,
            window_start="2099-01-09T18:00:00+00:00",
            window_end="2099-01-05T09:00:00+00:00",
        ),
        headers=recruiter_headers,
    )
    assert res.status_code == 422


def test_create_interview_requires_panelist(client, recruiter_headers, panelist_id):
    res = client.post(
        "/api/v1/interviews",
        json=valid_interview_payload(panelist_id, required_panelist_ids=[]),
        headers=recruiter_headers,
    )
    assert res.status_code == 422


def test_create_interview_invalid_round_type(client, recruiter_headers, panelist_id):
    res = client.post(
        "/api/v1/interviews",
        json=valid_interview_payload(panelist_id, round_type="lunch"),
        headers=recruiter_headers,
    )
    assert res.status_code == 422
