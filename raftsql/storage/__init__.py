from .base import Storage
from .filesystem import FileSystemStorage

# Module-level default storage instance.
# FileSystemStorage reads MEDIA_ROOT / MEDIA_URL lazily from the global
# raftsql config so it always reflects whatever setup() loaded.
default_storage: Storage = FileSystemStorage()

__all__ = ["Storage", "FileSystemStorage", "default_storage"]
