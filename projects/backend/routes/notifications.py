"""Notification HTTP Route Definitions (Router and Route Table)."""

from raft import route, Router
from views.notifications import (
    list_notifications_view,
    unread_count_view,
    mark_read_view,
    mark_all_read_view,
)

# Demonstrates Router prefix and decorators
router = Router(prefix="/api/notifications")
router.get("")(list_notifications_view)
router.get("/")(list_notifications_view)
router.get("/unread-count")(unread_count_view)
router.post("/{id}/read")(mark_read_view)
router.post("/read-all")(mark_all_read_view)

# Demonstrates route() table list
routes = [
    route("/api/notifications", list_notifications_view, methods=["GET"]),
    route("/api/notifications/unread-count", unread_count_view, methods=["GET"]),
    route("/api/notifications/{id}/read", mark_read_view, methods=["POST"]),
    route("/api/notifications/read-all", mark_all_read_view, methods=["POST"]),
]
