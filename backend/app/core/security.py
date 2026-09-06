import uuid
import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

# pbkdf2_sha256 is pure-python (no bcrypt/rust build), so it installs cleanly
# everywhere while still using the project's already-declared passlib dependency.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError):
        return False


def generate_secure_token() -> str:
    return str(uuid.uuid4())


def create_expiry(hours: int = None) -> datetime:
    expiry_hours = hours or settings.TOKEN_EXPIRY_HOURS
    return datetime.now(timezone.utc) + timedelta(hours=expiry_hours)


def is_token_expired(expires_at: datetime) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) > expires_at


def sanitize_string(value: str, max_length: int = 500) -> str:
    if not value:
        return value
    cleaned = re.sub(r'[<>&"\']', '', value)
    return cleaned[:max_length].strip()


def sanitize_email(email: str) -> str:
    email = email.lower().strip()
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValueError(f"Invalid email format: {email}")
    return email


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=24))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        return None
