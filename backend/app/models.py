from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Table, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

booking_attendees = Table(
    "booking_attendees",
    Base.metadata,
    Column("booking_id", ForeignKey("bookings.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Index("ix_booking_attendees_user_booking", "user_id", "booking_id"),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20), default="employee")


class Room(Base):
    __tablename__ = "rooms"
    __table_args__ = (Index("uq_rooms_name_lower", text("lower(name)"), unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    capacity: Mapped[int]


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (Index("ix_bookings_room_start_end", "room_id", "start", "end"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), index=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(200), default="")
    start: Mapped[datetime] = mapped_column(DateTime, index=True)
    end: Mapped[datetime] = mapped_column(DateTime)

    room: Mapped[Room] = relationship()
    creator: Mapped[User] = relationship()
    attendees: Mapped[list[User]] = relationship(secondary=booking_attendees)
