"""Test configuration: sets a throwaway SQLite DB and fake external keys BEFORE
importing the app, then boots it via TestClient so the lifespan seeds demo users."""
import os
import pathlib

# Must be set before `app.core.config` is imported.
_TEST_DB = pathlib.Path(__file__).parent / "test_sis.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TEST_DB}")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-secret")
os.environ.setdefault("GROQ_API_KEY", "test-groq")
os.environ.setdefault("RESEND_API_KEY", "test-resend")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-tests")
os.environ.setdefault("SEED_ADMIN_EMAIL", "admin@demo.com")
os.environ.setdefault("SEED_ADMIN_PASSWORD", "admin123")
os.environ.setdefault("SEED_RECRUITER_EMAIL", "recruiter@demo.com")
os.environ.setdefault("SEED_RECRUITER_PASSWORD", "recruiter123")

# Start each test session from a clean database.
if _TEST_DB.exists():
    _TEST_DB.unlink()

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:  # context manager runs lifespan → create_all + seed
        yield c
    if _TEST_DB.exists():
        _TEST_DB.unlink()


def _login(client, email, password):
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture(scope="session")
def admin_headers(client):
    return _login(client, "admin@demo.com", "admin123")


@pytest.fixture(scope="session")
def recruiter_headers(client):
    return _login(client, "recruiter@demo.com", "recruiter123")


@pytest.fixture(scope="session")
def panelist_id(client, admin_headers):
    res = client.post(
        "/api/v1/panelists",
        json={"name": "Panel One", "email": "panel1@demo.com", "role": "Engineer", "skills": ["Java"]},
        headers=admin_headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def valid_interview_payload(panelist_id, **overrides):
    payload = {
        "job_title": "Senior Engineer",
        "round_type": "technical",
        "candidate": {"name": "Jane Candidate", "email": "jane@example.com", "timezone": "Asia/Kolkata"},
        "required_panelist_ids": [panelist_id],
        "duration_minutes": 60,
        "buffer_minutes": 15,
        "window_start": "2099-01-05T09:00:00+00:00",
        "window_end": "2099-01-09T18:00:00+00:00",
        "notes": "n/a",
    }
    payload.update(overrides)
    return payload
