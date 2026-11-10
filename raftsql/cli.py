"""
RaftSQL CLI — registered as the `raftsql` command.

Usage
─────
  raftsql generate  [--name NAME] [--dry-run] [--check] [--no-input]
  raftsql apply     [--fake] [--fake-initial] [--plan] [--zero APP_DIR]
  raftsql status
  raftsql sql <migration_file>
  raftsql squash <app_dir>
  raftsql flush     [--no-input]
  raftsql inspect   [TABLE ...]

Configuration is read from setraft.py (auto-discovered in the project).
Models are auto-discovered by scanning .py files for Model subclasses.
"""
import argparse
import os
import sys

# Ensure project root (cwd) is importable
if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())


_SETRAFT_HINT = (
    "setraft.py not found.\n\n"
    "Create a setraft.py in your project root. Example:\n\n"
    "    import os\n"
    "    from pathlib import Path\n"
    "    from dotenv import load_dotenv\n\n"
    "    BASE_DIR = Path(__file__).resolve().parent\n"
    "    load_dotenv(BASE_DIR / '.env')\n\n"
    "    DATABASE = {\n"
    '        "ENGINE":   "postgresql",\n'
    '        "HOST":     os.getenv("DB_HOST", "localhost"),\n'
    '        "PORT":     int(os.getenv("DB_PORT", 5432)),\n'
    '        "USER":     os.getenv("DB_USER", "postgres"),\n'
    '        "PASSWORD": os.getenv("DB_PASSWORD", ""),\n'
    '        "NAME":     os.getenv("DB_NAME", "mydb"),\n'
    "    }\n"
)


def _project_root_safe() -> str:
    """Return project root or print hint and sys.exit(1)."""
    from raftsql.conf.loader import get_project_root
    try:
        return get_project_root()
    except RuntimeError:
        print(_SETRAFT_HINT, file=sys.stderr)
        sys.exit(1)


def _make_config(db: dict, alias: str = "default"):
    from raftsql.conf.config import Config
    return Config(
        engine=db.get("ENGINE", "postgresql"),
        host=db.get("HOST", "localhost"),
        port=int(db.get("PORT", 5432)),
        user=db.get("USER", "postgres"),
        password=db.get("PASSWORD", ""),
        dbname=db.get("NAME", ""),
        alias=alias,
    )


def _load_project():
    """Locate setraft.py, run setup once, return (project_root, db dict for default alias)."""
    project_root = _project_root_safe()
    _ensure_setup()
    import raftsql
    cfg = raftsql.get_db("default")
    db = {
        "ENGINE": cfg.engine,
        "HOST": cfg.host,
        "PORT": cfg.port,
        "USER": cfg.user,
        "PASSWORD": cfg.password,
        "NAME": cfg.dbname,
    }
    return project_root, db


def _ensure_setup() -> None:
    """Load setraft.py, DATABASE_ROUTERS / GUIDES, and multi-database configs."""
    import raftsql
    if not raftsql._global_configs:
        raftsql.setup()


def _describe_op(op) -> str:
    """One-line human-readable description of an operation for dry-run output."""
    from raftsql.migrations.operations import (
        CreateTable, DropTable, RenameTable,
        AddColumn, DropColumn, RenameColumn, AlterColumn,
        AddIndex, DropIndex, AddConstraint, DropConstraint,
    )
    if isinstance(op, CreateTable):
        return f"Create table '{op.table_name}'"
    if isinstance(op, DropTable):
        return f"Drop table '{op.table_name}'"
    if isinstance(op, RenameTable):
        return f"Rename table '{op.old_name}' -> '{op.new_name}'"
    if isinstance(op, AddColumn):
        return f"Add column '{op.column_name}' to '{op.table_name}'"
    if isinstance(op, DropColumn):
        return f"Drop column '{op.column_name}' from '{op.table_name}'"
    if isinstance(op, RenameColumn):
        return f"Rename column '{op.old_name}' -> '{op.new_name}' on '{op.table_name}'"
    if isinstance(op, AlterColumn):
        return f"Alter column '{op.column_name}' on '{op.table_name}'"
    if isinstance(op, AddIndex):
        return f"Add index on '{op.table_name}' ({', '.join(op.column_names)})"
    if isinstance(op, DropIndex):
        return f"Drop index '{op.index_name}'"
    if isinstance(op, AddConstraint):
        return f"Add constraint '{op.constraint_name}' on '{op.table_name}'"
    if isinstance(op, DropConstraint):
        return f"Drop constraint '{op.constraint_name}' from '{op.table_name}'"
    return repr(op)


