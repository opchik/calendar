from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PACKAGE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = PACKAGE_DIR.parent
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str = "postgresql+asyncpg://calendar:calendar@localhost:5432/calendar"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle: int = 1800

    bot_token: str = ""
    bot_mode: Literal["polling", "webhook"] = "polling"
    bot_username: str | None = None
    app_short_name: str | None = None
    public_url: str = "http://localhost:8000"
    webhook_secret: str = ""

    keycloak_enabled: bool = False
    keycloak_issuer: str = ""
    keycloak_client_id: str = ""
    keycloak_client_secret: str = ""
    keycloak_scopes: str = "openid profile email"
    keycloak_redirect_uri: str = ""
    keycloak_authorization_endpoint: str | None = None
    keycloak_token_endpoint: str | None = None
    keycloak_jwks_uri: str | None = None

    dev_bypass_auth: bool = False
    session_ttl_sec: int = 30 * 24 * 60 * 60
    init_data_max_age_sec: int = 24 * 60 * 60
    reminder_interval_sec: int = 60

    host: str = "0.0.0.0"
    port: int = 8000

    static_dir: Path = ROOT_DIR / "static"
    upload_dir: Path = ROOT_DIR / "data" / "uploads"
    max_cover_mb: int = 5

    @field_validator("public_url", "keycloak_issuer")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @property
    def static_dir_path(self) -> Path:
        return self.static_dir.resolve()

    @property
    def upload_dir_path(self) -> Path:
        return self.upload_dir.resolve()

    @property
    def max_cover_bytes(self) -> int:
        return self.max_cover_mb * 1024 * 1024

    @property
    def is_dev_mode(self) -> bool:
        return self.dev_bypass_auth and not self.public_url.startswith("https://")

    @property
    def effective_webhook_secret(self) -> str:
        if self.webhook_secret:
            return self.webhook_secret
        if self.bot_token:
            return hashlib.sha256(self.bot_token.encode()).hexdigest()[:32]
        return "dev-webhook-secret"

    @property
    def app_url(self) -> str:
        return self.public_url or f"http://localhost:{self.port}"

    @property
    def keycloak_enabled_effective(self) -> bool:
        return bool(
            self.keycloak_enabled and self.keycloak_issuer and self.keycloak_client_id
        )

    @property
    def keycloak_redirect(self) -> str:
        return (
            self.keycloak_redirect_uri
            or f"{self.app_url}/api/v1/auth/keycloak/callback"
        )

    @property
    def secure_cookies(self) -> bool:
        return self.public_url.startswith("https://")

    def share_url(self, event_id: str) -> str:
        if self.bot_username and self.app_short_name:
            return f"https://t.me/{self.bot_username}/{self.app_short_name}?startapp=event_{event_id}"
        return f"{self.app_url}?startapp=event_{event_id}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
