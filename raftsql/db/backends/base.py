"""
Base backend interface. All database-specific logic lives in backends/<name>/.
"""
import re
from abc import ABC, abstractmethod
from typing import Any


class Backend(ABC):
    """
    Database backend: quoting, features, and placeholder style for SQL building.
    Connections are created by the backend and handle driver-specific execute.
    """

    name: str = ""

    def quote_ident(self, name: str) -> str:
        """Quote a table or column identifier for this database."""
        if not name:
            raise ValueError("identifier must be non-empty")
        if re.search(r"[\x00]", name):
            raise ValueError("identifier must not contain null byte")
        return self._quote_ident(name)

    @abstractmethod
    def _quote_ident(self, name: str) -> str:
        """Backend-specific quoting (e.g. PostgreSQL \", MySQL `)."""
        ...

    def placeholder(self, index: int) -> str:
        """
        Placeholder for a parameter in SQL (for the builder).
        Default: %s (used by psycopg2, many MySQL drivers).
        Async PostgreSQL connection will convert %s to $1,$2 for asyncpg.
        """
        return "%s"

    def supports_returning(self) -> bool:
        """Whether INSERT ... RETURNING is supported (PostgreSQL yes, MySQL 8.0.21+ limited, etc.)."""
        return False

    def create_connection(self, config: Any) -> Any:
        """Create a sync connection for this backend. Must have .backend and .execute(sql, params, as_dict=)."""
        raise NotImplementedError(f"{self.name} backend does not implement create_connection")

    def create_async_connection(self, config: Any) -> Any:
        """Create an async connection for this backend. Must have .backend and .execute(sql, params, as_dict=)."""
        raise NotImplementedError(f"{self.name} backend does not implement create_async_connection")

    def get_create_table_sql(self, table_name: str, columns: list) -> str:
        """
        Return CREATE TABLE SQL. columns: list of (column_name, type_sql) e.g. [("id", "SERIAL PRIMARY KEY"), ("name", "TEXT")].
        """
        raise NotImplementedError(f"{self.name} backend does not implement get_create_table_sql")

    def get_drop_table_sql(self, table_name: str) -> str:
        """Return DROP TABLE SQL."""
        raise NotImplementedError(f"{self.name} backend does not implement get_drop_table_sql")

    def get_add_column_sql(self, table_name: str, column_name: str, column_type: str) -> str:
        """Return ALTER TABLE ... ADD COLUMN SQL."""
        raise NotImplementedError(f"{self.name} backend does not implement get_add_column_sql")

    def get_drop_column_sql(self, table_name: str, column_name: str) -> str:
        """Return ALTER TABLE ... DROP COLUMN SQL."""
        raise NotImplementedError(f"{self.name} backend does not implement get_drop_column_sql")

    def get_rename_column_sql(self, table_name: str, old_name: str, new_name: str) -> str:
        """Return ALTER TABLE ... RENAME COLUMN SQL."""
        raise NotImplementedError(f"{self.name} backend does not implement get_rename_column_sql")

    def get_alter_column_sqls(self, table_name: str, column_name: str, new_type: str) -> list:
        """
        Return a list of SQL statements to alter a column's type and constraints.
        May require multiple statements (e.g. TYPE change + SET NOT NULL).
        """
        raise NotImplementedError(f"{self.name} backend does not implement get_alter_column_sqls")

    def get_add_index_sql(self, table_name: str, column_names: list, index_name: str = None, unique: bool = False) -> str:
        """Return CREATE [UNIQUE] INDEX SQL."""
        raise NotImplementedError(f"{self.name} backend does not implement get_add_index_sql")

    def get_drop_index_sql(self, index_name: str) -> str:
        """Return DROP INDEX SQL."""
        raise NotImplementedError(f"{self.name} backend does not implement get_drop_index_sql")

    def get_existing_tables_sql(self) -> str:
        """
        Return a SQL query that lists all user-created table names in the current
        database/schema as a single column named 'tablename'.

        Every backend must override this so the migration runner never contains
        vendor-specific system-table names.

        Example results expected: SELECT 'items' AS tablename, ...
        """
        raise NotImplementedError(f"{self.name} backend does not implement get_existing_tables_sql")

    def get_add_constraint_sql(self, table_name: str, constraint_sql: str) -> str:
        """Return ALTER TABLE ... ADD CONSTRAINT SQL."""
        raise NotImplementedError(f"{self.name} backend does not implement get_add_constraint_sql")

    def get_drop_constraint_sql(self, table_name: str, constraint_name: str) -> str:
        """Return ALTER TABLE ... DROP CONSTRAINT SQL."""
        raise NotImplementedError(f"{self.name} backend does not implement get_drop_constraint_sql")
