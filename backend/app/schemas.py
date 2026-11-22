from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .scheduling import as_office_aware, as_office_naive

Role = Literal["employee", "manager", "intern"]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    role: Role


class RoomIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    capacity: int = Field(gt=0, le=100)

    @field_validator("name")
    @classmethod
    def trim_room_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Room name cannot be blank")
        return value


class RoomOut(RoomIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


class BookingIn(BaseModel):
    room_id: int = Field(gt=0)
    creator_id: int = Field(gt=0)
    title: str = Field(default="", max_length=200)
    attendee_ids: list[int] = Field(default_factory=list, max_length=100)
    start: datetime
    end: datetime

    @field_validator("start", "end")
    @classmethod
    def normalise_datetime(cls, value: datetime) -> datetime:
        return as_office_naive(value)

    @model_validator(mode="after")
    def check_order(self) -> "BookingIn":
        if self.end <= self.start:
            raise ValueError("end must be after start")
        return self


class SuggestRequest(BaseModel):
    requester_id: int = Field(gt=0)
    attendee_ids: list[int] = Field(default_factory=list, max_length=100)
    duration_minutes: int = Field(ge=15, le=240, multiple_of=15)
    date: date


class SlotOut(BaseModel):
    start: datetime
    end: datetime


class SuggestResponse(BaseModel):
    slots: list[SlotOut]


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    room: RoomOut
    creator_id: int
    attendees: list[UserOut]
    start: datetime
    end: datetime

    @field_validator("start", "end")
    @classmethod
    def display_office_time(cls, value: datetime) -> datetime:
        return as_office_aware(value)
