from datetime import UTC, datetime

import httpx
import structlog
from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import func, select

from app.config import get_settings
from app.database import SessionFactory
from app.models import User, UserCard

settings = get_settings()
logger = structlog.get_logger()


async def send_due_reminders(_ctx: dict) -> None:
    if not settings.telegram_bot_token:
        logger.info("reminders_skipped", reason="telegram token is empty")
        return
    now = datetime.now(UTC)
    async with SessionFactory() as session:
        rows = list(
            (
                await session.execute(
                    select(User.telegram_id, func.count(UserCard.entry_id))
                    .join(UserCard, UserCard.user_id == User.id)
                    .where(
                        User.telegram_id.is_not(None),
                        User.reminder_enabled.is_(True),
                        UserCard.due_at <= now,
                    )
                    .group_by(User.telegram_id)
                )
            ).all()
        )
    endpoint = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=10) as client:
        for telegram_id, due_count in rows:
            response = await client.post(
                endpoint,
                json={
                    "chat_id": telegram_id,
                    "text": (
                        f"Ӟечбур! На сегодня созрело карточек: {due_count}. "
                        "Пять минут — и серия продолжается 🌿"
                    ),
                    "reply_markup": {
                        "inline_keyboard": [
                            [
                                {
                                    "text": "Учить слова",
                                    "web_app": {"url": settings.telegram_webapp_url},
                                }
                            ]
                        ]
                    },
                },
            )
            if response.is_error:
                logger.warning(
                    "reminder_failed", telegram_id=telegram_id, status=response.status_code
                )


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    cron_jobs = [cron(send_due_reminders, hour=16, minute=0, run_at_startup=False)]
    max_jobs = 10
    job_timeout = 120
