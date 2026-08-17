"""
raft.core.views
~~~~~~~~~~~~~~~

Class-based view (CBV) support.

Subclass ``View`` and implement ``get()``, ``post()``, etc. to handle
HTTP methods via a clean OOP approach.

View authentication and permissions::

    from raft import View, route, Response
    from raft.auth import JWTAuthentication, IsAuthenticated

    class MeView(View):
        authentication_classes = [JWTAuthentication]
        permission_classes = [IsAuthenticated]

        async def get(self, request):
            return Response.success(data={"user": request.user})

    routes = [
        route("/me/", MeView, methods=["GET"]),
    ]

When ``methods`` is ``None`` the view itself decides which methods to accept.
"""

from __future__ import annotations

from typing import Any, ClassVar

from raft.auth.pipeline import check_permissions, instantiate_classes, perform_authentication
from raft.core.exceptions import MethodNotAllowed
from raft.core.request import RaftRequest
from raft.core.response import RawResponse


class View:
    """Base class for class-based views.

    Override ``get``, ``post``, ``put``, ``patch``, ``delete`` to handle
    the corresponding HTTP method.  Unimplemented methods return 405.

    Class attributes:
        authentication_classes: list of auth backend classes
        permission_classes: list of permission classes
    """

    authentication_classes: ClassVar[list[Any]] = []
    permission_classes: ClassVar[list[Any]] = []

    def get_authenticators(self) -> list[Any]:
        return instantiate_classes(self.authentication_classes)

    def get_permissions(self) -> list[Any]:
        return instantiate_classes(self.permission_classes)

    def perform_authentication(self, request: RaftRequest) -> None:
        perform_authentication(request, self.get_authenticators())

    def check_permissions(self, request: RaftRequest) -> None:
        check_permissions(
            request,
            self.get_permissions(),
            view=self,
            authenticators=self.get_authenticators(),
        )

    def initial(self, request: RaftRequest) -> None:
        """Run authentication and permission checks (before the HTTP method)."""
        self.perform_authentication(request)
        self.check_permissions(request)

    async def dispatch(self, request: RaftRequest) -> RawResponse:
        """Authenticate, authorize, then route to the correct method handler."""
        self.initial(request)
        method = request.method.lower()
        handler = getattr(self, method, None)
        if handler is None or not callable(handler):
            raise MethodNotAllowed(
                message=f"Method {request.method} not allowed"
            )
        return await handler(request)

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
