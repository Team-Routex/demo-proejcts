"""
raft.middleware.base
~~~~~~~~~~~~~~~~~~~~

Middleware protocol and pipeline runner.

Every middleware is an async callable that receives the request and a
``call_next`` callback.  It can inspect / modify the request *before*
calling ``call_next``, and inspect / modify the response *after*.

Example::

    async def timing_middleware(
        request: RaftRequest,
        call_next: CallNext,
    ) -> RawResponse:
        start = time.monotonic()
        response = await call_next(request)
        elapsed = time.monotonic() - start
        response.headers["X-Response-Time"] = f"{elapsed:.4f}s"
        return response
"""

from __future__ import annotations

from typing import Awaitable, Callable

from raft.core.request import RaftRequest
from raft.core.response import RawResponse

# Public type aliases for middleware authors.
CallNext = Callable[[RaftRequest], Awaitable[RawResponse]]
MiddlewareFunc = Callable[[RaftRequest, CallNext], Awaitable[RawResponse]]


class MiddlewarePipeline:
    """Builds a layered middleware chain around a final handler.

    Middleware is applied in LIFO order (last-added wraps outermost), so
    the first middleware added is the *innermost* — closest to the view.

    Parameters:
        middlewares: Ordered list of middleware functions.
    """

    def __init__(self, middlewares: list[MiddlewareFunc] | None = None) -> None:
        self._middlewares: list[MiddlewareFunc] = list(middlewares or [])

    def add(self, middleware: MiddlewareFunc) -> None:
        """Append a middleware to the pipeline."""
        self._middlewares.append(middleware)

    def build_chain(
        self, final_handler: Callable[[RaftRequest], Awaitable[RawResponse]]
    ) -> Callable[[RaftRequest], Awaitable[RawResponse]]:
        """Compose the middleware stack into a single callable.

        The resulting callable accepts a RaftRequest and returns a RawResponse,
        invoking every middleware in order.
        """
        handler = final_handler
        # Wrap from innermost (first) to outermost (last).
        for mw in reversed(self._middlewares):
            handler = _wrap(mw, handler)
        return handler


def _wrap(
    middleware: MiddlewareFunc,
    next_handler: Callable[[RaftRequest], Awaitable[RawResponse]],
) -> Callable[[RaftRequest], Awaitable[RawResponse]]:
    """Create a closure that threads *next_handler* as call_next."""

    async def wrapped(request: RaftRequest) -> RawResponse:
        return await middleware(request, next_handler)

    return wrapped
