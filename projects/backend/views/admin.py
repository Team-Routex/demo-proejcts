"""Admin Console and Telemetry Views."""

import datetime
from raft import Response
from raft.core.exceptions import HTTPException, NotFound
from raft.core.request import RaftRequest
from raftsql.orm.q import Q
from models.user import User, UserProfile
from models.blog import Blog, Category, BlogCategory
from models.comment import Comment
from models.reaction import Reaction
from models.analytics import PageView
from middleware.auth import require_admin
from models.notification import create_and_send_notification
from schemas import (
    AdminOverviewSchema,
    AdminBlogListItemSchema,
    AdminUserListItemSchema,
    CategoryResponseSchema,
    dump,
)


async def admin_overview_view(request: RaftRequest) -> Response:
    """Return dashboard summary metrics for the admin panel using RaftSQLORM."""
    require_admin(request)

    users_count = await User.objects.acount()
    blogs_count = await Blog.objects.acount()
    views_count = await PageView.objects.acount()

    likes_count = await Reaction.objects.acount()
    comments_count = await Comment.objects.acount()
    total_interactions = likes_count + comments_count

    pending_blogs = await Blog.objects.filter(approval_status="pending").acount()
    approved_blogs = await Blog.objects.filter(approval_status="approved").acount()

    overview_data = {
        "total_users": users_count,
        "total_blogs": blogs_count,
        "total_visits": views_count,
        "total_interactions": total_interactions,
        "breakdown": {
            "likes": likes_count,
            "comments": comments_count,
            "pending_blogs": pending_blogs,
            "approved_blogs": approved_blogs,
        },
    }
    return Response.success(data=dump(AdminOverviewSchema(**overview_data)))


