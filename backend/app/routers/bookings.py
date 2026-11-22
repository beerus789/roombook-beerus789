from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import Booking, Room, User
from ..scheduling import relevant_bookings_query, valid_booking_rules, valid_slot
from ..schemas import BookingIn, BookingOut

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.get("", response_model=list[BookingOut])
def list_bookings(
    date: date | None = None,
    room_id: int | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = (
        select(Booking)
        .options(selectinload(Booking.attendees), selectinload(Booking.room))
        .order_by(Booking.start, Booking.id)
    )
    if date is not None:
        day_start = datetime.combine(date, time.min)
        query = query.where(Booking.start >= day_start, Booking.start < day_start + timedelta(days=1))
    if room_id is not None:
        query = query.where(Booking.room_id == room_id)
    query = query.limit(limit).offset(offset)
    return db.scalars(query).all()


@router.post("", response_model=BookingOut, status_code=201)
def create_booking(payload: BookingIn, db: Session = Depends(get_db)):
    try:
        # SQLite ignores SELECT FOR UPDATE. BEGIN IMMEDIATE takes its single-writer
        # lock before checking availability; PostgreSQL locks only the room row.
        if db.get_bind().dialect.name == "sqlite":
            db.execute(text("BEGIN IMMEDIATE"))
            room = db.get(Room, payload.room_id)
        else:
            room = db.scalar(select(Room).where(Room.id == payload.room_id).with_for_update())
        if room is None:
            raise HTTPException(status_code=404, detail="Room not found")
        creator = db.get(User, payload.creator_id)
        if creator is None:
            raise HTTPException(status_code=404, detail="Creator not found")

        attendee_ids = set(payload.attendee_ids)
        attendees = db.scalars(select(User).where(User.id.in_(attendee_ids))).all() if attendee_ids else []
        if len(attendees) != len(attendee_ids):
            raise HTTPException(status_code=400, detail="Unknown attendee")
        participants = {user.id: user for user in [creator, *attendees]}
        if len(participants) > room.capacity:
            raise HTTPException(status_code=422, detail="Participant count exceeds room capacity")
        if db.get_bind().dialect.name != "sqlite":
            # Lock participants in a stable order too, so concurrent bookings in
            # different rooms cannot double-book the same person.
            locked_users = db.scalars(
                select(User)
                .where(User.id.in_(participants))
                .order_by(User.id)
                .with_for_update()
            ).all()
            participants = {user.id: user for user in locked_users}
        if not valid_booking_rules(
            room=room,
            users=list(participants.values()),
            start=payload.start,
            end=payload.end,
        ):
            raise HTTPException(status_code=422, detail="Booking violates office scheduling rules")

        day_start = datetime.combine(payload.start.date(), time.min)
        day_end = day_start + timedelta(days=1)
        existing = db.scalars(
            relevant_bookings_query(
                room_id=room.id,
                participant_ids=set(participants),
                day_start=day_start,
                day_end=day_end,
            )
        ).all()
        if not valid_slot(
            room=room,
            users=list(participants.values()),
            start=payload.start,
            end=payload.end,
            bookings=list(existing),
        ):
            raise HTTPException(status_code=409, detail="Room or attendee is unavailable, or booking violates office rules")

        booking = Booking(
            room_id=room.id,
            creator_id=creator.id,
            title=payload.title,
            start=payload.start,
            end=payload.end,
            attendees=list(attendees),
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        return booking
    except Exception:
        db.rollback()
        raise
