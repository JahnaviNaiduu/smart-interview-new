from datetime import datetime, timedelta, timezone
from typing import Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.core.config import settings


def build_calendar_client(access_token: str, refresh_token: str, token_expiry: Optional[datetime]):
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/calendar"],
    )
    if token_expiry:
        creds.expiry = token_expiry.replace(tzinfo=None)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def get_busy_blocks(
    access_token: str,
    refresh_token: str,
    token_expiry: Optional[datetime],
    calendar_id: str,
    time_min: datetime,
    time_max: datetime,
) -> list[dict]:
    try:
        service = build_calendar_client(access_token, refresh_token, token_expiry)
        body = {
            "timeMin": time_min.isoformat(),
            "timeMax": time_max.isoformat(),
            "items": [{"id": calendar_id}],
        }
        result = service.freebusy().query(body=body).execute()
        busy = result.get("calendars", {}).get(calendar_id, {}).get("busy", [])
        return [
            {
                "start": datetime.fromisoformat(b["start"].replace("Z", "+00:00")),
                "end": datetime.fromisoformat(b["end"].replace("Z", "+00:00")),
            }
            for b in busy
        ]
    except HttpError as e:
        raise RuntimeError(f"Google Calendar API error: {e.reason}")


def create_calendar_event(
    access_token: str,
    refresh_token: str,
    token_expiry: Optional[datetime],
    summary: str,
    description: str,
    start_time: datetime,
    end_time: datetime,
    attendee_emails: list[str],
    timezone: str = "UTC",
) -> dict:
    try:
        service = build_calendar_client(access_token, refresh_token, token_expiry)
        event = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_time.isoformat(), "timeZone": timezone},
            "end": {"dateTime": end_time.isoformat(), "timeZone": timezone},
            "attendees": [{"email": email} for email in attendee_emails],
            "conferenceData": {
                "createRequest": {
                    "requestId": f"meet-{start_time.timestamp()}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 24 * 60},
                    {"method": "popup", "minutes": 60},
                ],
            },
        }
        created = service.events().insert(
            calendarId="primary",
            body=event,
            conferenceDataVersion=1,
            sendUpdates="all",
        ).execute()
        meet_link = None
        if "conferenceData" in created:
            entry_points = created["conferenceData"].get("entryPoints", [])
            for ep in entry_points:
                if ep.get("entryPointType") == "video":
                    meet_link = ep.get("uri")
                    break
        return {"event_id": created["id"], "meet_link": meet_link, "html_link": created.get("htmlLink")}
    except HttpError as e:
        raise RuntimeError(f"Google Calendar event creation failed: {e.reason}")


def delete_calendar_event(
    access_token: str,
    refresh_token: str,
    token_expiry: Optional[datetime],
    event_id: str,
) -> None:
    try:
        service = build_calendar_client(access_token, refresh_token, token_expiry)
        service.events().delete(calendarId="primary", eventId=event_id, sendUpdates="all").execute()
    except HttpError as e:
        if e.status_code != 410:
            raise RuntimeError(f"Failed to delete calendar event: {e.reason}")


def get_oauth_url(state: Optional[str] = None) -> str:
    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=[
            "https://www.googleapis.com/auth/calendar",
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ],
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )
    kwargs = {"access_type": "offline", "prompt": "consent"}
    if state:
        kwargs["state"] = state
    auth_url, _ = flow.authorization_url(**kwargs)
    return auth_url


def exchange_code_for_tokens(code: str, panelist_id: str) -> dict:
    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=[
            "https://www.googleapis.com/auth/calendar",
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ],
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        state=panelist_id,
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    return {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_expiry": creds.expiry,
    }
