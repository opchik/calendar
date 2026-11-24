from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from urllib.parse import quote

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)

from ..config import Settings, get_settings
from ..services.reminders import reminder_loop

logger = logging.getLogger(__name__)
router = Router()


def _webapp_url(settings: Settings, payload: str | None = None) -> str:
    base = settings.app_url
    if not payload:
        return base
    separator = "&" if "?" in base else "?"
    return f"{base}{separator}startapp={quote(payload)}"


def _app_keyboard(
    settings: Settings, payload: str | None = None
) -> InlineKeyboardMarkup:
    url = _webapp_url(settings, payload)
    if url.startswith("https://"):
        button = InlineKeyboardButton(
            text="Открыть календарь", web_app=WebAppInfo(url=url)
        )
    else:
        button = InlineKeyboardButton(text="Открыть календарь", url=url)
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


@router.message(CommandStart())
async def on_start(message: Message, command: CommandObject) -> None:
    settings = get_settings()
    payload = (
        command.args if command.args and command.args.startswith("event_") else None
    )

    if payload:
        text = (
            "Вас пригласили на событие.\n\n"
            "Откройте карточку, чтобы посмотреть детали и ответить «Иду / Думаю / Не смогу»."
        )
    else:
        text = (
            "Привет! Это социальный календарь.\n\n"
            "Создавайте планы, приглашайте друзей одной ссылкой, "
            "обсуждайте детали и получайте напоминания."
        )

    await message.answer(text, reply_markup=_app_keyboard(settings, payload))


@router.message(F.text & ~F.text.startswith("/"))
async def on_text(message: Message) -> None:
    await message.answer(
        "Откройте календарь кнопкой ниже:",
        reply_markup=_app_keyboard(get_settings()),
    )


@dataclass
class BotRuntime:
    bot: Bot | None = None
    dispatcher: Dispatcher | None = None
    polling_task: asyncio.Task | None = None
    reminder_task: asyncio.Task | None = None


async def _configure_bot(bot: Bot, settings: Settings) -> None:
    try:
        await bot.set_my_commands(
            [BotCommand(command="start", description="Открыть календарь")]
        )
        if settings.public_url.startswith("https://"):
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="Календарь", web_app=WebAppInfo(url=settings.app_url)
                )
            )
    except Exception:
        logger.exception("[bot] не удалось настроить меню")


async def start_runtime(settings: Settings) -> BotRuntime:
    if not settings.bot_token:
        logger.warning("[bot] BOT_TOKEN не задан — бот и напоминания отключены")
        return BotRuntime()

    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    runtime = BotRuntime(bot=bot, dispatcher=dispatcher)

    await _configure_bot(bot, settings)

    if settings.bot_mode == "webhook":
        if settings.public_url:
            url = f"{settings.public_url}/telegram/webhook"
            try:
                await bot.set_webhook(
                    url=url,
                    secret_token=settings.effective_webhook_secret,
                    allowed_updates=["message"],
                    drop_pending_updates=True,
                )
                logger.info("[bot] webhook установлен: %s", url)
            except Exception:
                logger.exception("[bot] не удалось установить webhook")
    else:
        try:
            await bot.delete_webhook(drop_pending_updates=False)
        except Exception:
            logger.exception("[bot] не удалось удалить webhook")
        runtime.polling_task = asyncio.create_task(
            dispatcher.start_polling(
                bot, allowed_updates=["message"], handle_signals=False
            ),
            name="bot-polling",
        )
        logger.info("[bot] режим polling")

    runtime.reminder_task = asyncio.create_task(
        reminder_loop(bot, settings), name="reminders"
    )
    return runtime


async def stop_runtime(runtime: BotRuntime) -> None:
    for task in (runtime.polling_task, runtime.reminder_task):
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    if runtime.bot is not None:
        await runtime.bot.session.close()
