from fastapi import APIRouter

from ...deps import CurrentUser
from ...schemas import MeOut
from ...services.events import user_brief

router = APIRouter(tags=["users"])


@router.get("/me", response_model=MeOut)
async def me(user: CurrentUser) -> MeOut:
    return MeOut(user=user_brief(user), timezone=user.timezone)
