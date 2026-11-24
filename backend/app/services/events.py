from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import get_settings
from ..models import Comment, Event, EventParticipant, User
from ..schemas import (
    CircleOut,
    CommentOut,
    EventCreate,
    EventOut,
    EventUpdate,
    ParticipantOut,
    UserBrief,
)

_EVENT_LOADS = (
    selectinload(Event.owner),
    selectinload(Event.circle),
    selectinload(Event.participants).selectinload(EventParticipant.user),
)


def user_brief(user: User) -> UserBrief:
    return UserBrief(
        id=user.id,
        firstName=user.first_name,
        lastName=user.last_name,
        username=user.username,
        photoUrl=user.photo_url,
    )


def comment_out(comment: Comment) -> CommentOut:
    return CommentOut(
        id=comment.id,
        text=comment.text,
        createdAt=comment.created_at,
        user=user_brief(comment.user),
    )


def event_out(event: Event, user: User, comment_count: int) -> EventOut:
    participants = sorted(
        event.participants,
        key=lambda item: (
            0 if item.role == "owner" else 1,
            (item.user.first_name or item.user.username or "").lower(),
        ),
    )
    my_participation = next(
        (item for item in event.participants if item.user_id == user.id), None
    )

    return EventOut(
        id=event.id,
        title=event.title,
        description=event.description,
        startsAt=event.starts_at,
        locationText=event.location_text,
        locationUrl=event.location_url,
        cover=event.cover,
        privacy=event.privacy,
        circle=(
            CircleOut(
                id=event.circle.id,
                name=event.circle.name,
                color=event.circle.color,
                position=event.circle.position,
            )
            if event.circle
            else None
        ),
        owner=user_brief(event.owner),
        participants=[
            ParticipantOut(
                user=user_brief(item.user),
                status=item.status,
                role=item.role,
            )
            for item in participants
        ],
        myStatus=my_participation.status if my_participation else None,
        myRole=my_participation.role if my_participation else None,
        isOwner=event.owner_id == user.id,
        shareUrl=get_settings().share_url(str(event.id)),
        commentCount=comment_count,
        createdAt=event.created_at,
    )


async def _comment_count(session: AsyncSession, event_id: UUID) -> int:
    return (
        await session.scalar(
            select(func.count(Comment.id)).where(Comment.event_id == event_id)
        )
    ) or 0


async def _load_event(session: AsyncSession, event_id: UUID) -> Event | None:
    return await session.scalar(
        select(Event)
        .where(Event.id == event_id)
        .options(*_EVENT_LOADS)
        .execution_options(populate_existing=True)
    )


async def list_events(
    session: AsyncSession,
    user: User,
    starts_from: datetime,
    starts_to: datetime,
    circle_ids: list[UUID] | None = None,
) -> list[EventOut]:
    participant_ids = select(EventParticipant.event_id).where(
        EventParticipant.user_id == user.id,
        EventParticipant.status.in_(("going", "maybe")),
    )
    comment_count = (
        select(func.count(Comment.id))
        .where(Comment.event_id == Event.id)
        .correlate(Event)
        .scalar_subquery()
    )

    stmt = (
        select(Event, comment_count)
        .where(
            Event.starts_at >= starts_from,
            Event.starts_at <= starts_to,
            or_(Event.owner_id == user.id, Event.id.in_(participant_ids)),
        )
        .options(*_EVENT_LOADS)
        .order_by(Event.starts_at)
    )

    if circle_ids:
        stmt = stmt.where(
            or_(Event.circle_id.in_(circle_ids), Event.circle_id.is_(None))
        )

    rows = (await session.execute(stmt)).all()
    return [event_out(event, user, count or 0) for event, count in rows]


