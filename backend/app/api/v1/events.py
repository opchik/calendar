from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from ...deps import CurrentUser, SessionDep
from ...schemas import (
    CommentIn,
    CommentOut,
    CommentsOut,
    EventCreate,
    EventOut,
    EventsOut,
    EventUpdate,
    RSVPIn,
)
from ...services import events as service

router = APIRouter(prefix="/events", tags=["events"])


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


@router.get("", response_model=EventsOut)
async def list_events(
    user: CurrentUser,
    session: SessionDep,
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
    circles: Annotated[list[UUID] | None, Query()] = None,
) -> EventsOut:
    now = datetime.now(UTC)
    starts_from = _as_utc(date_from) if date_from else now - timedelta(days=1)
    starts_to = _as_utc(date_to) if date_to else now + timedelta(days=365)

    return EventsOut(
        events=await service.list_events(
            session, user, starts_from, starts_to, circles or None
        )
    )


@router.post("", response_model=EventOut, status_code=201)
async def create_event(
    payload: EventCreate, user: CurrentUser, session: SessionDep
) -> EventOut:
    return await service.create_event(session, user, payload)


@router.get("/{event_id}", response_model=EventOut)
async def get_event(event_id: UUID, user: CurrentUser, session: SessionDep) -> EventOut:
    return await service.get_event_detail(session, user, event_id)


@router.patch("/{event_id}", response_model=EventOut)
async def update_event(
    event_id: UUID,
    payload: EventUpdate,
    user: CurrentUser,
    session: SessionDep,
) -> EventOut:
    return await service.update_event(session, user, event_id, payload)


@router.delete("/{event_id}")
async def delete_event(event_id: UUID, user: CurrentUser, session: SessionDep) -> dict:
    await service.delete_event(session, user, event_id)
    return {"ok": True}


@router.post("/{event_id}/rsvp", response_model=EventOut)
async def rsvp(
    event_id: UUID,
    payload: RSVPIn,
    user: CurrentUser,
    session: SessionDep,
) -> EventOut:
    return await service.rsvp(session, user, event_id, payload.status)


@router.get("/{event_id}/comments", response_model=CommentsOut)
async def list_comments(
    event_id: UUID, user: CurrentUser, session: SessionDep
) -> CommentsOut:
    return CommentsOut(comments=await service.list_comments(session, user, event_id))


@router.post("/{event_id}/comments", response_model=CommentOut, status_code=201)
async def add_comment(
    event_id: UUID,
    payload: CommentIn,
    user: CurrentUser,
    session: SessionDep,
) -> CommentOut:
    return await service.add_comment(session, user, event_id, payload.text)
