"""Category Views (Class-Based and Function-Based Views)."""

import re
from raft import Response, View
from raft.core.exceptions import ValidationError, NotFound
from raft.core.request import RaftRequest
from raftsql.orm.q import Q
from models.blog import Category, BlogCategory, Blog
from middleware.auth import get_authenticated_user


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


class CategoryListView(View):
    """Class-Based View: GET (list categories with live counts) and POST (create category)."""

    async def get(self, request: RaftRequest) -> Response:
        query = (request.get_query_param("q") or "").strip().lower()

        if query:
            cats = await Category.objects.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            ).alist()
        else:
            cats = await Category.objects.alist()

        categories = []
        for c in cats:
            bcs = await BlogCategory.objects.filter(category_id=c.id).alist()
            blog_ids = [bc.blog_id for bc in bcs]
            blog_count = 0
            if blog_ids:
                blog_count = await Blog.objects.filter(
                    id__in=blog_ids,
                    publication_status="published",
                    approval_status="approved",
                ).acount()

            categories.append({
                "id": c.id,
                "name": c.name,
                "slug": c.slug,
                "description": c.description or "",
                "blog_count": blog_count,
                "created_at": c.created_at.isoformat() if hasattr(c.created_at, "isoformat") else str(c.created_at),
            })

        categories.sort(key=lambda x: (-x["blog_count"], x["name"].lower()))
        return Response.success(data=categories)

    async def post(self, request: RaftRequest) -> Response:
        claims = get_authenticated_user(request, require=True)
        user_id = claims["user_id"]

        data = await request.json() or {}
        name = str(data.get("name", "")).strip()
        description = str(data.get("description", "")).strip()

        if not name or len(name) < 2:
            raise ValidationError(message="Category name must be at least 2 characters long.")

        slug = _slugify(name)
        if not slug:
            raise ValidationError(message="Category name is invalid.")

        existing = await Category.objects.filter(slug=slug).afirst()
        if existing:
            return Response.success(
                data={"id": existing.id, "name": existing.name, "slug": existing.slug, "description": existing.description},
                message="Category already exists.",
            )

        cat = await Category.objects.acreate(
            name=name,
            slug=slug,
            description=description,
            created_by_id=user_id,
        )

        return Response.created(
            data={"id": cat.id, "name": cat.name, "slug": cat.slug, "description": cat.description, "blog_count": 0},
            message="Category created successfully.",
        )


class CategoryDetailView(View):
    """Class-Based View: GET category details and related published blogs by slug."""

    async def get(self, request: RaftRequest) -> Response:
        slug = request.path_params.get("slug", "").strip()
        cat = await Category.objects.filter(slug=slug).afirst()
        if not cat:
            raise NotFound(message="Category not found.")

        bcs = await BlogCategory.objects.filter(category_id=cat.id).alist()
        blog_ids = [bc.blog_id for bc in bcs]
        blog_count = 0
        blogs = []

        if blog_ids:
            blog_count = await Blog.objects.filter(
                id__in=blog_ids,
                publication_status="published",
                approval_status="approved",
            ).acount()

            recent = await Blog.objects.filter(
                id__in=blog_ids,
                publication_status="published",
                approval_status="approved",
            ).order_by("-created_at").limit(5).alist()

            for b in recent:
                blogs.append({
                    "id": b.id,
                    "title": b.title,
                    "slug": b.slug,
                    "summary": b.summary,
                    "featured_image": b.featured_image,
                    "views_count": int(b.views_count),
                    "created_at": b.created_at.isoformat() if hasattr(b.created_at, "isoformat") else str(b.created_at),
                })

        return Response.success(data={
            "id": cat.id,
            "name": cat.name,
            "slug": cat.slug,
            "description": cat.description or "",
            "blog_count": blog_count,
            "recent_blogs": blogs,
        })