# ── commands ──────────────────────────────────────────────────────────────────

def cmd_makemigrations(name: str, dry_run: bool, check: bool, no_input: bool) -> int:
    from raftsql.conf.loader import get_apps
    from raftsql.db.backends import get_backend
    from raftsql.migrations.makemigrations import (
        makemigrations_per_app, compute_changes_per_app,
    )
    from raftsql.utils.discovery import discover_models_by_app

    project_root, db = _load_project()
    explicit_apps = get_apps()
    if explicit_apps is not None:
        print(f"Using APPS from setraft.py: {explicit_apps}")
    else:
        print(f"Auto-detecting apps in: {project_root}")

    models_by_app = discover_models_by_app(project_root, app_dirs=explicit_apps)
    if not models_by_app:
        print("No Model subclasses found in the project.", file=sys.stderr)
        return 1

    for app_dir, models in models_by_app.items():
        rel = os.path.relpath(app_dir, project_root)
        print(f"  App '{rel}': {[m.__name__ for m in models]}")

    config = _make_config(db)
    backend = get_backend(config.engine)

    # --check and --dry-run: compute ops without writing
    if dry_run or check:
        changes = compute_changes_per_app(models_by_app, backend, no_input=True)
        if check:
            if changes:
                print(
                    "Model changes detected — run 'raftsql generate' "
                    "to generate migration files."
                )
                return 1
            print("No model changes detected.")
            return 0
        # dry_run: just print what would happen
        if not changes:
            print("No changes detected.")
            return 0
        for app_dir, ops in changes.items():
            rel_app = os.path.relpath(app_dir, project_root)
            print(f"\n[{rel_app}] Would generate:")
            for op in ops:
                print(f"  - {_describe_op(op)}")
        return 0

    try:
        created = makemigrations_per_app(models_by_app, backend, name, no_input=no_input)
    except KeyboardInterrupt:
        print("\nAborted.")
        return 1
    if created:
        for app_dir, path in created:
            rel_app = os.path.relpath(app_dir, project_root)
            print(f"Created [{rel_app}]: {path}")
    else:
        print("No new migrations (all tables already have migrations).")
    return 0


def cmd_migrate(
    fake: bool,
    fake_initial: bool,
    plan: bool,
    zero_app: str,
    database: str = "default",
) -> int:
    from raftsql.db.connection import Connection
    from raftsql.migrations.runner import migrate_all_apps, rollback_app

    project_root = _project_root_safe()
    _ensure_setup()

    import raftsql
    try:
        config = raftsql.get_db(database)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1

    if zero_app:
        # Resolve the migrations directory for the given app path
        abs_app = os.path.join(project_root, zero_app)
        migrations_dir = os.path.join(abs_app, "migrations")
        if not os.path.isdir(migrations_dir):
            print(f"No migrations directory found for: {zero_app}", file=sys.stderr)
            return 1
        with Connection(config) as conn:
            rolled_back = rollback_app(conn, migrations_dir, project_root)
        if rolled_back:
            for key in rolled_back:
                print(f"Unapplied: {key}")
        else:
            print("No applied migrations found for that app.")
        return 0

    with Connection(config) as conn:
        applied = migrate_all_apps(
            conn, project_root,
            fake=fake,
            fake_initial=fake_initial,
            plan=plan,
        )

    if applied:
        if plan:
            label = "Would apply"
        elif fake or fake_initial:
            label = "Faked"
        else:
            label = "Applied"
        for key in applied:
            print(f"{label}: {key}")
    else:
        print("No pending migrations.")
    return 0


