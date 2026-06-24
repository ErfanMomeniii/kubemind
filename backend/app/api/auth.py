"""Auth routes: register, login, refresh."""

from fastapi import APIRouter

from app.api.auth_deps import DbSession
from app.schemas.auth import AuthResponse, LoginRequest, RefreshRequest, TokenResponse, UserCreate
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(input: UserCreate, session: DbSession) -> AuthResponse:
    return await auth_service.register(input, session)


@router.post("/login", response_model=AuthResponse)
async def login(input: LoginRequest, session: DbSession) -> AuthResponse:
    return await auth_service.login(input, session)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(input: RefreshRequest, session: DbSession) -> TokenResponse:
    return await auth_service.refresh(input.refresh_token, session)
