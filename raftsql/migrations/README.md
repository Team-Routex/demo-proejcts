# Migrations

Generate and apply migrations from your Model classes (PostgreSQL supported).

## Quick start

1. **Define models** with `_fields` and optional `_field_types`:

   ```python
   from raftsql import Model

   class User(Model):
       _fields = ["id", "name", "email"]
       _pk = "id"
       _field_types = {"id": "SERIAL PRIMARY KEY", "name": "VARCHAR(255)", "email": "VARCHAR(255)"}
   ```

   If you omit `_field_types`, migrations use `SERIAL PRIMARY KEY` for the pk column and `TEXT` for others (PostgreSQL).

2. **Generate a migration** (from your project root, with models importable):

   ```bash
   python -m raftsql.cli makemigrations app.models
   ```
   or list models explicitly:
   ```bash
   python -m raftsql.cli makemigrations app.models:User,app.models:Post
   ```

   Creates e.g. `migrations/0001_auto.py` with `CreateTable` operations for any model whose table is not yet in an existing migration.

3. **Apply migrations**:

   ```bash
   python -m raftsql.cli migrate
   ```

   Uses `DB_*` env vars (or default config). Creates the `raftsql_migrations` tracking table if needed, then runs each pending migration file.

## Programmatic API

```python
from raftsql import Config, Connection
from raftsql.backends import get_backend
from raftsql.migrations import makemigrations, migrate
from your_app.models import User, Post

config = Config.from_env()
backend = get_backend(config.engine)

# Generate migration (only for tables not yet in any migration file)
path = makemigrations([User, Post], backend, "migrations", migration_name="initial")
if path:
    print("Created", path)

# Apply pending migrations
with Connection(config) as conn:
    applied = migrate(conn, "migrations")
    print("Applied:", applied)
```

## Options

- **makemigrations**: `--migrations-dir` (default `migrations`), `--name` (default `auto`).
- **migrate**: `--migrations-dir` (default `migrations`).

## Migration file format

Each file is a Python module with an `operations` list, e.g.:

```python
from raftsql.migrations.operations import CreateTable
operations = [
    CreateTable("user", [("id", "SERIAL PRIMARY KEY"), ("name", "VARCHAR(255)")]),
]
```

Files are named `0001_auto.py`, `0002_auto.py`, etc. Only `CreateTable` is supported in this version; alter/drop can be added later.
