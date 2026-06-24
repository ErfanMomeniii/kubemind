"""Base integration client: circuit breaker, retry, timeout, async.

All integration clients extend this. See docs/safety.md §10 and
docs/architecture.md §2.4.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.exceptions import IntegrationError, IntegrationTimeout
from app.core.logging import get_logger

log = get_logger()

T = TypeVar("T")


class CircuitBreakerOpen(IntegrationError):
    """Raised when circuit breaker is open — calls fail fast."""


class CircuitBreaker:
    """Simple circuit breaker: closed → open after N failures → half-open after timeout.

    See docs/safety.md §10. Not thread-safe per-instance; use one instance per client.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failures = 0
        self._opened_at: float | None = None
        self._state: str = "closed"  # closed | open | half-open

    @property
    def state(self) -> str:
        if self._state == "open":
            if self._opened_at and (time.monotonic() - self._opened_at) >= self.recovery_timeout:
                self._state = "half-open"
        return self._state

    def record_success(self) -> None:
        self._failures = 0
        self._state = "closed"
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._state = "open"
            self._opened_at = time.monotonic()
            log.warning("circuit_breaker_opened", failures=self._failures)

    def check(self) -> None:
        if self.state == "open":
            raise CircuitBreakerOpen("circuit breaker open — integration failing fast")


class BaseIntegrationClient:
    """Base for integration clients. Provides retry + circuit breaker + timeout.

    Subclasses define `base_url`, `timeout`, and methods that call `_call`.
    """

    base_url: str
    timeout: float = 10.0
    retry_attempts: int = 3

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float | None = None,
        credential_ref: str | None = None,
        breaker: CircuitBreaker | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.credential_ref = credential_ref
        self.breaker = breaker or CircuitBreaker()
        self._timeout = timeout or self.timeout
        self._client: httpx.AsyncClient | None = None

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self._timeout,
                headers=self._auth_headers(),
            )
        return self._client

    def _auth_headers(self) -> dict[str, str]:
        """Override to add auth headers (Bearer, Basic, etc.)."""
        return {}

    async def _call(
        self,
        operation: Callable[[], Awaitable[T]],
        *,
        retry_on: tuple[type[BaseException], ...] = (httpx.HTTPError,),
    ) -> T:
        """Run operation with circuit breaker + retry. Reads not retried on 4xx."""
        self.breaker.check()
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.retry_attempts),
                wait=wait_exponential(multiplier=1, max=8),
                retry=retry_if_exception_type(retry_on),
                reraise=True,
            ):
                with attempt:
                    return await asyncio.wait_for(operation(), timeout=self._timeout)
        except TimeoutError as exc:
            self.breaker.record_failure()
            raise IntegrationTimeout(f"{type(self).__name__} timed out") from exc
        except httpx.HTTPError as exc:
            self.breaker.record_failure()
            raise IntegrationError(f"{type(self).__name__} call failed: {exc}") from exc
        else:
            self.breaker.record_success()
            # unreachable: AsyncRetrying reraises
            raise IntegrationError("retry loop exited without result")

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
