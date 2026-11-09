from raftsql.orm.model import Model
from raftsql.orm.fields import (
    AutoField,
    TextField,
    BooleanField,
    DateTimeField,
    IntegerField,
    ForeignKey,
    CASCADE,
)
from models.user import User
from models.blog import Blog


class Comment(Model):
    id = AutoField(primary_key=True)
    blog = ForeignKey(Blog, on_delete=CASCADE, related_name="comments")
    user = ForeignKey(User, on_delete=CASCADE, related_name="comments")
    parent_id = IntegerField(null=True, blank=True, default=None)  # Parent comment ID for threading
    content = TextField()
    is_approved = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        db_table = "comments"
