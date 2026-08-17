"""WebSocket route matching utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from raft.core.router import path_resolution_candidates
from raft.websocket.connection import RaftWebSocket

WebSocketHandler = Callable[[RaftWebSocket], Awaitable[None]]


@dataclass
class WebSocketRoute:
    """A websocket path to handler mapping."""

    path: str
    handler: WebSocketHandler
    name: str | None = None
    _pattern: re.Pattern[str] = field(default=None, repr=False)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self._pattern = _compile_path(self.path)


def _compile_path(path: str) -> re.Pattern[str]:
    """Convert /ws/{room} style paths into named-group regex patterns."""
    parts = re.split(r"\{(\w+)\}", path)
    regex = ""
    for i, part in enumerate(parts):
        if i % 2 == 0:
            regex += re.escape(part)
        else:
            regex += rf"(?P<{part}>[^/]+)"
    return re.compile(f"^{regex}$")


class WebSocketRouter:
    """Collect websocket routes and resolve by request path."""

    def __init__(self, prefix: str = "") -> None:
        self.prefix = prefix.rstrip("/")
        self._routes: list[WebSocketRoute] = []

    def websocket(
        self,
        path: str,
        *,
        name: str | None = None,
    ) -> Callable[[WebSocketHandler], WebSocketHandler]:
        """Decorator to register a websocket handler."""

        def decorator(func: WebSocketHandler) -> WebSocketHandler:
            route = WebSocketRoute(path=self.prefix + path, handler=func, name=name)
            self._routes.append(route)
            return func

        return decorator

    def add_route(self, route: WebSocketRoute) -> None:
        """Register a pre-built websocket route."""
        route.path = self.prefix + route.path
        route._pattern = _compile_path(route.path)
        self._routes.append(route)

    def resolve(self, path: str) -> tuple[WebSocketRoute, dict[str, str]] | None:
        """Resolve websocket path to a route and extracted path params."""
        for candidate in path_resolution_candidates(path):
            for route in self._routes:
                match = route._pattern.match(candidate)
                if match is not None:
                    return route, match.groupdict()
        return None

    @property
    def routes(self) -> list[WebSocketRoute]:
        return list(self._routes)
