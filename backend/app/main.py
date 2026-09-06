from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.auth import require_staff
from app.core.database import engine, Base
from app.api.v1 import interviews, panelists, availability, bookings, notifications, auth
from app.api.v1.auth import seed_default_users
import app.models  # noqa: ensure all models are registered


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_default_users()
    yield


app = FastAPI(
    title="Smart Interview Scheduler API",
    version="1.0.0",
    description="AI-powered interview scheduling with Google Calendar, Llama 3.1 via Groq, and Resend email.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(interviews.router, prefix="/api/v1")
app.include_router(panelists.router, prefix="/api/v1")
app.include_router(availability.router, prefix="/api/v1")
app.include_router(bookings.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "service": "Smart Interview Scheduler", "db": "sqlite"}


@app.get("/api/v1/analytics")
def get_analytics(_: object = Depends(require_staff)):
    from app.core.database import SessionLocal
    from app.models.interview import InterviewRequest
    from app.models.notification_log import NotificationLog

    with SessionLocal() as db:
        total = db.query(InterviewRequest).count()
        booked = db.query(InterviewRequest).filter(InterviewRequest.status == "booked").count()
        cancelled = db.query(InterviewRequest).filter(InterviewRequest.status == "cancelled").count()
        pending = db.query(InterviewRequest).filter(
            InterviewRequest.status.in_(["pending", "slots_found", "candidate_notified"])
        ).count()
        rescheduling = db.query(InterviewRequest).filter(InterviewRequest.status == "rescheduling").count()
        notifications_sent = db.query(NotificationLog).filter(NotificationLog.status == "sent").count()
        notifications_failed = db.query(NotificationLog).filter(NotificationLog.status == "failed").count()

        return {
            "total_requests": total,
            "booked": booked,
            "cancelled": cancelled,
            "pending": pending,
            "rescheduling": rescheduling,
            "cancellation_rate": round(cancelled / total * 100, 1) if total else 0,
            "booking_rate": round(booked / total * 100, 1) if total else 0,
            "notifications_sent": notifications_sent,
            "notifications_failed": notifications_failed,
        }
