"""Blog HTTP Route Definitions (Router and Route Table)."""

from raft import route, Router
from views.blogs import (
    list_blogs_view,
    get_blog_view,
    create_blog_view,
    update_blog_view,
    delete_blog_view,
    submit_blog_view,
    list_user_blogs_view,
)

# Demonstrates Router routing with method decorators
router = Router(prefix="/api/blogs")
router.get("")(list_blogs_view)
router.get("/")(list_blogs_view)
router.post("")(create_blog_view)
router.post("/")(create_blog_view)
router.get("/user/my")(list_user_blogs_view)
router.get("/{slug}")(get_blog_view)
router.put("/{id}")(update_blog_view)
router.delete("/{id}")(delete_blog_view)
router.post("/{id}/submit")(submit_blog_view)

# Demonstrates List-based routes export
routes = [
    route("/api/blogs", list_blogs_view, methods=["GET"]),
    route("/api/blogs/user/my", list_user_blogs_view, methods=["GET"]),
    route("/api/blogs", create_blog_view, methods=["POST"]),
    route("/api/blogs/{slug}", get_blog_view, methods=["GET"]),
    route("/api/blogs/{id}", update_blog_view, methods=["PUT"]),
    route("/api/blogs/{id}", delete_blog_view, methods=["DELETE"]),
    route("/api/blogs/{id}/submit", submit_blog_view, methods=["POST"]),
]
