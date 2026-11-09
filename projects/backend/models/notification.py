import json
import logging
from typing import Any, Optional
from raftsql.orm.model import Model
from raftsql.orm.fields import (
    AutoField,
    CharField,
    TextField,
    BooleanField,
    DateTimeField,
    IntegerField,
    ForeignKey,
    CASCADE,
)
from models.user import User

logger = logging.getLogger("raft.notifications")


class Notification(Model):
    id = AutoField(primary_key=True)
    user = ForeignKey(User, on_delete=CASCADE, related_name="notifications")  # recipient
    sender = ForeignKey(User, on_delete=CASCADE)  # actor
    type = CharField(max_length=50)  # comment | reply | like_blog | like_comment | blog_approved | blog_rejected | blog_scheduled_published
    title = CharField(max_length=255)
    message = TextField()
    target_id = IntegerField(null=True, blank=True, default=None)
    target_slug = CharField(max_length=300, default="", blank=True)
    is_read = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"

    @classmethod
    async def create_and_send(
        cls,
        app: Any,
        user_id: int,
        sender_id: int,
        notif_type: str,
        title: str,
        message: str,
        target_id: Optional[int] = None,
        target_slug: str = "",
    ):
        """Create a persistent notification in PostgreSQL and broadcast to user's WebSocket room."""
        # For social likes, skip notifying oneself.
        # For editorial and review updates (blog_approved, blog_rejected), ALWAYS create and deliver notification.
        if user_id == sender_id and notif_type in ("like_blog", "like_comment"):
            return None

        try:
            notif = await cls.objects.acreate(
                user_id=user_id,
                sender_id=sender_id,
                type=notif_type,
                title=title,
                message=message,
                target_id=target_id,
                target_slug=target_slug or "",
                is_read=False,
            )

            # Dispatch real-time WebSocket notification if manager is active
            ws_manager = getattr(app, "websocket_manager", None)
            if ws_manager:
                payload = {
                    "event": "new_notification",
                    "type": "notification",
                    "data": {
                        "id": notif.id,
                        "type": notif.type,
                        "title": notif.title,
                        "message": notif.message,
                        "target_id": notif.target_id,
                        "target_slug": notif.target_slug,
                        "is_read": False,
                        "created_at": notif.created_at.isoformat() if hasattr(notif.created_at, "isoformat") else str(notif.created_at),
                    },
                }
                await ws_manager.send_to_room(f"user_{user_id}", json.dumps(payload))
                logger.info("Sent real-time notification to user_%s: %s", user_id, title)

            return notif
        except Exception as exc:
            logger.exception("Failed to create or send notification: %s", exc)
            return None


# Backward-compatible alias for existing route usages
create_and_send_notification = Notification.create_and_send
