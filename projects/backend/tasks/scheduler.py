"""RaftFramework Task Scheduler registration for background workers."""

from typing import Any
try:
    from tasks.periodic import publish_scheduled_blogs, auto_approve_pending_blogs
except ImportError:
    from .periodic import publish_scheduled_blogs, auto_approve_pending_blogs


def register_scheduled_tasks(app: Any) -> None:
    """Attach background workers to the Raft application lifecycle."""

    @app.task(every=30, repeat=True, run_immediately=True)
    async def timed_release_worker() -> None:
        """Checks for scheduled articles whose release time has arrived."""
        await publish_scheduled_blogs(app)

    @app.task(every=60, repeat=True, run_immediately=True)
    async def auto_approval_worker() -> None:
        """Auto-approves pending submissions older than 2 days (48 hours)."""
        await auto_approve_pending_blogs(app)
