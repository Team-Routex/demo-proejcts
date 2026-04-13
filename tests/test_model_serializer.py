import unittest
from dataclasses import dataclass

from raft import ModelSerializer


@dataclass
class User:
    id: int | None = None
    name: str = ""
    email: str = ""
    is_admin: bool = False
    password: str = ""


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email", "is_admin", "password"]
        read_only_fields = ["id"]
        write_only_fields = ["password"]

    def validate_name(self, value: str) -> str:
        if len(value.strip()) < 2:
            raise ValueError("Name too short.")
        return value.strip()

    def validate(self, attrs: dict):
        if "email" in attrs and "@" not in attrs["email"]:
            raise ValueError("Invalid email.")
        return attrs


class ModelSerializerTests(unittest.TestCase):
    def test_create_and_output_hides_write_only(self) -> None:
        serializer = UserSerializer(
            data={
                "name": "  Alice  ",
                "email": "alice@example.com",
                "is_admin": False,
                "password": "secret",
            }
        )
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        self.assertEqual(user.name, "Alice")
        self.assertNotIn("password", serializer.data)
        self.assertEqual(serializer.data["email"], "alice@example.com")

    def test_update_partial(self) -> None:
        user = User(id=1, name="Alice", email="alice@example.com", is_admin=False, password="x")
        serializer = UserSerializer(user, data={"name": "Alicia"}, partial=True)
        self.assertTrue(serializer.is_valid())
        updated = serializer.save()
        self.assertEqual(updated.name, "Alicia")
        self.assertEqual(updated.email, "alice@example.com")

    def test_read_only_rejected_as_required_and_not_writable(self) -> None:
        serializer = UserSerializer(data={"name": "Bo", "email": "bo@example.com", "password": "p"})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("id", serializer.validated_data)

    def test_validation_errors(self) -> None:
        serializer = UserSerializer(data={"name": "x", "email": "bad", "password": "pw"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)
        self.assertIn("non_field_errors", serializer.errors)

    def test_many_mode(self) -> None:
        serializer = UserSerializer(
            data=[
                {"name": "Ava", "email": "ava@example.com", "password": "1"},
                {"name": "Bob", "email": "bob@example.com", "password": "2"},
            ],
            many=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        users = serializer.save()
        self.assertEqual(len(users), 2)
        self.assertNotIn("password", serializer.data[0])


if __name__ == "__main__":
    unittest.main()
