from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..config import Settings
from ..db import SessionLocal
from ..models import Event, EventParticipant, ReminderLog

logger = logging.getLogger(__name__)

WINDOWS = (
    ("24h", 24, 2, "через 24 часа"),
    ("2h", 2, 0, "через 2 часа"),
)


def _event_url(settings: Settings, event_id) -> str:
    base = settings.app_url
    separator = "&" if "?" in base else "?"
    return f"{base}{separator}startapp=event_{event_id}"


def _keyboard(settings: Settings, event_id) -> InlineKeyboardMarkup:
    url = _event_url(settings, event_id)
    if url.startswith("https://"):
        button = InlineKeyboardButton(
            text="Открыть событие", web_app=WebAppInfo(url=url)
        )
    else:
        button = InlineKeyboardButton(text="Открыть событие", url=url)
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


def _format_time(event: Event, user_timezone: str) -> str:
    try:
        tz = ZoneInfo(user_timezone or "Europe/Moscow")
    except ZoneInfoNotFoundError:
        tz = UTC
    local = event.starts_at.astimezone(tz)
    return local.strftime("%d.%m в %H:%M")


async def send_due_reminders(bot: Bot, settings: Settings) -> None:
    now = datetime.now(UTC)

    async with SessionLocal() as session:
        for kind, upper_hours, lower_hours, label in WINDOWS:
            events = (
                await session.scalars(
                    select(Event)
                    .where(
                        Event.starts_at > now + timedelta(hours=lower_hours),
                        Event.starts_at <= now + timedelta(hours=upper_hours),
                    )
                    .options(
                        selectinload(Event.participants).selectinload(
                            EventParticipant.user
                        )
                    )
                )
            ).all()

            for event in events:
                for participant in event.participants:
                    if participant.status != "going":
                        continue
                    user = participant.user

                    already_sent = await session.scalar(
                        select(ReminderLog.id).where(
                            ReminderLog.event_id == event.id,
                            ReminderLog.user_id == user.id,
                            ReminderLog.kind == kind,
                        )
                    )
                    if already_sent:
                        continue

                    location = event.location_text or event.location_url or ""
                    text = f"🔔 Напоминание {label}\n\n{event.title}\n{_format_time(event, user.timezone)}"
                    if location:
                        text += f"\n{location}"

                    try:
                        await bot.send_message(
                            user.telegram_id,
                            text,
                            reply_markup=_keyboard(settings, event.id),
                        )
                    except Exception:
                        logger.exception(
                            "[reminders] не удалось отправить %s пользователю %s",
                            event.id,
                            user.telegram_id,
                        )

                    session.add(
                        ReminderLog(event_id=event.id, user_id=user.id, kind=kind)
                    )

            await session.commit()


async def reminder_loop(bot: Bot, settings: Settings) -> None:
    while True:
        try:
            await send_due_reminders(bot, settings)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("[reminders] ошибка")
        await asyncio.sleep(settings.reminder_interval_sec)
