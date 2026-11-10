# RaftSQL v2 — File and folder structure

Layout is **backend-based**: all database-specific code lives under `backends/<engine>/`. The rest is engine-agnostic.

---

## Top-level layout

```
raftsql/
├── __init__.py           # Public API: Config, Connection, AsyncConnection, Model, QuerySet, AsyncQuerySet, sql
├── config.py             # Config (engine, host, port, user, password, dbname); from_env()
├── connection.py         # Sync Connection: uses config.engine → get_backend() → backend.create_connection()
├── async_connection.py   # Async Connection: same, backend.create_async_connection()
├── model.py              # Model base, table/column mapping, from_row(), save(connection)
├── queryset.py           # QuerySet (sync), AsyncQuerySet (async); use connection.backend for SQL
├── sql/                  # SQL building (backend-agnostic; takes Backend for quoting)
│   ├── __init__.py
│   └── builder.py        # build_select(backend, ...), build_insert(backend, ...), build_update(backend, ...)
├── backends/             # One folder per database
│   ├── __init__.py       # get_backend(), register_backend(); imports postgresql to register it
│   ├── base.py           # Backend ABC: quote_ident(), supports_returning(), create_connection(), create_async_connection()
│   ├── registry.py       # get_backend(engine), register_backend(Backend)
│   ├── postgresql/       # Implemented
│   │   ├── __init__.py   # register_backend(PostgreSQLBackend)
│   │   ├── backend.py    # PostgreSQLBackend + create_connection / create_async_connection
│   │   ├── connection.py # Sync (psycopg2)
│   │   └── async_connection.py  # Async (asyncpg), converts %s → $1,$2
│   ├── mysql/            # Stub (future)
│   │   ├── __init__.py
│   │   └── README.md
│   ├── oracle/           # Stub (future)
│   │   ├── __init__.py
│   │   └── README.md
│   └── sqlite/           # Stub (future)
│       ├── __init__.py
│       └── README.md
├── pyproject.toml
├── STRUCTURE.md          # This file
└── v1.0.x/               # Versioned notes (what_done, what_to_do_next)
```

---

## How it stays maintainable

| Layer | Responsibility | Where |
|-------|-----------------|--------|
| **Config** | `engine` + connection params | `config.py` |
| **Backend** | Quoting, features (e.g. RETURNING), connection factories | `backends/<engine>/` |
| **SQL** | Build SELECT/INSERT/UPDATE using `backend.quote_ident()`; params use `%s` | `sql/builder.py` |
| **Connection** | Choose backend by `config.engine`, expose `.backend` and `.execute()` | `connection.py`, `async_connection.py` |
| **QuerySet / Model** | Call `build_*(connection.backend, ...)` then `connection.execute()` | `queryset.py`, `model.py` |

- **No DB-specific code** in `config.py`, `model.py`, `queryset.py`, or `sql/builder.py` except using the `Backend` interface.
- **All DB-specific code** (quoting, placeholders, driver, RETURNING) lives in `backends/<engine>/`.

---

## Adding a new backend (e.g. MySQL)

1. **`backends/mysql/backend.py`**  
   - Subclass `Backend`, set `name = "mysql"`.  
   - Implement `_quote_ident(name)` (e.g. backticks).  
   - Override `supports_returning()` if needed.  
   - Implement `create_connection(config)` and `create_async_connection(config)` returning objects with `.backend` and `.execute(sql, params, as_dict=)`.

2. **`backends/mysql/connection.py`**  
   - Sync connection (e.g. PyMySQL): connect with config, run SQL (convert `%s` to `%s` or `?` as the driver expects).

3. **`backends/mysql/async_connection.py`** (optional)  
   - Async driver (e.g. aiomysql); same `.execute` contract.

4. **Register** in `backends/mysql/__init__.py`:  
   `register_backend(MySQLBackend)`  
   and in `backends/__init__.py`:  
   `from . import mysql  # noqa: F401`

5. **Config**: set `engine="mysql"` (or `DB_ENGINE=mysql` in env).  
   Optionally extend `Config` with MySQL-specific fields (e.g. charset) and have the MySQL backend read them.

---

## Placeholder convention

- **Builder** always emits `%s` in SQL. Params are a list.
- **Sync connections** use the list as-is (psycopg2 and many MySQL drivers use `%s`).
- **Async PostgreSQL** converts `%s` → `$1`, `$2` inside the connection before calling asyncpg.
- Other backends (Oracle `:1`, SQLite `?`) can convert inside their own connection’s `execute()`.

This keeps `sql/builder.py` backend-agnostic while each backend handles its driver’s placeholder style.
