"""Generate migration files from Model classes using schema diff."""
import os
from typing import Dict, List, Optional, Tuple, Type

from ..db.backends.base import Backend
from ..orm.model import Model
from ..orm.model import table_name as table_name_fn
from .operations import (
    CreateTable, DropTable, RenameTable,
    AddColumn, DropColumn, RenameColumn, AlterColumn, AddIndex, DropIndex,
    AddConstraint, DropConstraint,
)
from .schema import get_m2m_schemas, get_schema_from_model, snapshot_from_models, field_signature
from .state import build_state, _auto_index_name
from .writer import write_migration_file, list_migration_files


def _consensus_app_label(models: List[Type[Model]]) -> str:
    """
    Single app_label for migration metadata from the model classes in one app dir.

    Warns if ``Meta.app_label`` values disagree — first model wins.
    """
    if not models:
        return ""
    labels = [m._meta.app_label for m in models]
    first = labels[0]
    bad = [lb for lb in labels if lb != first]
    if bad:
        import warnings
        uniq = sorted(set(labels))
        warnings.warn(
            f"Mixed Meta.app_label values in one migrations directory: {uniq!r}. "
            f"Using {first!r} in the new migration file — set explicit app_label on "
            "all models here to match.",
            UserWarning,
            stacklevel=4,
        )
    return first


def makemigrations(
    models: List[Type[Model]],
    backend: Backend,
    migrations_dir: str,
    migration_name: str = "auto",
    dry_run: bool = False,
    no_input: bool = False,
) -> Optional[str]:
    """
    Diff current model definitions against the recorded migration state and
    generate a new migration file for any detected changes.

    Detected changes
    ─────────────────
    • New table (model added)            → CreateTable
    • Deleted table (model removed)      → DropTable
    • Renamed table (interactive prompt) → RenameTable
    • New column (field added to model)  → AddColumn
    • Changed column type/constraints    → AlterColumn
    • Removed column (field deleted)     → DropColumn
    • New db_index field                 → AddIndex
    • Removed db_index field             → DropIndex

    Note: RenameColumn is NOT auto-generated (ambiguous intent — looks the
    same as DropColumn + AddColumn).  Add it manually if needed.

    Returns the path to the written file, or None if there is nothing to do.
    """
    state = build_state(migrations_dir)
    operations = _diff_models(models, backend, state, no_input=no_input)

    if not operations:
        return None

    if dry_run:
        return None  # Caller uses compute_migration_ops() for details

    # Auto-detect dependency: if there are already migrations in this app,
    # depend on the most recent one so the DAG stays linear within the app.
    dependencies = _get_previous_migration_dep(migrations_dir)

    # Snapshot current model structure so future makemigrations runs can
    # detect renames accurately by comparing field signatures.
    current_model_state = snapshot_from_models(models)

    app_lbl = _consensus_app_label(models)

    return write_migration_file(
        migrations_dir,
        migration_name,
        operations,
        dependencies,
        model_state=current_model_state,
        app_label=app_lbl or None,
    )


def compute_migration_ops(
    models: List[Type[Model]],
    backend: Backend,
    migrations_dir: str,
    no_input: bool = False,
) -> list:
    """Return the list of operations that would be generated (without writing any file)."""
    state = build_state(migrations_dir)
    return _diff_models(models, backend, state, no_input=no_input)


def compute_changes_per_app(
    models_by_app: Dict[str, List[Type[Model]]],
    backend: Backend,
    no_input: bool = False,
) -> Dict[str, list]:
    """Return {app_dir: [operations]} for every app that has pending changes."""
    result: Dict[str, list] = {}
    for app_dir, models in models_by_app.items():
        migrations_dir = _app_migrations_dir(app_dir)
        ops = compute_migration_ops(models, backend, migrations_dir, no_input=no_input)
        if ops:
            result[app_dir] = ops
    return result


def _prompt_rename(old: str, new: str, no_input: bool = False) -> bool:
    """
    Ask the user interactively whether old_table was renamed to new_table.
    Returns True if confirmed, False otherwise.
    When stdin is not a tty (e.g. CI) or no_input=True, defaults to False.
    """
    import sys
    if no_input or not sys.stdin.isatty():
        return False
    try:
        answer = input(f"  Was table '{old}' renamed to '{new}'? [y/N] ").strip().lower()
        return answer in ("y", "yes")
    except KeyboardInterrupt:
        raise
    except EOFError:
        return False


