from raftsql.orm.model import Model
from raftsql.orm.fields import (
    AutoField,
    CharField,
    TextField,
    BooleanField,
    DateTimeField,
    ForeignKey,
    CASCADE,
)


class User(Model):
    id = AutoField(primary_key=True)
    username = CharField(max_length=150, unique=True)
    email = CharField(max_length=255, unique=True)
    password_hash = CharField(max_length=255)
    role = CharField(max_length=50, default="user")  # "admin" | "user"
    is_verified = BooleanField(default=False)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"


class UserProfile(Model):
    id = AutoField(primary_key=True)
    user = ForeignKey(User, on_delete=CASCADE, unique=True, related_name="profile")
    full_name = CharField(max_length=255, default="", blank=True)
    bio = TextField(default="", blank=True)
    avatar_url = CharField(max_length=500, default="", blank=True)
    website = CharField(max_length=255, default="", blank=True)

    class Meta:
        db_table = "user_profiles"