async def admin_analytics_view(request: RaftRequest) -> Response:
    """Return data series for the 3 required analytics charts using RaftSQLORM."""
    require_admin(request)

    days = max(1, min(365, int(request.get_query_param("days") or 30)))
    now = datetime.datetime.now()
    start_date = now - datetime.timedelta(days=days)

    all_days = [
        (start_date + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(days + 1)
    ]

    # Chart 1: User registrations over time
    recent_users = await User.objects.filter(created_at__gte=start_date).alist()
    user_counts_by_day = {d: 0 for d in all_days}
    for u in recent_users:
        if u.created_at:
            day = u.created_at.strftime("%Y-%m-%d")
            if day in user_counts_by_day:
                user_counts_by_day[day] += 1
            else:
                user_counts_by_day[day] = 1

    chart1_data = [
        {"day": day, "count": user_counts_by_day[day]}
        for day in all_days
    ]

    # Chart 2: Blog publishing over time (pending vs approved)
    recent_blogs = await Blog.objects.filter(created_at__gte=start_date).alist()
    blog_pub_by_day = {d: {"approved_count": 0, "pending_count": 0} for d in all_days}
    for b in recent_blogs:
        if b.created_at:
            day = b.created_at.strftime("%Y-%m-%d")
            if day not in blog_pub_by_day:
                blog_pub_by_day[day] = {"approved_count": 0, "pending_count": 0}
            if b.approval_status == "approved":
                blog_pub_by_day[day]["approved_count"] += 1
            elif b.approval_status == "pending":
                blog_pub_by_day[day]["pending_count"] += 1

    chart2_data = [
        {
            "day": day,
            "approved_count": blog_pub_by_day[day]["approved_count"],
            "pending_count": blog_pub_by_day[day]["pending_count"],
        }
        for day in all_days
    ]

    # Chart 3: User interaction activity over time (likes vs comments vs replies)
    recent_reactions = await Reaction.objects.filter(created_at__gte=start_date).alist()
    recent_comments = await Comment.objects.filter(created_at__gte=start_date).alist()

    interactions_by_day = {d: {"likes": 0, "comments": 0, "replies": 0} for d in all_days}
    for r in recent_reactions:
        if r.created_at:
            day = r.created_at.strftime("%Y-%m-%d")
            if day not in interactions_by_day:
                interactions_by_day[day] = {"likes": 0, "comments": 0, "replies": 0}
            interactions_by_day[day]["likes"] += 1

    for c in recent_comments:
        if c.created_at:
            day = c.created_at.strftime("%Y-%m-%d")
            if day not in interactions_by_day:
                interactions_by_day[day] = {"likes": 0, "comments": 0, "replies": 0}
            if c.parent_id:
                interactions_by_day[day]["replies"] += 1
            else:
                interactions_by_day[day]["comments"] += 1

    chart3_data = [
        {
            "day": day,
            "likes": interactions_by_day[day]["likes"],
            "comments": interactions_by_day[day]["comments"],
            "replies": interactions_by_day[day]["replies"],
            "total": (
                interactions_by_day[day]["likes"]
                + interactions_by_day[day]["comments"]
                + interactions_by_day[day]["replies"]
            ),
        }
        for day in all_days
    ]

    return Response.success(data={
        "user_registrations": chart1_data,
        "blog_publishing": chart2_data,
        "user_interactions": chart3_data,
    })


async def admin_top_blogs_view(request: RaftRequest) -> Response:
    """Return top 5 most popular blogs ranked by engagement score using RaftSQLORM."""
    require_admin(request)

    blogs = await Blog.objects.filter(
        publication_status="published",
        approval_status="approved",
    ).alist()

    ranked_blogs = []
    for b in blogs:
        author = await User.objects.filter(id=b.author_id).afirst()
        likes_count = await Reaction.objects.filter(target_type="blog", target_id=b.id).acount()
        comments_count = await Comment.objects.filter(blog_id=b.id, is_approved=True, parent_id__isnull=True).acount()
        replies_count = await Comment.objects.filter(blog_id=b.id, is_approved=True).exclude(parent_id__isnull=True).acount()

        score = (b.views_count * 1) + (likes_count * 3) + (comments_count * 4) + (replies_count * 5)
        ranked_blogs.append({
            "id": b.id,
            "title": b.title,
            "slug": b.slug,
            "author": author.username if author else "Unknown",
            "author_id": b.author_id,
            "total_views": int(b.views_count),
            "total_likes": likes_count,
            "total_comments": comments_count,
            "total_replies": replies_count,
            "engagement_score": score,
            "approval_status": b.approval_status,
            "publication_status": b.publication_status,
            "publication_date": b.created_at.isoformat() if hasattr(b.created_at, "isoformat") else str(b.created_at),
        })

    ranked_blogs.sort(key=lambda x: x["engagement_score"], reverse=True)
    return Response.success(data=ranked_blogs[:5])


async def admin_top_authors_view(request: RaftRequest) -> Response:
    """Return top 5 most active/popular authors ranked by engagement using RaftSQLORM."""
    require_admin(request)

    users = await User.objects.alist()
    ranked_authors = []

    for u in users:
        total_blogs = await Blog.objects.filter(author_id=u.id).acount()
        if total_blogs == 0:
            continue

        approved_blogs = await Blog.objects.filter(author_id=u.id, approval_status="approved").acount()
        profile = await UserProfile.objects.filter(user_id=u.id).afirst()

        author_blogs = await Blog.objects.filter(author_id=u.id).alist()
        total_views = sum(int(b.views_count) for b in author_blogs)

        blog_ids = [b.id for b in author_blogs]
        total_likes = 0
        total_comments = 0
        total_replies = 0

        if blog_ids:
            for bid in blog_ids:
                total_likes += await Reaction.objects.filter(target_type="blog", target_id=bid).acount()
                total_comments += await Comment.objects.filter(blog_id=bid, parent_id__isnull=True).acount()
                total_replies += await Comment.objects.filter(blog_id=bid).exclude(parent_id__isnull=True).acount()

        total_engagement = (total_views * 1) + (total_likes * 3) + (total_comments * 4) + (total_replies * 5)

        ranked_authors.append({
            "id": u.id,
            "author_name": profile.full_name if profile and profile.full_name else u.username,
            "username": u.username,
            "profile_image": profile.avatar_url if profile and profile.avatar_url else "",
            "avatar_url": profile.avatar_url if profile and profile.avatar_url else "",
            "total_blogs": total_blogs,
            "approved_blogs": approved_blogs,
            "total_views": total_views,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_replies": total_replies,
            "total_engagement": total_engagement,
        })

    ranked_authors.sort(key=lambda x: x["total_engagement"], reverse=True)
    return Response.success(data=ranked_authors[:5])


async def admin_list_users_view(request: RaftRequest) -> Response:
    """List users with search, role filters, and pagination using RaftSQLORM."""
    require_admin(request)

    page = max(1, int(request.get_query_param("page") or 1))
    limit = min(50, max(1, int(request.get_query_param("limit") or 10)))
    offset = (page - 1) * limit
    search = (request.get_query_param("q") or "").strip().lower()
    role_filter = (request.get_query_param("role") or "").strip().lower()

    qs = User.objects.filter()
    if role_filter:
        qs = qs.filter(role=role_filter)
    if search:
        qs = qs.filter(Q(username__icontains=search) | Q(email__icontains=search))

    total = await qs.acount()
    users_list = await qs.order_by("-created_at").offset(offset).limit(limit).alist()

    users = []
    for u in users_list:
        profile = await UserProfile.objects.filter(user_id=u.id).afirst()
        total_blogs = await Blog.objects.filter(author_id=u.id).acount()
        likes_given = await Reaction.objects.filter(user_id=u.id).acount()
        comments_given = await Comment.objects.filter(user_id=u.id).acount()

        users.append({
            "id": u.id,
            "username": u.username,
            "name": profile.full_name if profile and profile.full_name else u.username,
            "email": u.email,
            "role": u.role,
            "is_verified": u.is_verified,
            "is_active": u.is_active,
            "avatar_url": profile.avatar_url if profile and profile.avatar_url else "",
            "total_blogs": total_blogs,
            "total_interactions": likes_given + comments_given,
            "registration_date": u.created_at.isoformat() if hasattr(u.created_at, "isoformat") else str(u.created_at),
        })

    user_schemas = [AdminUserListItemSchema(**u) for u in users]
    return Response.success(data={
        "items": dump(user_schemas),
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if limit > 0 else 1,
    })


async def admin_toggle_verify_user_view(request: RaftRequest) -> Response:
    """Verify or unverify user using RaftSQLORM."""
    require_admin(request)
    target_user_id = int(request.path_params.get("id", 0))

    user = await User.objects.filter(id=target_user_id).afirst()
    if not user:
        raise NotFound(message="User not found.")

    user.is_verified = not user.is_verified
    await user.asave()

    return Response.success(data={"id": user.id, "is_verified": user.is_verified}, message=f"User {'verified' if user.is_verified else 'unverified'} successfully.")


async def admin_toggle_status_user_view(request: RaftRequest) -> Response:
    """Activate or deactivate user using RaftSQLORM."""
    admin_claims = require_admin(request)
    target_user_id = int(request.path_params.get("id", 0))

    if admin_claims["user_id"] == target_user_id:
        raise HTTPException(status_code=400, message="Administrators cannot deactivate their own account.")

    user = await User.objects.filter(id=target_user_id).afirst()
    if not user:
        raise NotFound(message="User not found.")

    user.is_active = not user.is_active
    await user.asave()

    return Response.success(data={"id": user.id, "is_active": user.is_active}, message=f"User {'activated' if user.is_active else 'deactivated'} successfully.")


async def admin_delete_user_view(request: RaftRequest) -> Response:
    """Delete user using RaftSQLORM."""
    admin_claims = require_admin(request)
    target_user_id = int(request.path_params.get("id", 0))

    if admin_claims["user_id"] == target_user_id:
        raise HTTPException(status_code=400, message="Administrators cannot delete their own account.")

    user = await User.objects.filter(id=target_user_id).afirst()
    if not user:
        raise NotFound(message="User not found.")

    await UserProfile.objects.filter(user_id=user.id).adelete()
    await Reaction.objects.filter(user_id=user.id).adelete()
    await Comment.objects.filter(user_id=user.id).adelete()
    await user.adelete()

    return Response.success(message="User deleted successfully.")


async def admin_update_user_view(request: RaftRequest) -> Response:
    """Update user information using RaftSQLORM."""
    require_admin(request)
    user_id = int(request.path_params.get("id", 0))
    user = await User.objects.filter(id=user_id).afirst()
    if not user:
        raise NotFound(message="User not found.")

    data = await request.json() or {}
    if "full_name" in data:
        profile = await UserProfile.objects.filter(user_id=user.id).afirst()
        if profile:
            profile.full_name = str(data["full_name"]).strip()
            await profile.asave()
    if "role" in data:
        user.role = str(data["role"]).strip()
    if "is_verified" in data:
        user.is_verified = bool(data["is_verified"])
    if "is_active" in data:
        user.is_active = bool(data["is_active"])

    await user.asave()
    return Response.success(data={"id": user.id, "username": user.username, "role": user.role, "is_verified": user.is_verified, "is_active": user.is_active}, message="User updated.")


async def admin_list_blogs_view(request: RaftRequest) -> Response:
    """List all blogs for moderation using RaftSQLORM."""
    require_admin(request)

    page = max(1, int(request.get_query_param("page") or 1))
    limit = min(50, max(1, int(request.get_query_param("limit") or 10)))
    offset = (page - 1) * limit
    status = (request.get_query_param("status") or "").strip().lower()
    search = (request.get_query_param("q") or "").strip().lower()

    qs = Blog.objects.filter()
    if status:
        if status in ("approved", "pending", "rejected"):
            qs = qs.filter(approval_status=status)
        elif status == "draft":
            qs = qs.filter(publication_status="draft")

    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(slug__icontains=search))

    total = await qs.acount()
    blogs_list = await qs.order_by("-created_at").offset(offset).limit(limit).alist()

    blogs = []
    for b in blogs_list:
        author = await User.objects.filter(id=b.author_id).afirst()
        profile = await UserProfile.objects.filter(user_id=b.author_id).afirst() if author else None
        likes_count = await Reaction.objects.filter(target_type="blog", target_id=b.id).acount()
        comments_count = await Comment.objects.filter(blog_id=b.id).acount()

        author_data = {
            "id": author.id if author else None,
            "username": author.username if author else "Unknown",
            "full_name": profile.full_name if profile and profile.full_name else (author.username if author else "Unknown"),
            "avatar_url": profile.avatar_url if profile and profile.avatar_url else "",
        }

        blogs.append({
            "id": b.id,
            "title": b.title,
            "slug": b.slug,
            "summary": b.summary,
            "author": author_data,
            "author_username": author.username if author else "Unknown",
            "publication_status": b.publication_status,
            "approval_status": b.approval_status,
            "rejection_reason": b.rejection_reason or "",
            "views_count": int(b.views_count),
            "likes_count": likes_count,
            "comments_count": comments_count,
            "created_at": b.created_at.isoformat() if hasattr(b.created_at, "isoformat") else str(b.created_at),
            "updated_at": b.updated_at.isoformat() if hasattr(b.updated_at, "isoformat") else str(b.updated_at),
        })

    blog_schemas = [AdminBlogListItemSchema(**b) for b in blogs]
    return Response.success(data={
        "items": dump(blog_schemas),
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if limit > 0 else 1,
    })


