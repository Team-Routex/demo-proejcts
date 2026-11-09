"""Comment HTTP Route Definitions (Router and Route Table)."""

from raft import route, Router
from views.comments import (
    list_blog_comments_view,
    create_comment_view,
    update_comment_view,
    delete_comment_view,
)

# Demonstrates Router decorators for comment mutation routes
router = Router(prefix="/api/comments")
router.put("/{id}")(update_comment_view)
router.delete("/{id}")(delete_comment_view)

# Demonstrates route() table list for blog comment nested routes
routes = [
    route("/api/blogs/{blog_id}/comments", list_blog_comments_view, methods=["GET"]),
    route("/api/blogs/{blog_id}/comments", create_comment_view, methods=["POST"]),
    route("/api/comments/{id}", update_comment_view, methods=["PUT"]),
    route("/api/comments/{id}", delete_comment_view, methods=["DELETE"]),
]
