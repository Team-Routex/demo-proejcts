"""Tag Views (Class-Based and Function-Based Views)."""

import re
from raft import Response, View
from raft.core.exceptions import ValidationError, NotFound
from raft.core.request import RaftRequest
from models.blog import Tag, BlogTag, Blog
from middleware.auth import get_authenticated_user, require_admin
from schemas import TagResponseSchema, dump


def slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    return slug.strip("-")


class TagListView(View):
    """Class-Based View: Handles GET (list all tags) and POST (create tag)."""

    async def get(self, request: RaftRequest) -> Response:
        tags = await Tag.objects.order_by("name").alist()
        tag_schemas = []
        for t in tags:
            pivots = await BlogTag.objects.filter(tag_id=t.id).alist()
            tag_schemas.append(
                TagResponseSchema(
                    id=t.id,
                    name=t.name,
                    slug=t.slug,
                    description=t.description or "",
                    blog_count=len(pivots),
                    created_at=t.created_at,
                )
            )

        return Response.success(data=dump(tag_schemas))

    async def post(self, request: RaftRequest) -> Response:
        get_authenticated_user(request, require=True)
        body = await request.json() or {}
        name = (body.get("name") or "").strip()
        if not name:
            raise ValidationError(message="Tag name is required")

        slug = slugify(body.get("slug") or name)
        existing = await Tag.objects.filter(slug=slug).afirst()
        if existing:
            raise ValidationError(message="A tag with this name or slug already exists")

        tag = await Tag.objects.acreate(
            name=name,
            slug=slug,
            description=(body.get("description") or "").strip(),
        )

        schema = TagResponseSchema(
            id=tag.id,
            name=tag.name,
            slug=tag.slug,
            description=tag.description or "",
            blog_count=0,
            created_at=tag.created_at,
        )
        return Response.success(
            data=dump(schema),
            message="Tag created successfully",
            status_code=201,
        )


class TagSlugView(View):
    """Class-Based View: GET tag details and associated blogs by slug."""

    async def get(self, request: RaftRequest) -> Response:
        slug = request.path_params.get("slug", "").strip()
        tag = await Tag.objects.filter(slug=slug).afirst()
        if not tag:
            raise NotFound(message="Tag not found")

        pivots = await BlogTag.objects.filter(tag_id=tag.id).alist()
        blog_ids = [p.blog_id for p in pivots]

        blogs = []
        if blog_ids:
            for bid in blog_ids:
                b = await Blog.objects.filter(id=bid, publication_status="published", approval_status="approved").afirst()
                if b:
                    blogs.append({
                        "id": b.id,
                        "title": b.title,
                        "slug": b.slug,
                        "summary": b.summary or "",
                        "featured_image": b.featured_image or "",
                        "views_count": int(b.views_count or 0),
                        "created_at": b.created_at.isoformat() if hasattr(b.created_at, "isoformat") else str(b.created_at),
                    })

        schema = TagResponseSchema(
            id=tag.id,
            name=tag.name,
            slug=tag.slug,
            description=tag.description or "",
            blog_count=len(blogs),
            created_at=tag.created_at,
        )
        data = dump(schema)
        data["blogs"] = blogs

        return Response.success(data=data)


class TagDetailView(View):
    """Class-Based View: Update (PUT) and Delete (DELETE) a tag by ID (admin only)."""

    async def put(self, request: RaftRequest) -> Response:
        require_admin(request)
        tag_id = int(request.path_params.get("id", 0))
        tag = await Tag.objects.filter(id=tag_id).afirst()
        if not tag:
            raise NotFound(message="Tag not found")

        body = await request.json() or {}
        if "name" in body and body["name"]:
            tag.name = body["name"].strip()
        if "slug" in body and body["slug"]:
            tag.slug = slugify(body["slug"])
        if "description" in body:
            tag.description = body["description"].strip()

        await tag.asave()
        schema = TagResponseSchema(
            id=tag.id,
            name=tag.name,
            slug=tag.slug,
            description=tag.description or "",
            blog_count=0,
            created_at=tag.created_at,
        )
        return Response.success(
            data=dump(schema),
            message="Tag updated successfully",
        )

    async def delete(self, request: RaftRequest) -> Response:
        require_admin(request)
        tag_id = int(request.path_params.get("id", 0))
        tag = await Tag.objects.filter(id=tag_id).afirst()
        if not tag:
            raise NotFound(message="Tag not found")

        await BlogTag.objects.filter(tag_id=tag_id).adelete()
        await Tag.objects.filter(id=tag_id).adelete()
        return Response.success(message="Tag deleted successfully")
