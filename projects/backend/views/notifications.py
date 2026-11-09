"""Notification Views (List, Unread Count, Read Updates)."""

from raft import Response
from raft.core.exceptions import NotFound
from raft.core.request import RaftRequest
from models.notification import Notification
from models.user import User, UserProfile
from middleware.auth import get_authenticated_user


async def list_notifications_view(request: RaftRequest) -> Response:
    """List notifications for current user with pagination using RaftSQLORM."""
    claims = get_authenticated_user(request, require=True)
    user_id = claims["user_id"]

    page = max(1, int(request.get_query_param("page") or 1))
    limit = min(50, max(1, int(request.get_query_param("limit") or 20)))
    offset = (page - 1) * limit

    total = await Notification.objects.filter(user_id=user_id).acount()
    unread_count = await Notification.objects.filter(user_id=user_id, is_read=False).acount()
    notifs = await Notification.objects.filter(user_id=user_id).order_by("-created_at").offset(offset).limit(limit).alist()

    items = []
    for n in notifs:
        sender = await User.objects.filter(id=n.sender_id).afirst() if n.sender_id else None
        profile = await UserProfile.objects.filter(user_id=n.sender_id).afirst() if n.sender_id else None

        items.append({
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "message": n.message,
            "target_id": n.target_id,
            "target_slug": n.target_slug,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if hasattr(n.created_at, "isoformat") else str(n.created_at),
            "sender": {
                "id": n.sender_id,
                "username": sender.username if sender else "system",
                "name": profile.full_name if profile and profile.full_name else (sender.username if sender else "System"),
                "avatar": profile.avatar_url if profile and profile.avatar_url else "",
            },
        })

    return Response.success(data={
        "items": items,
        "total": total,
        "unread_count": unread_count,
        "page": page,
        "limit": limit,
    })


async def unread_count_view(request: RaftRequest) -> Response:
    """Return count of unread notifications using RaftSQLORM."""
    claims = get_authenticated_user(request, require=True)
    user_id = claims["user_id"]

    unread = await Notification.objects.filter(user_id=user_id, is_read=False).acount()
    return Response.success(data={"unread_count": unread})


async def mark_read_view(request: RaftRequest) -> Response:
    """Mark a single notification as read using RaftSQLORM."""
    claims = get_authenticated_user(request, require=True)
    user_id = claims["user_id"]
    notif_id = int(request.path_params.get("id", 0))

    notif = await Notification.objects.filter(id=notif_id, user_id=user_id).afirst()
    if not notif:
        raise NotFound(message="Notification not found.")

    notif.is_read = True
    await notif.asave()

    return Response.success(data={"id": notif.id, "is_read": True}, message="Notification marked as read.")


async def mark_all_read_view(request: RaftRequest) -> Response:
    """Mark all unread notifications for current user as read using RaftSQLORM."""
    claims = get_authenticated_user(request, require=True)
    user_id = claims["user_id"]

    await Notification.objects.filter(user_id=user_id, is_read=False).aupdate(is_read=True)
    return Response.success(message="All notifications marked as read.")

