"""Write migration Python files."""
import ast
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from .operations import (
    CreateTable, DropTable, RenameTable,
    AddColumn, DropColumn, RenameColumn, AlterColumn,
    AddIndex, DropIndex, AddConstraint, DropConstraint,
)


def read_migration_app_label(filepath: str) -> str:
    """
    Return the ``app_label`` string from a migration file, or ``""`` if absent.

    New migrations declare ``app_label = "myapp"`` (synced from
    ``Model._meta.app_label`` when the file is generated). Older files omit it;
    callers should fall back to path-based inference.

    Parsing uses ``ast.literal_eval`` for the RHS — only static string literals
    are recognised.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=filepath)
    except (OSError, SyntaxError):
        return ""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "app_label":
                    try:
                        value = ast.literal_eval(node.value)
                        if isinstance(value, str):
                            return value
                    except (ValueError, TypeError):
                        pass
    return ""


def _migration_filename(name: str) -> str:
    """Sanitize an arbitrary string for use as a filename segment."""
    return re.sub(r"[^\w]", "_", name).strip("_") or "auto"


def _name_from_operations(operations: list) -> str:
    """
    Derive a meaningful migration name from the list of operations.

    Single-operation rules:
      CreateTable  → create_{table}
      DropTable    → drop_{table}
      RenameTable  → rename_{old}_to_{new}
      AddColumn    → add_{col}_to_{table}
      DropColumn   → remove_{col}_from_{table}
      AlterColumn  → alter_{col}_in_{table}
      RenameColumn → rename_{old}_to_{new}_in_{table}
      AddIndex     → add_index_on_{table}
      DropIndex    → drop_index_{name}

    Multiple-operation rules:
      All same type + same table → e.g. "add_columns_to_items"
      All CreateTable (1 table)  → "create_{table}"
      All CreateTable (2-3)      → "create_{t1}_{t2}"
      All CreateTable (4+)       → "create_{t1}_{t2}_and_{n}_more"
      Mixed                      → "update_{table}" or "update_{t1}_and_more"

    Total segment is capped at 60 chars.
    """
    if not operations:
        return "auto"

    if len(operations) == 1:
        op = operations[0]
        if isinstance(op, CreateTable):
            seg = f"create_{op.table_name}"
        elif isinstance(op, DropTable):
            seg = f"drop_{op.table_name}"
        elif isinstance(op, RenameTable):
            seg = f"rename_{op.old_name}_to_{op.new_name}"
        elif isinstance(op, AddColumn):
            seg = f"add_{op.column_name}_to_{op.table_name}"
        elif isinstance(op, DropColumn):
            seg = f"remove_{op.column_name}_from_{op.table_name}"
        elif isinstance(op, AlterColumn):
            seg = f"alter_{op.column_name}_in_{op.table_name}"
        elif isinstance(op, RenameColumn):
            seg = f"rename_{op.old_name}_to_{op.new_name}_in_{op.table_name}"
        elif isinstance(op, AddIndex):
            seg = f"add_index_on_{op.table_name}"
        elif isinstance(op, DropIndex):
            seg = f"drop_index_{op.index_name}"
        else:
            seg = "auto"
        return _migration_filename(seg[:60])

    # Multiple operations
    op_types = {type(op).__name__ for op in operations}
    tables = [op.table_name for op in operations if hasattr(op, "table_name")]
    unique_tables = sorted(set(tables))

    if op_types == {"CreateTable"}:
        if len(unique_tables) == 1:
            seg = f"create_{unique_tables[0]}"
        elif len(unique_tables) <= 3:
            seg = "create_" + "_".join(unique_tables)
        else:
            seg = f"create_{unique_tables[0]}_{unique_tables[1]}_and_{len(unique_tables) - 2}_more"

    elif len(op_types) == 1 and len(unique_tables) == 1:
        # All same op type, all same table
        t = unique_tables[0]
        ot = op_types.pop()
        if ot == "AddColumn":
            seg = f"add_columns_to_{t}"
        elif ot == "DropColumn":
            seg = f"remove_columns_from_{t}"
        elif ot == "AlterColumn":
            seg = f"alter_{t}"
        elif ot == "AddIndex":
            seg = f"add_indexes_on_{t}"
        else:
            seg = f"update_{t}"

    elif len(unique_tables) == 1:
        seg = f"update_{unique_tables[0]}"
    elif len(unique_tables) <= 2:
        seg = "update_" + "_and_".join(unique_tables)
    else:
        seg = f"update_{unique_tables[0]}_and_{len(unique_tables) - 1}_more"

    if len(seg) > 60:
        seg = seg[:60].rstrip("_")

    return _migration_filename(seg)


def list_migration_files(migrations_dir: str) -> List[Tuple[int, str, str]]:
    """Return list of (number, name, full_path) sorted by number. Expects files like 0001_initial.py."""
    if not os.path.isdir(migrations_dir):
        return []
    result = []
    for f in os.listdir(migrations_dir):
        if f.endswith(".py") and not f.startswith("_"):
            base = f[:-3]
            parts = base.split("_", 1)
            try:
                num = int(parts[0])
            except (ValueError, IndexError):
                continue
            name = parts[1] if len(parts) > 1 else "auto"
            result.append((num, name, os.path.join(migrations_dir, f)))
    result.sort(key=lambda x: x[0])
    return result


def get_created_tables_from_file(filepath: str) -> List[str]:
    """Parse a migration file and return list of table names from CreateTable operations."""
    tables = []
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    for m in re.finditer(r'CreateTable\s*\(\s*["\']([^"\']+)["\']', content):
        tables.append(m.group(1))
    return tables


def get_all_created_tables(migrations_dir: str) -> set:
    """Return set of table names created in any migration file (backward compat)."""
    created = set()
    for _num, _name, path in list_migration_files(migrations_dir):
        created.update(get_created_tables_from_file(path))
    return created


def write_migration_file(
    migrations_dir: str,
    migration_name: str,
    operations: list,
    dependencies: Optional[List[Tuple[str, str]]] = None,
    model_state: Optional[Dict[str, Any]] = None,
    *,
    app_label: Optional[str] = None,
) -> str:
    """
    Write a new migration file. Returns the path to the written file.

    Parameters
    ----------
    dependencies:
        A list of ``(app_label, migration_name)`` tuples this migration
        depends on, e.g. ``[("inventory", "0001_initial")]``.
    model_state:
        A dict of ``{table: {"fields": {attr_name: {"field_class", "col", "sql"}}}}``
        representing the *complete* schema state after this migration is applied.
        Stored in the file as ``model_state = {...}`` so subsequent
        ``makemigrations`` runs can use Python-level field metadata for
        accurate rename detection (instead of raw SQL comparison).
    app_label:
        ORM app label (same as ``Model._meta.app_label``) written into the file
        so ``allow_migrate`` and routing use one source of truth instead of only
        inferring from the directory name. Omit for empty / special cases.
    """
    os.makedirs(migrations_dir, exist_ok=True)
    existing = list_migration_files(migrations_dir)
    next_num = (existing[-1][0] + 1) if existing else 1

    if migration_name and migration_name != "auto":
        safe_name = _migration_filename(migration_name)
    else:
        safe_name = _name_from_operations(operations)

    # Guard against duplicate filenames
    base_name = safe_name
    counter = 1
    while any(
        f == f"{next_num:04d}_{safe_name}.py"
        for _, _, f in [
            (n, nm, os.path.join(migrations_dir, f"{n:04d}_{nm}.py"))
            for n, nm, _ in existing
        ]
    ):
        safe_name = f"{base_name}_{counter}"
        counter += 1

    filename = f"{next_num:04d}_{safe_name}.py"
    filepath = os.path.join(migrations_dir, filename)

    # Collect which operation types are used so we write a minimal import line
    used_op_names = sorted({type(op).__name__ for op in operations})
    import_line = "from raftsql.migrations.operations import " + ", ".join(used_op_names)

    import raftsql
    version = getattr(raftsql, "__version__", "unknown")

    # Serialise dependencies list
    if dependencies:
        dep_lines = [
            f'    {repr(list(dep))},' for dep in dependencies
        ]
        dep_block = "dependencies = [\n" + "\n".join(dep_lines) + "\n]\n"
    else:
        dep_block = "dependencies = []\n"

    # Serialise model_state (pretty-printed repr)
    if model_state:
        model_state_block = "model_state = " + _fmt_model_state(model_state) + "\n"
    else:
        model_state_block = ""

    lines = [
        f"# Generated by RaftSQL {version}",
        import_line,
        "",
        dep_block,
    ]
    if model_state_block:
        lines.append(model_state_block)
    if app_label:
        lines.append(f'app_label = {app_label!r}')
        lines.append("")
    lines += [
        "operations = [",
    ]
    for op in operations:
        lines.append("    " + _serialize_op(op) + ",")
    lines.append("]")
    lines.append("")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return filepath


def _fmt_model_state(state: dict) -> str:
    """Pretty-print model_state dict as valid Python literal."""
    import json
    # json.dumps gives valid Python for str/int/list/dict/None/bool
    return json.dumps(state, indent=4)


def read_dependencies(filepath: str) -> List[Tuple[str, str]]:
    """
    Parse a migration file and return its ``dependencies`` list as a list of
    ``(app_label, migration_name)`` tuples.  Returns an empty list for files
    that pre-date the dependency system (fully backward-compatible).
    """
    import ast
    try:
        with open(filepath, "r", encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=filepath)
    except (OSError, SyntaxError):
        return []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "dependencies":
                    try:
                        value = ast.literal_eval(node.value)
                        if isinstance(value, list):
                            return [
                                (str(item[0]), str(item[1]))
                                for item in value
                                if isinstance(item, (list, tuple)) and len(item) == 2
                            ]
                    except (ValueError, TypeError):
                        pass
    return []


def read_model_state(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Parse a migration file and return its ``model_state`` dict, or ``None`` if
    the file pre-dates model_state (fully backward-compatible).

    model_state format::

        {
            "blogs": {
                "fields": {
                    "id":    {"field_class": "AutoField",  "col": "id",    "sql": "SERIAL PRIMARY KEY"},
                    "title": {"field_class": "CharField",  "col": "title", "sql": "VARCHAR(255) NOT NULL"},
                }
            },
            ...
        }
    """
    import json
    try:
        with open(filepath, "r", encoding="utf-8") as fh:
            source = fh.read()
    except OSError:
        return None

    # Fast path: look for the model_state = { ... } assignment using ast
    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "model_state":
                    try:
                        return ast.literal_eval(node.value)
                    except (ValueError, TypeError):
                        pass
    return None


