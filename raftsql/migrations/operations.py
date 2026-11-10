"""Migration operations — all DDL change types supported by RaftSQL."""
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class CreateTable:
    """Create a new table."""
    table_name: str
    columns: List[Tuple[str, str]]


@dataclass
class DropTable:
    """Drop a table (destructive — review before applying)."""
    table_name: str


@dataclass
class RenameTable:
    """Rename a table. All data is preserved."""
    old_name: str
    new_name: str


@dataclass
class AddColumn:
    """Add a column to an existing table."""
    table_name: str
    column_name: str
    column_type: str  # full SQL spec e.g. "VARCHAR(255) NOT NULL"


@dataclass
class DropColumn:
    """Drop a column from a table (destructive — review before applying)."""
    table_name: str
    column_name: str


@dataclass
class RenameColumn:
    """Rename a column in a table."""
    table_name: str
    old_name: str
    new_name: str


@dataclass
class AlterColumn:
    """Change a column's type or constraints."""
    table_name: str
    column_name: str
    new_type: str  # full SQL spec e.g. "NUMERIC(15, 2) NOT NULL"


@dataclass
class AddIndex:
    """Create an index on one or more columns."""
    table_name: str
    column_names: List[str]
    index_name: Optional[str] = None
    unique: bool = False


@dataclass
class DropIndex:
    """Drop an index by name."""
    index_name: str


@dataclass
class AddConstraint:
    """Add a named table constraint (CHECK or UNIQUE) to an existing table."""
    table_name: str
    constraint_name: str
    constraint_sql: str  # full CONSTRAINT "name" CHECK (...) / UNIQUE (...) fragment


@dataclass
class DropConstraint:
    """Drop a named table constraint."""
    table_name: str
    constraint_name: str
