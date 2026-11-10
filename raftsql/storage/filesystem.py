"""
Local filesystem storage backend for RaftSQL.

Files are saved under MEDIA_ROOT (from setraft.py or explicit argument).
URLs are built from MEDIA_URL (from setraft.py or explicit argument).
"""
import os
from typing import IO, Optional

from .base import Storage


def _get_global_media_root() -> str:
    """Read media_root from the live global config (set during raftsql.setup())."""
    try:
        import raftsql
        cfg = getattr(raftsql, "_media_root", None)
        if cfg:
            return cfg
    except Exception:
        pass
    return "media"


def _get_global_media_url() -> str:
    """Read media_url from the live global config (set during raftsql.setup())."""
    try:
        import raftsql
        cfg = getattr(raftsql, "_media_url", None)
        if cfg:
            return cfg
    except Exception:
        pass
    return "/media/"


class FileSystemStorage(Storage):
    """
    Stores files on the local filesystem under MEDIA_ROOT.

    Args:
        location : Absolute path to the root directory where files are stored.
                   Defaults to the MEDIA_ROOT value in setraft.py.
        base_url : URL prefix for accessing stored files.
                   Defaults to the MEDIA_URL value in setraft.py.
    """

    def __init__(
        self,
        location: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self._location = location
        self._base_url = base_url

    @property
    def location(self) -> str:
        return self._location or _get_global_media_root()

    @property
    def base_url(self) -> str:
        url = self._base_url or _get_global_media_url()
        if not url.endswith("/"):
            url += "/"
        return url

    def _full_path(self, name: str) -> str:
        return os.path.normpath(os.path.join(self.location, name))

    def save(self, name: str, content: IO) -> str:
        """Save *content* to disk; return the relative path stored in the DB."""
        name = self.get_available_name(name)
        full = self._full_path(name)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        if hasattr(content, "read"):
            data = content.read()
        else:
            data = content
        with open(full, "wb") as f:
            f.write(data if isinstance(data, bytes) else data.encode())
        return name

    def url(self, name: str) -> str:
        if not name:
            return ""
        return self.base_url + name.replace("\\", "/")

    def delete(self, name: str) -> None:
        full = self._full_path(name)
        if os.path.exists(full):
            os.remove(full)

    def exists(self, name: str) -> bool:
        return os.path.exists(self._full_path(name))

    def open(self, name: str, mode: str = "rb") -> IO:
        return open(self._full_path(name), mode)
