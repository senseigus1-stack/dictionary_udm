import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.models import User

bearer = HTTPBearer(auto_error=False)
settings = get_settings()


def create_access_token(user_id: uuid.UUID) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(days=settings.access_token_days),
        "aud": "zechbur",
        "iss": "zechbur-api",
    }
    return jwt.encode(payload, settings.app_secret, algorithm="HS256")


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Нужна авторизация",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.app_secret,
            algorithms=["HS256"],
            audience="zechbur",
            issuer="zechbur-api",
        )
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise unauthorized from exc
    user = await session.get(User, user_id)
    if user is None:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
