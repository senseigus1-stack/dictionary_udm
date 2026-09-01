import hashlib
import hmac
import json
import secrets
import time
from typing import Annotated
from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, create_access_token
from app.config import get_settings
from app.database import get_session
from app.models import User
from app.schemas import GuestCreate, TelegramAuth, TelegramWebAppAuth, TokenResponse, UserView

router = APIRouter(prefix="/auth", tags=["auth"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/me", response_model=UserView)
async def current_profile(user: CurrentUser) -> User:
    return user


@router.post("/guest", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def create_guest(payload: GuestCreate, session: Session) -> TokenResponse:
    user = User(display_name=payload.display_name)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id), user=user)


@router.post("/telegram", response_model=TokenResponse)
async def authenticate_telegram(
    payload: TelegramAuth,
    session: Session,
    x_bot_secret: Annotated[str | None, Header()] = None,
) -> TokenResponse:
    settings = get_settings()
    if not x_bot_secret or not secrets.compare_digest(x_bot_secret, settings.telegram_bot_secret):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Неверный секрет бота")
    user = await session.scalar(select(User).where(User.telegram_id == payload.telegram_id))
    if user is None:
        user = User(telegram_id=payload.telegram_id, display_name=payload.display_name)
        session.add(user)
    else:
        user.display_name = payload.display_name
    await session.commit()
    await session.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id), user=user)


@router.post("/telegram-webapp", response_model=TokenResponse)
async def authenticate_telegram_webapp(
    payload: TelegramWebAppAuth,
    session: Session,
) -> TokenResponse:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=503, detail="Telegram Web App не настроен")
    values = dict(parse_qsl(payload.init_data, keep_blank_values=True))
    received_hash = values.pop("hash", "")
    data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret_key = hmac.new(
        b"WebAppData", settings.telegram_bot_token.encode(), hashlib.sha256
    ).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    try:
        auth_date = int(values.get("auth_date", "0"))
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Некорректные данные Telegram") from exc
    if (
        not received_hash
        or not hmac.compare_digest(received_hash, expected_hash)
        or abs(time.time() - auth_date) > 3600
    ):
        raise HTTPException(status_code=403, detail="Подпись Telegram не прошла проверку")
    try:
        telegram_user = json.loads(values["user"])
        telegram_id = int(telegram_user["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=403, detail="Пользователь Telegram не найден") from exc
    display_name = (
        " ".join(
            part
            for part in (telegram_user.get("first_name"), telegram_user.get("last_name"))
            if part
        )[:80]
        or "Ученик"
    )
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        user = User(telegram_id=telegram_id, display_name=display_name)
        session.add(user)
    else:
        user.display_name = display_name
    await session.commit()
    await session.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id), user=user)
