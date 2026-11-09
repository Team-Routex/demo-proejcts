from raftsql.orm.model import Model
from raftsql.orm.fields import (
    AutoField,
    CharField,
    DateTimeField,
    IntegerField,
    ForeignKey,
    CASCADE,
)
from models.user import User


class Reaction(Model):
    id = AutoField(primary_key=True)
    user = ForeignKey(User, on_delete=CASCADE, related_name="reactions")
    target_type = CharField(max_length=30)  # "blog" | "comment"
    target_id = IntegerField()
    reaction_type = CharField(max_length=30, default="like")
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reactions"
