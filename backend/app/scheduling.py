from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from .models import Booking, Room, User, booking_attendees

OFFICE_TZ = ZoneInfo("Asia/Kolkata")
WORK_START = time(9, 30)
WORK_END = time(18, 30)
LUNCH_START = time(13, 0)
LUNCH_END = time(14, 0)
SLOT_STEP_MINUTES = 15
MIN_DURATION_MINUTES = 15
MAX_DURATION_MINUTES = 240
CLEANING_BUFFER = timedelta(minutes=15)


@dataclass(frozen=True)
class Slot:
    start: datetime
    end: datetime


def as_office_naive(value: datetime) -> datetime:
    """Normalize API timestamps to naive IST for the existing database schema.

    Naive values are treated as office-local time. Aware values are converted to
    IST before dropping tzinfo, so an offset cannot silently shift a booking.
    """
    if value.tzinfo is not None:
        value = value.astimezone(OFFICE_TZ).replace(tzinfo=None)
    return value


def as_office_aware(value: datetime) -> datetime:
    return as_office_naive(value).replace(tzinfo=OFFICE_TZ)


def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    """Whether half-open time ranges overlap; touching endpoints are available."""
    return a_start < b_end and b_start < a_end


def duration_minutes(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds() // 60)


def valid_duration(start: datetime, end: datetime) -> bool:
    minutes = duration_minutes(start, end)
    return (
        end > start
        and minutes in range(MIN_DURATION_MINUTES, MAX_DURATION_MINUTES + 1)
        and minutes % SLOT_STEP_MINUTES == 0
    )


def valid_office_window(start: datetime, end: datetime) -> bool:
    return (
        start.date() == end.date()
        and start.weekday() < 5
        and WORK_START <= start.time()
        and end.time() <= WORK_END
    )


def overlaps_lunch(start: datetime, end: datetime) -> bool:
    lunch_start = datetime.combine(start.date(), LUNCH_START)
    lunch_end = datetime.combine(start.date(), LUNCH_END)
    return overlaps(start, end, lunch_start, lunch_end)


def room_block_end(start: datetime, end: datetime) -> datetime:
    if duration_minutes(start, end) > 60:
        return end + CLEANING_BUFFER
    return end


def valid_booking_rules(*, room: Room, users: list[User], start: datetime, end: datetime) -> bool:
    start, end = as_office_naive(start), as_office_naive(end)
    return (
        valid_duration(start, end)
        and valid_office_window(start, end)
        and start.minute % SLOT_STEP_MINUTES == 0
        and start.second == 0
        and start.microsecond == 0
        and end.second == 0
        and end.microsecond == 0
        and not (overlaps_lunch(start, end) and duration_minutes(start, end) > 30)
        and not (
            room.name.strip().casefold() == "board room"
            and any(user.role == "intern" for user in users)
        )
    )


def valid_slot(
    *,
    room: Room,
    users: list[User],
    start: datetime,
    end: datetime,
    bookings: list[Booking],
) -> bool:
    start, end = as_office_naive(start), as_office_naive(end)
    if not valid_booking_rules(room=room, users=users, start=start, end=end):
        return False

    candidate_block_end = room_block_end(start, end)
    user_ids = {user.id for user in users}
    for booking in bookings:
        existing_end = room_block_end(booking.start, booking.end)
        if booking.room_id == room.id and overlaps(start, candidate_block_end, booking.start, existing_end):
            return False
        booking_user_ids = {user.id for user in booking.attendees}
        booking_user_ids.add(booking.creator_id)
        if user_ids & booking_user_ids and overlaps(start, end, booking.start, booking.end):
            return False
    return True


def relevant_bookings_query(
    *, room_id: int, participant_ids: set[int], day_start: datetime, day_end: datetime
):
    attendee_booking_ids = select(booking_attendees.c.booking_id).where(
        booking_attendees.c.user_id.in_(participant_ids)
    )
    return (
        select(Booking)
        .options(selectinload(Booking.attendees))
        .where(
            Booking.start < day_end,
            Booking.end > day_start,
            or_(
                Booking.room_id == room_id,
                Booking.creator_id.in_(participant_ids),
                Booking.id.in_(attendee_booking_ids),
            ),
        )
        .distinct()
    )


def suggest_slots(
    *, room: Room, users: list[User], day: date, duration: int, bookings: list[Booking], limit: int = 3
) -> list[Slot]:
    if duration < MIN_DURATION_MINUTES or duration > MAX_DURATION_MINUTES or duration % SLOT_STEP_MINUTES:
        return []
    if day.weekday() >= 5:
        return []
    slots: list[Slot] = []
    cursor = datetime.combine(day, WORK_START)
    last_start = datetime.combine(day, WORK_END) - timedelta(minutes=duration)
    while cursor <= last_start and len(slots) < limit:
        end = cursor + timedelta(minutes=duration)
        if valid_slot(room=room, users=users, start=cursor, end=end, bookings=bookings):
            slots.append(Slot(cursor.replace(tzinfo=OFFICE_TZ), end.replace(tzinfo=OFFICE_TZ)))
        cursor += timedelta(minutes=SLOT_STEP_MINUTES)
    return slots
