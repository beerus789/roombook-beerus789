from datetime import datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Room, User
from ..scheduling import relevant_bookings_query, suggest_slots
from ..schemas import RoomIn, RoomOut, SuggestRequest, SuggestResponse

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("", response_model=list[RoomOut])
def list_rooms(db: Session = Depends(get_db)):
    return db.scalars(select(Room).order_by(Room.id)).all()


@router.get("/{room_id}", response_model=RoomOut)
def get_room(room_id: int, db: Session = Depends(get_db)):
    room = db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@router.post("", response_model=RoomOut, status_code=201)
def create_room(payload: RoomIn, db: Session = Depends(get_db)):
    room = Room(name=payload.name, capacity=payload.capacity)
    db.add(room)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A room with that name already exists")
    return room


@router.post("/{room_id}/suggest", response_model=SuggestResponse)
def suggest_room_slots(room_id: int, payload: SuggestRequest, db: Session = Depends(get_db)):
    room = db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    requester = db.get(User, payload.requester_id)
    if requester is None:
        raise HTTPException(status_code=404, detail="Requester not found")
    attendee_ids = set(payload.attendee_ids)
    attendees = db.scalars(select(User).where(User.id.in_(attendee_ids))).all() if attendee_ids else []
    if len(attendees) != len(attendee_ids):
        raise HTTPException(status_code=400, detail="Unknown attendee")
    users = {user.id: user for user in [requester, *attendees]}
    if len(users) > room.capacity:
        raise HTTPException(status_code=422, detail="Participant count exceeds room capacity")

    day_start = datetime.combine(payload.date, time.min)
    day_end = day_start + timedelta(days=1)
    bookings = db.scalars(
        relevant_bookings_query(
            room_id=room.id,
            participant_ids=set(users),
            day_start=day_start,
            day_end=day_end,
        )
    ).all()
    slots = suggest_slots(
        room=room,
        users=list(users.values()),
        day=payload.date,
        duration=payload.duration_minutes,
        bookings=list(bookings),
    )
    return {"slots": [{"start": slot.start, "end": slot.end} for slot in slots]}
