"""PostgreSQL sync connection (psycopg2)."""
from contextlib import contextmanager
from typing import Any, Generator, List, Optional, Sequence, Union

import psycopg2
from psycopg2.extras import RealDictCursor

from ....conf.config import Config
from ..base import Backend


class PostgreSQLConnection:
    """Sync connection for PostgreSQL. Holds backend and executes with %s placeholders."""

    def __init__(self, config: Config, backend: Backend):
        self._config = config
        self.backend = backend
        self._conn: Optional[psycopg2.extensions.connection] = None
        self._transaction_depth: int = 0
        self._savepoint_counter: int = 0
        self._pooled: bool = False   # True when conn was taken from psycopg2 pool

    def open(self) -> "PostgreSQLConnection":
        if self._conn is not None:
            return self
        from ....db.pool import get_sync_pool
        pool = get_sync_pool()
        if pool is not None:
            self._conn = pool.getconn()
            self._pooled = True
        else:
            self._conn = psycopg2.connect(
                host=self._config.host,
                port=self._config.port,
                user=self._config.user,
                password=self._config.password,
                dbname=self._config.dbname,
            )
            self._pooled = False
        return self

    def close(self) -> None:
        if self._conn is not None:
            try:
                if self._transaction_depth == 0:
                    self._conn.commit()
                else:
                    # Closed mid-transaction — rollback to keep DB consistent.
                    self._conn.rollback()
            except Exception:
                self._conn.rollback()
            finally:
                if self._pooled:
                    from ....db.pool import get_sync_pool
                    pool = get_sync_pool()
                    if pool is not None:
                        pool.putconn(self._conn)
                    else:
                        self._conn.close()
                else:
                    self._conn.close()
                self._conn = None
                self._pooled = False

    @property
    def conn(self) -> psycopg2.extensions.connection:
        if self._conn is None:
            self.open()
        return self._conn

    def __enter__(self) -> "PostgreSQLConnection":
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
        params = params or ()
        with self.conn.cursor(cursor_factory=RealDictCursor if as_dict else None) as cur:
            cur.execute(sql, params)
            # Only auto-commit when not inside an atomic() block.
            if self._transaction_depth == 0:
                self.conn.commit()
            if cur.description is None:
                return []
            if as_dict:
                return [dict(row) for row in cur.fetchall()]
            return list(cur.fetchall())

    @contextmanager
    def atomic(self) -> Generator[None, None, None]:
        """
        Transaction context manager with savepoint support for nesting.

        Outermost atomic() wraps statements in a single transaction:
            with conn.atomic():
                conn.execute(...)   # no per-statement commit
                conn.execute(...)   # both committed together on exit

        Nested atomic() uses a SAVEPOINT so only the inner block
        can be rolled back independently:
            with conn.atomic():         # BEGIN (implicit)
                conn.execute(...)
                with conn.atomic():     # SAVEPOINT sp_1
                    conn.execute(...)   # RELEASE sp_1 on success
                                        # ROLLBACK TO sp_1 on error
        """
        if self._transaction_depth == 0:
            # Outermost block: psycopg2 auto-BEGINs on the first statement.
            self._transaction_depth += 1
            try:
                yield
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise
            finally:
                self._transaction_depth -= 1
        else:
            # Nested block: use a named SAVEPOINT.
            self._savepoint_counter += 1
            sp = f"sp_{self._savepoint_counter}"
            self._transaction_depth += 1
            with self.conn.cursor() as cur:
                cur.execute(f"SAVEPOINT {sp}")
            try:
                yield
                with self.conn.cursor() as cur:
                    cur.execute(f"RELEASE SAVEPOINT {sp}")
            except Exception:
                with self.conn.cursor() as cur:
                    cur.execute(f"ROLLBACK TO SAVEPOINT {sp}")
                raise
            finally:
                self._transaction_depth -= 1
