import unittest

from pydantic import BaseModel

from raft import Raft
from raft.core.response import Response
from raft.openapi.schema import build_openapi_schema


class CreateUserBody(BaseModel):
    name: str
    age: int


class OpenAPISwaggerSchemaTests(unittest.TestCase):
    def test_openapi_contains_path_params_body_and_response_structure(self) -> None:
        app = Raft()

        @app.route("/users/{user_id}", methods=["GET"])
        async def get_user(request):
            return Response.success(data={"id": request.path_params["user_id"]})

        @app.route(
            "/users",
            methods=["POST"],
            request_body=CreateUserBody,
            responses={201: "Created"},
        )
        async def create_user(request):
            return Response.created(data={"ok": True})

        schema = build_openapi_schema(app.router, title="Test API", version="1.0.0")

        get_op = schema["paths"]["/users/{user_id}"]["get"]
        post_op = schema["paths"]["/users"]["post"]

        # Path parameter should be exposed for Swagger input.
        self.assertIn("parameters", get_op)
        self.assertEqual(get_op["parameters"][0]["name"], "user_id")
        self.assertEqual(get_op["parameters"][0]["in"], "path")

        # Request body schema should be exposed for Swagger request editor.
        self.assertIn("requestBody", post_op)
        body_schema_ref = post_op["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        self.assertEqual(body_schema_ref, "#/components/schemas/CreateUserBody")

        # Response structure should reference Response envelope schema.
        self.assertIn("responses", get_op)
        get_200_ref = get_op["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        self.assertEqual(get_200_ref, "#/components/schemas/Response")

        # Components should include both Raft envelope and request model schema.
        self.assertIn("Response", schema["components"]["schemas"])
        self.assertIn("CreateUserBody", schema["components"]["schemas"])


if __name__ == "__main__":
    unittest.main()
