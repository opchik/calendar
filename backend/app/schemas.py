from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

Privacy = Literal["private", "link", "circle"]
RSVPStatus = Literal["going", "maybe", "declined"]


class TelegramAuthIn(BaseModel):
    initData: str


class ConfigOut(BaseModel):
    dev: bool
    botUsername: str | None = None
    appShortName: str | None = None
    publicUrl: str
    keycloakEnabled: bool = False


class UserBrief(BaseModel):
    id: UUID
    firstName: str | None = None
    lastName: str | None = None
    username: str | None = None
    photoUrl: str | None = None


class MeOut(BaseModel):
    user: UserBrief
    timezone: str


class CircleIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: str = Field(default="#3390ec", pattern=r"^#[0-9a-fA-F]{6}$")

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Название круга не может быть пустым")
        return value


class CircleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


class CircleOut(BaseModel):
    id: UUID
    name: str
    color: str
    position: int


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    startsAt: datetime
    description: str | None = Field(default=None, max_length=4000)
    locationText: str | None = Field(default=None, max_length=200)
    locationUrl: str | None = Field(default=None, max_length=500)
    cover: str = Field(default="preset:sunset", max_length=500)
    privacy: Privacy = "link"
    circleId: UUID | None = None

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Название не может быть пустым")
        return value

    @field_validator("startsAt")
    @classmethod
    def _ensure_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class EventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    startsAt: datetime | None = None
    description: str | None = Field(default=None, max_length=4000)
    locationText: str | None = Field(default=None, max_length=200)
    locationUrl: str | None = Field(default=None, max_length=500)
    cover: str | None = Field(default=None, max_length=500)
    privacy: Privacy | None = None
    circleId: UUID | None = None

    @field_validator("startsAt")
    @classmethod
    def _ensure_timezone(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class RSVPIn(BaseModel):
    status: RSVPStatus


class CommentIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)

    @field_validator("text")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Комментарий не может быть пустым")
        return value


class ParticipantOut(BaseModel):
    user: UserBrief
    status: str
    role: str


class EventOut(BaseModel):
    id: UUID
    title: str
    description: str | None
    startsAt: datetime
    locationText: str | None
    locationUrl: str | None
    cover: str
    privacy: str
    circle: CircleOut | None
    owner: UserBrief
    participants: list[ParticipantOut]
    myStatus: str | None
    myRole: str | None
    isOwner: bool
    shareUrl: str
    commentCount: int
    createdAt: datetime


class EventsOut(BaseModel):
    events: list[EventOut]


class CommentOut(BaseModel):
    id: UUID
    text: str
    createdAt: datetime
    user: UserBrief


class CommentsOut(BaseModel):
    comments: list[CommentOut]


class CoverUploadOut(BaseModel):
    url: str
