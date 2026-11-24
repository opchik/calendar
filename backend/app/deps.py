from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .config import get_settings
from .db import get_session
from .models import Session as UserSession
from .models import User
from .security import hash_token
from .services.users import get_or_create_dev_user

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(request: Request, session: SessionDep) -> User:
    token = request.cookies.get("sid")
    settings = get_settings()

    if token:
        row = await session.scalar(
            select(UserSession)
            .where(UserSession.token_hash == hash_token(token))
            .options(selectinload(UserSession.user))
        )
        if row is not None:
            expires_at = row.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at > datetime.now(UTC):
                return row.user

    if settings.is_dev_mode:
        return await get_or_create_dev_user(session)

    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Не авторизован")


CurrentUser = Annotated[User, Depends(get_current_user)]
