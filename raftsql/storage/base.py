"""
Abstract Storage base class for RaftSQL file fields.

Custom storage backends must subclass Storage and implement all methods.
"""
from abc import ABC, abstractmethod
from typing import IO


class Storage(ABC):
    """Abstract base for all storage backends."""

    @abstractmethod
    def save(self, name: str, content: IO) -> str:
        """
        Save *content* under the given *name* and return the stored path.
        The returned path is what gets written to the database column.
        """

    @abstractmethod
    def url(self, name: str) -> str:
        """Return the publicly accessible URL for the file stored at *name*."""

    @abstractmethod
    def delete(self, name: str) -> None:
        """Delete the file stored at *name*."""

    @abstractmethod
    def exists(self, name: str) -> bool:
        """Return True if a file with the given *name* already exists."""

    @abstractmethod
    def open(self, name: str, mode: str = "rb") -> IO:
        """Open and return the file stored at *name*."""

    def get_available_name(self, name: str) -> str:
        """
        Return a filename that is available in the storage location.
        Appends a 7-character random string if the name already exists,
        matching Django's behaviour.
        """
        import os
        import uuid
        if not self.exists(name):
            return name
        stem, ext = os.path.splitext(name)
        while True:
            suffix = uuid.uuid4().hex[:7]
            candidate = f"{stem}_{suffix}{ext}"
            if not self.exists(candidate):
                return candidate
