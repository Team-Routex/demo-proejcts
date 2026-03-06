"""
raft.graphql.integration
~~~~~~~~~~~~~~~~~~~~~~~~

Strawberry GraphQL integration for Raft.

Provides ``GraphQLRouter`` — a helper that mounts a Strawberry schema
onto a Raft ``Router`` at a given path (default ``/graphql``).

Usage::

    import strawberry
    from raft.graphql.integration import GraphQLRouter

    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self) -> str:
            return "Hello from Raft GraphQL!"

    schema = strawberry.Schema(Query)
    graphql_router = GraphQLRouter(schema, path="/graphql")

    app.include_router(graphql_router.router)
"""

from __future__ import annotations

import json
from typing import Any

import strawberry
from strawberry.schema import Schema

from raft.core.request import RaftRequest
from raft.core.response import RawResponse
from raft.core.router import Route, Router


class GraphQLRouter:
    """Wraps a Strawberry ``Schema`` into a Raft ``Router``.

    Parameters:
        schema: A ``strawberry.Schema`` instance.
        path: URL path to mount the GraphQL endpoint at.
    """

    def __init__(self, schema: Schema, path: str = "/graphql") -> None:
        self.schema: Schema = schema
        self.path: str = path
        self.router: Router = Router()
        self._register()

    def _register(self) -> None:
        """Register GET and POST routes for the GraphQL endpoint."""
        self.router.add_routes(
            [
                Route(
                    path=self.path,
                    handler=self._handle,
                    methods=["GET", "POST"],
                    name="graphql",
                ),
            ]
        )

    async def _handle(self, request: RaftRequest) -> RawResponse:
        """Process a GraphQL request (GET with query params, or POST with JSON body)."""
        query: str | None = None
        variables: dict[str, Any] | None = None
        operation_name: str | None = None

        if request.method == "GET":
            query = request.get_query_param("query")
            variables_raw = request.get_query_param("variables")
            if variables_raw:
                variables = json.loads(variables_raw)
            operation_name = request.get_query_param("operationName")
        else:
            body = await request.json()
            if body:
                query = body.get("query")
                variables = body.get("variables")
                operation_name = body.get("operationName")

        if not query:
            return RawResponse(
                body=json.dumps(
                    {"status": False, "message": "No query provided", "data": None, "errors": ["Missing GraphQL query"]}
                ).encode(),
                status_code=400,
                content_type="application/json",
            )

        result = await self.schema.execute(
            query,
            variable_values=variables,
            operation_name=operation_name,
        )

        response_data: dict[str, Any] = {"data": result.data}
        if result.errors:
            response_data["errors"] = [str(e) for e in result.errors]

        return RawResponse(
            body=json.dumps(response_data, default=str).encode(),
            status_code=200,
            content_type="application/json",
        )
