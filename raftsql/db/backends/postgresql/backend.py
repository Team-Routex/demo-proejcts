"""PostgreSQL backend: quoting, features, and connection factories."""
import re
from typing import Any, List, Optional

from ..base import Backend
from .async_connection import PostgreSQLAsyncConnection
from .connection import PostgreSQLConnection


class PostgreSQLBackend(Backend):
    name = "postgresql"

    def _quote_ident(self, name: str) -> str:
        escaped = name.replace('"', '""')
        return f'"{escaped}"'

    def supports_returning(self) -> bool:
        return True

    def create_connection(self, config: Any) -> PostgreSQLConnection:
        return PostgreSQLConnection(config, self)

    def create_async_connection(self, config: Any) -> PostgreSQLAsyncConnection:
        return PostgreSQLAsyncConnection(config, self)

    # ── DDL helpers ───────────────────────────────────────────────────────

    def get_create_table_sql(self, table_name: str, columns: list) -> str:
        q_table = self.quote_ident(table_name)
        parts = []
        for col, type_sql in columns:
            if col.startswith("__c__"):
                # Constraint entry: type_sql is the full CONSTRAINT ... SQL
                parts.append(type_sql)
            else:
                parts.append(self.quote_ident(col) + " " + type_sql)
        return f"CREATE TABLE {q_table} (" + ", ".join(parts) + ")"

    def get_drop_table_sql(self, table_name: str) -> str:
        return f"DROP TABLE IF EXISTS {self.quote_ident(table_name)}"

    def get_rename_table_sql(self, old_name: str, new_name: str) -> str:
        q = self.quote_ident
        return f"ALTER TABLE {q(old_name)} RENAME TO {q(new_name)}"

    def get_add_column_sql(self, table_name: str, column_name: str, column_type: str) -> str:
        q = self.quote_ident
        return f"ALTER TABLE {q(table_name)} ADD COLUMN {q(column_name)} {column_type}"

    def get_drop_column_sql(self, table_name: str, column_name: str) -> str:
        q = self.quote_ident
        return f"ALTER TABLE {q(table_name)} DROP COLUMN {q(column_name)}"

    def get_rename_column_sql(self, table_name: str, old_name: str, new_name: str) -> str:
        q = self.quote_ident
        return f"ALTER TABLE {q(table_name)} RENAME COLUMN {q(old_name)} TO {q(new_name)}"

    def get_alter_column_sqls(self, table_name: str, column_name: str, new_type: str) -> List[str]:
        """
        Decompose new_type (e.g. "VARCHAR(255) NOT NULL") into separate ALTER
        statements for PostgreSQL:
          1. ALTER COLUMN col TYPE <base_type>
          2. SET / DROP NOT NULL
          3. SET / DROP DEFAULT (when present)
        """
        q = self.quote_ident
        base_type, not_null, default_val = _decompose_column_sql(new_type)
        t = q(table_name)
        c = q(column_name)
        sqls: List[str] = []
        sqls.append(f"ALTER TABLE {t} ALTER COLUMN {c} TYPE {base_type}")
        if not_null:
            sqls.append(f"ALTER TABLE {t} ALTER COLUMN {c} SET NOT NULL")
        else:
            sqls.append(f"ALTER TABLE {t} ALTER COLUMN {c} DROP NOT NULL")
        if default_val is not None:
            sqls.append(f"ALTER TABLE {t} ALTER COLUMN {c} SET DEFAULT {default_val}")
        return sqls

    def get_add_index_sql(
        self,
        table_name: str,
        column_names: list,
        index_name: Optional[str] = None,
        unique: bool = False,
    ) -> str:
        q = self.quote_ident
        unique_kw = "UNIQUE " if unique else ""
        name = index_name or f"{table_name}_{'_'.join(column_names)}_idx"
        cols = ", ".join(q(c) for c in column_names)
        return f"CREATE {unique_kw}INDEX {q(name)} ON {q(table_name)} ({cols})"

    def get_drop_index_sql(self, index_name: str) -> str:
        return f"DROP INDEX IF EXISTS {self.quote_ident(index_name)}"

    def get_existing_tables_sql(self) -> str:
        """PostgreSQL: list all tables in the 'public' schema."""
        return "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"

    def get_add_constraint_sql(self, table_name: str, constraint_sql: str) -> str:
        return f"ALTER TABLE {self.quote_ident(table_name)} ADD {constraint_sql}"

    def get_drop_constraint_sql(self, table_name: str, constraint_name: str) -> str:
        return (
            f"ALTER TABLE {self.quote_ident(table_name)} "
            f"DROP CONSTRAINT IF EXISTS {self.quote_ident(constraint_name)}"
        )


def _decompose_column_sql(type_sql: str):
    """
    Decompose a full column SQL spec such as "VARCHAR(255) NOT NULL DEFAULT 'x'"
    into (base_type: str, not_null: bool, default_val: str | None).
    """
    s = type_sql.strip()
    not_null = bool(re.search(r'\bNOT\s+NULL\b', s, re.I))

    # Extract DEFAULT value (a single token — covers simple defaults)
    default_match = re.search(r'\bDEFAULT\s+(\S+)', s, re.I)
    default_val = default_match.group(1) if default_match else None

    # Strip all modifiers to isolate the base type
    base = re.sub(r'\bNOT\s+NULL\b|\bNULL\b|\bUNIQUE\b|\bDEFAULT\s+\S+|\bPRIMARY\s+KEY\b', '', s, flags=re.I)
    base = ' '.join(base.split())  # normalise whitespace

    return base, not_null, default_val
