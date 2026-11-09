"""Tag HTTP Route Table (Class-Based View Routing)."""

from raft import route
from views.tags import TagListView, TagSlugView, TagDetailView

routes = [
    route("/api/tags", TagListView, methods=["GET", "POST"]),
    route("/api/tags/{slug}", TagSlugView, methods=["GET"]),
    route("/api/tags/{id}", TagDetailView, methods=["PUT", "DELETE"]),
]
