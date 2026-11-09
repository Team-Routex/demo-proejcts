"""Comment and Discussion Views."""

from raft import Response
from raft.core.exceptions import ValidationError, NotFound, Forbidden
from raft.core.request import RaftRequest
from models.comment import Comment
from models.blog import Blog
from models.user import User, UserProfile
from models.reaction import Reaction
from middleware.auth import get_authenticated_user
from models.notification import create_and_send_notification


async def list_blog_comments_view(request: RaftRequest) -> Response:
    """Retrieve threaded comments for a blog post using RaftSQLORM."""
    blog_id = int(request.path_params.get("blog_id", 0))

    claims = get_authenticated_user(request, require=False)
    current_user_id = claims.get("user_id") if claims else None

    comments = await Comment.objects.filter(blog_id=blog_id, is_approved=True).order_by("created_at").alist()

    comments_by_id = {}
    root_comments = []

    for c in comments:
        user = await User.objects.filter(id=c.user_id).afirst()
        profile = await UserProfile.objects.filter(user_id=c.user_id).afirst() if user else None
        likes_count = await Reaction.objects.filter(target_type="comment", target_id=c.id).acount()

        user_has_liked = False
        if current_user_id:
            user_has_liked = await Reaction.objects.filter(
                user_id=current_user_id,
                target_type="comment",
                target_id=c.id,
            ).aexists()

        c_obj = {
            "id": c.id,
            "blog_id": c.blog_id,
            "parent_id": c.parent_id,
            "content": c.content,
            "likes_count": likes_count,
            "user_has_liked": user_has_liked,
            "created_at": c.created_at.isoformat() if hasattr(c.created_at, "isoformat") else str(c.created_at),
            "updated_at": c.updated_at.isoformat() if hasattr(c.updated_at, "isoformat") else str(c.updated_at),
            "author": {
                "id": c.user_id,
                "username": user.username if user else "anonymous",
                "name": profile.full_name if profile and profile.full_name else (user.username if user else "Anonymous"),
                "avatar": profile.avatar_url if profile and profile.avatar_url else "",
                "is_verified": user.is_verified if user else False,
            },
            "replies": [],
        }
        comments_by_id[c.id] = c_obj

    for cid, c_obj in comments_by_id.items():
        pid = c_obj["parent_id"]
        if pid and pid in comments_by_id:
            comments_by_id[pid]["replies"].append(c_obj)
        else:
            root_comments.append(c_obj)

    root_comments.sort(key=lambda x: x["created_at"], reverse=True)
    return Response.success(data=root_comments)


async def create_comment_view(request: RaftRequest) -> Response:
    """Create a comment or reply to an existing comment using RaftSQLORM."""
    claims = get_authenticated_user(request, require=True)
    user_id = claims["user_id"]
    sender_username = claims.get("username", "Someone")

    blog_id = int(request.path_params.get("blog_id", 0))
    blog = await Blog.objects.filter(id=blog_id).afirst()
    if not blog:
        raise NotFound(message="Blog post not found.")

    data = await request.json() or {}
    content = str(data.get("content", "")).strip()
    parent_id = data.get("parent_id")

    if not content:
        raise ValidationError(message="Comment content cannot be empty.")

    parent_comment = None
    if parent_id is not None:
        parent_id = int(parent_id)
        parent_comment = await Comment.objects.filter(id=parent_id, blog_id=blog_id).afirst()
        if not parent_comment:
            raise NotFound(message="Parent comment not found.")

    comment = await Comment.objects.acreate(
        blog_id=blog_id,
        user_id=user_id,
        parent_id=parent_id,
        content=content,
        is_approved=True,
    )

    app = getattr(request, "_scope", {}).get("app")

    if parent_comment:
        if parent_comment.user_id != user_id:
            await create_and_send_notification(
                app=app,
                user_id=parent_comment.user_id,
                sender_id=user_id,
                notif_type="reply",
                title=f"New reply from @{sender_username}",
                message=f"{sender_username} replied to your comment on '{blog.title}': \"{content[:80]}\"",
                target_id=blog.id,
                target_slug=blog.slug,
            )
    else:
        if blog.author_id != user_id:
            await create_and_send_notification(
                app=app,
                user_id=blog.author_id,
                sender_id=user_id,
                notif_type="comment",
                title=f"New comment on '{blog.title}'",
                message=f"{sender_username} commented: \"{content[:80]}\"",
                target_id=blog.id,
                target_slug=blog.slug,
            )

    profile = await UserProfile.objects.filter(user_id=user_id).afirst()

    return Response.created(
        data={
            "id": comment.id,
            "blog_id": comment.blog_id,
            "parent_id": comment.parent_id,
            "content": comment.content,
            "likes_count": 0,
            "user_has_liked": False,
            "created_at": comment.created_at.isoformat() if hasattr(comment.created_at, "isoformat") else str(comment.created_at),
            "author": {
                "id": user_id,
                "username": claims["username"],
                "name": profile.full_name if profile and profile.full_name else claims["username"],
                "avatar": profile.avatar_url if profile and profile.avatar_url else "",
            },
            "replies": [],
        },
        message="Comment posted successfully.",
    )


async def update_comment_view(request: RaftRequest) -> Response:
    """Update a comment using RaftSQLORM."""
    claims = get_authenticated_user(request, require=True)
    user_id = claims["user_id"]
    is_admin = claims.get("role") == "admin"

    comment_id = int(request.path_params.get("id", 0))
    comment = await Comment.objects.filter(id=comment_id).afirst()
    if not comment:
        raise NotFound(message="Comment not found.")

    if comment.user_id != user_id and not is_admin:
        raise Forbidden(message="You do not have permission to edit this comment.")

    data = await request.json() or {}
    content = str(data.get("content", "")).strip()
    if not content:
        raise ValidationError(message="Comment content cannot be empty.")

    comment.content = content
    await comment.asave()

    return Response.success(data={"id": comment.id, "content": comment.content}, message="Comment updated successfully.")


async def delete_comment_view(request: RaftRequest) -> Response:
    """Delete a comment using RaftSQLORM."""
    claims = get_authenticated_user(request, require=True)
    user_id = claims["user_id"]
    is_admin = claims.get("role") == "admin"

    comment_id = int(request.path_params.get("id", 0))
    comment = await Comment.objects.filter(id=comment_id).afirst()
    if not comment:
        raise NotFound(message="Comment not found.")

    if comment.user_id != user_id and not is_admin:
        raise Forbidden(message="You do not have permission to delete this comment.")

    await Reaction.objects.filter(target_type="comment", target_id=comment.id).adelete()
    await Comment.objects.filter(parent_id=comment.id).adelete()
    await comment.adelete()

    return Response.success(message="Comment deleted successfully.")

