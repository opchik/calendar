from __future__ import annotations

import asyncio
import base64
import hashlib
import secrets
import time

import httpx
import jwt

from ..config import Settings

_discovery_cache: dict[str, tuple[float, dict]] = {}
_jwk_clients: dict[str, jwt.PyJWKClient] = {}

DISCOVERY_TTL_SEC = 3600


class KeycloakError(Exception):
    pass


def pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    return verifier, challenge


def new_state() -> str:
    return secrets.token_urlsafe(32)


async def get_oidc_config(settings: Settings) -> dict:
    if (
        settings.keycloak_authorization_endpoint
        and settings.keycloak_token_endpoint
        and settings.keycloak_jwks_uri
    ):
        return {
            "issuer": settings.keycloak_issuer,
            "authorization_endpoint": settings.keycloak_authorization_endpoint,
            "token_endpoint": settings.keycloak_token_endpoint,
            "jwks_uri": settings.keycloak_jwks_uri,
        }

    cached = _discovery_cache.get(settings.keycloak_issuer)
    if cached and time.monotonic() - cached[0] < DISCOVERY_TTL_SEC:
        return cached[1]

    url = f"{settings.keycloak_issuer}/.well-known/openid-configuration"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()
            config = response.json()
    except Exception as error:
        raise KeycloakError(
            f"Не удалось получить OIDC-конфиг Keycloak: {error}"
        ) from error

    if not config.get("authorization_endpoint") or not config.get("token_endpoint"):
        raise KeycloakError("Keycloak вернул неполный OIDC-конфиг")

    _discovery_cache[settings.keycloak_issuer] = (time.monotonic(), config)
    return config


def authorization_url(
    config: dict, settings: Settings, state: str, challenge: str
) -> str:
    params = {
        "client_id": settings.keycloak_client_id,
        "redirect_uri": settings.keycloak_redirect,
        "response_type": "code",
        "scope": settings.keycloak_scopes,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return str(httpx.URL(config["authorization_endpoint"]).copy_merge_params(params))


async def exchange_code(settings: Settings, code: str, verifier: str) -> dict:
    config = await get_oidc_config(settings)
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.keycloak_redirect,
        "client_id": settings.keycloak_client_id,
        "code_verifier": verifier,
    }
    if settings.keycloak_client_secret:
        payload["client_secret"] = settings.keycloak_client_secret

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(config["token_endpoint"], data=payload)
            response.raise_for_status()
            token_data = response.json()
    except Exception as error:
        raise KeycloakError(f"Keycloak не обменял код на токены: {error}") from error

    id_token = token_data.get("id_token")
    if not id_token:
        raise KeycloakError("Keycloak не вернул id_token")

    return await validate_id_token(settings, config, id_token)


async def validate_id_token(settings: Settings, config: dict, id_token: str) -> dict:
    jwks_uri = config.get("jwks_uri")
    if not jwks_uri:
        raise KeycloakError("В OIDC-конфиге нет jwks_uri")

    def _decode() -> dict:
        key_client = _jwk_clients.get(jwks_uri)
        if key_client is None:
            key_client = jwt.PyJWKClient(jwks_uri, cache_keys=True)
            _jwk_clients[jwks_uri] = key_client

        signing_key = key_client.get_signing_key_from_jwt(id_token)
        return jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256", "RS384", "RS512", "ES256", "ES384"],
            audience=settings.keycloak_client_id,
            issuer=settings.keycloak_issuer,
            options={"require": ["exp", "iat", "sub"]},
        )

    try:
        return await asyncio.to_thread(_decode)
    except Exception as error:
        raise KeycloakError(f"Неверный id_token Keycloak: {error}") from error
