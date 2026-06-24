"""Typed exceptions mapped to HTTP error envelope."""

from fastapi import HTTPException, status


class AppError(HTTPException):
    """Base app error with code + envelope shape."""

    code: str = "INTERNAL_ERROR"
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(
            status_code=self.status_code,
            detail={
                "error": {
                    "code": self.code,
                    "message": message,
                    "details": details or {},
                }
            },
        )


class AuthError(AppError):
    code = "UNAUTHENTICATED"
    status_code = status.HTTP_401_UNAUTHORIZED


class PermissionDenied(AppError):
    code = "PERMISSION_DENIED"
    status_code = status.HTTP_403_FORBIDDEN


class NotFound(AppError):
    code = "NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND


class Conflict(AppError):
    code = "CONFLICT"
    status_code = status.HTTP_409_CONFLICT


class ValidationFailed(AppError):
    code = "VALIDATION_ERROR"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class RateLimited(AppError):
    code = "RATE_LIMITED"
    status_code = status.HTTP_429_TOO_MANY_REQUESTS


class IntegrationError(AppError):
    code = "INTEGRATION_ERROR"
    status_code = status.HTTP_502_BAD_GATEWAY


class IntegrationTimeout(AppError):
    code = "INTEGRATION_TIMEOUT"
    status_code = status.HTTP_504_GATEWAY_TIMEOUT


class LLMError(AppError):
    code = "LLM_ERROR"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
