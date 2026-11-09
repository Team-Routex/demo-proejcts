"""Category HTTP Route Table (Class-Based View Routing)."""

from raft import route
from views.categories import CategoryListView, CategoryDetailView

routes = [
    route("/api/categories", CategoryListView, methods=["GET", "POST"]),
    route("/api/categories/{slug}", CategoryDetailView, methods=["GET"]),
]
