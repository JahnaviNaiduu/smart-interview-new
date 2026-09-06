import uuid
from datetime import datetime, timezone, timedelta
from app.core.config import settings


def generate_candidate_token() -> tuple[str, datetime]:
    token = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.TOKEN_EXPIRY_HOURS)
    return token, expires_at


def generate_confirm_token() -> str:
    return str(uuid.uuid4())


def is_expired(expires_at: datetime) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) > expires_at
