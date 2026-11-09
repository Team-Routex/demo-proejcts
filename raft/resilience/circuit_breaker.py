"""
raft.resilience.circuit_breaker
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In-process circuit breaker for outbound calls (HTTP clients, DB helpers,
other services). Use it in monoliths for flaky externals and in
microservices for inter-service calls.

States:
    CLOSED     — calls pass through; failures counted
    OPEN       — calls fail fast with ``CircuitOpenError``
    HALF_OPEN  — limited trial calls; success closes, failure re-opens

Example::

    from raft import CircuitBreaker, CircuitOpenError

    payments = CircuitBreaker("payments", failure_threshold=5, recovery_timeout=30)

    @payments
    async def charge(amount: float) -> dict:
        # outbound HTTP / RPC here
        ...

    try:
        await charge(10.0)
    except CircuitOpenError:
        return Response.custom(status=False, message="Payments unavailable", http_status=503)
"""

from __future__ import annotations

import enum
import functools
import inspect
import threading
import time
from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar, overload

from raft.core.exceptions import HTTPException

P = ParamSpec("P")
R = TypeVar("R")


class CircuitState(enum.Enum):
    """Lifecycle states for a circuit breaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(HTTPException):
    """Raised when the circuit is open (fail-fast). Maps to HTTP 503 in views."""

    def __init__(
        self,
        name: str = "circuit",
        *,
        retry_after: float | None = None,
    ) -> None:
        message = f"Circuit '{name}' is open — dependency unavailable"
        errors = [f"retry_after={retry_after:.1f}s"] if retry_after is not None else []
        super().__init__(status_code=503, message=message, errors=errors)
        self.name: str = name
        self.retry_after: float | None = retry_after


class CircuitBreaker:
    """Protect an outbound dependency with a circuit breaker.

    Parameters:
        name: Label used in errors and the global registry.
        failure_threshold: Consecutive failures in CLOSED before opening.
        recovery_timeout: Seconds to wait in OPEN before trying HALF_OPEN.
        half_open_success_threshold: Successes in HALF_OPEN needed to CLOSE.
        excluded_exceptions: Exceptions that do **not** count as failures
            (e.g. local validation errors).
    """

    def __init__(
        self,
        name: str = "default",
        *,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_success_threshold: int = 1,
        excluded_exceptions: tuple[type[BaseException], ...] = (),
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if recovery_timeout < 0:
            raise ValueError("recovery_timeout must be >= 0")
        if half_open_success_threshold < 1:
            raise ValueError("half_open_success_threshold must be >= 1")

        self.name: str = name
        self.failure_threshold: int = failure_threshold
        self.recovery_timeout: float = recovery_timeout
        self.half_open_success_threshold: int = half_open_success_threshold
        self.excluded_exceptions: tuple[type[BaseException], ...] = excluded_exceptions

        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._half_open_successes: int = 0
        self._opened_at: float | None = None
        self._lock = threading.RLock()

    # ---- Introspection ----------------------------------------------------

    @property
    def state(self) -> CircuitState:
        with self._lock:
            self._maybe_enter_half_open()
            return self._state

    @property
    def failure_count(self) -> int:
        with self._lock:
            return self._failure_count

    def reset(self) -> None:
        """Force the circuit back to CLOSED (useful in tests)."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._half_open_successes = 0
            self._opened_at = None

    # ---- Call API ---------------------------------------------------------

    def call(self, func: Callable[P, R], /, *args: P.args, **kwargs: P.kwargs) -> R:
        """Run a sync callable through the breaker."""
        self._before_call()
        try:
            result = func(*args, **kwargs)
        except self.excluded_exceptions:
            raise
        except BaseException:
            self._on_failure()
            raise
        else:
            self._on_success()
            return result

    async def acall(
        self,
        func: Callable[P, Awaitable[R]] | Callable[P, R],
        /,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> R:
        """Run a sync or async callable through the breaker."""
        self._before_call()
        try:
            result = func(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await result  # type: ignore[assignment]
        except self.excluded_exceptions:
            raise
        except BaseException:
            self._on_failure()
            raise
        else:
            self._on_success()
            return result  # type: ignore[return-value]

    @overload
    def __call__(self, func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]: ...

    @overload
    def __call__(self, func: Callable[P, R]) -> Callable[P, R]: ...

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator: ``@breaker`` / ``@breaker_instance`` for sync or async functions."""
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await self.acall(func, *args, **kwargs)

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return self.call(func, *args, **kwargs)

        return sync_wrapper

    # ---- State machine ----------------------------------------------------

    def _maybe_enter_half_open(self) -> None:
        if self._state is not CircuitState.OPEN or self._opened_at is None:
            return
        if time.monotonic() - self._opened_at >= self.recovery_timeout:
            self._state = CircuitState.HALF_OPEN
            self._half_open_successes = 0

    def _before_call(self) -> None:
        with self._lock:
            self._maybe_enter_half_open()
            if self._state is CircuitState.OPEN:
                retry_after = None
                if self._opened_at is not None:
                    elapsed = time.monotonic() - self._opened_at
                    retry_after = max(0.0, self.recovery_timeout - elapsed)
                raise CircuitOpenError(self.name, retry_after=retry_after)

    def _on_success(self) -> None:
        with self._lock:
            if self._state is CircuitState.HALF_OPEN:
                self._half_open_successes += 1
                if self._half_open_successes >= self.half_open_success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._half_open_successes = 0
                    self._opened_at = None
                return
            # CLOSED: clear consecutive failure streak
            self._failure_count = 0

    def _on_failure(self) -> None:
        with self._lock:
            if self._state is CircuitState.HALF_OPEN:
                self._trip_open()
                return
            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._trip_open()

    def _trip_open(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = time.monotonic()
        self._half_open_successes = 0


# ---- Registry -------------------------------------------------------------

_REGISTRY: dict[str, CircuitBreaker] = {}
_REGISTRY_LOCK = threading.Lock()


def get_circuit(
    name: str,
    *,
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
    half_open_success_threshold: int = 1,
    excluded_exceptions: tuple[type[BaseException], ...] = (),
) -> CircuitBreaker:
    """Return a shared breaker by *name* (created on first use).

    Later calls with the same *name* reuse the existing instance; threshold
    kwargs are ignored if the breaker already exists.
    """
    with _REGISTRY_LOCK:
        existing = _REGISTRY.get(name)
        if existing is not None:
            return existing
        breaker = CircuitBreaker(
            name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            half_open_success_threshold=half_open_success_threshold,
            excluded_exceptions=excluded_exceptions,
        )
        _REGISTRY[name] = breaker
        return breaker


def reset_circuits() -> None:
    """Reset and clear all registered breakers (for tests / process recycle)."""
    with _REGISTRY_LOCK:
        for breaker in _REGISTRY.values():
            breaker.reset()
        _REGISTRY.clear()