async def get_accessible_event(
    session: AsyncSession, user: User, event_id: UUID
) -> Event:
    event = await _load_event(session, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Событие не найдено")

    is_participant = any(item.user_id == user.id for item in event.participants)
    if (
        event.owner_id == user.id
        or is_participant
        or event.privacy in {"link", "circle"}
    ):
        return event

    raise HTTPException(status.HTTP_404_NOT_FOUND, "Событие не найдено")


async def get_event_detail(
    session: AsyncSession, user: User, event_id: UUID
) -> EventOut:
    event = await get_accessible_event(session, user, event_id)
    return event_out(event, user, await _comment_count(session, event.id))


async def _validate_circle(
    session: AsyncSession, user: User, circle_id: UUID | None
) -> None:
    if circle_id is None:
        return
    from .circles import get_owned_circle

    await get_owned_circle(session, user, circle_id)


async def create_event(
    session: AsyncSession, user: User, payload: EventCreate, cover: str | None = None
) -> EventOut:
    circle_id = payload.circleId
    await _validate_circle(session, user, circle_id)

    if payload.privacy == "circle" and circle_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Для приватности «Для круга» выберите круг",
        )

    location_text = payload.locationText
    location_url = payload.locationUrl
    if (
        not location_url
        and location_text
        and location_text.startswith(("http://", "https://"))
    ):
        location_url = location_text
        location_text = None

    event = Event(
        owner_id=user.id,
        circle_id=circle_id,
        title=payload.title,
        description=payload.description,
        starts_at=payload.startsAt,
        location_text=location_text,
        location_url=location_url,
        cover=cover or payload.cover,
        privacy=payload.privacy,
    )
    event.participants.append(
        EventParticipant(user_id=user.id, status="going", role="owner")
    )
    session.add(event)
    await session.commit()

    loaded = await _load_event(session, event.id)
    return event_out(loaded, user, 0)


async def update_event(
    session: AsyncSession, user: User, event_id: UUID, payload: EventUpdate
) -> EventOut:
    event = await get_accessible_event(session, user, event_id)
    if event.owner_id != user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Менять событие может только автор"
        )

    data = payload.model_dump(exclude_unset=True)
    if "circleId" in data:
        await _validate_circle(session, user, data["circleId"])
        event.circle_id = data["circleId"]

    if "startsAt" in data and data["startsAt"] is not None:
        event.starts_at = data["startsAt"]
    if "title" in data and data["title"] is not None:
        event.title = data["title"].strip()
    if "description" in data:
        event.description = data["description"]
    if "locationText" in data:
        event.location_text = data["locationText"]
    if "locationUrl" in data:
        event.location_url = data["locationUrl"]
    if "cover" in data and data["cover"] is not None:
        event.cover = data["cover"]
    if "privacy" in data and data["privacy"] is not None:
        event.privacy = data["privacy"]

    if event.privacy == "circle" and event.circle_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Для приватности «Для круга» выберите круг",
        )

    await session.commit()
    loaded = await _load_event(session, event.id)
    return event_out(loaded, user, await _comment_count(session, event.id))


async def delete_event(session: AsyncSession, user: User, event_id: UUID) -> None:
    event = await get_accessible_event(session, user, event_id)
    if event.owner_id != user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Удалять событие может только автор"
        )

    await session.delete(event)
    await session.commit()


async def rsvp(
    session: AsyncSession, user: User, event_id: UUID, new_status: str
) -> EventOut:
    event = await get_accessible_event(session, user, event_id)
    participation = next(
        (item for item in event.participants if item.user_id == user.id), None
    )

    if participation is None:
        participation = EventParticipant(
            event_id=event.id,
            user_id=user.id,
            status=new_status,
            role="guest",
        )
        session.add(participation)
    elif participation.role != "owner":
        participation.status = new_status

    await session.commit()
    loaded = await _load_event(session, event.id)
    return event_out(loaded, user, await _comment_count(session, event.id))


async def list_comments(
    session: AsyncSession, user: User, event_id: UUID
) -> list[CommentOut]:
    event = await get_accessible_event(session, user, event_id)
    comments = await session.scalars(
        select(Comment)
        .where(Comment.event_id == event.id)
        .options(selectinload(Comment.user))
        .order_by(Comment.created_at)
    )
    return [comment_out(comment) for comment in comments]


async def add_comment(
    session: AsyncSession, user: User, event_id: UUID, text: str
) -> CommentOut:
    event = await get_accessible_event(session, user, event_id)
    comment = Comment(event_id=event.id, user_id=user.id, text=text)
    session.add(comment)
    await session.commit()

    loaded = await session.scalar(
        select(Comment)
        .where(Comment.id == comment.id)
        .options(selectinload(Comment.user))
    )
    return comment_out(loaded)
