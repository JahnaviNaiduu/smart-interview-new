from datetime import datetime, timedelta, timezone
from typing import Optional
import pytz
from sqlalchemy.orm import Session
from app.models.panelist import Panelist
from app.services.calendar_service import get_busy_blocks


WORKING_HOUR_START = 9   # 9 AM local time
WORKING_HOUR_END = 18    # 6 PM local time


def _ensure_utc(dt: datetime) -> datetime:
    """Make a datetime UTC-aware, treating naive datetimes as UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_free_blocks(
    busy_blocks: list[dict],
    window_start: datetime,
    window_end: datetime,
) -> list[dict]:
    """Invert busy blocks to get free blocks within the window."""
    ws = _ensure_utc(window_start)
    we = _ensure_utc(window_end)
    sorted_busy = sorted(busy_blocks, key=lambda x: _ensure_utc(x["start"]))
    free = []
    current = ws

    for busy in sorted_busy:
        b_start = _ensure_utc(busy["start"])
        b_end = _ensure_utc(busy["end"])
        if b_start > current:
            free.append({"start": current, "end": b_start})
        current = max(current, b_end)

    if current < we:
        free.append({"start": current, "end": we})

    return free


def intersect_free_blocks(all_free_blocks: list[list[dict]]) -> list[dict]:
    """Find time blocks where ALL panelists are free."""
    if not all_free_blocks:
        return []

    result = all_free_blocks[0]
    for blocks in all_free_blocks[1:]:
        new_result = []
        for a in result:
            for b in blocks:
                start = max(a["start"], b["start"])
                end = min(a["end"], b["end"])
                if start < end:
                    new_result.append({"start": start, "end": end})
        result = new_result

    return result


def filter_to_working_hours(
    free_blocks: list[dict],
    tz_name: str = "UTC",
    window_end: Optional[datetime] = None,
) -> list[dict]:
    """Keep only portions of free blocks that fall within working hours."""
    try:
        tz = pytz.timezone(tz_name)
    except pytz.exceptions.UnknownTimeZoneError:
        tz = pytz.UTC

    filtered = []
    we_utc = _ensure_utc(window_end) if window_end else None

    for block in free_blocks:
        block_start = _ensure_utc(block["start"])
        block_end = _ensure_utc(block["end"])

        # Cap the block directly at window_end if provided
        if we_utc and block_end > we_utc:
            block_end = we_utc

        if block_start >= block_end:
            continue

        start_local = block_start.astimezone(tz)
        end_local = block_end.astimezone(tz)

        current_day = start_local.date()
        end_day = end_local.date()

        while current_day <= end_day:
            day_start_naive = datetime(current_day.year, current_day.month, current_day.day, WORKING_HOUR_START, 0)
            day_end_naive = datetime(current_day.year, current_day.month, current_day.day, WORKING_HOUR_END, 0)

            day_start = tz.localize(day_start_naive).astimezone(timezone.utc)
            day_end = tz.localize(day_end_naive).astimezone(timezone.utc)

            # Skip weekends
            if current_day.weekday() < 5:
                clipped_start = max(block_start, day_start)
                clipped_end = min(block_end, day_end)
                
                # Double-check against hard upper window limit
                if we_utc and clipped_end > we_utc:
                    clipped_end = we_utc

                if clipped_start < clipped_end:
                    filtered.append({"start": clipped_start, "end": clipped_end})

            current_day = (datetime(current_day.year, current_day.month, current_day.day) + timedelta(days=1)).date()

    return filtered

def split_into_slots(
    free_blocks: list[dict],
    duration_minutes: int,
    buffer_minutes: int = 0,
) -> list[dict]:
    """Split free blocks into discrete interview slots."""
    slots = []
    slot_duration = timedelta(minutes=duration_minutes)
    buffer = timedelta(minutes=buffer_minutes)
    step = slot_duration + buffer

    for block in free_blocks:
        current = block["start"]
        while current + slot_duration <= block["end"]:
            slots.append({"start": current, "end": current + slot_duration})
            current += step

    return slots


def find_available_slots(
    db: Session,
    panelist_ids: list[str],
    window_start: datetime,
    window_end: datetime,
    duration_minutes: int,
    buffer_minutes: int = 15,
    preferred_timezone: str = "UTC",
) -> list[dict]:
    """Main scheduling function: check calendars, find intersection, return slots."""
    all_free_blocks = []

    for pid in panelist_ids:
        panelist = db.query(Panelist).filter(Panelist.id == pid, Panelist.is_active == True).first()
        if not panelist:
            continue

        if panelist.google_access_token and panelist.google_calendar_id:
            try:
                busy = get_busy_blocks(
                    access_token=panelist.google_access_token,
                    refresh_token=panelist.google_refresh_token,
                    token_expiry=panelist.token_expiry,
                    calendar_id=panelist.google_calendar_id,
                    time_min=window_start,
                    time_max=window_end,
                )
            except RuntimeError:
                busy = []
        else:
            # No calendar connected — treat the full window as free
            busy = []

        free = get_free_blocks(busy, window_start, window_end)
        all_free_blocks.append(free)

    if not all_free_blocks:
        return []

    intersection = intersect_free_blocks(all_free_blocks)
    within_hours = filter_to_working_hours(
        free_blocks=intersection, 
        tz_name=preferred_timezone, 
        window_end=window_end
    )
    slots = split_into_slots(within_hours, duration_minutes, buffer_minutes)

    return slots[:20]  # cap at 20 slots