def _prompt_field_rename(table: str, old_col: str, new_col: str, no_input: bool = False) -> bool:
    """
    Ask the user interactively whether old_col was renamed to new_col on table.
    Returns True if confirmed, False otherwise.
    When stdin is not a tty or no_input=True, defaults to False.
    """
    import sys
    if no_input or not sys.stdin.isatty():
        return False
    try:
        answer = input(
            f"  Was column '{old_col}' on '{table}' renamed to '{new_col}'? [y/N] "
        ).strip().lower()
        return answer in ("y", "yes")
    except KeyboardInterrupt:
        raise
    except EOFError:
        return False


def _default_hint_for_type(type_sql: str) -> tuple:
    """
    Given a column type SQL, return (hint_text, suggested_default) so the
    prompt can show a useful example.

    Returns (hint, suggested) where:
      hint       — printed as "e.g. <hint>"  (what the user might type)
      suggested  — pre-filled suggestion shown in brackets, or ""
    """
    import re
    t = type_sql.upper().split()[0] if type_sql else ""

    if re.search(r'\bTIMESTAMP\b|\bDATETIME\b', type_sql, re.I):
        return "CURRENT_TIMESTAMP  or  NOW()", "CURRENT_TIMESTAMP"
    if re.search(r'\bDATE\b', type_sql, re.I):
        return "CURRENT_DATE", "CURRENT_DATE"
    if re.search(r'\bTIME\b', type_sql, re.I):
        return "CURRENT_TIME", "CURRENT_TIME"
    if re.search(r'\bBOOLEAN\b|\bBOOL\b', type_sql, re.I):
        return "true  or  false", "false"
    if re.search(r'\bSERIAL\b|\bINTEGER\b|\bINT\b|\bBIGINT\b|\bSMALLINT\b', type_sql, re.I):
        return "0  or  1  or  any integer", "0"
    if re.search(r'\bNUMERIC\b|\bDECIMAL\b|\bFLOAT\b|\bREAL\b|\bDOUBLE\b', type_sql, re.I):
        return "0.0  or  any number", "0.0"
    if re.search(r'\bVARCHAR\b|\bTEXT\b|\bCHAR\b', type_sql, re.I):
        return "''  (empty string)  or  any quoted string", "''"
    if re.search(r'\bJSONB?\b', type_sql, re.I):
        return "'{}'  (empty JSON object)  or  '[]'", "'{}'"
    if re.search(r'\bUUID\b', type_sql, re.I):
        return "gen_random_uuid()  (requires pgcrypto)", ""
    return "", ""


def _check_not_null_add(table: str, col: str, type_sql: str, no_input: bool = False) -> str:
    """
    When adding a NOT NULL column with no DEFAULT to an existing table, warn the user.
    In interactive mode, offer to enter a default value so the migration won't fail
    if the table has existing rows.

    For date/time/datetime columns the prompt shows CURRENT_DATE / CURRENT_TIMESTAMP
    as suggestions (analogous to Django's timezone.now).
    Returns potentially modified type_sql.
    """
    import re, sys
    has_not_null = bool(re.search(r'\bNOT\s+NULL\b', type_sql, re.I))
    has_default = bool(re.search(r'\bDEFAULT\b', type_sql, re.I))
    if not has_not_null or has_default:
        return type_sql

    hint, suggested = _default_hint_for_type(type_sql)

    if no_input or not sys.stdin.isatty():
        warn = (
            f"  WARNING: Adding NOT NULL column '{col}' to '{table}' with no default."
        )
        if suggested:
            warn += f" Consider DEFAULT {suggested}."
        warn += " This will fail if the table has existing rows."
        print(warn, file=sys.stderr)
        return type_sql

    try:
        print(f"\n  Column '{col}' on '{table}' ({type_sql.split()[0]}) is NOT NULL with no default.")
        print(f"  If the table already has rows, this migration will fail.")
        if hint:
            print(f"  e.g. {hint}")
        prompt = f"  Default value for existing rows"
        if suggested:
            prompt += f" [{suggested}]"
        prompt += " (or Enter to skip): "
        val = input(prompt).strip()
        if not val and suggested:
            val = suggested
        if val:
            val = _normalize_default_value(val)
            return type_sql.rstrip() + f" DEFAULT {val}"
        return type_sql
    except KeyboardInterrupt:
        raise
    except EOFError:
        return type_sql


