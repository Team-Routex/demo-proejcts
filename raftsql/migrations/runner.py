"""Run pending migrations. Tracks applied migrations in raftsql_migrations table."""
import os
import sys
import importlib.util
from typing import Any, List

from .operations import CreateTable
from .writer import list_migration_files, read_dependencies

MIGRATIONS_TABLE = "raftsql_migrations"

_RUNNER_SKIP_DIRS = {
    "env", "venv", ".venv", "ENV", "VENV",
    "__pycache__", "node_modules", ".git",
    "dist", "build", "site-packages",
    ".mypy_cache", ".pytest_cache",
}


def _ensure_migrations_table(connection: Any) -> None:
    """Create the tracking table if it does not exist."""
    backend = connection.backend
    q = backend.quote_ident(MIGRATIONS_TABLE)
    sql = (
        f"CREATE TABLE IF NOT EXISTS {q} "
        "(id SERIAL PRIMARY KEY, name VARCHAR(255) NOT NULL UNIQUE, "
        "applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    connection.execute(sql, [], as_dict=True)


def _get_applied_names(connection: Any) -> set:
    """Return set of already-applied migration names from the tracking table."""
    backend = connection.backend
    q = backend.quote_ident(MIGRATIONS_TABLE)
    rows = connection.execute(f"SELECT name FROM {q} ORDER BY id", [], as_dict=True)
    return {r["name"] for r in rows}


def _run_migration_file(connection: Any, filepath: str) -> None:
    """Load a migration .py file and execute all its operations."""
    from .operations import (
        CreateTable, DropTable, RenameTable,
        AddColumn, DropColumn, RenameColumn, AlterColumn,
        AddIndex, DropIndex, AddConstraint, DropConstraint,
    )
    backend = connection.backend
    spec = importlib.util.spec_from_file_location("migration_module", filepath)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load migration: {filepath}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    for op in getattr(module, "operations", []):
        if isinstance(op, CreateTable):
            sql = backend.get_create_table_sql(op.table_name, op.columns)
            connection.execute(sql, [], as_dict=True)
        elif isinstance(op, DropTable):
            sql = backend.get_drop_table_sql(op.table_name)
            connection.execute(sql, [], as_dict=True)
        elif isinstance(op, RenameTable):
            sql = backend.get_rename_table_sql(op.old_name, op.new_name)
            connection.execute(sql, [], as_dict=True)
        elif isinstance(op, AddColumn):
            sql = backend.get_add_column_sql(op.table_name, op.column_name, op.column_type)
            connection.execute(sql, [], as_dict=True)
        elif isinstance(op, DropColumn):
            sql = backend.get_drop_column_sql(op.table_name, op.column_name)
            connection.execute(sql, [], as_dict=True)
        elif isinstance(op, RenameColumn):
            sql = backend.get_rename_column_sql(op.table_name, op.old_name, op.new_name)
            connection.execute(sql, [], as_dict=True)
        elif isinstance(op, AlterColumn):
            for sql in backend.get_alter_column_sqls(op.table_name, op.column_name, op.new_type):
                connection.execute(sql, [], as_dict=True)
        elif isinstance(op, AddIndex):
            sql = backend.get_add_index_sql(
                op.table_name, op.column_names, op.index_name, op.unique
            )
            connection.execute(sql, [], as_dict=True)
        elif isinstance(op, DropIndex):
            sql = backend.get_drop_index_sql(op.index_name)
            connection.execute(sql, [], as_dict=True)
        elif isinstance(op, AddConstraint):
            sql = backend.get_add_constraint_sql(op.table_name, op.constraint_sql)
            connection.execute(sql, [], as_dict=True)
        elif isinstance(op, DropConstraint):
            sql = backend.get_drop_constraint_sql(op.table_name, op.constraint_name)
            connection.execute(sql, [], as_dict=True)


def _record_migration(connection: Any, name: str) -> None:
    """Record a migration as applied in the tracking table."""
    backend = connection.backend
    q = backend.quote_ident(MIGRATIONS_TABLE)
    connection.execute(f"INSERT INTO {q} (name) VALUES (%s)", [name], as_dict=True)


def _is_applied(migration_key: str, applied: set) -> bool:
    """
    Check if a migration is already applied.
    Supports both:
    - New format: "apps/inventory/migrations/0001_auto"  (relative path key)
    - Legacy format: "0001_auto"  (bare filename, pre-per-app)
    """
    if migration_key in applied:
        return True
    # Backward-compat: old entries stored only the basename
    return os.path.basename(migration_key) in applied


def collect_migration_dirs(project_root: str) -> List[str]:
    """
    Walk project_root and return every 'migrations' directory found.
    Skips virtualenv dirs, __pycache__, .git, etc.
    """
    dirs_found = []
    for root, dirs, _files in os.walk(project_root):
        dirs[:] = [
            d for d in dirs
            if d not in _RUNNER_SKIP_DIRS and not d.startswith(".")
        ]
        if os.path.basename(root) == "migrations" and os.path.isdir(root):
            dirs_found.append(root)
    return dirs_found


def migrate(connection: Any, migrations_dir: str) -> List[str]:
    """
    Apply all pending migrations in a single migrations_dir.
    Kept for backward compatibility (single global migrations directory).
    Returns list of migration keys applied this run.
    """
    if not os.path.isdir(migrations_dir):
        return []
    _ensure_migrations_table(connection)
    applied = _get_applied_names(connection)
    applied_this_run: List[str] = []
    for _num, _name, filepath in list_migration_files(migrations_dir):
        key = os.path.basename(filepath)[:-3]   # e.g. "0001_auto"
        if _is_applied(key, applied):
            continue
        _run_migration_file(connection, filepath)
        _record_migration(connection, key)
        applied_this_run.append(key)
    return applied_this_run


def _topological_sort(
    migrations: List[tuple],
    project_root: str,
) -> List[tuple]:
    """
    Given a list of ``(num, key, filepath)`` tuples, return them in an order
    that satisfies every migration's ``dependencies`` list.

    The key format is ``"apps/inventory/migrations/0001_initial"`` (relative,
    forward-slash, no .py extension).

    Dependency tuples in the migration file look like::

        dependencies = [
            ["inventory", "0001_initial"],
        ]

    Resolution strategy
    ───────────────────
    1. Try an exact full-key match first.
    2. Fall back to basename match (``app_label/migrations/name`` → ``name``).
    3. Unknown/missing dependencies are silently skipped (still backward-
       compatible with files that have no ``dependencies`` attribute).
    """
    # Build lookup: basename → [key] and key → index
    key_set = {k for _, k, _ in migrations}
    by_basename: dict = {}
    for _, k, _ in migrations:
        by_basename.setdefault(os.path.basename(k), []).append(k)

    def _resolve_dep(app_label: str, name: str) -> str | None:
        # Attempt 1: construct a likely full-path key
        # key pattern: "<something>/migrations/<num>_name"
        # The dep may use just the base name, matching   anything ending in that name
        candidates = by_basename.get(name, [])
        # Filter by app_label appearing somewhere in the key path
        filtered = [k for k in candidates if app_label in k]
        if filtered:
            return filtered[0]
        if candidates:
            return candidates[0]
        return None

    # Build dependency graph: key → {keys it depends on}
    graph: dict = {k: set() for _, k, _ in migrations}
    filepath_for = {k: fp for _, k, fp in migrations}

    for _, key, filepath in migrations:
        for app_label, dep_name in read_dependencies(filepath):
            resolved = _resolve_dep(app_label, dep_name)
            if resolved and resolved in key_set and resolved != key:
                graph[key].add(resolved)

    # Kahn's algorithm (BFS topological sort)
    from collections import deque
    in_degree = {k: 0 for k in graph}
    for k, deps in graph.items():
        for dep in deps:
            in_degree[k] = in_degree.get(k, 0)  # ensure present
    for k, deps in graph.items():
        for dep in deps:
            # dep must come before k → increment k's in-degree
            pass
    # Rebuild in-degree properly
    in_degree = {k: 0 for k in graph}
    reverse_edges: dict = {k: [] for k in graph}
    for k, deps in graph.items():
        for dep in deps:
            reverse_edges[dep].append(k)   # dep → k  (k depends on dep)
            in_degree[k] += 1

    queue: deque = deque([
        k for k in graph
        if in_degree[k] == 0
    ])
    # Stable ordering within same in-degree: sort by (num, key)
    num_for = {k: num for num, k, _ in migrations}
    queue = deque(sorted(queue, key=lambda k: (num_for.get(k, 0), k)))

    order: List[str] = []
    while queue:
        k = queue.popleft()
        order.append(k)
        # Sort next candidates for stable output
        next_batch = []
        for neighbour in reverse_edges.get(k, []):
            in_degree[neighbour] -= 1
            if in_degree[neighbour] == 0:
                next_batch.append(neighbour)
        next_batch.sort(key=lambda x: (num_for.get(x, 0), x))
        queue.extend(next_batch)

    if len(order) != len(graph):
        # Cycle detected — fall back to numeric order
        return sorted(migrations, key=lambda x: x[0])

    # Rebuild result list in computed order
    mig_by_key = {k: (num, k, fp) for num, k, fp in migrations}
    return [mig_by_key[k] for k in order]


def _migration_app_label_from_path(migration_key: str) -> str:
    """
    Infer Django-style app_label from a migration tracking key (path fallback)::

        apps/logs/migrations/0001_initial  →  logs
    """
    parts = migration_key.replace("\\", "/").split("/")
    if "migrations" in parts:
        i = parts.index("migrations")
        if i > 0:
            return parts[i - 1]
    return ""


def resolve_migration_app_label(migration_key: str, filepath: str) -> str:
    """
    Canonical app_label for ``allow_migrate`` and tooling.

    Prefers ``app_label = "..."`` inside the migration file (written by current
    ``makemigrations`` from ``Model._meta.app_label``). Falls back to the path
    segment before ``migrations/`` for legacy files.
    """
    from .writer import read_migration_app_label

    label = read_migration_app_label(filepath)
    if label:
        return label
    return _migration_app_label_from_path(migration_key)

def _get_existing_tables(connection: Any) -> set:
    """Return set of all table names currently in the database.

    Delegates to backend.get_existing_tables_sql() so the runner stays
    vendor-neutral — adding MySQL, SQLite, etc. only requires updating
    the respective backend, not this file.
    """
    sql = connection.backend.get_existing_tables_sql()
    rows = connection.execute(sql, [], as_dict=True)
    return {r["tablename"] for r in rows}


def _get_migration_tables(filepath: str) -> List[str]:
    """Return the table names a migration file would create."""
    spec = importlib.util.spec_from_file_location("_probe_migration", filepath)
    if spec is None or spec.loader is None:
        return []
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tables = []
    for op in getattr(module, "operations", []):
        if isinstance(op, CreateTable):
            tables.append(op.table_name)
    return tables


def _upgrade_legacy_keys(connection: Any, all_keys: List[str], applied: set) -> set:
    """
    Upgrade bare migration keys (e.g. "0001_auto") stored by the old single-dir
    runner to their full relative-path equivalents.

    When only ONE full key matches → unambiguous, rename directly.
    When multiple full keys match → resolve by checking which migration's tables
    already exist in the database (the one that was originally applied).
    Keys that cannot be resolved (no tables found) are left as-is (safe to skip).
    """
    backend = connection.backend
    q = backend.quote_ident(MIGRATIONS_TABLE)
    updated = set(applied)

    # Group full keys by basename; build filepath lookup
    by_basename: dict = {}
    filepath_for_key: dict = {}
    for key in all_keys:
        base = os.path.basename(key)
        by_basename.setdefault(base, []).append(key)

    for bare_key in list(applied):
        if "/" in bare_key or os.sep in bare_key:
            continue  # already a full-path key
        candidates = by_basename.get(bare_key, [])
        if not candidates:
            continue

        if len(candidates) == 1:
            winner = candidates[0]
        else:
            # Ambiguous: find which candidate's tables already exist in the DB
            existing_tables = _get_existing_tables(connection)
            winner = None
            for candidate_key in candidates:
                # Reconstruct filepath from key
                # key format: "apps/inventory/migrations/0001_auto"
                # We stored all_keys; need to find the actual filepath
                # We'll search collect_migration_dirs output for matching files
                # Since we only have keys here, derive filepath from key + project root via stored map
                # Use the _filepath_for_key dict populated by migrate_all_apps
                candidate_filepath = getattr(_upgrade_legacy_keys, "_filepath_map", {}).get(candidate_key)
                if not candidate_filepath:
                    continue
                tables = _get_migration_tables(candidate_filepath)
                if tables and all(t in existing_tables for t in tables):
                    winner = candidate_key
                    break

        if winner and winner not in updated:
            connection.execute(
                f"UPDATE {q} SET name = %s WHERE name = %s",
                [winner, bare_key],
                as_dict=True,
            )
            updated.discard(bare_key)
            updated.add(winner)

    return updated


# ── new utility functions ─────────────────────────────────────────────────────

def get_sql_for_ops(backend: Any, operations: list) -> List[str]:
    """Convert a list of migration operations to SQL strings without executing them."""
    from .operations import (
        CreateTable, DropTable, RenameTable,
        AddColumn, DropColumn, RenameColumn, AlterColumn,
        AddIndex, DropIndex,
    )
    sqls: List[str] = []
    for op in operations:
        if isinstance(op, CreateTable):
            sqls.append(backend.get_create_table_sql(op.table_name, op.columns))
        elif isinstance(op, DropTable):
            sqls.append(backend.get_drop_table_sql(op.table_name))
        elif isinstance(op, RenameTable):
            sqls.append(backend.get_rename_table_sql(op.old_name, op.new_name))
        elif isinstance(op, AddColumn):
            sqls.append(backend.get_add_column_sql(op.table_name, op.column_name, op.column_type))
        elif isinstance(op, DropColumn):
            sqls.append(backend.get_drop_column_sql(op.table_name, op.column_name))
        elif isinstance(op, RenameColumn):
            sqls.append(backend.get_rename_column_sql(op.table_name, op.old_name, op.new_name))
        elif isinstance(op, AlterColumn):
            sqls.extend(backend.get_alter_column_sqls(op.table_name, op.column_name, op.new_type))
        elif isinstance(op, AddIndex):
            sqls.append(backend.get_add_index_sql(
                op.table_name, op.column_names, op.index_name, op.unique
            ))
        elif isinstance(op, DropIndex):
            sqls.append(backend.get_drop_index_sql(op.index_name))
    return sqls


def load_operations(filepath: str) -> list:
    """Load and return the operations list from a migration file."""
    spec = importlib.util.spec_from_file_location("_raftsql_load_ops", filepath)
    if spec is None or spec.loader is None:
        return []
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        return []
    return list(getattr(module, "operations", []))


def _compute_reverse_ops(operations: list, state_before: dict) -> list:
    """
    Compute the reverse (undo) operations for a list of forward operations.
    Uses state_before to recover original column/table definitions for
    operations like DropColumn and AlterColumn whose reversal requires
    knowing the original type.
    Returns reverse operations in reverse chronological order.
    """
    from .operations import (
        CreateTable, DropTable, RenameTable,
        AddColumn, DropColumn, RenameColumn, AlterColumn,
        AddIndex, DropIndex,
    )

    def _auto_idx(table: str, cols: list) -> str:
        return f"{table}_{'_'.join(cols)}_idx"

    reverse: list = []
    for op in reversed(operations):
        if isinstance(op, CreateTable):
            reverse.append(DropTable(op.table_name))
        elif isinstance(op, DropTable):
            cols = state_before["tables"].get(op.table_name, {})
            if cols:
                reverse.append(CreateTable(op.table_name, list(cols.items())))
        elif isinstance(op, RenameTable):
            reverse.append(RenameTable(op.new_name, op.old_name))
        elif isinstance(op, AddColumn):
            reverse.append(DropColumn(op.table_name, op.column_name))
        elif isinstance(op, DropColumn):
            orig_type = state_before["tables"].get(op.table_name, {}).get(op.column_name)
            if orig_type:
                reverse.append(AddColumn(op.table_name, op.column_name, orig_type))
        elif isinstance(op, RenameColumn):
            reverse.append(RenameColumn(op.table_name, op.new_name, op.old_name))
        elif isinstance(op, AlterColumn):
            orig_type = state_before["tables"].get(op.table_name, {}).get(op.column_name)
            if orig_type:
                reverse.append(AlterColumn(op.table_name, op.column_name, orig_type))
        elif isinstance(op, AddIndex):
            idx_name = op.index_name or _auto_idx(op.table_name, op.column_names)
            reverse.append(DropIndex(idx_name))
        elif isinstance(op, DropIndex):
            idx_data = state_before["indexes"].get(op.index_name, {})
            if idx_data:
                reverse.append(AddIndex(
                    idx_data["table"], list(idx_data["columns"]),
                    op.index_name, idx_data.get("unique", False),
                ))
    return reverse


def get_migration_status(connection: Any, project_root: str) -> dict:
    """
    Return migration applied/pending status grouped by app directory.
    {
        "rel_app_dir": [
            {"num": int, "name": str, "key": str, "filepath": str, "applied": bool},
            ...
        ]
    }
    """
    _ensure_migrations_table(connection)
    applied = _get_applied_names(connection)

    status: dict = {}
    for mig_dir in sorted(collect_migration_dirs(project_root)):
        files = list_migration_files(mig_dir)
        if not files:
            continue
        app_dir = os.path.dirname(mig_dir)
        rel_app = os.path.relpath(app_dir, project_root)
        entries = []
        for num, name, filepath in files:
            rel = os.path.relpath(filepath, project_root)
            key = rel.replace(os.sep, "/")[:-3]
            entries.append({
                "num": num,
                "name": name,
                "key": key,
                "filepath": filepath,
                "applied": _is_applied(key, applied),
            })
        status[rel_app] = entries
    return status


def rollback_app(connection: Any, migrations_dir: str, project_root: str) -> List[str]:
    """
    Unapply ALL applied migrations for one app (equivalent to ``migrate --zero APP``).
    Reverses migrations in reverse chronological order.
    Returns list of migration keys that were rolled back.
    """
    from .state import build_state_before

    if not os.path.isdir(migrations_dir):
        return []

    _ensure_migrations_table(connection)
    applied = _get_applied_names(connection)

    files = list_migration_files(migrations_dir)
    applied_files = []
    for num, _name, filepath in files:
        rel = os.path.relpath(filepath, project_root)
        key = rel.replace(os.sep, "/")[:-3]
        if _is_applied(key, applied):
            applied_files.append((num, key, filepath))

    if not applied_files:
        return []

    backend = connection.backend
    q = backend.quote_ident(MIGRATIONS_TABLE)
    rolled_back: List[str] = []

    for num, key, filepath in reversed(applied_files):
        state_before = build_state_before(migrations_dir, num)
        ops = load_operations(filepath)
        reverse_ops = _compute_reverse_ops(ops, state_before)
        for sql in get_sql_for_ops(backend, reverse_ops):
            connection.execute(sql, [], as_dict=True)
        connection.execute(f"DELETE FROM {q} WHERE name = %s", [key], as_dict=True)
        rolled_back.append(key)

    return rolled_back


def migrate_all_apps(
    connection: Any,
    project_root: str,
    fake: bool = False,
    fake_initial: bool = False,
    plan: bool = False,
) -> List[str]:
    """
    Discover and apply pending migrations from EVERY migrations/ directory
    found under project_root.

    Migration tracking key: relative path from project_root without .py extension.
    Example: "apps/inventory/migrations/0001_auto"

    Backward-compatible: bare keys like "0001_auto" written by the old single-dir
    migrate() are upgraded to full-path keys before comparison so they are never
    accidentally matched against a same-named migration in a different app.

    Returns list of migration keys applied this run.
    """
    _ensure_migrations_table(connection)
    applied = _get_applied_names(connection)
    applied_this_run: List[str] = []

    # Collect ALL migration files first (needed for legacy key upgrade)
    all_migrations = []
    filepath_map: dict = {}
    for mig_dir in collect_migration_dirs(project_root):
        for num, _name, filepath in list_migration_files(mig_dir):
            rel = os.path.relpath(filepath, project_root)
            key = rel.replace(os.sep, "/")[:-3]   # forward-slash, no .py
            all_migrations.append((num, key, filepath))
            filepath_map[key] = filepath

    # Upgrade any bare legacy keys before checking applied status
    all_keys = [k for _, k, _ in all_migrations]
    _upgrade_legacy_keys._filepath_map = filepath_map  # type: ignore[attr-defined]
    applied = _upgrade_legacy_keys(connection, all_keys, applied)

    # Safety net: any bare key still in applied (ambiguous — upgrade couldn't
    # determine a unique owner) means the migration was applied before per-app
    # tracking existed. Treat ALL candidates with that basename as applied so we
    # never re-run a migration whose table already exists.
    by_basename: dict = {}
    for key in all_keys:
        by_basename.setdefault(os.path.basename(key), []).append(key)
    for bare_key in list(applied):
        if "/" not in bare_key and os.sep not in bare_key:
            for candidate in by_basename.get(bare_key, []):
                applied.add(candidate)

    # Now determine which are pending (full-path match only — no bare fallback)
    pending = [
        (num, key, filepath)
        for num, key, filepath in all_migrations
        if key not in applied
    ]

    # Sort using dependency-aware topological sort
    pending_sorted = _topological_sort(pending, project_root)

    from ..routing import allow_migrate_allowed

    db_alias = getattr(connection._config, "alias", "default")

    for _num, key, filepath in pending_sorted:
        app_label = resolve_migration_app_label(key, filepath)
        if app_label and not allow_migrate_allowed(db_alias, app_label, None):
            continue
        if plan:
            applied_this_run.append(key)
            continue
        if fake:
            _record_migration(connection, key)
        elif fake_initial and _num == 1:
            # Mark as applied only if all tables this migration creates already exist
            mig_tables = _get_migration_tables(filepath)
            existing_tables = _get_existing_tables(connection)
            if mig_tables and all(t in existing_tables for t in mig_tables):
                _record_migration(connection, key)
            else:
                _run_migration_file(connection, filepath)
                _record_migration(connection, key)
        else:
            _run_migration_file(connection, filepath)
            _record_migration(connection, key)
        applied_this_run.append(key)

    return applied_this_run
