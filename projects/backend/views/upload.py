"""Media Upload Views using RaftSQL ORM File Storage."""

import io
import secrets
from pathlib import Path
from raft import Response
from raft.core.exceptions import HTTPException, ValidationError
from raft.core.request import RaftRequest
from raftsql.storage import default_storage
from middleware.auth import get_authenticated_user

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


async def upload_file_view(request: RaftRequest) -> Response:
    """Handle multipart file upload using RaftSQL ORM default_storage."""
    get_authenticated_user(request, require=True)

    files = await request.files()
    if not files or "file" not in files:
        raise ValidationError(message="No file uploaded. Expected 'file' form field.")

    uploaded = files["file"]
    if uploaded.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, message="File size exceeds 5MB limit.")

    ext = Path(uploaded.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, message=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    # Delegate file management, saving, and URL resolution to RaftSQL default_storage
    safe_name = f"{secrets.token_hex(12)}{ext}"
    content = io.BytesIO(uploaded.content) if hasattr(uploaded, "content") else uploaded.file
    saved_name = default_storage.save(safe_name, content)
    file_url = default_storage.url(saved_name)

    return Response.success(data={"url": file_url, "filename": saved_name, "size": uploaded.size})