def cmd_showmigrations() -> int:
    from raftsql.db.connection import Connection
    from raftsql.migrations.runner import get_migration_status

    project_root, db = _load_project()
    config = _make_config(db)

    with Connection(config) as conn:
        status = get_migration_status(conn, project_root)

    if not status:
        print("No migrations found.")
        return 0

    for app_dir, entries in sorted(status.items()):
        print(f"\n{app_dir}")
        for entry in entries:
            mark = "X" if entry["applied"] else " "
            print(f"  [{mark}] {entry['num']:04d}_{entry['name']}")
    print()
    return 0


def cmd_sqlmigrate(migration_spec: str) -> int:
    """Print the SQL for a migration file without executing it."""
    from raftsql.db.backends import get_backend
    from raftsql.migrations.runner import get_sql_for_ops, load_operations

    project_root, db = _load_project()
    config = _make_config(db)
    backend = get_backend(config.engine)

    # Resolve filepath (relative to project root or absolute)
    filepath = migration_spec
    if not os.path.isabs(filepath):
        filepath = os.path.join(project_root, filepath)
    if not filepath.endswith(".py"):
        filepath += ".py"

    if not os.path.isfile(filepath):
        print(f"Migration file not found: {filepath}", file=sys.stderr)
        return 1

    ops = load_operations(filepath)
    if not ops:
        print("No operations found in migration.")
        return 0

    sqls = get_sql_for_ops(backend, ops)
    for sql in sqls:
        print(sql.rstrip(";") + ";")
    return 0


def cmd_squashmigrations(app_dir_arg: str) -> int:
    """Squash all migrations for an app into a single file."""
    from raftsql.migrations.writer import squash_migrations

    project_root, _ = _load_project()
    abs_app = os.path.join(project_root, app_dir_arg)
    migrations_dir = os.path.join(abs_app, "migrations")

    if not os.path.isdir(migrations_dir):
        print(f"No migrations directory found for: {app_dir_arg}", file=sys.stderr)
        return 1

    path = squash_migrations(migrations_dir)
    if path:
        print(f"Squashed into: {path}")
        print()
        print("If these migrations were already applied to the database, run:")
        print("  raftsql apply --fake-initial")
    else:
        print("Nothing to squash.")
    return 0


def cmd_flush(no_input: bool) -> int:
    """
    Delete ALL data from every model table (TRUNCATE ... RESTART IDENTITY CASCADE).
    The schema (tables, columns, indexes) is left intact — only rows are removed.
    Equivalent to Django's ``manage.py flush``.
    """
    from raftsql.utils.discovery import discover_models_by_app
    from raftsql.db.connection import Connection

    project_root, db = _load_project()
    config = _make_config(db)
    models_by_app = discover_models_by_app(project_root)
    all_models = [m for models in models_by_app.values() for m in models]

    if not all_models:
        print("No models found.")
        return 0

    from raftsql.orm.model import table_name as table_name_fn
    tables = sorted({table_name_fn(m) for m in all_models})

    print("This will DELETE ALL DATA from the following tables:")
    for t in tables:
        print(f"  {t}")

    if not no_input:
        try:
            answer = input("Are you sure? Type 'yes' to continue: ").strip()
        except KeyboardInterrupt:
            print("\nAborted.")
            return 1
        if answer != "yes":
            print("Flush cancelled.")
            return 1

    table_list = ", ".join(f'"{t}"' for t in tables)
    with Connection(config) as conn:
        # Only truncate tables that actually exist in the database
        rows = conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename = ANY(%s)",
            (list(tables),),
            as_dict=False,
        )
        existing = [row[0] for row in rows]
        if not existing:
            print("No tables exist in the database yet.")
            return 0
        existing_list = ", ".join(f'"{t}"' for t in existing)
        conn.execute(f"TRUNCATE TABLE {existing_list} RESTART IDENTITY CASCADE")

    skipped = set(tables) - set(existing)
    if skipped:
        print(f"Skipped (not in DB): {', '.join(sorted(skipped))}")

    print(f"Flushed {len(tables)} table(s).")
    return 0


