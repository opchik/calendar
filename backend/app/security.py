from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from urllib.parse import parse_qsl

from .config import get_settings


class InitDataError(Exception):
    pass


def validate_init_data(raw: str | None) -> dict:
    settings = get_settings()

    if not raw:
        raise InitDataError("EMPTY")
    if not settings.bot_token:
        raise InitDataError("NO_BOT_TOKEN")

    pairs = parse_qsl(raw, keep_blank_values=True)
    params: dict[str, str] = {}
    for key, value in pairs:
        params.setdefault(key, value)

    received_hash = params.get("hash")
    if not received_hash:
        raise InitDataError("NO_HASH")

    data_check_string = "\n".join(
        f"{key}={value}"
        for key, value in sorted(
            (key, value) for key, value in pairs if key not in {"hash", "signature"}
        )
    )
    secret_key = hmac.new(
        b"WebAppData", settings.bot_token.encode("utf-8"), hashlib.sha256
    ).digest()
    expected = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).digest()

    try:
        received = bytes.fromhex(received_hash)
    except ValueError as error:
        raise InitDataError("BAD_HASH") from error

    if not hmac.compare_digest(received, expected):
        raise InitDataError("BAD_HASH")

    try:
        auth_date = int(params["auth_date"])
    except (KeyError, ValueError) as error:
        raise InitDataError("NO_AUTH_DATE") from error

    if time.time() - auth_date > settings.init_data_max_age_sec:
        raise InitDataError("EXPIRED")

    try:
        user = json.loads(params.get("user") or "null")
    except json.JSONDecodeError as error:
        raise InitDataError("NO_USER") from error

    if not isinstance(user, dict) or not user.get("id"):
        raise InitDataError("NO_USER")

    return {"user": user, "auth_date": auth_date}


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
