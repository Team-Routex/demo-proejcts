"""Periodic background tasks for timed releases and automatic 48-hour approval."""

from datetime import datetime, timedelta, timezone
import logging
from typing import Any
from models.blog import Blog
from models.notification import Notification

logger = logging.getLogger("raft.tasks.blog_worker")


async def publish_scheduled_blogs(app: Any = None) -> int:
    """Timed Release Worker: Auto-publish scheduled articles when release time arrives."""
    now = datetime.now()
    published_count = 0

    try:
        # Find approved articles scheduled for release where scheduled_at <= now
        scheduled_blogs = await Blog.objects.filter(
            publication_status="scheduled",
            approval_status="approved",
        ).alist()

        for blog in scheduled_blogs:
            sched_time = getattr(blog, "scheduled_at", None)
            if sched_time and sched_time <= now:
                blog.publication_status = "published"
                blog.updated_at = now
                await blog.asave()
                published_count += 1
                logger.info(f"[Timed Release] Published scheduled blog ID={blog.id} ('{blog.title}')")

                # Notify the author
                author_id = blog.author_id if hasattr(blog, "author_id") else getattr(blog.author, "id", None)
                if author_id:
                    await Notification.create_and_send(
                        app=app,
                        user_id=author_id,
                        sender_id=author_id,  # system alert
                        notif_type="blog_scheduled_published",
                        title=f"Article Published: {blog.title}",
                        message=f"Your scheduled article '{blog.title}' has arrived at its release time and is now published!",
                        target_id=blog.id,
                        target_slug=blog.slug,
                    )
    except Exception as exc:
        logger.exception(f"[Timed Release] Worker error: {exc}")

    return published_count


async def auto_approve_pending_blogs(app: Any = None) -> int:
    """Auto-Approval Worker: Auto-approve articles pending review for more than 2 days (48 hours)."""
    cutoff = datetime.now() - timedelta(days=2)
    now = datetime.now()
    approved_count = 0

    try:
        # Find all pending articles submitted 2+ days ago
        pending_blogs = await Blog.objects.filter(approval_status="pending").alist()

        for blog in pending_blogs:
            created_at = getattr(blog, "created_at", None)
            if created_at and created_at <= cutoff:
                blog.approval_status = "approved"

                # If scheduled for a future time, set to "scheduled"; otherwise publish immediately
                sched_time = getattr(blog, "scheduled_at", None)
                if sched_time and sched_time > now:
                    blog.publication_status = "scheduled"
                else:
                    blog.publication_status = "published"

                blog.updated_at = now
                await blog.asave()
                approved_count += 1
                logger.info(f"[Auto-Approval] Auto-approved blog ID={blog.id} ('{blog.title}') after 48h review window")

                # Notify author
                author_id = blog.author_id if hasattr(blog, "author_id") else getattr(blog.author, "id", None)
                if author_id:
                    await Notification.create_and_send(
                        app=app,
                        user_id=author_id,
                        sender_id=author_id,
                        notif_type="blog_approved",
                        title=f"Article Auto-Approved: {blog.title}",
                        message=f"Your article '{blog.title}' was automatically approved after the 2-day review window.",
                        target_id=blog.id,
                        target_slug=blog.slug,
                    )
    except Exception as exc:
        logger.exception(f"[Auto-Approval] Worker error: {exc}")

    return approved_count
