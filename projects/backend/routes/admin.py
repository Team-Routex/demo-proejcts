"""Admin Console HTTP Route Definitions (Router and Route Table)."""

from raft import route, Router
from views.admin import (
    admin_overview_view,
    admin_analytics_view,
    admin_top_blogs_view,
    admin_top_authors_view,
    admin_list_users_view,
    admin_update_user_view,
    admin_toggle_verify_user_view,
    admin_toggle_status_user_view,
    admin_delete_user_view,
    admin_list_blogs_view,
    admin_approve_blog_view,
    admin_reject_blog_view,
    admin_moderate_blog_view,
    admin_delete_blog_view,
    admin_list_comments_view,
    admin_delete_comment_view,
    admin_list_categories_view,
    admin_update_category_view,
    admin_delete_category_view,
)

# Demonstrates Router prefix and method decorators
router = Router(prefix="/api/admin")
router.get("/overview")(admin_overview_view)
router.get("/analytics")(admin_analytics_view)
router.get("/top-blogs")(admin_top_blogs_view)
router.get("/top-authors")(admin_top_authors_view)
router.get("/users")(admin_list_users_view)
router.put("/users/{id}")(admin_update_user_view)
router.patch("/users/{id}/verify")(admin_toggle_verify_user_view)
router.patch("/users/{id}/status")(admin_toggle_status_user_view)
router.delete("/users/{id}")(admin_delete_user_view)
router.get("/blogs")(admin_list_blogs_view)
router.post("/blogs/{id}/approve")(admin_approve_blog_view)
router.post("/blogs/{id}/reject")(admin_reject_blog_view)
router.post("/blogs/{id}/moderate")(admin_moderate_blog_view)
router.delete("/blogs/{id}")(admin_delete_blog_view)
router.get("/comments")(admin_list_comments_view)
router.delete("/comments/{id}")(admin_delete_comment_view)
router.get("/categories")(admin_list_categories_view)
router.put("/categories/{id}")(admin_update_category_view)
router.delete("/categories/{id}")(admin_delete_category_view)

# Demonstrates List-based routes table export
routes = [
    route("/api/admin/overview", admin_overview_view, methods=["GET"]),
    route("/api/admin/analytics", admin_analytics_view, methods=["GET"]),
    route("/api/admin/top-blogs", admin_top_blogs_view, methods=["GET"]),
    route("/api/admin/top-authors", admin_top_authors_view, methods=["GET"]),
    route("/api/admin/users", admin_list_users_view, methods=["GET"]),
    route("/api/admin/users/{id}", admin_update_user_view, methods=["PUT"]),
    route("/api/admin/users/{id}/verify", admin_toggle_verify_user_view, methods=["PATCH"]),
    route("/api/admin/users/{id}/status", admin_toggle_status_user_view, methods=["PATCH"]),
    route("/api/admin/users/{id}", admin_delete_user_view, methods=["DELETE"]),
    route("/api/admin/blogs", admin_list_blogs_view, methods=["GET"]),
    route("/api/admin/blogs/{id}/approve", admin_approve_blog_view, methods=["POST"]),
    route("/api/admin/blogs/{id}/reject", admin_reject_blog_view, methods=["POST"]),
    route("/api/admin/blogs/{id}/moderate", admin_moderate_blog_view, methods=["POST"]),
    route("/api/admin/blogs/{id}", admin_delete_blog_view, methods=["DELETE"]),
    route("/api/admin/comments", admin_list_comments_view, methods=["GET"]),
    route("/api/admin/comments/{id}", admin_delete_comment_view, methods=["DELETE"]),
    route("/api/admin/categories", admin_list_categories_view, methods=["GET"]),
    route("/api/admin/categories/{id}", admin_update_category_view, methods=["PUT"]),
    route("/api/admin/categories/{id}", admin_delete_category_view, methods=["DELETE"]),
]
