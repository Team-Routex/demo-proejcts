from raftsql.orm.model import Model
from raftsql.orm.fields import (
    AutoField,
    CharField,
    DateTimeField,
    ForeignKey,
    CASCADE,
)
from models.blog import Blog


class PageView(Model):
    id = AutoField(primary_key=True)
    blog = ForeignKey(Blog, on_delete=CASCADE, null=True, blank=True)
    ip_address = CharField(max_length=64, default="", blank=True)
    user_agent = CharField(max_length=500, default="", blank=True)
    viewed_at = DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "page_views"
