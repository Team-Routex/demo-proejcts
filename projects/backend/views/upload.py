"""Media Upload Views."""

import secrets
from pathlib import Path
from raft import Response
from raft.core.exceptions import HTTPException, ValidationError
from raft.core.request import RaftRequest
from middleware.auth import get_authenticated_user

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


async def upload_file_view(request: RaftRequest) -> Response:
    """Handle multipart file upload for featured images and avatars."""
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

    # Generate collision-free sanitized name
    safe_name = f"{secrets.token_hex(12)}{ext}"
    upload_dir = Path(__file__).resolve().parent.parent / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    dest_path = upload_dir / safe_name
    uploaded.save(str(dest_path))

    file_url = f"/uploads/{safe_name}"
    return Response.success(data={"url": file_url, "filename": safe_name, "size": uploaded.size})

