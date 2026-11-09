"""Blog HTTP Route Definitions (Router and Route Table)."""

from raft import route, Router
from schemas import (
    BlogCreateSchema,
    BlogUpdateSchema,
    BlogDetailSchema,
    BlogListItemSchema,
)
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
router.post("", request_body=BlogCreateSchema, responses={201: BlogListItemSchema})(create_blog_view)
router.post("/", request_body=BlogCreateSchema, responses={201: BlogListItemSchema})(create_blog_view)
router.get("/user/my")(list_user_blogs_view)
router.get("/user/me")(list_user_blogs_view)
router.get("/{slug}", responses={200: BlogDetailSchema})(get_blog_view)
router.put("/{id}", request_body=BlogUpdateSchema)(update_blog_view)
router.delete("/{id}")(delete_blog_view)
router.post("/{id}/submit")(submit_blog_view)

# Demonstrates List-based routes export
routes = [
    route("/api/blogs", list_blogs_view, methods=["GET"]),
    route("/api/blogs/user/my", list_user_blogs_view, methods=["GET"]),
    route("/api/blogs/user/me", list_user_blogs_view, methods=["GET"]),
    route("/api/blogs", create_blog_view, methods=["POST"], request_body=BlogCreateSchema, responses={201: BlogListItemSchema}),
    route("/api/blogs/{slug}", get_blog_view, methods=["GET"], responses={200: BlogDetailSchema}),
    route("/api/blogs/{id}", update_blog_view, methods=["PUT"], request_body=BlogUpdateSchema),
    route("/api/blogs/{id}", delete_blog_view, methods=["DELETE"]),
    route("/api/blogs/{id}/submit", submit_blog_view, methods=["POST"]),
]