async def admin_approve_blog_view(request: RaftRequest) -> Response:
    """Approve a blog post using RaftSQLORM."""
    admin_claims = require_admin(request)
    blog_id = int(request.path_params.get("id", 0))

    blog = await Blog.objects.filter(id=blog_id).afirst()
    if not blog:
        raise NotFound(message="Blog not found.")

    blog.approval_status = "approved"
    blog.publication_status = "published"
    blog.rejection_reason = ""
    await blog.asave()

    app = getattr(request, "app", None) or getattr(request, "_scope", {}).get("app")
    await create_and_send_notification(
        app=app,
        user_id=blog.author_id,
        sender_id=admin_claims["user_id"],
        notif_type="blog_approved",
        title="Blog Approved! 🎉",
        message=f"Your blog post '{blog.title}' has been reviewed and approved. It is now publicly visible.",
        target_id=blog.id,
        target_slug=blog.slug,
    )

    return Response.success(data={"id": blog.id, "approval_status": "approved"}, message="Blog post approved.")


async def admin_reject_blog_view(request: RaftRequest) -> Response:
    """Reject a blog post with reason using RaftSQLORM."""
    admin_claims = require_admin(request)
    blog_id = int(request.path_params.get("id", 0))

    blog = await Blog.objects.filter(id=blog_id).afirst()
    if not blog:
        raise NotFound(message="Blog not found.")

    data = await request.json() or {}
    reason = str(data.get("rejection_reason") or data.get("reason") or "Content does not meet publication guidelines.").strip()

    blog.approval_status = "rejected"
    blog.rejection_reason = reason
    await blog.asave()

    app = getattr(request, "app", None) or getattr(request, "_scope", {}).get("app")
    await create_and_send_notification(
        app=app,
        user_id=blog.author_id,
        sender_id=admin_claims["user_id"],
        notif_type="blog_rejected",
        title="Blog Post Update",
        message=f"Your blog post '{blog.title}' was rejected: {reason}",
        target_id=blog.id,
        target_slug=blog.slug,
    )

    return Response.success(data={"id": blog.id, "approval_status": "rejected", "rejection_reason": reason, "reason": reason}, message="Blog post rejected.")


