"""Blog Publication and Management Views."""

import re
import secrets
from datetime import datetime
from typing import Any, Optional
from raft import Response
from raft.core.exceptions import ValidationError, NotFound, Forbidden
from raft.core.request import RaftRequest
from raftsql.orm.q import Q
from models.blog import Blog, Category, BlogCategory, Tag, BlogTag
from models.user import User, UserProfile
from models.analytics import PageView
from models.reaction import Reaction
from models.comment import Comment
from middleware.auth import get_authenticated_user
from schemas import (
    BlogListItemSchema,
    BlogDetailSchema,
    AuthorCompactSchema,
    CategoryResponseSchema,
    TagResponseSchema,
    dump,
)


def _parse_scheduled_at(val: Any) -> Optional[datetime]:
    if not val:
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=None) if val.tzinfo else val
    try:
        clean = str(val).replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)
        return dt.replace(tzinfo=None) if dt.tzinfo else dt
    except Exception:
        return None


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


async def list_blogs_view(request: RaftRequest) -> Response:
    """Public listing of approved, published blog posts using RaftSQLORM."""
    page = max(1, int(request.get_query_param("page") or 1))
    limit = min(50, max(1, int(request.get_query_param("limit") or 10)))
    offset = (page - 1) * limit

    search = (request.get_query_param("q") or "").strip()
    category_slug = (request.get_query_param("category") or "").strip()
    tag_slug = (request.get_query_param("tag") or "").strip()
    author_username = (request.get_query_param("author") or "").strip()
    sort_by = (request.get_query_param("sort") or "newest").strip().lower()

    qs = Blog.objects.filter(publication_status="published", approval_status="approved")

    if author_username:
        author = await User.objects.filter(username=author_username).afirst()
        if not author:
            return Response.success(data={"items": [], "total": 0, "page": page, "limit": limit, "total_pages": 0})
        qs = qs.filter(author_id=author.id)

    if category_slug:
        cat = await Category.objects.filter(slug=category_slug).afirst()
        if not cat:
            return Response.success(data={"items": [], "total": 0, "page": page, "limit": limit, "total_pages": 0})
        bcs = await BlogCategory.objects.filter(category_id=cat.id).alist()
        blog_ids = [bc.blog_id for bc in bcs]
        if not blog_ids:
            return Response.success(data={"items": [], "total": 0, "page": page, "limit": limit, "total_pages": 0})
        qs = qs.filter(id__in=blog_ids)

    if tag_slug:
        tag = await Tag.objects.filter(slug=tag_slug).afirst()
        if not tag:
            return Response.success(data={"items": [], "total": 0, "page": page, "limit": limit, "total_pages": 0})
        bts = await BlogTag.objects.filter(tag_id=tag.id).alist()
        blog_ids = [bt.blog_id for bt in bts]
        if not blog_ids:
            return Response.success(data={"items": [], "total": 0, "page": page, "limit": limit, "total_pages": 0})
        qs = qs.filter(id__in=blog_ids)

    if search:
        qs = qs.filter(
            Q(title__icontains=search) | Q(summary__icontains=search) | Q(content__icontains=search)
        )

    total = await qs.acount()

    if sort_by == "popular":
        qs = qs.order_by("-views_count", "-created_at")
    elif sort_by == "oldest":
        qs = qs.order_by("created_at")
    else:
        qs = qs.order_by("-created_at")

    blogs = await qs.offset(offset).limit(limit).alist()

    items = []
    for b in blogs:
        author = await User.objects.filter(id=b.author_id).afirst()
        profile = await UserProfile.objects.filter(user_id=b.author_id).afirst() if author else None
        likes_count = await Reaction.objects.filter(target_type="blog", target_id=b.id).acount()
        comments_count = await Comment.objects.filter(blog_id=b.id, is_approved=True).acount()

        bcs = await BlogCategory.objects.filter(blog_id=b.id).alist()
        cat_ids = [bc.category_id for bc in bcs]
        cats = [await Category.objects.filter(id=cid).afirst() for cid in cat_ids] if cat_ids else []
        categories = [
            CategoryResponseSchema(
                id=c.id,
                name=c.name,
                slug=c.slug,
                description=c.description or "",
            )
            for c in cats if c
        ]

        bts = await BlogTag.objects.filter(blog_id=b.id).alist()
        tag_ids = [bt.tag_id for bt in bts]
        tag_objs = [await Tag.objects.filter(id=tid).afirst() for tid in tag_ids] if tag_ids else []
        tags = [
            TagResponseSchema(
                id=t.id,
                name=t.name,
                slug=t.slug,
                description=t.description or "",
            )
            for t in tag_objs if t
        ]

        author_schema = AuthorCompactSchema(
            id=author.id if author else None,
            username=author.username if author else "",
            name=profile.full_name if profile and profile.full_name else (author.username if author else "Author"),
            avatar=profile.avatar_url if profile and profile.avatar_url else "",
        )

        item = BlogListItemSchema(
            id=b.id,
            title=b.title,
            slug=b.slug,
            summary=b.summary or "",
            featured_image=b.featured_image or "",
            views_count=int(b.views_count or 0),
            likes_count=likes_count,
            comments_count=comments_count,
            publication_status=b.publication_status,
            approval_status=b.approval_status,
            rejection_reason=b.rejection_reason or "",
            scheduled_at=b.scheduled_at,
            created_at=b.created_at,
            updated_at=b.updated_at,
            author=author_schema,
            categories=categories,
            tags=tags,
        )
        items.append(item)

    return Response.success(data={
        "items": dump(items),
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if limit > 0 else 1,
    })


