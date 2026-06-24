"""Auth service: register, login, refresh."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthError, Conflict
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models import Organization, User
from app.schemas.auth import AuthResponse, LoginRequest, TokenResponse, UserCreate, UserResponse


async def register(input: UserCreate, session: AsyncSession) -> AuthResponse:
    """Create user + org, return tokens."""
    existing = await session.scalar(select(User).where(User.email == input.email))
    if existing is not None:
        raise Conflict("email already registered", {"email": input.email})

    org = Organization(name=input.org_name, slug=_slugify(input.org_name))
    session.add(org)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise Conflict("org slug already taken", {"org_name": input.org_name}) from exc

    user = User(
        email=input.email,
        password_hash=hash_password(input.password),
        name=input.name,
        org_id=org.id,
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise Conflict("email already registered", {"email": input.email}) from exc

    await session.commit()
    await session.refresh(user)

    tokens = _issue_tokens(str(user.id), settings_token_expiry())
    return AuthResponse(user=UserResponse.model_validate(user), tokens=tokens)


async def login(input: LoginRequest, session: AsyncSession) -> AuthResponse:
    user = await session.scalar(select(User).where(User.email == input.email))
    if user is None or user.password_hash is None:
        raise AuthError("invalid email or password")
    if not verify_password(input.password, user.password_hash):
        raise AuthError("invalid email or password")
    if user.status != "active":
        raise AuthError("account is not active")

    user.last_login_at = datetime.now(timezone.utc)
    await session.commit()

    tokens = _issue_tokens(str(user.id), settings_token_expiry())
    return AuthResponse(user=UserResponse.model_validate(user), tokens=tokens)


async def refresh(refresh_token: str, session: AsyncSession) -> TokenResponse:
    from app.core.security import decode_refresh_token

    try:
        payload = decode_refresh_token(refresh_token)
    except Exception as exc:
        raise AuthError("invalid refresh token") from exc

    user_id = payload["sub"]
    user = await session.get(User, UUID(user_id))
    if user is None or user.status != "active":
        raise AuthError("user not found or inactive")

    return _issue_tokens(str(user.id), settings_token_expiry())


def _issue_tokens(user_id: str, expires_in: int) -> TokenResponse:
    access = create_access_token(user_id)
    refresh_tok = create_refresh_token(user_id)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh_tok,
        expires_in=expires_in,
    )


def settings_token_expiry() -> int:
    from app.core.config import settings

    return settings.jwt_access_expire_minutes * 60


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace("_", "-")[:64]
