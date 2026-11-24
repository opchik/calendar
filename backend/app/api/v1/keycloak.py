from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse

from ...config import get_settings
from ...deps import SessionDep
from ...models import Session as UserSession
from ...security import hash_token, new_session_token
from ...services import keycloak as service
from ...services.users import upsert_keycloak_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth/keycloak", tags=["auth"])

STATE_COOKIE = "oidc_state"
VERIFIER_COOKIE = "oidc_verifier"
NEXT_COOKIE = "oidc_next"
TEMP_MAX_AGE = 600


def _safe_next(value: str | None) -> str:
    if (
        not value
        or not value.startswith("/")
        or value.startswith("//")
        or "\\" in value
        or any(ord(char) < 32 for char in value)
    ):
        return "/"
    return value


def _set_temp_cookie(response, name: str, value: str, secure: bool) -> None:
    response.set_cookie(
        name,
        value,
        max_age=TEMP_MAX_AGE,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )


def _clear_temp_cookie(response, name: str, secure: bool) -> None:
    response.delete_cookie(name, path="/", secure=secure, samesite="lax")


def _fail(settings, message: str) -> RedirectResponse:
    logger.warning("[keycloak] %s", message)
    response = RedirectResponse(
        f"{settings.app_url}/?auth_error=keycloak", status_code=302
    )
    secure = settings.secure_cookies
    for name in (STATE_COOKIE, VERIFIER_COOKIE, NEXT_COOKIE):
        _clear_temp_cookie(response, name, secure)
    return response


@router.get("/login")
async def keycloak_login(
    next_path: str = Query(default="/", alias="next"),
) -> RedirectResponse:
    settings = get_settings()
    if not settings.keycloak_enabled_effective:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Keycloak не настроен")

    redirect_to = _safe_next(next_path)
    state = service.new_state()
    verifier, challenge = service.pkce_pair()

    try:
        oidc = await service.get_oidc_config(settings)
        location = service.authorization_url(oidc, settings, state, challenge)
    except service.KeycloakError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error

    response = RedirectResponse(location, status_code=302)
    secure = settings.secure_cookies
    _set_temp_cookie(response, STATE_COOKIE, state, secure)
    _set_temp_cookie(response, VERIFIER_COOKIE, verifier, secure)
    _set_temp_cookie(response, NEXT_COOKIE, redirect_to, secure)
    return response


@router.get("/callback")
async def keycloak_callback(
    request: Request,
    session: SessionDep,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
) -> RedirectResponse:
    settings = get_settings()
    if not settings.keycloak_enabled_effective:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Keycloak не настроен")

    expected_state = request.cookies.get(STATE_COOKIE)
    verifier = request.cookies.get(VERIFIER_COOKIE)
    next_path = _safe_next(request.cookies.get(NEXT_COOKIE))

    if not code or not state or not expected_state or not verifier:
        return _fail(settings, "callback без code/state/verifier")
    if not secrets.compare_digest(state, expected_state):
        return _fail(settings, "state не совпадает")

    try:
        claims = await service.exchange_code(settings, code, verifier)
        user = await upsert_keycloak_user(session, claims)
    except Exception as error:
        logger.exception("[keycloak] ошибка входа")
        return _fail(settings, str(error))

    token = new_session_token()
    session.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(UTC) + timedelta(seconds=settings.session_ttl_sec),
        )
    )
    await session.commit()

    response = RedirectResponse(f"{settings.app_url}{next_path}", status_code=302)
    secure = settings.secure_cookies
    response.set_cookie(
        "sid",
        token,
        max_age=settings.session_ttl_sec,
        httponly=True,
        secure=secure,
        samesite="none" if secure else "lax",
        path="/",
    )
    for name in (STATE_COOKIE, VERIFIER_COOKIE, NEXT_COOKIE):
        _clear_temp_cookie(response, name, secure)
    return response
