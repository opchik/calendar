from __future__ import annotations

import hmac
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from aiogram.types import Update
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from .api.v1.router import router as api_router
from .bot.runtime import start_runtime, stop_runtime
from .config import get_settings
from .db import engine

logging.basicConfig(
    level="INFO",
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()
settings.upload_dir_path.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))

    app.state.bot_runtime = await start_runtime(settings)
    logger.info("[http] http://localhost:%s", settings.port)
    try:
        yield
    finally:
        runtime = app.state.bot_runtime
        if runtime is not None:
            await stop_runtime(runtime)
        await engine.dispose()


app = FastAPI(title="Social Calendar", version="1.0.0", lifespan=lifespan)
app.include_router(api_router, prefix="/api/v1")
app.mount(
    "/uploads",
    StaticFiles(directory=settings.upload_dir_path),
    name="uploads",
)


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return {"status": "ready"}


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request) -> dict:
    runtime = getattr(request.app.state, "bot_runtime", None)
    if runtime is None or runtime.bot is None or runtime.dispatcher is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Bot is disabled")

    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not hmac.compare_digest(secret, settings.effective_webhook_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid secret")

    try:
        update = Update.model_validate(await request.json())
    except Exception as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid update") from error

    await runtime.dispatcher.feed_webhook_update(runtime.bot, update)
    return {"ok": True}


def _static_response(full_path: str) -> FileResponse | JSONResponse:
    root = settings.static_dir_path
    relative = full_path.strip("/")

    if relative and "." in Path(relative).name:
        candidate = (root / relative).resolve()
        if candidate.is_relative_to(root) and candidate.is_file():
            cache = "public, max-age=31536000, immutable"
            return FileResponse(candidate, headers={"Cache-Control": cache})
        return JSONResponse({"detail": "Not found"}, status_code=404)

    index = root / "index.html"
    if index.is_file():
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    return JSONResponse({"detail": "Frontend is not built"}, status_code=404)


@app.get("/", response_model=None)
async def index():
    return _static_response("")


@app.get("/{full_path:path}", response_model=None)
async def spa_fallback(full_path: str):
    if full_path.startswith("api/"):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    if full_path == "telegram/webhook":
        return JSONResponse({"detail": "Method not allowed"}, status_code=405)
    return _static_response(full_path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
