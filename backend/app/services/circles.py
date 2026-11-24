from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Circle, Event, User
from ..schemas import CircleIn, CircleUpdate


async def list_circles(session: AsyncSession, user: User) -> list[Circle]:
    result = await session.scalars(
        select(Circle)
        .where(Circle.owner_id == user.id)
        .order_by(Circle.position, Circle.name)
    )
    return list(result)


async def create_circle(session: AsyncSession, user: User, payload: CircleIn) -> Circle:
    position = await session.scalar(
        select(func.coalesce(func.max(Circle.position), -1) + 1).where(
            Circle.owner_id == user.id
        )
    )
    circle = Circle(
        owner_id=user.id,
        name=payload.name,
        color=payload.color,
        position=position or 0,
    )
    session.add(circle)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Круг с таким названием уже есть"
        ) from error
    await session.refresh(circle)
    return circle


async def get_owned_circle(
    session: AsyncSession, user: User, circle_id: UUID
) -> Circle:
    circle = await session.scalar(
        select(Circle).where(Circle.id == circle_id, Circle.owner_id == user.id)
    )
    if circle is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Круг не найден")
    return circle


async def update_circle(
    session: AsyncSession, user: User, circle_id: UUID, payload: CircleUpdate
) -> Circle:
    circle = await get_owned_circle(session, user, circle_id)
    data = payload.model_dump(exclude_unset=True)

    if "name" in data and data["name"] is not None:
        circle.name = data["name"].strip()
    if "color" in data and data["color"] is not None:
        circle.color = data["color"]

    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Круг с таким названием уже есть"
        ) from error
    await session.refresh(circle)
    return circle


async def delete_circle(session: AsyncSession, user: User, circle_id: UUID) -> None:
    circle = await get_owned_circle(session, user, circle_id)
    await session.execute(
        update(Event)
        .where(Event.circle_id == circle.id, Event.privacy == "circle")
        .values(privacy="link")
    )
    await session.execute(
        update(Event).where(Event.circle_id == circle.id).values(circle_id=None)
    )
    await session.delete(circle)
    await session.commit()
