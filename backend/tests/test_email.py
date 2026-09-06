"""Problem 1 — dynamic email recipient resolution + safe failure handling."""
import app.services.notification_service as notif


def test_recipient_is_dynamic_not_from_env(client, monkeypatch):
    """The 'to' address must be the resolved recipient, never an env override."""
    captured = {}

    def fake_send(params):
        captured.update(params)
        return {"id": "msg_123"}

    monkeypatch.setattr(notif.resend.Emails, "send", staticmethod(fake_send))

    from app.core.database import SessionLocal
    with SessionLocal() as db:
        ok = notif.send_email(db, "candidate@real.com", "Subj", "<p>hi</p>", "candidate", "invite")
    assert ok is True
    assert captured["to"] == ["candidate@real.com"]      # dynamic recipient
    assert "yourdomain.com" not in captured["to"][0]      # not the sender/from


def test_no_recipient_email_config_exists():
    """Env/config must not carry any candidate recipient override."""
    from app.core.config import settings
    assert not hasattr(settings, "RESEND_TEST_TO_EMAIL")


def test_provider_failure_is_reported_not_swallowed(client, monkeypatch):
    def boom(params):
        raise RuntimeError("provider down")

    monkeypatch.setattr(notif.resend.Emails, "send", staticmethod(boom))
    from app.core.database import SessionLocal
    with SessionLocal() as db:
        ok = notif.send_email(db, "candidate@real.com", "Subj", "<p>hi</p>", "candidate", "invite")
    assert ok is False  # failure surfaced to the caller, not reported as success


def test_credentials_never_logged(client, monkeypatch, caplog):
    monkeypatch.setattr(notif.resend, "api_key", "re_supersecret_key")

    def boom(params):
        raise RuntimeError("boom")

    monkeypatch.setattr(notif.resend.Emails, "send", staticmethod(boom))
    from app.core.database import SessionLocal
    with caplog.at_level("ERROR"):
        with SessionLocal() as db:
            notif.send_email(db, "candidate@real.com", "S", "<p>h</p>", "candidate", "invite")
    assert "re_supersecret_key" not in caplog.text
