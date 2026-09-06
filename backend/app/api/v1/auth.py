import os
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db, SessionLocal
from app.core.security import create_access_token, hash_password, verify_password
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, UserOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    # Same generic error for unknown-user and wrong-password to avoid user enumeration.
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    # Role is taken from the DB record, never from the request.
    token = create_access_token({"sub": user.id, "role": user.role, "email": user.email})
    return LoginResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)


# --- Demo seeding -----------------------------------------------------------
# Creates default staff accounts on first boot so the dashboard is usable.
# Credentials are overridable via env; change them for any real deployment.
def seed_default_users() -> None:
    defaults = [
        (os.getenv("SEED_ADMIN_EMAIL", "admin@demo.com"),
         os.getenv("SEED_ADMIN_PASSWORD", "admin123"), "Admin User", "admin"),
        (os.getenv("SEED_RECRUITER_EMAIL", "recruiter@demo.com"),
         os.getenv("SEED_RECRUITER_PASSWORD", "recruiter123"), "Recruiter User", "recruiter"),
    ]
    with SessionLocal() as db:
        for email, password, name, role in defaults:
            if not db.query(User).filter(User.email == email).first():
                db.add(User(email=email, name=name, role=role, hashed_password=hash_password(password)))
                logger.info("Seeded default %s user: %s", role, email)
        db.commit()
