import json
import unittest

from pydantic import ValidationError as PydanticValidationError

from raft import Raft, RaftResponse, Serializer
from raft.openapi.schema import build_openapi_schema
from raft.serialization.base import validation_error
from raft.serialization.fields import CharField, EmailField, IntegerField


class UserSerializer(Serializer):
    id: int | None = IntegerField(read_only=True, default=None)
    username: str = CharField()
    email: str = EmailField()
    password: str = CharField(write_only=True)
    confirm_password: str = CharField(write_only=True)
    age: int = IntegerField()

    def validate_age(self, value: int) -> int:
        if value < 18:
            raise ValueError("Age must be at least 18.")
        return value

    def validate(self, attrs: dict) -> None:
        if attrs["password"] != attrs["confirm_password"]:
            validation_error({"confirm_password": "Passwords do not match."})


class ProfileIn(Serializer):
    """Used to assert OpenAPI JSON Schema for read/write flags."""

    id: int | None = IntegerField(read_only=True, default=None)
    name: str = CharField()
    token: str = CharField(write_only=True)


class SerializerReadWriteTests(unittest.TestCase):
    def test_read_only_stripped_from_input(self) -> None:
        u = UserSerializer.from_payload(
            {
                "id": 999,
                "username": "bob",
                "email": "bob@example.com",
                "password": "secret",
                "confirm_password": "secret",
                "age": 21,
            }
        )
        self.assertIsNone(u.id)

    def test_write_only_excluded_from_dump(self) -> None:
        u = UserSerializer.from_payload(
            {
                "username": "bob",
                "email": "bob@example.com",
                "password": "secret",
                "confirm_password": "secret",
                "age": 21,
            }
        )
        d = u.model_dump(mode="json")
        self.assertNotIn("password", d)
        self.assertNotIn("confirm_password", d)
        self.assertIn("username", d)

    def test_field_level_validate_age(self) -> None:
        with self.assertRaises(PydanticValidationError):
            UserSerializer.from_payload(
                {
                    "username": "bob",
                    "email": "bob@example.com",
                    "password": "a",
                    "confirm_password": "a",
                    "age": 10,
                }
            )

    def test_object_level_validate_passwords(self) -> None:
        with self.assertRaises(PydanticValidationError):
            UserSerializer.from_payload(
                {
                    "username": "bob",
                    "email": "bob@example.com",
                    "password": "one",
                    "confirm_password": "two",
                    "age": 21,
                }
            )


class SerializerDataAPITests(unittest.TestCase):
    def test_data_property_after_model_validate(self) -> None:
        u = UserSerializer.model_validate(
            {
                "username": "bob",
                "email": "bob@example.com",
                "password": "s",
                "confirm_password": "s",
                "age": 21,
            }
        )
        d = u.data
        self.assertEqual(d["username"], "bob")
        self.assertNotIn("password", d)

    def test_constructor_data_kwarg_and_is_valid(self) -> None:
        u = UserSerializer(
            data={
                "username": "ann",
                "email": "ann@example.com",
                "password": "x",
                "confirm_password": "x",
                "age": 30,
            }
        )
        self.assertTrue(u.is_valid())
        self.assertEqual(u.validated_data["username"], "ann")


class SerializerOpenAPIReadWriteTests(unittest.TestCase):
    def test_openapi_schema_read_write_flags_and_no_raft_internals(self) -> None:
        app = Raft(auto_discover_serializers=False)

        @app.route(
            "/profiles",
            methods=["POST"],
            request_serializer=ProfileIn,
            responses={201: ProfileIn},
        )
        async def create_profile(request):
            return RaftResponse.created(data={})

        spec = build_openapi_schema(app.router, title="T", version="1")
        schemas = spec["components"]["schemas"]
        self.assertIn("ProfileIn", schemas)
        blob = json.dumps(schemas["ProfileIn"])
        self.assertNotIn("raft_", blob)

        props = schemas["ProfileIn"].get("properties") or {}
        self.assertEqual(props["id"].get("readOnly"), True)
        self.assertEqual(props["token"].get("writeOnly"), True)


if __name__ == "__main__":
    unittest.main()
