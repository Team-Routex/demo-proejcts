"""
raft.core.views
~~~~~~~~~~~~~~~

Class-based view (CBV) support.

Subclass ``View`` and implement ``get()``, ``post()``, etc. to handle
HTTP methods via a clean OOP approach.

Example::

    class UserView(View):
        async def get(self, request: RaftRequest) -> RawResponse:
            return RaftResponse.ok(data={"users": []})

        async def post(self, request: RaftRequest) -> RawResponse:
            body = await request.json()
            return RaftResponse.created(data=body)

Register it on a router::

    router.add_route(Route("/users", UserView.as_view(), methods=None))

When ``methods`` is ``None`` the view itself decides which methods to accept.
"""

from __future__ import annotations

from typing import Any

from raft.core.exceptions import MethodNotAllowed
from raft.core.request import RaftRequest
from raft.core.response import RawResponse, RaftResponse


class View:
    """Base class for class-based views.

    Override ``get``, ``post``, ``put``, ``patch``, ``delete`` to handle
    the corresponding HTTP method.  Unimplemented methods return 405.
    """

    async def dispatch(self, request: RaftRequest) -> RawResponse:
        """Route the request to the correct method handler."""
        method = request.method.lower()
        handler = getattr(self, method, None)
        if handler is None or not callable(handler):
            raise MethodNotAllowed(
                message=f"Method {request.method} not allowed"
            )
        return await handler(request)

    # Default handlers — subclasses override the ones they need.
    # Unoverridden methods stay as None so dispatch() raises 405.

    @classmethod
    def as_view(cls) -> Any:
        """Return an async callable suitable for route registration.

        Usage::

            Route("/items", ItemView.as_view())
        """

        async def view_handler(request: RaftRequest) -> RawResponse:
            instance = cls()
            return await instance.dispatch(request)

        view_handler.__name__ = cls.__name__
        view_handler.__qualname__ = cls.__qualname__
        return view_handler
