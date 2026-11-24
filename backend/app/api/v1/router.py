from fastapi import APIRouter

from . import auth, circles, events, keycloak, system, uploads, users

router = APIRouter()
router.include_router(system.router)
router.include_router(auth.router)
router.include_router(keycloak.router)
router.include_router(users.router)
router.include_router(circles.router)
router.include_router(events.router)
router.include_router(uploads.router)