def _normalize_default_value(val: str) -> str:
    """
    Normalize a user-supplied default value for safe use in SQL DEFAULT clauses.

    - Double-quoted strings ("foo", "") → single-quoted ('foo', '')
    - Bare unquoted words that aren't SQL keywords get single-quoted
      e.g.  hello → 'hello'
    - SQL keywords/functions pass through unchanged:
      CURRENT_TIMESTAMP, NOW(), CURRENT_DATE, true, false, 0, 0.0, ...
    """
    import re

    # Already single-quoted → leave as-is
    if val.startswith("'") and val.endswith("'") and len(val) >= 2:
        return val

    # Double-quoted string ("...") → convert outer quotes to single quotes
    if val.startswith('"') and val.endswith('"') and len(val) >= 2:
        inner = val[1:-1].replace("'", "''")   # escape any single quotes inside
        return f"'{inner}'"

    # SQL keywords / functions / numeric literals that need no quoting
    _SQL_LITERALS = re.compile(
        r"""^(
            CURRENT_TIMESTAMP | CURRENT_DATE | CURRENT_TIME |
            NOW\(\) | TRUE | FALSE | true | false |
            NULL |
            gen_random_uuid\(\) |
            -?\d+(\.\d+)?          # numeric literals
        )$""",
        re.VERBOSE | re.IGNORECASE,
    )
    if _SQL_LITERALS.match(val):
        return val

    # Anything else (bare word, unquoted text) → wrap in single quotes
    escaped = val.replace("'", "''")
    return f"'{escaped}'"


# ── diff helpers ──────────────────────────────────────────────────────────────

