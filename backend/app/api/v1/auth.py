from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import delete

from ...config import get_settings
from ...deps import SessionDep
from ...models import Session as UserSession
from ...schemas import TelegramAuthIn
from ...security import InitDataError, hash_token, new_session_token, validate_init_data
from ...services.users import upsert_telegram_user

router = APIRouter(tags=["auth"])

AUTH_ERRORS = {
    "NO_BOT_TOKEN": "Сервер не настроен: не задан BOT_TOKEN",
    "EXPIRED": "Данные входа устарели, переоткройте приложение",
}


@router.post("/auth/telegram")
async def auth_telegram(
    payload: TelegramAuthIn,
    response: Response,
    session: SessionDep,
) -> dict:
    try:
        data = validate_init_data(payload.initData)
    except InitDataError as error:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            AUTH_ERRORS.get(str(error), "Подпись Telegram неверна"),
        ) from error

    settings = get_settings()
    user = await upsert_telegram_user(session, data["user"])

    token = new_session_token()
    session.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(UTC) + timedelta(seconds=settings.session_ttl_sec),
        )
    )
    await session.commit()

    secure = settings.public_url.startswith("https://")
    response.set_cookie(
        "sid",
        token,
        max_age=settings.session_ttl_sec,
        httponly=True,
        secure=secure,
        # None нужен для iframe web.telegram.org; локально оставляем Lax.
        samesite="none" if secure else "lax",
        path="/",
    )
    return {"ok": True}


@router.post("/auth/logout")
async def logout(
    request: Request,
    response: Response,
    session: SessionDep,
) -> dict:
    token = request.cookies.get("sid")
    if token:
        await session.execute(
            delete(UserSession).where(UserSession.token_hash == hash_token(token))
        )
        await session.commit()

    secure = get_settings().public_url.startswith("https://")
    response.delete_cookie(
        "sid",
        path="/",
        secure=secure,
        samesite="none" if secure else "lax",
    )
    return {"ok": True}
