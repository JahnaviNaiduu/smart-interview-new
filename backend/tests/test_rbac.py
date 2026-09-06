"""RBAC / authorization tests. The backend is the final authority."""


# --- Authentication ---------------------------------------------------------
def test_unauthenticated_protected_endpoint_returns_401(client):
    assert client.get("/api/v1/interviews").status_code == 401


def test_login_wrong_password_returns_401(client):
    res = client.post("/api/v1/auth/login", json={"email": "admin@demo.com", "password": "wrong"})
    assert res.status_code == 401


def test_login_success_returns_token_and_trusted_role(client):
    res = client.post("/api/v1/auth/login", json={"email": "recruiter@demo.com", "password": "recruiter123"})
    assert res.status_code == 200
    body = res.json()
    assert body["access_token"]
    assert body["user"]["role"] == "recruiter"


def test_tampered_token_returns_401(client):
    res = client.get("/api/v1/interviews", headers={"Authorization": "Bearer not.a.real.jwt"})
    assert res.status_code == 401


# --- Role-based authorization ----------------------------------------------
def test_authorized_recruiter_can_list_interviews(client, recruiter_headers):
    assert client.get("/api/v1/interviews", headers=recruiter_headers).status_code == 200


def test_recruiter_cannot_create_panelist_403(client, recruiter_headers):
    res = client.post(
        "/api/v1/panelists",
        json={"name": "X", "email": "x@demo.com", "skills": []},
        headers=recruiter_headers,
    )
    assert res.status_code == 403


def test_admin_can_create_panelist_201(client, admin_headers):
    res = client.post(
        "/api/v1/panelists",
        json={"name": "Admin Made", "email": "adminmade@demo.com", "skills": []},
        headers=admin_headers,
    )
    assert res.status_code == 201


def test_role_in_request_body_does_not_escalate(client, recruiter_headers):
    # A recruiter injecting {"role": "admin"} into the body must NOT gain admin access.
    res = client.post(
        "/api/v1/panelists",
        json={"name": "Sneaky", "email": "sneaky@demo.com", "skills": [], "role": "admin"},
        headers=recruiter_headers,
    )
    assert res.status_code == 403


def test_analytics_requires_staff(client, recruiter_headers):
    assert client.get("/api/v1/analytics").status_code == 401
    assert client.get("/api/v1/analytics", headers=recruiter_headers).status_code == 200


# --- Public candidate plane (token-based, no staff login) -------------------
def test_candidate_link_public_but_scoped(client, recruiter_headers, panelist_id):
    from tests.conftest import valid_interview_payload
    created = client.post(
        "/api/v1/interviews", json=valid_interview_payload(panelist_id), headers=recruiter_headers
    ).json()
    token = created["candidate_link_token"]

    # Reachable WITHOUT a staff token (candidate flow)...
    ok = client.get(f"/api/v1/availability/candidate/{token}")
    assert ok.status_code == 200

    # ...but another (guessed) token cannot reach this candidate's data.
    other = client.get("/api/v1/availability/candidate/00000000-0000-0000-0000-000000000000")
    assert other.status_code == 404
