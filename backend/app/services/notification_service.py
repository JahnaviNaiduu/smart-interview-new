import logging
from datetime import datetime, timezone
from typing import Optional
import resend
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.notification_log import NotificationLog

logger = logging.getLogger(__name__)
resend.api_key = settings.RESEND_API_KEY


def send_email(
    db: Session,
    to_email: str,
    subject: str,
    html_body: str,
    recipient_type: str,
    notification_type: str,
    booking_id=None,
    plain_body: str = "",
) -> bool:
    log = NotificationLog(
        booking_id=booking_id,
        recipient_email=to_email,
        recipient_type=recipient_type,
        notification_type=notification_type,
        subject=subject,
        body=plain_body or html_body,
        status="pending",
    )
    db.add(log)
    db.flush()

    try:
        actual_to = settings.RESEND_TEST_TO_EMAIL or to_email
        params = {
            "from": f"Smart Scheduler <{settings.RESEND_FROM_EMAIL}>",
            "to": [actual_to],
            "subject": subject,
            "html": html_body,
        }
        result = resend.Emails.send(params)
        log.status = "sent"
        log.resend_message_id = result.get("id")
        log.sent_at = datetime.now(timezone.utc)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Email send failed to {to_email}: {e}")
        log.status = "failed"
        db.commit()
        return False


def send_candidate_invite(
    db: Session,
    to_email: str,
    candidate_name: str,
    job_title: str,
    round_type: str,
    availability_link: str,
    email_body: str,
    expires_at: datetime,
    booking_id=None,
) -> bool:
    subject = f"Interview Invitation — {job_title} ({round_type.title()} Round)"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#000;color:#fff;padding:32px;border-radius:12px;border:1px solid rgba(255,255,255,0.1)">
      <h2 style="color:#fff;margin-bottom:8px">Interview Invitation</h2>
      <hr style="border:none;border-top:1px solid rgba(255,255,255,0.1);margin:16px 0"/>
      <p style="white-space:pre-line;line-height:1.6;color:#e0e0e0">{email_body}</p>
      <div style="margin:24px 0;text-align:center">
        <a href="{availability_link}" style="background:#fff;color:#000;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:bold;display:inline-block">
          Select Your Time Slot →
        </a>
      </div>
      <p style="color:#888;font-size:12px">This link expires {expires_at.strftime('%B %d, %Y at %I:%M %p UTC')}.</p>
      <p style="color:#888;font-size:12px">If you have any questions, reply to this email.</p>
    </div>
    """
    return send_email(db, to_email, subject, html, "candidate", "invite", booking_id, email_body)


def send_booking_confirmation(
    db: Session,
    to_email: str,
    recipient_name: str,
    recipient_type: str,
    job_title: str,
    round_type: str,
    start_time: datetime,
    end_time: datetime,
    meet_link: Optional[str],
    confirm_link: str,
    booking_id=None,
) -> bool:
    time_str = start_time.strftime("%A, %B %d, %Y at %I:%M %p UTC")
    subject = f"Interview Confirmed — {job_title} ({round_type.title()} Round)"
    meet_section = f'<p><strong>Meeting Link:</strong> <a href="{meet_link}" style="color:#fff">{meet_link}</a></p>' if meet_link else ""
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#000;color:#fff;padding:32px;border-radius:12px;border:1px solid rgba(255,255,255,0.1)">
      <h2 style="color:#fff">Interview Confirmed ✓</h2>
      <hr style="border:none;border-top:1px solid rgba(255,255,255,0.1);margin:16px 0"/>
      <p>Hi {recipient_name},</p>
      <p>Your <strong>{round_type.title()} interview</strong> for <strong>{job_title}</strong> has been confirmed.</p>
      <div style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:16px;margin:16px 0">
        <p style="margin:4px 0"><strong>Date & Time:</strong> {time_str}</p>
        <p style="margin:4px 0"><strong>Duration:</strong> {int((end_time - start_time).total_seconds() / 60)} minutes</p>
        {meet_section}
      </div>
      <p style="color:#888;font-size:12px">You will receive reminders 24 hours and 1 hour before the interview.</p>
      <p style="color:#888;font-size:12px">Need to reschedule? <a href="{confirm_link}" style="color:#aaa">Click here</a></p>
    </div>
    """
    plain = f"Interview confirmed for {job_title} on {time_str}. Meet link: {meet_link or 'TBD'}"
    return send_email(db, to_email, subject, html, recipient_type, "confirmation", booking_id, plain)


def send_reminder(
    db: Session,
    to_email: str,
    recipient_name: str,
    recipient_type: str,
    job_title: str,
    round_type: str,
    start_time: datetime,
    meet_link: Optional[str],
    reminder_type: str,
    booking_id=None,
) -> bool:
    time_str = start_time.strftime("%A, %B %d at %I:%M %p UTC")
    when = "24 hours" if reminder_type == "reminder_24h" else "1 hour"
    subject = f"Reminder: Interview in {when} — {job_title}"
    meet_section = f'<p><strong>Join here:</strong> <a href="{meet_link}" style="color:#fff">{meet_link}</a></p>' if meet_link else ""
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#000;color:#fff;padding:32px;border-radius:12px;border:1px solid rgba(255,255,255,0.1)">
      <h2>Interview Reminder ⏰</h2>
      <p>Hi {recipient_name}, your <strong>{round_type.title()} interview</strong> for <strong>{job_title}</strong> is in {when}.</p>
      <p><strong>Time:</strong> {time_str}</p>
      {meet_section}
    </div>
    """
    return send_email(db, to_email, subject, html, recipient_type, reminder_type, booking_id)


def send_cancellation(
    db: Session,
    to_email: str,
    recipient_name: str,
    recipient_type: str,
    job_title: str,
    round_type: str,
    reason: str = "",
    booking_id=None,
) -> bool:
    subject = f"Interview Cancelled — {job_title}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#000;color:#fff;padding:32px;border-radius:12px;border:1px solid rgba(255,255,255,0.1)">
      <h2>Interview Cancelled</h2>
      <p>Hi {recipient_name}, the <strong>{round_type.title()} interview</strong> for <strong>{job_title}</strong> has been cancelled.</p>
      {"<p>Reason: " + reason + "</p>" if reason else ""}
      <p>You will receive a new invitation if the interview is rescheduled.</p>
    </div>
    """
    return send_email(db, to_email, subject, html, recipient_type, "cancellation", booking_id)