async def get_blog_view(request: RaftRequest) -> Response:
    """Retrieve full blog post details by slug using RaftSQLORM."""
    slug = request.path_params.get("slug", "").strip()
    if not slug:
        raise NotFound(message="Blog slug is required.")

    blog = await Blog.objects.filter(slug=slug).afirst()
    if not blog:
        raise NotFound(message="Blog post not found.")

    claims = get_authenticated_user(request, require=False)
    current_user_id = claims["user_id"] if claims else None
    is_admin = claims.get("role") == "admin" if claims else False

    if blog.approval_status != "approved" or blog.publication_status != "published":
        if not current_user_id or (current_user_id != blog.author_id and not is_admin):
            raise NotFound(message="Blog post not found or pending approval.")

    ip = request.client_ip or ""
    ua = request.user_agent or ""
    await PageView.objects.acreate(blog_id=blog.id, ip_address=ip, user_agent=ua[:500])
    await Blog.objects.filter(id=blog.id).aupdate(views_count=blog.views_count + 1)
    blog.views_count += 1

    user_has_liked = False
    if current_user_id:
        user_has_liked = await Reaction.objects.filter(user_id=current_user_id, target_type="blog", target_id=blog.id).aexists()

    likes_count = await Reaction.objects.filter(target_type="blog", target_id=blog.id).acount()
    comments_count = await Comment.objects.filter(blog_id=blog.id, is_approved=True).acount()

    author = await User.objects.filter(id=blog.author_id).afirst()
    profile = await UserProfile.objects.filter(user_id=blog.author_id).afirst() if author else None

    bcs = await BlogCategory.objects.filter(blog_id=blog.id).alist()
    cat_ids = [bc.category_id for bc in bcs]
    cats = [await Category.objects.filter(id=cid).afirst() for cid in cat_ids] if cat_ids else []
    categories = [
        CategoryResponseSchema(
            id=c.id,
            name=c.name,
            slug=c.slug,
            description=c.description or "",
        )
        for c in cats if c
    ]

    bts = await BlogTag.objects.filter(blog_id=blog.id).alist()
    tag_ids = [bt.tag_id for bt in bts]
    tag_objs = [await Tag.objects.filter(id=tid).afirst() for tid in tag_ids] if tag_ids else []
    tags = [
        TagResponseSchema(
            id=t.id,
            name=t.name,
            slug=t.slug,
            description=t.description or "",
        )
        for t in tag_objs if t
    ]

    author_schema = AuthorCompactSchema(
        id=author.id if author else None,
        username=author.username if author else "",
        name=profile.full_name if profile and profile.full_name else (author.username if author else "Author"),
        avatar=profile.avatar_url if profile and profile.avatar_url else "",
    )

    detail_schema = BlogDetailSchema(
        id=blog.id,
        title=blog.title,
        slug=blog.slug,
        content=blog.content,
        summary=blog.summary or "",
        featured_image=blog.featured_image or "",
        views_count=int(blog.views_count or 0),
        likes_count=likes_count,
        comments_count=comments_count,
        publication_status=blog.publication_status,
        approval_status=blog.approval_status,
        rejection_reason=blog.rejection_reason or "",
        scheduled_at=blog.scheduled_at,
        created_at=blog.created_at,
        updated_at=blog.updated_at,
        has_liked=user_has_liked,
        is_liked=user_has_liked,
        is_bookmarked=False,
        author=author_schema,
        categories=categories,
        tags=tags,
    )

    data = dump(detail_schema)
    if profile:
        data["author"]["bio"] = profile.bio or ""
        data["author"]["website"] = profile.website or ""
    return Response.success(data=data)


