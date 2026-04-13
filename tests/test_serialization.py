import unittest
from types import SimpleNamespace

from pydantic import ValidationError as PydanticValidationError, field_validator, model_validator

from raft import RaftResponse, Serializer
from raft.openapi.schema import build_openapi_schema
from raft.serialization.registry import clear_serializer_registry, registered_serializers


class ItemInSerializer(Serializer):
    name: str
    qty: int

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name required")
        return v.strip()

    @model_validator(mode="after")
    def qty_cap(self):
        if self.qty > 99:
            raise ValueError("qty too large")
        return self


class ItemOutSerializer(Serializer):
    id: int
    name: str
    qty: int


class SerializationTests(unittest.TestCase):
    def tearDown(self) -> None:
        clear_serializer_registry()

    def test_from_payload_field_and_model_validation(self) -> None:
        with self.assertRaises(PydanticValidationError):
            ItemInSerializer.from_payload({"name": "   ", "qty": 1})
        with self.assertRaises(PydanticValidationError):
            ItemInSerializer.from_payload({"name": "a", "qty": 100})
        obj = ItemInSerializer.from_payload({"name": "  tea  ", "qty": 2})
        self.assertEqual(obj.name, "tea")
        self.assertEqual(obj.qty, 2)

    def test_serialize_dict_and_object(self) -> None:
        d = ItemOutSerializer.serialize({"id": 1, "name": "x", "qty": 3})
        self.assertEqual(d, {"id": 1, "name": "x", "qty": 3})
        row = SimpleNamespace(id=2, name="y", qty=4)
        d2 = ItemOutSerializer.serialize(row)
        self.assertEqual(d2, {"id": 2, "name": "y", "qty": 4})

    def test_route_serializer_kwargs_openapi(self) -> None:
        from raft import Raft

        app = Raft(auto_discover_serializers=False)

        @app.route(
            "/items",
            methods=["POST"],
            request_serializer=ItemInSerializer,
            response_serializer=ItemOutSerializer,
        )
        async def create_item(request):
            return RaftResponse.created(
                message="ok",
                data=ItemOutSerializer.serialize(SimpleNamespace(id=1, name="n", qty=1)),
            )

        spec = build_openapi_schema(app.router, title="T", version="1")
        post = spec["paths"]["/items"]["post"]
        self.assertIn("requestBody", post)
        ref = post["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        self.assertEqual(ref, "#/components/schemas/ItemInSerializer")
        self.assertEqual(
            post["responses"]["201"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/ItemOutSerializer",
        )
        self.assertIn("ItemInSerializer", spec["components"]["schemas"])
        self.assertIn("ItemOutSerializer", spec["components"]["schemas"])


class SerializerRegistryOpenAPITests(unittest.TestCase):
    def tearDown(self) -> None:
        clear_serializer_registry()

    def test_registered_serializers_merge_into_openapi_components(self) -> None:
        from raft import Raft
        from raft.serialization.registry import register_serializer

        register_serializer(ItemOutSerializer)
        app = Raft(auto_discover_serializers=False)

        @app.route("/x", methods=["GET"])
        async def x(request):
            return RaftResponse.ok()

        spec = build_openapi_schema(app.router)
        self.assertIn("ItemOutSerializer", spec["components"]["schemas"])
        self.assertIn("ItemOutSerializer", registered_serializers())
