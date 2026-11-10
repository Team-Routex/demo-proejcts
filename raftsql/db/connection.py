"""
Sync database connection. Dispatches to the backend for the given config.engine.
"""
from typing import Any, List, Optional, Sequence, Union

from .backends import get_backend
from ..conf.config import Config


class Connection:
    """
    Sync connection. Uses config.engine to select backend; exposes .backend and .execute().
    Use as context manager or call open/close.
    """

    def __init__(self, config: Optional[Config] = None):
        self._config = config or Config.from_env()
        self._backend = get_backend(self._config.engine)
        self._conn = self._backend.create_connection(self._config)

    @property
    def backend(self):
        return self._conn.backend

    def open(self) -> "Connection":
        self._conn.open()
        return self

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Connection":
        self.open()
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def execute(
        self,
        sql: str,
        params: Optional[Sequence[Any]] = None,
        *,
        as_dict: bool = True,
    ) -> List[Union[tuple, dict]]:
        return self._conn.execute(sql, params or (), as_dict=as_dict)

    def atomic(self):
        """Return a transaction context manager (with savepoint support for nesting)."""
        return self._conn.atomic()
