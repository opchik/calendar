from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Circle, User

DEFAULT_CIRCLES = (
    ("Семья", "#ef4444"),
    ("Друзья", "#3b82f6"),
    ("Личное", "#8b5cf6"),
    ("Работа", "#f59e0b"),
)


async def ensure_default_circles(session: AsyncSession, user: User) -> None:
    count = await session.scalar(
        select(func.count(Circle.id)).where(Circle.owner_id == user.id)
    )
    if count:
        return

    for position, (name, color) in enumerate(DEFAULT_CIRCLES):
        session.add(Circle(owner_id=user.id, name=name, color=color, position=position))
    await session.flush()


async def upsert_telegram_user(session: AsyncSession, tg_user: dict) -> User:
    telegram_id = int(tg_user["id"])
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    now = datetime.now(UTC)

    if user is None:
        user = User(
            telegram_id=telegram_id,
            first_name=tg_user.get("first_name"),
            last_name=tg_user.get("last_name"),
            username=tg_user.get("username"),
            photo_url=tg_user.get("photo_url"),
            language_code=tg_user.get("language_code"),
            last_seen_at=now,
        )
        session.add(user)
        await session.flush()
        await ensure_default_circles(session, user)
    else:
        user.first_name = tg_user.get("first_name")
        user.last_name = tg_user.get("last_name")
        user.username = tg_user.get("username")
        user.photo_url = tg_user.get("photo_url")
        user.language_code = tg_user.get("language_code")
        user.last_seen_at = now
        await ensure_default_circles(session, user)

    await session.commit()
    await session.refresh(user)
    return user


async def upsert_keycloak_user(session: AsyncSession, claims: dict) -> User:
    subject = claims.get("sub")
    if not subject:
        raise ValueError("Keycloak не вернул sub")

    user = await session.scalar(select(User).where(User.keycloak_sub == str(subject)))
    now = datetime.now(UTC)

    given_name = claims.get("given_name")
    family_name = claims.get("family_name")
    if not given_name and claims.get("name"):
        parts = str(claims["name"]).split(maxsplit=1)
        given_name = parts[0]
        family_name = parts[1] if len(parts) > 1 else family_name

    email = claims.get("email")
    username = claims.get("preferred_username") or (
        email.split("@")[0] if email else None
    )
    photo_url = claims.get("picture")
    language = claims.get("locale")

    if user is None:
        user = User(
            keycloak_sub=str(subject),
            email=email,
            username=username,
            first_name=given_name,
            last_name=family_name,
            photo_url=photo_url,
            language_code=language,
            last_seen_at=now,
        )
        session.add(user)
        await session.flush()
        await ensure_default_circles(session, user)
    else:
        user.email = email
        user.username = username
        user.first_name = given_name
        user.last_name = family_name
        user.photo_url = photo_url
        user.language_code = language
        user.last_seen_at = now
        await ensure_default_circles(session, user)

    await session.commit()
    await session.refresh(user)
    return user


async def get_or_create_dev_user(session: AsyncSession) -> User:
    return await upsert_telegram_user(
        session,
        {
            "id": 1,
            "first_name": "друг",
            "last_name": None,
            "username": "dev",
            "language_code": "ru",
        },
    )