def cmd_inspectdb(table_names=None) -> int:
    """Print Model class definitions inferred from the live database schema."""
    from raftsql.management.inspectdb import inspectdb
    _project_root, db = _load_project()
    config = _make_config(db)
    inspectdb(config, table_names=table_names)
    return 0


# ── argument parser ───────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="raftsql",
        description="RaftSQL — database migrations CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # generate (was: makemigrations)
    mk = sub.add_parser("generate", help="Generate migration files from model changes")
    mk.add_argument("--name", "-n", default="auto", help="Migration name suffix (default: auto)")
    mk.add_argument("--dry-run", action="store_true",
                    help="Show what would be generated without writing any file")
    mk.add_argument("--check", action="store_true",
                    help="Exit with non-zero code if model changes exist (CI mode)")
    mk.add_argument("--no-input", action="store_true",
                    help="Never prompt interactively; always use safe defaults")

    # apply (was: migrate)
    mg = sub.add_parser("apply", help="Apply pending migrations to the database")
    mg.add_argument("--fake", action="store_true",
                    help="Mark migrations as applied without running SQL")
    mg.add_argument("--fake-initial", action="store_true",
                    help="Mark first (num=1) migrations as applied if tables already exist")
    mg.add_argument("--plan", action="store_true",
                    help="Show what would be applied without executing anything")
    mg.add_argument("--database", "--db", metavar="ALIAS", default="default",
                    help="Database alias from DATABASES / setup (default: default)")
    mg.add_argument("--zero", metavar="APP_DIR",
                    help="Unapply (roll back) ALL migrations for APP_DIR")

    # status (was: showmigrations)
    sub.add_parser("status", help="List all migrations and their applied status")

    # sql (was: sqlmigrate)
    sm = sub.add_parser("sql", help="Print the SQL for a migration without running it")
    sm.add_argument("migration", help="Path to the migration file (relative to project root)")

    # squash (was: squashmigrations)
    sq = sub.add_parser("squash", help="Squash all migrations for an app into one file")
    sq.add_argument("app_dir", help="App directory path (relative to project root)")

    # flush
    fl = sub.add_parser("flush", help="Delete all data from all model tables (keeps schema)")
    fl.add_argument("--no-input", action="store_true",
                    help="Skip the confirmation prompt")

    # inspect (was: inspectdb)
    idb = sub.add_parser(
        "inspect",
        help="Introspect the database and print Model class definitions",
    )
    idb.add_argument(
        "tables", nargs="*", metavar="TABLE",
        help="Specific table names to inspect (default: all public tables)",
    )

    args = parser.parse_args()

    if args.command == "generate":
        return cmd_makemigrations(args.name, args.dry_run, args.check, args.no_input)

    if args.command == "apply":
        return cmd_migrate(
            args.fake,
            args.fake_initial,
            args.plan,
            args.zero,
            database=args.database,
        )

    if args.command == "status":
        return cmd_showmigrations()

    if args.command == "sql":
        return cmd_sqlmigrate(args.migration)

    if args.command == "squash":
        return cmd_squashmigrations(args.app_dir)

    if args.command == "inspect":
        return cmd_inspectdb(args.tables or None)

    if args.command == "flush":
        return cmd_flush(args.no_input)

    return 0


if __name__ == "__main__":
    sys.exit(main())

