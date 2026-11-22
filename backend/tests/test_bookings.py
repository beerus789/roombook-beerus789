def test_list_bookings_for_date(client):
    res = client.get("/bookings", params={"date": "2026-12-07"})
    assert res.status_code == 200
    bookings = res.json()
    assert len(bookings) == 8
    starts = [b["start"] for b in bookings]
    assert starts == sorted(starts)


def test_list_bookings_for_room(client):
    res = client.get("/bookings", params={"date": "2026-12-07", "room_id": 3})
    assert [b["title"] for b in res.json()] == ["Standup sync", "Retro"]


def test_create_booking(client):
    res = client.post(
        "/bookings",
        json={
            "room_id": 3,
            "creator_id": 2,
            "title": "Pairing",
            "attendee_ids": [2, 6],
            "start": "2026-12-07T15:00:00",
            "end": "2026-12-07T15:30:00",
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["room"]["name"] == "Huddle"
    assert {a["name"] for a in body["attendees"]} == {"Ben", "Farah"}


def test_overlapping_booking_is_rejected(client):
    res = client.post(
        "/bookings",
        json={
            "room_id": 1,
            "creator_id": 1,
            "attendee_ids": [1],
            "start": "2026-12-07T10:30:00",
            "end": "2026-12-07T11:00:00",
        },
    )
    assert res.status_code == 409


def test_back_to_back_booking_is_allowed(client):
    res = client.post(
        "/bookings",
        json={
            "room_id": 3,
            "creator_id": 4,
            "attendee_ids": [4],
            "start": "2026-12-07T12:15:00+05:30",
            "end": "2026-12-07T12:45:00+05:30",
        },
    )
    assert res.status_code == 201


def test_attendee_cannot_be_double_booked_in_another_room(client):
    res = client.post(
        "/bookings",
        json={
            "room_id": 3,
            "creator_id": 1,
            "attendee_ids": [1],
            "start": "2026-12-07T09:45:00",
            "end": "2026-12-07T10:15:00",
        },
    )
    assert res.status_code == 409


def test_non_ist_offset_is_converted_before_storage(client):
    res = client.post(
        "/bookings",
        json={
            "room_id": 3,
            "creator_id": 4,
            "attendee_ids": [4],
            "start": "2026-12-07T04:00:00+00:00",
            "end": "2026-12-07T04:30:00+00:00",
        },
    )
    assert res.status_code == 201
    assert res.json()["start"] == "2026-12-07T09:30:00+05:30"


def test_booking_must_start_on_quarter_hour_and_within_office_hours(client):
    off_grid = client.post(
        "/bookings",
        json={
            "room_id": 3,
            "creator_id": 4,
            "attendee_ids": [4],
            "start": "2026-12-07T09:35:00",
            "end": "2026-12-07T10:05:00",
        },
    )
    assert off_grid.status_code == 422

    subminute = client.post(
        "/bookings",
        json={
            "room_id": 3,
            "creator_id": 4,
            "attendee_ids": [4],
            "start": "2026-12-07T10:00:01",
            "end": "2026-12-07T10:30:00",
        },
    )
    assert subminute.status_code == 422

    outside_hours = client.post(
        "/bookings",
        json={
            "room_id": 3,
            "creator_id": 4,
            "attendee_ids": [4],
            "start": "2026-12-07T18:15:00",
            "end": "2026-12-07T18:45:00",
        },
    )
    assert outside_hours.status_code == 422


def test_long_booking_cleaning_buffer_blocks_room(client):
    res = client.post(
        "/bookings",
        json={
            "room_id": 2,
            "creator_id": 2,
            "attendee_ids": [2],
            "start": "2026-12-07T17:00:00",
            "end": "2026-12-07T17:30:00",
        },
    )
    assert res.status_code == 409


def test_lunch_rule_and_intern_board_room_restriction(client):
    blocked_lunch = client.post(
        "/bookings",
        json={
            "room_id": 3,
            "creator_id": 4,
            "attendee_ids": [4],
            "start": "2026-12-07T12:30:00",
            "end": "2026-12-07T13:15:00",
        },
    )
    assert blocked_lunch.status_code == 422

    intern_board_room = client.post(
        "/bookings",
        json={
            "room_id": 2,
            "creator_id": 4,
            "attendee_ids": [4],
            "start": "2026-12-07T14:00:00",
            "end": "2026-12-07T14:30:00",
        },
    )
    assert intern_board_room.status_code == 422


def test_suggest_returns_first_three_available_slots(client):
    res = client.post(
        "/rooms/3/suggest",
        json={
            "requester_id": 4,
            "attendee_ids": [2],
            "duration_minutes": 45,
            "date": "2026-12-07",
        },
    )
    assert res.status_code == 200
    slots = res.json()["slots"]
    assert len(slots) == 3
    assert [slot["start"] for slot in slots] == sorted(slot["start"] for slot in slots)
    assert slots[0] == {
        "start": "2026-12-07T09:30:00+05:30",
        "end": "2026-12-07T10:15:00+05:30",
    }


def test_suggest_respects_attendee_conflicts_and_returns_empty_weekend(client):
    attendee_conflict = client.post(
        "/rooms/3/suggest",
        json={
            "requester_id": 4,
            "attendee_ids": [1],
            "duration_minutes": 30,
            "date": "2026-12-07",
        },
    )
    assert attendee_conflict.status_code == 200
    assert attendee_conflict.json()["slots"][0]["start"] == "2026-12-07T10:00:00+05:30"

    weekend = client.post(
        "/rooms/3/suggest",
        json={"requester_id": 4, "attendee_ids": [], "duration_minutes": 30, "date": "2026-12-12"},
    )
    assert weekend.status_code == 200
    assert weekend.json()["slots"] == []


def test_suggest_rejects_invalid_duration(client):
    res = client.post(
        "/rooms/3/suggest",
        json={"requester_id": 1, "attendee_ids": [], "duration_minutes": 20, "date": "2026-12-07"},
    )
    assert res.status_code == 422


def test_booking_rejects_more_people_than_room_capacity(client):
    res = client.post(
        "/bookings",
        json={
            "room_id": 1,
            "creator_id": 1,
            "attendee_ids": [2, 3, 4, 5],
            "start": "2026-12-10T09:30:00",
            "end": "2026-12-10T10:00:00",
        },
    )
    assert res.status_code == 422
    assert "capacity" in res.json()["detail"]


def test_booking_allows_participant_count_at_room_capacity(client):
    res = client.post(
        "/bookings",
        json={
            "room_id": 1,
            "creator_id": 1,
            "attendee_ids": [2, 3, 4],
            "start": "2026-12-10T09:30:00",
            "end": "2026-12-10T10:00:00",
        },
    )
    assert res.status_code == 201


def test_suggest_rejects_more_people_than_room_capacity(client):
    res = client.post(
        "/rooms/1/suggest",
        json={
            "requester_id": 1,
            "attendee_ids": [2, 3, 4, 5],
            "duration_minutes": 30,
            "date": "2026-12-10",
        },
    )
    assert res.status_code == 422


def test_booking_list_supports_bounded_pagination(client):
    first = client.get("/bookings", params={"date": "2026-12-07", "limit": 2})
    second = client.get("/bookings", params={"date": "2026-12-07", "limit": 2, "offset": 2})
    assert first.status_code == second.status_code == 200
    assert len(first.json()) == len(second.json()) == 2
    assert first.json()[0]["start"] < second.json()[0]["start"]


def test_attendee_list_has_a_hard_size_limit(client):
    res = client.post(
        "/rooms/1/suggest",
        json={
            "requester_id": 1,
            "attendee_ids": list(range(1, 102)),
            "duration_minutes": 30,
            "date": "2026-12-10",
        },
    )
    assert res.status_code == 422


def test_booking_list_rejects_unsafe_page_sizes(client):
    assert client.get("/bookings", params={"limit": 0}).status_code == 422
    assert client.get("/bookings", params={"limit": 501}).status_code == 422


def test_end_must_be_after_start(client):
    res = client.post(
        "/bookings",
        json={
            "room_id": 1,
            "creator_id": 1,
            "start": "2026-12-07T11:00:00",
            "end": "2026-12-07T10:00:00",
        },
    )
    assert res.status_code == 422


def test_unknown_room(client):
    res = client.post(
        "/bookings",
        json={
            "room_id": 99,
            "creator_id": 1,
            "start": "2026-12-07T10:00:00",
            "end": "2026-12-07T11:00:00",
        },
    )
    assert res.status_code == 404


def test_unknown_attendee(client):
    res = client.post(
        "/bookings",
        json={
            "room_id": 3,
            "creator_id": 1,
            "attendee_ids": [42],
            "start": "2026-12-07T15:00:00",
            "end": "2026-12-07T15:30:00",
        },
    )
    assert res.status_code == 400
