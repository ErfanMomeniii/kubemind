"""Auth dependencies: current user extraction from JWT."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthError
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models import User


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_session),
) -> User:
    if authorization is None or not authorization.startswith("Bearer "):
        raise AuthError("missing bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_access_token(token)
    except Exception as exc:
        raise AuthError("invalid or expired token") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise AuthError("invalid token payload")

    user = await session.get(User, UUID(user_id))
    if user is None or user.status != "active":
        raise AuthError("user not found or inactive")
    if user.deleted_at is not None:
        raise AuthError("user deleted")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_session)]
