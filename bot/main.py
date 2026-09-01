import asyncio
import html
import logging

import httpx
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)
from app.config import get_settings

settings = get_settings()
router = Router()


class ApiClient:
    def __init__(self) -> None:
        self.base_url = settings.api_internal_url.rstrip("/") + "/api/v1"

    async def token_for(self, telegram_id: int, display_name: str) -> str:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{self.base_url}/auth/telegram",
                headers={"X-Bot-Secret": settings.telegram_bot_secret},
                json={"telegram_id": telegram_id, "display_name": display_name},
            )
            response.raise_for_status()
            return response.json()["access_token"]

    async def get(self, path: str, token: str) -> dict | list:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{self.base_url}{path}", headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            return response.json()

    async def post(self, path: str, token: str, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{self.base_url}{path}",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )
            response.raise_for_status()
            return response.json()


api = ApiClient()


def display_name(event: Message | CallbackQuery) -> str:
    user = event.from_user
    if user is None:
        return "Ученик"
    return user.full_name[:80]


async def user_token(event: Message | CallbackQuery) -> str:
    if event.from_user is None:
        raise RuntimeError("Telegram user is missing")
    return await api.token_for(event.from_user.id, display_name(event))


def webapp_keyboard(label: str = "Открыть приложение") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=label,
                    web_app=WebAppInfo(url=settings.telegram_webapp_url),
                )
            ]
        ]
    )


@router.message(CommandStart())
async def start(message: Message) -> None:
    await user_token(message)
    await message.answer(
        "<b>Ӟечбур!</b> 🌿\n\n"
        "Я помогу учить удмуртские слова маленькими порциями: сначала вспомнить, "
        "потом увидеть живое значение, а нужные карточки вернутся вовремя.\n\n"
        "Команды: /learn — слова, /grammar — правила, /stats — прогресс.",
        reply_markup=webapp_keyboard("Начать маршрут"),
    )


@router.message(Command("learn"))
async def learn(message: Message) -> None:
    await send_next_card(message, message)


async def send_next_card(message: Message, actor: Message | CallbackQuery) -> None:
    try:
        token = await user_token(actor)
        study = await api.get("/learn/session?limit=1", token)
        cards = study["cards"]
        if not cards:
            await message.answer(
                "На сегодня всё повторено. Можно открыть грамматику "
                "или взять новую сессию в приложении.",
                reply_markup=webapp_keyboard(),
            )
            return
        card = cards[0]
        entry = card["entry"]
        buttons = [
            [
                InlineKeyboardButton(
                    text=option["text"][:60],
                    callback_data=f"answer:{entry['id']}:{option['entry_id']}",
                )
            ]
            for option in card["options"]
        ]
        await message.answer(
            f"Что означает <b>{html.escape(entry['word'])}</b>?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        )
    except httpx.HTTPError:
        await message.answer("Сервис пока не отвечает. Попробуйте ещё раз через минуту.")


@router.callback_query(F.data.startswith("answer:"))
async def answer(callback: CallbackQuery) -> None:
    if callback.data is None or callback.message is None:
        return
    _, entry_id_raw, selected_id_raw = callback.data.split(":", 2)
    entry_id = int(entry_id_raw)
    correct = entry_id == int(selected_id_raw)
    token = await user_token(callback)
    result = await api.post(
        "/learn/review",
        token,
        {"entry_id": entry_id, "correct": correct, "confidence": 2},
    )
    entry = await api.get(f"/dictionary/{entry_id}", token)
    await callback.answer("Верно!" if correct else "Запомним на следующий раз")
    await callback.message.edit_reply_markup(reply_markup=None)
    example = entry["examples"][0] if entry["examples"] else entry["definition"][:400]
    await callback.message.answer(
        f"{'✅' if correct else '🌱'} <b>{html.escape(entry['word'])}</b> — "
        f"{html.escape(entry['gloss'])}\n\n"
        f"<i>{html.escape(example)}</i>\n\n"
        f"+{result['xp_earned']} XP",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Следующее слово →", callback_data="next")]]
        ),
    )


@router.callback_query(F.data == "next")
async def next_card(callback: CallbackQuery) -> None:
    if callback.message is None:
        return
    await callback.answer()
    await send_next_card(callback.message, callback)


@router.message(Command("stats"))
async def stats(message: Message) -> None:
    token = await user_token(message)
    data = await api.get("/learn/stats", token)
    await message.answer(
        "<b>Ваш ритм</b>\n\n"
        f"🔥 Серия: <b>{data['streak']}</b> дн.\n"
        f"🌿 Изучено: <b>{data['learned']}</b> слов\n"
        f"✓ Точность: <b>{data['accuracy_30d']}%</b>\n"
        f"✦ Опыт: <b>{data['xp']} XP</b>\n"
        f"◇ Сегодня: <b>{data['reviewed_today']}/{data['daily_goal']}</b>",
        reply_markup=webapp_keyboard("Посмотреть маршрут"),
    )


@router.message(Command("grammar"))
async def grammar(message: Message) -> None:
    token = await user_token(message)
    lessons = await api.get("/grammar/lessons", token)
    completed = sum(lesson["progress"]["completed"] for lesson in lessons)
    next_lesson = next(
        (lesson for lesson in lessons if not lesson["progress"]["completed"]), lessons[-1]
    )
    await message.answer(
        f"<b>Грамматическая тропа: {completed}/{len(lessons)}</b>\n\n"
        f"Следующий шаг — <b>{html.escape(next_lesson['title'])}</b>.\n"
        f"{html.escape(next_lesson['summary'])}",
        reply_markup=webapp_keyboard("Открыть урок"),
    )


async def main() -> None:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required for the bot process")
    logging.basicConfig(level=logging.INFO)
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await bot.set_my_commands(
        [
            BotCommand(command="learn", description="Учить слова"),
            BotCommand(command="grammar", description="Грамматика"),
            BotCommand(command="stats", description="Мой прогресс"),
        ]
    )
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