async def admin_moderate_blog_view(request: RaftRequest) -> Response:
    data = await request.json() or {}
    action = data.get("action", "approve")
    if action == "reject":
        return await admin_reject_blog_view(request)
    return await admin_approve_blog_view(request)


async def admin_delete_blog_view(request: RaftRequest) -> Response:
    """Delete a blog post using RaftSQLORM."""
    require_admin(request)
    blog_id = int(request.path_params.get("id", 0))

    blog = await Blog.objects.filter(id=blog_id).afirst()
    if not blog:
        raise NotFound(message="Blog not found.")

    await BlogCategory.objects.filter(blog_id=blog.id).adelete()
    await Reaction.objects.filter(target_type="blog", target_id=blog.id).adelete()
    await Comment.objects.filter(blog_id=blog.id).adelete()
    await PageView.objects.filter(blog_id=blog.id).adelete()
    await blog.adelete()

    return Response.success(message="Blog deleted successfully.")


async def admin_list_comments_view(request: RaftRequest) -> Response:
    """List comments for moderation using RaftSQLORM."""
    require_admin(request)

    page = max(1, int(request.get_query_param("page") or 1))
    limit = min(50, max(1, int(request.get_query_param("limit") or 10)))
    offset = (page - 1) * limit
    search = (request.get_query_param("q") or "").strip().lower()

    qs = Comment.objects.filter()
    if search:
        qs = qs.filter(content__icontains=search)

    total = await qs.acount()
    comments_list = await qs.order_by("-created_at").offset(offset).limit(limit).alist()

    items = []
    for c in comments_list:
        user = await User.objects.filter(id=c.user_id).afirst()
        profile = await UserProfile.objects.filter(user_id=c.user_id).afirst() if user else None
        blog = await Blog.objects.filter(id=c.blog_id).afirst()
        reply_count = await Comment.objects.filter(parent_id=c.id).acount()

        user_data = {
            "id": user.id if user else None,
            "username": user.username if user else "Unknown",
            "full_name": profile.full_name if profile and profile.full_name else (user.username if user else "Unknown"),
            "avatar_url": profile.avatar_url if profile and profile.avatar_url else "",
        }

        items.append({
            "id": c.id,
            "blog_id": c.blog_id,
            "blog_title": blog.title if blog else "Deleted Blog",
            "blog_slug": blog.slug if blog else "",
            "author": user_data["full_name"],
            "user": user_data,
            "content": c.content,
            "parent_id": c.parent_id,
            "is_reply": bool(c.parent_id),
            "reply_count": reply_count,
            "is_approved": c.is_approved,
            "created_at": c.created_at.isoformat() if hasattr(c.created_at, "isoformat") else str(c.created_at),
        })

    return Response.success(data={
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if limit > 0 else 1,
    })


