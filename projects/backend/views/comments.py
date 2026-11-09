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
from schemas import CommentResponseSchema, dump


async def list_blog_comments_view(request: RaftRequest) -> Response:
    """Retrieve threaded comments for a blog post using RaftSQLORM."""
    blog_id = int(request.path_params.get("blog_id", 0))

    claims = get_authenticated_user(request, require=False)
    current_user_id = claims.get("user_id") if claims else None

    comments = await Comment.objects.filter(blog_id=blog_id).order_by("created_at").alist()

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
            "is_approved": c.is_approved,
            "likes_count": likes_count,
            "user_has_liked": user_has_liked,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
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

    root_comments.sort(key=lambda x: str(x["created_at"]), reverse=True)
    schemas = [CommentResponseSchema.model_validate(rc) for rc in root_comments]
    return Response.success(data=dump(schemas))


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
        raise ValidationError(message="Comment text cannot be empty.")

    if parent_id is not None:
        try:
            parent_id = int(parent_id)
            parent = await Comment.objects.filter(id=parent_id, blog_id=blog_id).afirst()
            if not parent:
                raise ValidationError(message="Parent comment does not exist.")
        except (ValueError, TypeError):
            parent_id = None

    comment = await Comment.objects.acreate(
        blog_id=blog_id,
        user_id=user_id,
        content=content,
        parent_id=parent_id,
        is_approved=True,
    )

    user = await User.objects.filter(id=user_id).afirst()
    profile = await UserProfile.objects.filter(user_id=user_id).afirst()
    app = getattr(request, "_scope", {}).get("app")

    if parent_id:
        parent_comment = await Comment.objects.filter(id=parent_id).afirst()
        if parent_comment and parent_comment.user_id != user_id:
            await create_and_send_notification(
                app=app,
                user_id=parent_comment.user_id,
                sender_id=user_id,
                notif_type="reply_comment",
                title=f"@{sender_username} replied to your comment",
                message=f"{sender_username} replied: '{content[:80]}...'",
                target_id=blog.id,
                target_slug=blog.slug,
            )
    elif blog.author_id != user_id:
        await create_and_send_notification(
            app=app,
            user_id=blog.author_id,
            sender_id=user_id,
            notif_type="new_comment",
            title=f"@{sender_username} commented on your blog",
            message=f"{sender_username} commented on '{blog.title}'",
            target_id=blog.id,
            target_slug=blog.slug,
        )

    comment_dict = {
        "id": comment.id,
        "blog_id": comment.blog_id,
        "parent_id": comment.parent_id,
        "content": comment.content,
        "is_approved": comment.is_approved,
        "likes_count": 0,
        "user_has_liked": False,
        "created_at": comment.created_at,
        "updated_at": comment.updated_at,
        "author": {
            "id": user_id,
            "username": user.username if user else "user",
            "name": profile.full_name if profile and profile.full_name else (user.username if user else "User"),
            "avatar": profile.avatar_url if profile and profile.avatar_url else "",
            "is_verified": user.is_verified if user else False,
        },
        "replies": [],
    }

    schema = CommentResponseSchema.model_validate(comment_dict)
    return Response.created(data=dump(schema), message="Comment submitted.")


async def delete_comment_view(request: RaftRequest) -> Response:
    """Delete a comment (author or admin only) using RaftSQLORM."""
    claims = get_authenticated_user(request, require=True)
    user_id = claims["user_id"]
    role = claims.get("role", "user")

    comment_id = int(request.path_params.get("id", 0))
    comment = await Comment.objects.filter(id=comment_id).afirst()
    if not comment:
        raise NotFound(message="Comment not found.")

    if comment.user_id != user_id and role != "admin":
        raise Forbidden(message="You do not have permission to delete this comment.")

    await Reaction.objects.filter(target_type="comment", target_id=comment.id).adelete()
    await Comment.objects.filter(parent_id=comment.id).adelete()
    await comment.adelete()

    return Response.success(message="Comment deleted.")


async def update_comment_view(request: RaftRequest) -> Response:
    """Update a comment (author or admin only) using RaftSQLORM."""
    claims = get_authenticated_user(request, require=True)
    user_id = claims["user_id"]
    role = claims.get("role", "user")

    comment_id = int(request.path_params.get("id", 0))
    comment = await Comment.objects.filter(id=comment_id).afirst()
    if not comment:
        raise NotFound(message="Comment not found.")

    if comment.user_id != user_id and role != "admin":
        raise Forbidden(message="You do not have permission to edit this comment.")

    data = await request.json() or {}
    content = str(data.get("content", "")).strip()
    if not content:
        raise ValidationError(message="Comment text cannot be empty.")

    comment.content = content
    await comment.asave()

    schema = CommentResponseSchema.model_validate({
        "id": comment.id,
        "blog_id": comment.blog_id,
        "parent_id": comment.parent_id,
        "content": comment.content,
        "is_approved": comment.is_approved,
        "likes_count": 0,
        "user_has_liked": False,
        "created_at": comment.created_at,
        "updated_at": comment.updated_at,
    })
    return Response.success(data=dump(schema), message="Comment updated.")