async def create_blog_view(request: RaftRequest) -> Response:
    """Create a new blog post using RaftSQLORM."""
    claims = get_authenticated_user(request, require=True)
    author_id = claims["user_id"]

    data = await request.json() or {}
    title = str(data.get("title", "")).strip()
    content = str(data.get("content", "")).strip()
    summary = str(data.get("summary", "")).strip()
    featured_image = str(data.get("featured_image", "")).strip()
    category_ids = data.get("category_ids", [])
    tag_ids = data.get("tag_ids", [])
    action = str(data.get("action", "")).strip().lower()
    if action == "submit":
        publication_status = "published"
    elif action == "draft":
        publication_status = "draft"
    else:
        publication_status = str(data.get("publication_status", "draft")).strip().lower()

    raw_scheduled = data.get("scheduled_at")
    scheduled_at = _parse_scheduled_at(raw_scheduled)

    if not title or len(title) < 3:
        raise ValidationError(message="Blog title must be at least 3 characters long.")
    if not content or len(content) < 10:
        raise ValidationError(message="Blog content must be at least 10 characters long.")

    base_slug = _slugify(title)
    if not base_slug:
        base_slug = f"post-{secrets.token_hex(4)}"

    slug = base_slug
    counter = 1
    while await Blog.objects.filter(slug=slug).aexists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    if not summary:
        plain = re.sub(r"<[^>]+>", " ", content)
        summary = plain.strip()[:200]

    # New submissions go to pending for review (even if created by an admin), unless explicitly overridden by an admin
    if "approval_status" in data and claims.get("role") == "admin":
        approval_status = str(data["approval_status"]).strip().lower()
    else:
        approval_status = "pending"

    blog = await Blog.objects.acreate(
        author_id=author_id,
        title=title,
        slug=slug,
        content=content,
        summary=summary,
        featured_image=featured_image,
        publication_status=publication_status,
        approval_status=approval_status,
        rejection_reason="",
        scheduled_at=scheduled_at,
        views_count=0,
    )

    if category_ids:
        for cid in category_ids:
            try:
                cid = int(cid)
                if await Category.objects.filter(id=cid).aexists():
                    await BlogCategory.objects.acreate(blog_id=blog.id, category_id=cid)
            except Exception:
                pass

    if tag_ids:
        for tid in tag_ids:
            try:
                tid = int(tid)
                if await Tag.objects.filter(id=tid).aexists():
                    await BlogTag.objects.acreate(blog_id=blog.id, tag_id=tid)
            except Exception:
                pass

    item = BlogListItemSchema(
        id=blog.id,
        title=blog.title,
        slug=blog.slug,
        summary=blog.summary or "",
        featured_image=blog.featured_image or "",
        views_count=0,
        likes_count=0,
        comments_count=0,
        publication_status=blog.publication_status,
        approval_status=blog.approval_status,
        rejection_reason=blog.rejection_reason or "",
        scheduled_at=blog.scheduled_at,
        created_at=blog.created_at,
        updated_at=blog.updated_at,
    )
    return Response.created(
        data=dump(item),
        message="Blog post created successfully.",
    )