def _diff_models(
    models: List[Type[Model]],
    backend: Backend,
    state: dict,
    no_input: bool = False,
) -> list:
    """Return the list of operations needed to bring the DB up to date."""
    tables_state = state["tables"]   # {table: {col: type_sql}}
    indexes_state = state["indexes"] # {index_name: {table, columns, unique}}

    ops: list = []

    # Snapshot the current models at the Python level for accurate rename detection
    current_model_state = snapshot_from_models(models)

    # Build current model column map: {table: {col: type_sql}}
    model_col_map: Dict[str, Dict[str, str]] = {}
    model_index_map: Dict[str, List[dict]] = {}
    for model in models:
        table, columns = get_schema_from_model(model, backend)
        model_col_map[table] = dict(columns)
        model_index_map[table] = _indexes_for_model(model, table)

    # M2M junction tables (no model class, just columns)
    junction_col_map: Dict[str, Dict[str, str]] = {}
    seen_junctions: set = set()
    for model in models:
        for junction, columns in get_m2m_schemas(model):
            if junction not in seen_junctions:
                seen_junctions.add(junction)
                junction_col_map[junction] = dict(columns)

    # ── 1. Detect new and removed tables ───────────────────────────────────
    all_current_tables = set(model_col_map) | set(junction_col_map)
    new_tables = sorted(t for t in all_current_tables if t not in tables_state)
    dropped_tables = sorted(t for t in tables_state if t not in all_current_tables)

    # ── 1a. Interactive rename detection ───────────────────────────────────
    # If there are both new and dropped tables, ask the user whether any pair
    # is a rename rather than a delete + create.
    confirmed_renames: Dict[str, str] = {}   # {old_table: new_table}
    if new_tables and dropped_tables:
        for old in list(dropped_tables):
            for new in list(new_tables):
                if new in confirmed_renames.values():
                    continue
                old_ms = state.get("model_state", {}).get(old, {})
                new_ms = current_model_state.get(new, {})
                if old_ms and new_ms:
                    # Django-style: compare field signatures (class + SQL type),
                    # excluding PK fields that are identical in every model.
                    def _non_pk_sigs(ms: dict) -> set:
                        return {
                            field_signature(fmeta)
                            for fmeta in ms.get("fields", {}).values()
                            if "PRIMARY KEY" not in fmeta.get("sql", "").upper()
                        }
                    sig_overlap = len(_non_pk_sigs(old_ms) & _non_pk_sigs(new_ms))
                    should_prompt = sig_overlap >= 1 or (len(new_tables) == 1 and len(dropped_tables) == 1)
                else:
                    # Legacy fallback: SQL column-name overlap
                    old_cols = set(tables_state[old].keys())
                    new_cols = set((model_col_map.get(new) or junction_col_map.get(new) or {}).keys())
                    overlap = len(old_cols & new_cols) / max(len(old_cols | new_cols), 1)
                    should_prompt = overlap > 0.3 or (len(new_tables) == 1 and len(dropped_tables) == 1)
                if should_prompt:
                    answer = _prompt_rename(old, new, no_input)
                else:
                    answer = False
                if answer:
                    confirmed_renames[old] = new

    # ── 1b. Emit renames, then new-creates (skipping renamed targets) ──────
    for old, new in confirmed_renames.items():
        ops.append(RenameTable(old, new))
        # Column diff for the renamed table (old state → new model),
        # including signature-based column-rename detection.
        existing = tables_state[old]
        current = model_col_map.get(new) or junction_col_map.get(new) or {}

        added_cols = [col for col in current if col not in existing]
        dropped_cols = [col for col in existing if col not in current]
        tbl_col_renames: Dict[str, str] = {}  # {old_col: new_col}
        if added_cols and dropped_cols:
            def _col_sig_map_inline(ms_fields: dict) -> Dict[str, str]:
                return {
                    fmeta["col"]: field_signature(fmeta)
                    for fmeta in ms_fields.values()
                }
            old_col_sigs = _col_sig_map_inline(
                state.get("model_state", {}).get(old, {}).get("fields", {})
            )
            new_col_sigs = _col_sig_map_inline(
                current_model_state.get(new, {}).get("fields", {})
            )
            for old_col in dropped_cols:
                for new_col in added_cols:
                    if new_col in tbl_col_renames.values():
                        continue
                    if old_col_sigs and new_col_sigs:
                        old_sig = old_col_sigs.get(old_col)
                        new_sig = new_col_sigs.get(new_col)
                        if not old_sig or not new_sig or old_sig != new_sig:
                            continue
                    if _prompt_field_rename(new, old_col, new_col, no_input):
                        tbl_col_renames[old_col] = new_col
                        break

        for old_col, new_col in tbl_col_renames.items():
            ops.append(RenameColumn(new, old_col, new_col))

        for col, type_sql in current.items():
            if col not in existing:
                if col in tbl_col_renames.values():
                    continue
                ops.append(AddColumn(new, col, type_sql))
            elif existing[col] != type_sql:
                ops.append(AlterColumn(new, col, type_sql))
        for col in existing:
            if col not in current:
                if col in tbl_col_renames:
                    continue
                ops.append(DropColumn(new, col))

    renamed_old = set(confirmed_renames.keys())
    renamed_new = set(confirmed_renames.values())

    for table in sorted(new_tables):
        if table in renamed_new:
            continue  # already handled as a rename
        cols = model_col_map.get(table) or junction_col_map[table]
        ops.append(CreateTable(table, list(cols.items())))
        for idx in model_index_map.get(table, []):
            ops.append(AddIndex(table, idx["columns"], idx["name"], idx["unique"]))

    for table in sorted(dropped_tables):
        if table in renamed_old:
            continue  # already handled as a rename
        ops.append(DropTable(table))

    # ── 2. Existing tables: column diff ────────────────────────────────────
    for table in sorted(model_col_map):
        if table not in tables_state:
            continue  # handled above

        existing = tables_state[table]
        current = model_col_map[table]

        # ── column rename detection (prompt before diff) ──────────────────
        added_cols = [col for col in current if col not in existing]
        dropped_cols = [col for col in existing if col not in current]
        confirmed_col_renames: Dict[str, str] = {}  # {old_col: new_col}
        if added_cols and dropped_cols:
            # Build col → field-signature maps from model_state when available
            def _col_sig_map(ms_fields: dict) -> Dict[str, str]:
                return {
                    fmeta["col"]: field_signature(fmeta)
                    for fmeta in ms_fields.values()
                }
            old_col_sigs = _col_sig_map(
                state.get("model_state", {}).get(table, {}).get("fields", {})
            )
            new_col_sigs = _col_sig_map(
                current_model_state.get(table, {}).get("fields", {})
            )

            for old_col in dropped_cols:
                for new_col in added_cols:
                    if new_col in confirmed_col_renames.values():
                        continue
                    if old_col_sigs and new_col_sigs:
                        # Only propose as a rename when field types match exactly
                        old_sig = old_col_sigs.get(old_col)
                        new_sig = new_col_sigs.get(new_col)
                        if not old_sig or not new_sig or old_sig != new_sig:
                            continue  # different types → drop + add, not a rename
                    if _prompt_field_rename(table, old_col, new_col, no_input):
                        confirmed_col_renames[old_col] = new_col
                        break

        for old_col, new_col in confirmed_col_renames.items():
            ops.append(RenameColumn(table, old_col, new_col))

        for col, type_sql in current.items():
            if col not in existing:
                if col in confirmed_col_renames.values():
                    continue  # already a rename
                type_sql = _check_not_null_add(table, col, type_sql, no_input)
                ops.append(AddColumn(table, col, type_sql))
            elif existing[col] != type_sql:
                ops.append(AlterColumn(table, col, type_sql))

        for col in existing:
            if col not in current:
                if col in confirmed_col_renames:
                    continue  # already a rename
                ops.append(DropColumn(table, col))

        # ── index diff for db_index fields ─────────────────────────────
        model_idxs = {
            (idx["name"] or _auto_index_name(table, idx["columns"])): idx
            for idx in model_index_map.get(table, [])
        }
        existing_idxs = {
            n: v for n, v in indexes_state.items() if v["table"] == table
        }

        for idx_name, idx in model_idxs.items():
            if idx_name not in existing_idxs:
                ops.append(AddIndex(table, idx["columns"], idx["name"], idx["unique"]))

        for idx_name in existing_idxs:
            if idx_name not in model_idxs:
                ops.append(DropIndex(idx_name))

        # ── constraint diff (CheckConstraint / UniqueConstraint in Meta) ──
        # Model constraints are stored alongside columns as __c__{name} keys.
        model_constraints: Dict[str, str] = {}
        for model in models:
            if table_name_fn(model) == table:
                for c in getattr(model, "_constraints", []):
                    model_constraints[c.name] = c.as_sql(backend)
                break

        state_constraints: Dict[str, str] = {
            k[5:]: v
            for k, v in existing.items()
            if k.startswith("__c__")
        }

        for cname, csql in model_constraints.items():
            if cname not in state_constraints:
                ops.append(AddConstraint(table, cname, csql))
            elif state_constraints[cname] != csql:
                ops.append(DropConstraint(table, cname))
                ops.append(AddConstraint(table, cname, csql))

        for cname in state_constraints:
            if cname not in model_constraints:
                ops.append(DropConstraint(table, cname))

    return ops


