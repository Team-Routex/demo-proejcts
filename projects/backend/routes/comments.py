"""Comment HTTP Route Definitions (Router and Route Table)."""

from raft import Router
from views.comments import (
    list_blog_comments_view,
    create_comment_view,
    update_comment_view,
    delete_comment_view,
)

# Demonstrates Router with method decorators for comments
router = Router()
router.get("/api/blogs/{blog_id}/comments")(list_blog_comments_view)
router.post("/api/blogs/{blog_id}/comments")(create_comment_view)
router.put("/api/comments/{id}")(update_comment_view)
router.delete("/api/comments/{id}")(delete_comment_view)
