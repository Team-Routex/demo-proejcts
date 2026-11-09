from raftsql.orm.model import Model
from raftsql.orm.fields import (
    AutoField,
    CharField,
    TextField,
    DateTimeField,
    IntegerField,
    ForeignKey,
    CASCADE,
    SET_NULL,
)
from models.user import User


class Category(Model):
    id = AutoField(primary_key=True)
    name = CharField(max_length=100, unique=True)
    slug = CharField(max_length=120, unique=True)
    description = TextField(default="", blank=True)
    created_by = ForeignKey(User, on_delete=SET_NULL, null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "categories"


class Tag(Model):
    id = AutoField(primary_key=True)
    name = CharField(max_length=100, unique=True)
    slug = CharField(max_length=120, unique=True)
    description = TextField(default="", blank=True)
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tags"


class Blog(Model):
    id = AutoField(primary_key=True)
    title = CharField(max_length=255)
    slug = CharField(max_length=300, unique=True)
    content = TextField()
    summary = TextField(default="", blank=True)
    featured_image = CharField(max_length=500, default="", blank=True)
    author = ForeignKey(User, on_delete=CASCADE, related_name="blogs")
    publication_status = CharField(max_length=30, default="draft")  # draft | published
    approval_status = CharField(max_length=30, default="pending")  # pending | approved | rejected
    rejection_reason = TextField(default="", blank=True)
    views_count = IntegerField(default=0)
    scheduled_at = DateTimeField(null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        db_table = "blogs"


class BlogCategory(Model):
    id = AutoField(primary_key=True)
    blog = ForeignKey(Blog, on_delete=CASCADE, related_name="categories_pivot")
    category = ForeignKey(Category, on_delete=CASCADE, related_name="blogs_pivot")
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "blog_categories"


class BlogTag(Model):
    id = AutoField(primary_key=True)
    blog = ForeignKey(Blog, on_delete=CASCADE, related_name="tags_pivot")
    tag = ForeignKey(Tag, on_delete=CASCADE, related_name="blogs_pivot")
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "blog_tags"
