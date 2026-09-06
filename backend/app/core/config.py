from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"
    GROQ_API_KEY: str
    RESEND_API_KEY: str
    RESEND_FROM_EMAIL: str = "noreply@yourdomain.com"
    SECRET_KEY: str
    ENCRYPTION_KEY: Optional[str] = None
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"
    TOKEN_EXPIRY_HOURS: int = 72

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