def _indexes_for_model(model: Type[Model], table: str) -> List[dict]:
    """Return [{name, columns, unique}] for db_index=True fields on the model."""
    db_indexes = getattr(model, "_db_indexes", [])
    return [
        {
            "name": f"{table}_{col}_idx",
            "columns": [col],
            "unique": False,
        }
        for col in db_indexes
    ]


# ── per-app entry point ───────────────────────────────────────────────────────

def makemigrations_per_app(
    models_by_app: Dict[str, List[Type[Model]]],
    backend: Backend,
    migration_name: str = "auto",
    dry_run: bool = False,
    no_input: bool = False,
) -> List[Tuple[str, str]]:
    """
    Generate per-app migration files.

    For each app in models_by_app, migrations are written into:
        <app_dir>/migrations/

    Parameters
    ----------
    models_by_app : {absolute_app_dir: [model_classes]}
                    returned by discover_models_by_app()
    backend       : database backend instance
    migration_name: base name used for the migration file (default "auto")

    Returns
    -------
    List of (app_dir, migration_file_path) for every file that was created.
    Apps with no changes produce no entry in the result.
    """
    created_files: List[Tuple[str, str]] = []
    for app_dir, models in models_by_app.items():
        migrations_dir = _app_migrations_dir(app_dir)
        path = makemigrations(models, backend, migrations_dir, migration_name, dry_run=dry_run, no_input=no_input)
        if path:
            created_files.append((app_dir, path))
    return created_files


def _app_migrations_dir(app_dir: str) -> str:
    import os
    return os.path.join(app_dir, "migrations")


def _get_previous_migration_dep(migrations_dir: str) -> List[Tuple[str, str]]:
    """
    Return a ``[(app_label, migration_name)]`` list pointing to the most
    recently numbered migration already in *migrations_dir*.

    The app_label in the dependency tuple prefers the embedded ``app_label =``
    assignment in that migration file; otherwise it uses the basename of the
    app directory containing ``migrations/`` (e.g. ``apps/inventory`` → ``inventory``).

    Returns an empty list when this is the first migration.
    """
    existing = list_migration_files(migrations_dir)
    if not existing:
        return []
    last_num, last_name, filepath = existing[-1]
    migration_name = f"{last_num:04d}_{last_name}"
    from .writer import read_migration_app_label

    label = read_migration_app_label(filepath)
    if not label:
        label = os.path.basename(os.path.dirname(migrations_dir))
    return [(label, migration_name)]