async def admin_delete_comment_view(request: RaftRequest) -> Response:
    """Delete a comment using RaftSQLORM."""
    require_admin(request)
    comment_id = int(request.path_params.get("id", 0))

    comment = await Comment.objects.filter(id=comment_id).afirst()
    if not comment:
        raise NotFound(message="Comment not found.")

    await Reaction.objects.filter(target_type="comment", target_id=comment.id).adelete()
    await Comment.objects.filter(parent_id=comment.id).adelete()
    await comment.adelete()

    return Response.success(message="Comment deleted successfully.")


async def admin_list_categories_view(request: RaftRequest) -> Response:
    """List categories for admin management using RaftSQLORM."""
    require_admin(request)
    cats = await Category.objects.order_by("name").alist()

    items = []
    for c in cats:
        blog_count = await BlogCategory.objects.filter(category_id=c.id).acount()
        items.append({
            "id": c.id,
            "name": c.name,
            "slug": c.slug,
            "description": c.description or "",
            "blog_count": blog_count,
            "created_at": c.created_at.isoformat() if hasattr(c.created_at, "isoformat") else str(c.created_at),
        })

    serialized_cats = dump([CategoryResponseSchema(**c) for c in items])
    return Response.success(data=serialized_cats)


async def admin_update_category_view(request: RaftRequest) -> Response:
    """Update a category using RaftSQLORM."""
    require_admin(request)
    cat_id = int(request.path_params.get("id", 0))

    cat = await Category.objects.filter(id=cat_id).afirst()
    if not cat:
        raise NotFound(message="Category not found.")

    data = await request.json() or {}
    if "name" in data:
        name = str(data["name"]).strip()
        if len(name) >= 2:
            cat.name = name
    if "description" in data:
        cat.description = str(data["description"]).strip()

    await cat.asave()
    return Response.success(data={"id": cat.id, "name": cat.name, "description": cat.description}, message="Category updated successfully.")


async def admin_delete_category_view(request: RaftRequest) -> Response:
    """Delete a category using RaftSQLORM."""
    require_admin(request)
    cat_id = int(request.path_params.get("id", 0))

    cat = await Category.objects.filter(id=cat_id).afirst()
    if not cat:
        raise NotFound(message="Category not found.")

    await BlogCategory.objects.filter(category_id=cat.id).adelete()
    await cat.adelete()
    return Response.success(message="Category deleted successfully.")

