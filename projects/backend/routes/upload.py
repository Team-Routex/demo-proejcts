"""Media Upload Route Table."""

from raft import route
from views.upload import upload_file_view

routes = [
    route("/api/upload", upload_file_view, methods=["POST"]),
]
