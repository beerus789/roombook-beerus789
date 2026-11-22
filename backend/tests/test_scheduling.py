from datetime import date, datetime

from app.models import Booking, Room, User
from app.scheduling import suggest_slots, valid_slot


def user(user_id=1, role="employee"):
    return User(id=user_id, name=f"User {user_id}", role=role)


def room(room_id=1, name="Focus Room"):
    return Room(id=room_id, name=name, capacity=8)


def booking(*, room_id=1, creator_id=2, attendees=None, start="2026-12-07T10:00", end="2026-12-07T11:15"):
    return Booking(
        room_id=room_id,
        creator_id=creator_id,
        attendees=attendees or [],
        start=datetime.fromisoformat(start),
        end=datetime.fromisoformat(end),
    )


def test_long_suggestion_skips_lunch_and_uses_first_later_slot():
    slots = suggest_slots(
        room=room(), users=[user()], day=date(2026, 12, 7), duration=240, bookings=[]
    )
    assert len(slots) == 3
    assert slots[0].start.isoformat() == "2026-12-07T14:00:00+05:30"
    assert slots[0].end.isoformat() == "2026-12-07T18:00:00+05:30"


def test_short_meeting_may_overlap_lunch_but_long_meeting_may_not():
    short = valid_slot(
        room=room(), users=[user()], start=datetime(2026, 12, 7, 13),
        end=datetime(2026, 12, 7, 13, 30), bookings=[]
    )
    long = valid_slot(
        room=room(), users=[user()], start=datetime(2026, 12, 7, 12, 45),
        end=datetime(2026, 12, 7, 13, 30), bookings=[]
    )
    assert short is True
    assert long is False


def test_long_booking_cleaning_buffer_blocks_following_slot():
    existing = booking()
    assert not valid_slot(
        room=room(), users=[user(3)], start=datetime(2026, 12, 7, 11, 15),
        end=datetime(2026, 12, 7, 11, 30), bookings=[existing]
    )
    assert valid_slot(
        room=room(), users=[user(3)], start=datetime(2026, 12, 7, 11, 30),
        end=datetime(2026, 12, 7, 11, 45), bookings=[existing]
    )


def test_intern_cannot_suggest_board_room():
    slots = suggest_slots(
        room=room(2, "Board Room"), users=[user(role="intern")],
        day=date(2026, 12, 7), duration=30, bookings=[]
    )
    assert slots == []


def test_attendee_booking_in_another_room_removes_overlapping_candidate():
    existing = booking(room_id=2, creator_id=7, attendees=[user(5)], start="2026-12-07T10:00", end="2026-12-07T10:30")
    assert not valid_slot(
        room=room(1), users=[user(5)], start=datetime(2026, 12, 7, 10),
        end=datetime(2026, 12, 7, 10, 30), bookings=[existing]
    )
