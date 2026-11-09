"""Comment HTTP Route Definitions (Router and Route Table)."""

from raft import Router
from schemas import (
    CommentCreateSchema,
    CommentUpdateSchema,
    CommentResponseSchema,
)
from views.comments import (
    list_blog_comments_view,
    create_comment_view,
    update_comment_view,
    delete_comment_view,
)

# Demonstrates Router with method decorators for comments
router = Router()
router.get("/api/blogs/{blog_id}/comments")(list_blog_comments_view)
router.post("/api/blogs/{blog_id}/comments", request_body=CommentCreateSchema, responses={201: CommentResponseSchema})(create_comment_view)
router.put("/api/comments/{id}", request_body=CommentUpdateSchema)(update_comment_view)
router.delete("/api/comments/{id}")(delete_comment_view)
