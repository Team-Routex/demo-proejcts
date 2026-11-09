"""Reaction and Engagement Views (Likes & Status)."""

from raft import Response
from raft.core.exceptions import ValidationError
from raft.core.request import RaftRequest
from models.reaction import Reaction
from models.blog import Blog
from models.comment import Comment
from middleware.auth import get_authenticated_user
from models.notification import create_and_send_notification


async def toggle_reaction_view(request: RaftRequest) -> Response:
    """Toggle like/unlike for a blog post or comment using RaftSQLORM."""
    claims = get_authenticated_user(request, require=True)
    user_id = claims["user_id"]
    sender_username = claims.get("username", "Someone")

    data = await request.json() or {}
    target_type = str(data.get("target_type", "")).strip().lower()
    target_id = int(data.get("target_id", 0))

    if target_type not in ("blog", "comment"):
        raise ValidationError(message="target_type must be 'blog' or 'comment'.")
    if target_id <= 0:
        raise ValidationError(message="Valid target_id is required.")

    app = getattr(request, "_scope", {}).get("app")

    existing = await Reaction.objects.filter(
        user_id=user_id,
        target_type=target_type,
        target_id=target_id,
    ).afirst()

    if existing:
        await existing.adelete()
        liked = False
    else:
        await Reaction.objects.acreate(
            user_id=user_id,
            target_type=target_type,
            target_id=target_id,
            reaction_type="like",
        )
        liked = True

    new_count = await Reaction.objects.filter(target_type=target_type, target_id=target_id).acount()

    if liked:
        if target_type == "blog":
            blog = await Blog.objects.filter(id=target_id).afirst()
            if blog and blog.author_id != user_id:
                await create_and_send_notification(
                    app=app,
                    user_id=blog.author_id,
                    sender_id=user_id,
                    notif_type="like_blog",
                    title=f"@{sender_username} liked your blog",
                    message=f"{sender_username} liked your post '{blog.title}'",
                    target_id=blog.id,
                    target_slug=blog.slug,
                )
        elif target_type == "comment":
            comment = await Comment.objects.filter(id=target_id).afirst()
            if comment and comment.user_id != user_id:
                blog = await Blog.objects.filter(id=comment.blog_id).afirst()
                blog_title = blog.title if blog else "a post"
                blog_slug = blog.slug if blog else ""
                await create_and_send_notification(
                    app=app,
                    user_id=comment.user_id,
                    sender_id=user_id,
                    notif_type="like_comment",
                    title=f"@{sender_username} liked your comment",
                    message=f"{sender_username} liked your comment on '{blog_title}'",
                    target_id=comment.blog_id,
                    target_slug=blog_slug,
                )

    return Response.success(
        data={"target_type": target_type, "target_id": target_id, "liked": liked, "likes_count": new_count},
        message="Liked." if liked else "Unliked.",
    )


async def get_reaction_status_view(request: RaftRequest) -> Response:
    """Check reaction status for target items using RaftSQLORM."""
    claims = get_authenticated_user(request, require=False)
    user_id = claims.get("user_id") if claims else None

    target_type = request.get_query_param("target_type", "blog")
    target_ids_param = request.get_query_param("target_ids", "")

    if not target_ids_param:
        return Response.success(data={})

    ids = [int(i.strip()) for i in target_ids_param.split(",") if i.strip().isdigit()]
    if not ids:
        return Response.success(data={})

    results = {}
    for item_id in ids:
        count = await Reaction.objects.filter(target_type=target_type, target_id=item_id).acount()
        has_liked = False
        if user_id:
            has_liked = await Reaction.objects.filter(
                user_id=user_id,
                target_type=target_type,
                target_id=item_id,
            ).aexists()

        results[item_id] = {
            "likes_count": count,
            "user_has_liked": has_liked,
        }

    return Response.success(data=results)

