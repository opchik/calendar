from fastapi import APIRouter

from ...config import get_settings
from ...schemas import ConfigOut

router = APIRouter(tags=["system"])


@router.get("/config", response_model=ConfigOut)
async def get_config() -> ConfigOut:
    settings = get_settings()
    return ConfigOut(
        dev=settings.is_dev_mode,
        botUsername=settings.bot_username,
        appShortName=settings.app_short_name,
        publicUrl=settings.app_url,
        keycloakEnabled=settings.keycloak_enabled_effective,
    )
