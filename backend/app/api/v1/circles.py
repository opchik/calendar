from uuid import UUID

from fastapi import APIRouter

from ...deps import CurrentUser, SessionDep
from ...models import Circle
from ...schemas import CircleIn, CircleOut, CircleUpdate
from ...services import circles as service

router = APIRouter(prefix="/circles", tags=["circles"])


def _out(circle: Circle) -> CircleOut:
    return CircleOut(
        id=circle.id,
        name=circle.name,
        color=circle.color,
        position=circle.position,
    )


@router.get("", response_model=list[CircleOut])
async def list_circles(user: CurrentUser, session: SessionDep) -> list[CircleOut]:
    return [_out(circle) for circle in await service.list_circles(session, user)]


@router.post("", response_model=CircleOut, status_code=201)
async def create_circle(
    payload: CircleIn, user: CurrentUser, session: SessionDep
) -> CircleOut:
    return _out(await service.create_circle(session, user, payload))


@router.patch("/{circle_id}", response_model=CircleOut)
async def update_circle(
    circle_id: UUID, payload: CircleUpdate, user: CurrentUser, session: SessionDep
) -> CircleOut:
    return _out(await service.update_circle(session, user, circle_id, payload))


@router.delete("/{circle_id}")
async def delete_circle(
    circle_id: UUID, user: CurrentUser, session: SessionDep
) -> dict:
    await service.delete_circle(session, user, circle_id)
    return {"ok": True}