async def update_blog_view(request: RaftRequest) -> Response:
    """Update an existing blog post using RaftSQLORM."""
    claims = get_authenticated_user(request, require=True)
    author_id = claims["user_id"]
    is_admin = claims.get("role") == "admin"

    blog_id = int(request.path_params.get("id", 0))
    blog = await Blog.objects.filter(id=blog_id).afirst()
    if not blog:
        raise NotFound(message="Blog post not found.")

    if blog.author_id != author_id and not is_admin:
        raise Forbidden(message="You do not have permission to edit this blog post.")

    data = await request.json() or {}
    title = data.get("title")
    content = data.get("content")
    summary = data.get("summary")
    featured_image = data.get("featured_image")
    publication_status = data.get("publication_status")
    category_ids = data.get("category_ids")
    tag_ids = data.get("tag_ids")
    raw_scheduled = data.get("scheduled_at")

    if title is not None:
        title = str(title).strip()
        if len(title) >= 3:
            blog.title = title
    if content is not None:
        blog.content = str(content).strip()
    if summary is not None:
        blog.summary = str(summary).strip()
    if featured_image is not None:
        blog.featured_image = str(featured_image).strip()
    action = str(data.get("action", "")).strip().lower()
    if action == "submit":
        blog.publication_status = "published"
        blog.approval_status = "pending"
        blog.rejection_reason = ""
    elif action == "draft":
        blog.publication_status = "draft"
    elif publication_status is not None:
        val = str(publication_status).strip().lower()
        if val in ("draft", "published", "scheduled"):
            blog.publication_status = val

    if raw_scheduled is not None:
        blog.scheduled_at = _parse_scheduled_at(raw_scheduled)

    blog.updated_at = datetime.now()
    await blog.asave()

    if category_ids is not None:
        await BlogCategory.objects.filter(blog_id=blog.id).adelete()
        for cid in category_ids:
            try:
                cid = int(cid)
                if await Category.objects.filter(id=cid).aexists():
                    await BlogCategory.objects.acreate(blog_id=blog.id, category_id=cid)
            except Exception:
                pass

    if tag_ids is not None:
        await BlogTag.objects.filter(blog_id=blog.id).adelete()
        for tid in tag_ids:
            try:
                tid = int(tid)
                if await Tag.objects.filter(id=tid).aexists():
                    await BlogTag.objects.acreate(blog_id=blog.id, tag_id=tid)
            except Exception:
                pass

    return Response.success(data={"id": blog.id, "slug": blog.slug, "title": blog.title, "status": blog.publication_status, "approval": blog.approval_status}, message="Blog updated successfully.")


async def delete_blog_view(request: RaftRequest) -> Response:
    """Delete a blog post using RaftSQLORM."""
    claims = get_authenticated_user(request, require=True)
    user_id = claims["user_id"]
    is_admin = claims.get("role") == "admin"

    blog_id = int(request.path_params.get("id", 0))
    blog = await Blog.objects.filter(id=blog_id).afirst()
    if not blog:
        raise NotFound(message="Blog post not found.")

    if blog.author_id != user_id and not is_admin:
        raise Forbidden(message="You do not have permission to delete this blog post.")

    await BlogCategory.objects.filter(blog_id=blog.id).adelete()
    await BlogTag.objects.filter(blog_id=blog.id).adelete()
    await Reaction.objects.filter(target_type="blog", target_id=blog.id).adelete()
    await Comment.objects.filter(blog_id=blog.id).adelete()
    await PageView.objects.filter(blog_id=blog.id).adelete()
    await blog.adelete()

    return Response.success(message="Blog deleted successfully.")