def _fmt_columns(columns: list) -> str:
    """Format a list of (col_name, col_sql) tuples across multiple indented lines."""
    inner = ",\n".join(f'            ("{col}", "{sql}")' for col, sql in columns)
    return f"[\n{inner},\n        ]"


def _serialize_op(op: object) -> str:
    """Serialize a single operation to its Python constructor string."""
    if isinstance(op, CreateTable):
        cols = _fmt_columns(op.columns)
        return f'CreateTable(\n        "{op.table_name}",\n        {cols},\n    )'
    if isinstance(op, DropTable):
        return f'DropTable("{op.table_name}")'
    if isinstance(op, RenameTable):
        return f'RenameTable("{op.old_name}", "{op.new_name}")'
    if isinstance(op, AddColumn):
        return (
            f'AddColumn(\n'
            f'        "{op.table_name}",\n'
            f'        "{op.column_name}",\n'
            f'        "{op.column_type}",\n'
            f'    )'
        )
    if isinstance(op, DropColumn):
        return f'DropColumn("{op.table_name}", "{op.column_name}")'
    if isinstance(op, RenameColumn):
        return f'RenameColumn("{op.table_name}", "{op.old_name}", "{op.new_name}")'
    if isinstance(op, AlterColumn):
        return (
            f'AlterColumn(\n'
            f'        "{op.table_name}",\n'
            f'        "{op.column_name}",\n'
            f'        "{op.new_type}",\n'
            f'    )'
        )
    if isinstance(op, AddIndex):
        cols = repr(op.column_names)
        parts = [f'        "{op.table_name}"', f'        {cols}']
        if op.index_name is not None:
            parts.append(f'        index_name="{op.index_name}"')
        if op.unique:
            parts.append('        unique=True')
        return 'AddIndex(\n' + ',\n'.join(parts) + ',\n    )'
    if isinstance(op, DropIndex):
        return f'DropIndex("{op.index_name}")'
    if isinstance(op, AddConstraint):
        return (
            f'AddConstraint(\n'
            f'        "{op.table_name}",\n'
            f'        "{op.constraint_name}",\n'
            f'        "{op.constraint_sql}",\n'
            f'    )'
        )
    if isinstance(op, DropConstraint):
        return f'DropConstraint("{op.table_name}", "{op.constraint_name}")'
    raise TypeError(f"Unknown operation type: {type(op).__name__}")


def squash_migrations(migrations_dir: str) -> Optional[str]:
    """
    Squash all migrations in migrations_dir into a single squashed file.

    Builds the final schema state by replaying all existing migrations, then
    writes a new file with CreateTable + AddIndex operations representing that
    final state. All old migration files are deleted.

    Returns the path to the squashed file, or None if there is nothing to squash.

    After squashing, if the migrations were already applied to the database:
        raftsql migrate --fake-initial
    """
    from .state import build_state
    from .operations import CreateTable, AddIndex

    files = list_migration_files(migrations_dir)
    if not files:
        return None

    state = build_state(migrations_dir)
    if not state["tables"] and not state["indexes"]:
        return None

    ops: list = []
    for table_name, columns in sorted(state["tables"].items()):
        ops.append(CreateTable(table_name, list(columns.items())))
    for idx_name, idx_data in sorted(state["indexes"].items()):
        ops.append(AddIndex(
            idx_data["table"], list(idx_data["columns"]),
            idx_name, idx_data.get("unique", False),
        ))

    # Remove all existing migration files
    for _, _, filepath in files:
        os.remove(filepath)

    return write_migration_file(migrations_dir, "squashed", ops)