async def submit_blog_view(request: RaftRequest) -> Response:
    """Submit a draft blog post for admin review using RaftSQLORM."""
    claims = get_authenticated_user(request, require=True)
    user_id = claims["user_id"]

    blog_id = int(request.path_params.get("id", 0))
    blog = await Blog.objects.filter(id=blog_id).afirst()
    if not blog:
        raise NotFound(message="Blog post not found.")

    if blog.author_id != user_id:
        raise Forbidden(message="You do not have permission to submit this blog post.")

    blog.publication_status = "published"
    blog.approval_status = "pending"
    blog.rejection_reason = ""
    await blog.asave()

    return Response.success(data={"id": blog.id, "approval_status": blog.approval_status}, message="Blog submitted for admin approval.")


async def list_user_blogs_view(request: RaftRequest) -> Response:
    """List all blogs authored by current authenticated user using RaftSQLORM."""
    claims = get_authenticated_user(request, require=True)
    user_id = claims["user_id"]

    status_filter = (request.get_query_param("status") or "").strip().lower()
    page = max(1, int(request.get_query_param("page") or 1))
    limit = min(50, max(1, int(request.get_query_param("limit") or 20)))
    offset = (page - 1) * limit

    qs = Blog.objects.filter(author_id=user_id)
    if status_filter:
        if status_filter in ("draft", "published"):
            qs = qs.filter(publication_status=status_filter)
        elif status_filter in ("pending", "approved", "rejected"):
            qs = qs.filter(approval_status=status_filter)

    total = await qs.acount()
    blogs = await qs.order_by("-updated_at").offset(offset).limit(limit).alist()

    items = []
    for b in blogs:
        likes_count = await Reaction.objects.filter(target_type="blog", target_id=b.id).acount()
        comments_count = await Comment.objects.filter(blog_id=b.id, is_approved=True).acount()

        bcs = await BlogCategory.objects.filter(blog_id=b.id).alist()
        cat_ids = [bc.category_id for bc in bcs]
        cats = [await Category.objects.filter(id=cid).afirst() for cid in cat_ids] if cat_ids else []
        categories = [
            CategoryResponseSchema(
                id=c.id,
                name=c.name,
                slug=c.slug,
                description=c.description or "",
            )
            for c in cats if c
        ]

        bts = await BlogTag.objects.filter(blog_id=b.id).alist()
        tag_ids = [bt.tag_id for bt in bts]
        tag_objs = [await Tag.objects.filter(id=tid).afirst() for tid in tag_ids] if tag_ids else []
        tags = [
            TagResponseSchema(
                id=t.id,
                name=t.name,
                slug=t.slug,
                description=t.description or "",
            )
            for t in tag_objs if t
        ]

        item = BlogListItemSchema(
            id=b.id,
            title=b.title,
            slug=b.slug,
            summary=b.summary or "",
            featured_image=b.featured_image or "",
            views_count=int(b.views_count or 0),
            likes_count=likes_count,
            comments_count=comments_count,
            publication_status=b.publication_status,
            approval_status=b.approval_status,
            rejection_reason=b.rejection_reason or "",
            scheduled_at=b.scheduled_at,
            created_at=b.created_at,
            updated_at=b.updated_at,
            categories=categories,
            tags=tags,
        )
        items.append(item)

    return Response.success(data={
        "items": dump(items),
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if limit > 0 else 1,
    })
