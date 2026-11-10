# RaftSQL

[![Version](https://img.shields.io/badge/version-1.1.0-blue)](https://pypi.org/project/raftsql/)
[![Python versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://pypi.org/project/raftsql/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](https://opensource.org/licenses/MIT)
[![PostgreSQL](https://img.shields.io/badge/database-PostgreSQL-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Async support](https://img.shields.io/badge/async-asyncpg-9cf)](https://github.com/MagicStack/asyncpg)
[![Sync support](https://img.shields.io/badge/sync-psycopg2-9cf)](https://github.com/psycopg/psycopg2)

A Python ORM built from the ground up. No dependencies on any web framework, no code generation, no black-box magic. Write expressive queries with a clean, chainable API. Switch between sync and async execution without changing a single line of query code. Full migration system, multi-table inheritance, generic relations, schema introspection, file/image field support, DRF-style serializers, connection pooling, atomic transactions, Django-style signals, and constraint management. All in one focused library. Currently supports **PostgreSQL**.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
  - [setraft.py](#setraftpy)
  - [Environment Variables](#environment-variables)
- [Multi-database support](#multi-database-support)
- [Defining Models](#defining-models)
  - [Field Types](#field-types)
  - [File Fields and Storage](#file-fields-and-storage)
  - [Relation Fields](#relation-fields)
  - [Meta Options](#meta-options)
  - [CheckConstraint and UniqueConstraint](#checkconstraint-and-uniqueconstraint)
- [Multi-table Inheritance](#multi-table-inheritance)
- [GenericForeignKey](#genericforeignkey)
- [Migrations](#migrations)
  - [generate (makemigrations)](#generate-makemigrations)
  - [apply (migrate)](#apply-migrate)
  - [Per-App Migrations](#per-app-migrations)
- [Schema Introspection — inspect](#schema-introspection--inspect)
- [Querying](#querying)
  - [Basic Retrieval](#basic-retrieval)
  - [Filtering](#filtering)
  - [Lookup Expressions](#lookup-expressions)
  - [Q Objects — Complex Conditions](#q-objects--complex-conditions)
  - [F Objects — Column References](#f-objects--column-references)
  - [exclude()](#exclude)
  - [Ordering](#ordering)
  - [Slicing — limit() and offset()](#slicing--limit-and-offset)
  - [distinct()](#distinct)
  - [values() and values\_list()](#values-and-values_list)
  - [exists()](#exists)
  - [count()](#count)
- [Writing Data](#writing-data)
  - [create()](#create)
  - [update()](#update)
  - [delete()](#delete)
  - [Raw SQL](#raw-sql)
- [Aggregation and Annotation](#aggregation-and-annotation)
  - [aggregate()](#aggregate)
  - [annotate()](#annotate)
  - [Available Aggregates](#available-aggregates)
- [Advanced Expressions](#advanced-expressions)
  - [Window Functions](#window-functions)
  - [COALESCE](#coalesce)
  - [Subquery and OuterRef](#subquery-and-outerref)
  - [Case / When](#case--when)
  - [Cast](#cast)
- [Relations](#relations)
  - [ForeignKey — select\_related()](#foreignkey--select_related)
  - [Reverse FK Accessors](#reverse-fk-accessors)
  - [ManyToMany — prefetch\_related()](#manytomany--prefetch_related)
  - [ManyToMany with through= Model](#manytomany-with-through-model)
- [Serializers](#serializers)
  - [Serializer](#serializer)
  - [ModelSerializer](#modelserializer)
- [Transactions](#transactions)
- [Connection Pooling](#connection-pooling)
- [Signals](#signals)
- [Async API](#async-api)
  - [Method Reference](#method-reference)
  - [FastAPI Example](#fastapi-example)
- [Project Structure](#project-structure)
- [Exceptions](#exceptions)
- [CLI Reference](#cli-reference)
- [Changelog](#changelog)

---

## Features

| Category | What's included |
|---|---|
| **Sync & Async** | All QuerySet methods have both sync and `a`-prefixed async variants |
| **Filtering** | 20+ lookup expressions including `__istartswith`, `__iendswith`, `__regex`, `__iregex`, `__ne`, and more |
| **Q Objects** | OR / AND / NOT composition of arbitrary filter conditions |
| **F Objects** | Column-to-column comparisons and updates without a Python roundtrip |
| **Aggregates** | `Count`, `Sum`, `Avg`, `Max`, `Min` — in both `.aggregate()` and `.annotate()` |
| **Window Functions** | `ROW_NUMBER`, `RANK`, `DENSE_RANK`, `LAG`, `LEAD`, `FIRST_VALUE`, `LAST_VALUE`, `NTILE`, and more with `PARTITION BY` / `ORDER BY` / frame support |
| **COALESCE** | `Coalesce("col", Value("default"))` for NULL handling |
| **Subqueries** | `Subquery()` + `OuterRef()` for correlated and IN-subqueries |
| **Case / When** | `Case(When(..., then=...), default=...)` conditional expressions in annotations |
| **Cast** | `Cast("col", "INTEGER")` explicit type casting in expressions |
| **Relations** | `ForeignKey`, `OneToOneField`, `ManyToManyField`, `select_related()`, `prefetch_related()` |
| **Reverse FK Accessors** | `related_name` on FK/O2O auto-creates reverse accessors on related models |
| **through= Models** | Explicit junction models for M2M with extra columns |
| **on\_delete ORM enforcement** | `PROTECT` / `RESTRICT` raise `ProtectedError` before hitting the DB |
| **Constraints** | `CheckConstraint` and `UniqueConstraint` (including partial) in `Meta.constraints` |
| **Multi-table Inheritance** | Child models extend parent via a pointer FK; parent columns accessible via JOIN |
| **GenericForeignKey** | Polymorphic FK to any model using a content-type string + integer pk |
| **File Fields** | `FileField` and `ImageField` — store file paths in DB, files on disk (or custom storage) |
| **Storage Backends** | `FileSystemStorage` out of the box; `Storage` ABC for custom backends |
| **Serializers** | `Serializer` and `ModelSerializer` — DRF-style input/output, sync + async, file upload aware |
| **Transactions** | `atomic()` (async) and `atomic_sync()` — nested savepoints, `set_rollback()` |
| **Connection Pooling** | asyncpg pool + psycopg2 ThreadedConnectionPool — `setup_async_pool()` / `setup_sync_pool()` (per-database `using=` alias) |
| **Multi-database** | `DATABASES` aliases, **`class Meta`** routing (`db_alias`, `db_for_*`, `for_read`/`for_write`, `allow_*`), `.using()`, optional routers/Guides, `atomic(using=)`, per-alias pools, `apply --db` |
| **Signals** | `pre_save`, `post_save`, `pre_delete`, `post_delete` — sync and async receivers |
| **inspectdb** | Reverse-engineer an existing database into ready-to-use Model definitions |
| **Migrations** | Auto-generated, per-app SQL migration files with a tracking table |
| **Auto-discovery** | Models and apps discovered automatically — no manual registration |
| **Zero config** | One `setraft.py` file is all you need |

---

## Installation

```bash
pip install raftsql
```

**Requirements:** Python ≥ 3.10, PostgreSQL

**Dependencies installed automatically:**

| Package | Purpose |
|---|---|
| `psycopg2` | Sync PostgreSQL driver |
| `asyncpg` | Async PostgreSQL driver |

---

## Quick Start

```bash
# 1. Create project structure
mkdir myproject && cd myproject
mkdir -p apps/posts
touch setraft.py .env apps/__init__.py apps/posts/__init__.py apps/posts/models.py app.py
```

**setraft.py**

```python
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATABASE = {
    "ENGINE":   "postgresql",
    "HOST":     os.getenv("DB_HOST", "localhost"),
    "PORT":     int(os.getenv("DB_PORT", 5432)),
    "USER":     os.getenv("DB_USER", "postgres"),
    "PASSWORD": os.getenv("DB_PASSWORD", ""),
    "NAME":     os.getenv("DB_NAME", "mydb"),
}
```

**apps/posts/models.py**

```python
from raftsql import models

class Post(models.Model):
    id      = models.AutoField(primary_key=True)
    title   = models.CharField(max_length=255)
    body    = models.TextField(null=True, blank=True)
    views   = models.IntegerField(default=0)
    published = models.BooleanField(default=False)

    class Meta:
        db_table = "posts"
```

**Run migrations:**

```bash
raftsql generate   # → apps/posts/migrations/0001_create_posts.py
raftsql apply      # → creates the table in your DB
```

**Use it:**

```python
import raftsql
raftsql.setup()

from apps.posts.models import Post

# Create
post = Post.objects.create(title="Hello RaftSQL", body="First post")

# Read
posts = Post.objects.filter(published=True).order_by("-views").limit(10).all()

# Update
Post.objects.filter(pk=post.id).update(views=100)

# Delete
Post.objects.filter(pk=post.id).delete()
```

---

## Configuration

### setraft.py

RaftSQL automatically discovers `setraft.py` by searching from the current working directory upward, then downward, so it works regardless of where you launch the process from.

```python
# setraft.py — place at your project root
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATABASE = {
    "ENGINE":   "postgresql",           # only supported engine currently
    "HOST":     os.getenv("DB_HOST", "localhost"),
    "PORT":     int(os.getenv("DB_PORT", 5432)),
    "USER":     os.getenv("DB_USER", "postgres"),
    "PASSWORD": os.getenv("DB_PASSWORD", ""),
    "NAME":     os.getenv("DB_NAME", "mydb"),
}

# ── File / Image field storage (optional) ─────────────────────────────────────

# Absolute path where uploaded files are stored (default: "media" relative to cwd)
MEDIA_ROOT = BASE_DIR / "media"

# URL prefix for serving media files (default: "/media/")
MEDIA_URL = "/media/"

# ── Optional ───────────────────────────────────────────────────────────────

# Explicit app list — omit this and RaftSQL auto-detects apps via models.py
# APPS = [
#     "apps.posts",
#     "apps.users",
# ]
```

**Initialise once at startup:**

```python
import raftsql
raftsql.setup()   # idempotent — safe to call multiple times (e.g. uvicorn --reload)
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | _(empty)_ | Database password |
| `DB_NAME` | _(empty)_ | Database name |

---

## Multi-database support

RaftSQL loads **multiple PostgreSQL configurations** under string **aliases**. **Primary routing is declared on each model via `class Meta`** (`db_alias`, `db_for_read` / `db_for_write`, `for_read` / `for_write`, `allow_relation`, `allow_migrate`, `allow_migrate_on_databases`). Use **`.using("alias")`** on a queryset when you want a one-off connection.

Models with **no** routing fields on `Meta` start from the **`"default"`** alias (same idea as Django). Optional **`DATABASE_ROUTERS`** and **`Guides`** apply only if `Meta` did not pick an alias for that operation — see [Optional — routers and Guides](#optional--routers-and-guides).

### Declaring databases in `setraft.py`

**`DATABASES` (recommended):**

```python
DATABASES = {
    "default": {
        "ENGINE":   "postgresql",
        "HOST":     os.getenv("DB_HOST", "localhost"),
        "PORT":     int(os.getenv("DB_PORT", 5432)),
        "USER":     os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "NAME":     os.getenv("DB_NAME", "mydb"),
    },
    "analytics": {
        "ENGINE":   "postgresql",
        "HOST":     os.getenv("ANALYTICS_DB_HOST", "localhost"),
        "PORT":     int(os.getenv("ANALYTICS_DB_PORT", 5432)),
        "USER":     os.getenv("ANALYTICS_DB_USER", "postgres"),
        "PASSWORD": os.getenv("ANALYTICS_DB_PASSWORD", ""),
        "NAME":     os.getenv("ANALYTICS_DB_NAME", "analytics"),
    },
    "replica": {
        "ENGINE":   "postgresql",
        "HOST":     os.getenv("REPLICA_DB_HOST", "localhost"),
        "PORT":     int(os.getenv("REPLICA_DB_PORT", 5432)),
        "USER":     os.getenv("REPLICA_DB_USER", "postgres"),
        "PASSWORD": os.getenv("REPLICA_DB_PASSWORD", ""),
        "NAME":     os.getenv("REPLICA_DB_NAME", "mydb"),
    },
}
```

Required keys per alias: `ENGINE`, `HOST`, `PORT`, `USER`, `PASSWORD`, `NAME`.

**Legacy `DATABASE`:** mapped to **`DATABASES["default"]`**.

After **`raftsql.setup()`**, **`raftsql.get_db("analytics")`** returns **`Config`** for that alias (includes **`alias`**).

### Routing on each model — `class Meta`

Alias names **must** exist in **`DATABASES`**. When **`Meta` supplies an alias for an operation**, routers and Guides are **not** consulted for that half.

**Same DB for reads and writes**

```python
class SalesOrder(models.Model):
    id = models.AutoField(primary_key=True)

    class Meta:
        db_table = "sales_orders"
        db_alias = "analytics"
```

**Different DBs for reads vs writes** — explicit strings:

```python
class Metric(models.Model):
    id = models.AutoField(primary_key=True)

    class Meta:
        db_table = "metrics"
        db_for_read = "replica"
        db_for_write = "default"
```

Or one **`db_alias`** with **boolean gates** (default **`True`** when **`db_alias`** is set):

```python
class Event(models.Model):
    id = models.AutoField(primary_key=True)

    class Meta:
        db_table = "events"
        db_alias = "analytics"
        for_read = False      # reads → default / optional hooks; writes still use analytics if for_write True
        for_write = True
```

**`db_for_read` / `db_for_write` strings override** **`db_alias`** **+** **`for_*`** for that half.

**Relations and migrations**

```python
class Profile(models.Model):
    id = models.AutoField(primary_key=True)

    class Meta:
        db_table = "profiles"
        db_alias = "users_db"
        allow_relation = None                               # None | False | True — see [Meta Options](#meta-options)
        allow_migrate = True
        allow_migrate_on_databases = ("default",)            # optional whitelist per model
```

Full semantics → **[Meta Options](#meta-options)**.

### Pinning a queryset — `.using()`

```python
Report.objects.using("analytics").filter(year=2025).all()
await Report.objects.using("analytics").filter(year=2025).alist()
```

**`.using("alias")`** bypasses **`Meta`**, routers, and Guides for that queryset (`Model.objects.using` is the same).

### Resolution order (no `.using()`)

1. **`class Meta`** — routing fields above.
2. Optional **`DATABASE_ROUTERS`** / **`GUIDES`** — only if **`Meta`** did **not** decide that read/write half.
3. Starter alias (**`"default"`**).

**`save()` / `asave()`** use **write** resolution; lazy FK loads use **read** resolution on the **related** model.

### Optional — routers and Guides

Centralised **`DATABASE_ROUTERS`** (Django-style classes in **`setraft.py`**) or **`Guide`** / **`GUIDES`** / **`add_guide()`** are supported when you want policies in one module. They run **only for a read/write half where `Meta` did not pick an alias**. Details → **`routing.py`** docstrings.

### Enforcement summary

| Topic | Configuration |
|-------|----------------|
| Hosts / DB names | **`DATABASES`** / **`DATABASE`** |
| Per-model read & write DB | **`Meta`** (`db_alias`, `db_for_*`, `for_read`, `for_write`) |
| Cross-DB FK on save | **`Meta.allow_relation`** (+ optional routers) |
| **`raftsql apply --db`** vs app | **`Meta.allow_migrate`**, **`allow_migrate_on_databases`**, routers |
| Migration **`app_label`** | **`Meta.app_label`** or **`__module__`**; generated migrations include **`app_label = "..."`**. |

### Transactions per alias

Both accept a **`using`** keyword argument to select the alias (defaults to **`"default"`**):

```python
from raftsql import atomic, atomic_sync

async with atomic(using="analytics"):
    await Event.objects.using("analytics").acreate(name="page_view")

with atomic_sync(using="analytics"):
    Event.objects.using("analytics").create(name="page_view")
```

Scoped connections are tracked **per alias** (async and sync ContextVar maps nest independently). Queries inside the block should target the **same alias** as the transaction for correct behaviour.

See also [Transactions](#transactions).

### Connection pools per alias

```python
await raftsql.setup_async_pool(using="default",   min_size=2, max_size=10)
await raftsql.setup_async_pool(using="analytics", min_size=1, max_size=5)

raftsql.setup_sync_pool(using="default", min_conn=2, max_conn=10)
```

Teardown: **`teardown_async_pool(using="...")`**, **`teardown_all_async_pools()`**, **`teardown_sync_pool`**, **`teardown_all_sync_pools()`**.

`pool_stats()` returns **one entry per alias** that has been initialised, each with `"async"` and/or `"sync"` sub-dicts (`None` where that pool type was not started). See [Connection pooling](#connection-pooling).

### CLI — apply migrations to a chosen database

```bash
raftsql apply --database analytics
raftsql apply --db analytics       # synonym
```

Runs pending migrations against **`DATABASES["analytics"]`**, respecting **`Meta.allow_migrate`**, **`Meta.allow_migrate_on_databases`**, and optional routers.

Other CLI commands (`status`, `generate`, etc.) are unchanged in this README; when in doubt, use **`raftsql --help`** / **`raftsql apply --help`** for flags.

### Public API recap

| Item | Role |
|------|------|
| `DATABASES` / `DATABASE` | Declare aliases (`get_all_db_configs`) |
| `raftsql.setup()` | Load configs; register optional `DATABASE_ROUTERS` + `GUIDES` from **`setraft.py`** |
| `get_db(alias)` | **`Config`** for an alias |
| **`Meta`**: `db_alias`, `db_for_*`, `for_read`, `for_write`, `allow_relation`, `allow_migrate`, `allow_migrate_on_databases` | **Primary** per-model routing and migration/relation rules |
| `QuerySet.using` / `Manager.using` | Overrides **`Meta`** and all hooks |
| `resolve_default_database_alias(...)` | Effective alias resolver (reads **`Meta`** first) |
| `DATABASE_ROUTERS`, `Guide`, `GUIDES`, `add_guide`, `BaseDatabaseRouter` | Optional; used only where **`Meta`** defers that half |
| `allow_relation_allowed`, `allow_migrate_allowed` | Aggregate routers + **`Meta`** |
| `atomic(using=)`, `atomic_sync(using=)` | Transactions per alias |
| `setup_async_pool(using=)`, `setup_sync_pool(using=)`, teardown helpers | Pools per alias |

---

## Defining Models

```python
from raftsql import models
from raftsql.orm import CheckConstraint, UniqueConstraint, Q

class Article(models.Model):
    id         = models.AutoField(primary_key=True)
    title      = models.CharField(max_length=200)
    slug       = models.SlugField(max_length=200, unique=True)
    body       = models.TextField(null=True, blank=True)
    views      = models.IntegerField(default=0)
    rating     = models.DecimalField(max_digits=3, decimal_places=1, null=True)
    published  = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata   = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "articles"
        constraints = [
            CheckConstraint(check=Q(rating__gte=0) & Q(rating__lte=5), name="rating_valid"),
            UniqueConstraint(fields=["slug", "published"], name="slug_pub_unique"),
        ]
```

### Field Types

Every field accepts the following common keyword arguments:

| Argument | Type | Default | Description |
|---|---|---|---|
| `null` | `bool` | `False` | Allows `NULL` in the database column |
| `blank` | `bool` | `True` | Allows empty values at the application level |
| `unique` | `bool` | `False` | Adds a `UNIQUE` constraint |
| `default` | `Any` | `None` | Default value for the column |
| `db_column` | `str` | `None` | Override the column name in the database |
| `primary_key` | `bool` | `False` | Mark this column as the primary key |
| `db_index` | `bool` | `False` | Create a non-unique database index on this column |

---

| Field | SQL type | Extra arguments |
|---|---|---|
| `AutoField` | `SERIAL PRIMARY KEY` | — |
| `IntegerField` | `INTEGER` | — |
| `BigIntegerField` | `BIGINT` | — |
| `SmallIntegerField` | `SMALLINT` | — |
| `PositiveIntegerField` | `INTEGER CHECK (col >= 0)` | — |
| `FloatField` | `FLOAT` | — |
| `DecimalField` | `NUMERIC(p, s)` | `max_digits`, `decimal_places` |
| `CharField` | `VARCHAR(n)` | `max_length` (default `255`) |
| `SlugField` | `VARCHAR(n)` | `max_length` (default `50`), `db_index=True` by default |
| `TextField` | `TEXT` | — |
| `EmailField` | `VARCHAR(n)` | `max_length` (default `255`) |
| `BooleanField` | `BOOLEAN` | — |
| `DateField` | `DATE` | — |
| `DateTimeField` | `TIMESTAMP` | `auto_now_add`, `auto_now` |
| `TimeField` | `TIME` | — |
| `JSONField` | `JSONB` | — |
| `UUIDField` | `UUID` | — |
| `BinaryField` | `BYTEA` | — |
| `ArrayField` | `{base_type}[]` | `base_field`, `dimensions` |
| `FileField` | `VARCHAR(n)` | `upload_to`, `max_length`, `storage` |
| `ImageField` | `VARCHAR(n)` | `upload_to`, `max_length`, `storage` (validates image with Pillow) |

#### DateTimeField — auto timestamps

```python
created_at = models.DateTimeField(auto_now_add=True)   # set on INSERT
updated_at = models.DateTimeField(auto_now=True)        # updated on every save
```

`auto_now_add=True` adds `DEFAULT CURRENT_TIMESTAMP` to the column DDL — the database fills it automatically on every insert.  
`auto_now=True` signals the application layer to update the value on save (no DDL default).

#### UUIDField

```python
import models
from raftsql.orm import UUIDField

class Token(models.Model):
    id    = UUIDField(primary_key=True, default="gen_random_uuid()")
    value = models.CharField(max_length=64)

    class Meta:
        db_table = "tokens"
```

SQL function strings like `gen_random_uuid()` and `uuid_generate_v4()` are emitted verbatim as `DEFAULT gen_random_uuid()` in the DDL.

---

### File Fields and Storage

`FileField` and `ImageField` store a file path string in the database and delegate the actual file to a **storage backend** (default: `FileSystemStorage`, which writes to `MEDIA_ROOT`).

#### FileField

```python
from raftsql import models

class Document(models.Model):
    id    = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    file  = models.FileField(upload_to="documents/", null=True, blank=True)

    class Meta:
        db_table = "documents"
```

#### ImageField

`ImageField` is identical to `FileField` but validates the uploaded content is a valid image using **Pillow** (if installed). If Pillow is not available, it falls back to `FileField` behaviour.

```python
class Post(models.Model):
    id        = models.AutoField(primary_key=True)
    title     = models.CharField(max_length=200)
    thumbnail = models.ImageField(upload_to="thumbnails/", null=True, blank=True)

    class Meta:
        db_table = "posts"
```

#### upload_to — subdirectory or callable

```python
def user_upload_path(instance, filename):
    return f"users/{instance.id}/{filename}"

class Profile(models.Model):
    avatar = models.ImageField(upload_to=user_upload_path, null=True)

    class Meta:
        db_table = "profiles"
```

#### Accessing files — FieldFile

Accessing a `FileField` attribute on a model instance returns a `FieldFile` proxy:

```python
post = Post.objects.get(pk=1)
ff = post.thumbnail       # → FieldFile instance

print(ff.name)            # relative path stored in DB, e.g. "thumbnails/photo.jpg"
print(ff.url)             # full URL, e.g. "/media/thumbnails/photo.jpg"
print(bool(ff))           # False if no file is saved

# Save a new file
ff.save("new_photo.jpg", open("photo.jpg", "rb"))

# Delete the file from storage
ff.delete()
```

#### Assigning upload objects directly

Direct assignment of any upload object is supported — the file is saved to storage immediately and only the path string is stored in the DB column:

```python
# FastAPI UploadFile
post.thumbnail = upload_file    # saves to MEDIA_ROOT/thumbnails/<filename>
post.save()                     # writes the path string to the DB

# Flask FileStorage, Django InMemoryUploadedFile, BytesIO, bytes — all work
```

#### Custom storage backend

```python
from raftsql.storage import Storage

class S3Storage(Storage):
    def save(self, name, content):
        # upload to S3, return the key
        ...
    def url(self, name):
        return f"https://mybucket.s3.amazonaws.com/{name}"
    def delete(self, name): ...
    def exists(self, name): ...
    def open(self, name, mode="rb"): ...

class Post(models.Model):
    thumbnail = models.ImageField(
        upload_to="thumbnails/",
        storage=S3Storage(),
    )

    class Meta:
        db_table = "posts"
```

#### MEDIA_ROOT and MEDIA_URL

Set in `setraft.py` (used by the default `FileSystemStorage`):

```python
# setraft.py
MEDIA_ROOT = BASE_DIR / "media"   # physical path where files are written
MEDIA_URL  = "/media/"            # URL prefix for serving files
```

Serve media files in FastAPI:

```python
from fastapi.staticfiles import StaticFiles

app.mount("/media", StaticFiles(directory="media"), name="media")
```

### Relation Fields

#### ForeignKey

```python
class Comment(models.Model):
    id      = models.AutoField(primary_key=True)
    body    = models.TextField()
    post    = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="comments",   # optional reverse accessor hint
    )

    class Meta:
        db_table = "comments"
```

Creates a `post_id INTEGER` column on this model's table.

| `on_delete` value | DB level | ORM level |
|---|---|---|
| `CASCADE` | Delete child rows when parent is deleted | — |
| `SET_NULL` | Set FK column to NULL (requires `null=True`) | — |
| `PROTECT` | DB constraint raises error | `ProtectedError` raised **before** the DELETE reaches the DB |
| `RESTRICT` | DB constraint raises error | `ProtectedError` raised **before** the DELETE reaches the DB |
| `DO_NOTHING` | No referential action | — |

Both `PROTECT` and `RESTRICT` are enforced at the ORM level by scanning the model registry for any model with a FK pointing to the instance being deleted, and raising a `ProtectedError` immediately, before any SQL is sent.

```python
from raftsql.orm import ProtectedError

try:
    author.delete()   # raises if any Article references this author with on_delete=PROTECT
except ProtectedError as e:
    print(e)  # "Cannot delete Author pk=1: 3 Article row(s) reference it via author (on_delete=PROTECT)"
```

Async:

```python
try:
    await author.adelete()
except ProtectedError as e:
    ...
```

#### OneToOneField

```python
class Profile(models.Model):
    id   = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio  = models.TextField(null=True)

    class Meta:
        db_table = "profiles"
```

Identical to `ForeignKey` but always adds a `UNIQUE` constraint on the column.

#### ManyToManyField

```python
class Post(models.Model):
    id   = models.AutoField(primary_key=True)
    tags = models.ManyToManyField("Tag", related_name="posts")

    class Meta:
        db_table = "posts"
```

No column is added to this model's table. Instead, a junction table `posts_tags` (sorted alphabetically) is created automatically with `posts_id` and `tags_id` columns.

```python
# Override the junction table name (string)
tags = models.ManyToManyField("Tag", through="post_tag_assignments")
```

### Meta Options

```python
class Meta:
    db_table    = "my_table_name"   # required — the physical table name in the DB
    constraints = [...]             # optional — list of CheckConstraint / UniqueConstraint
    app_label   = "billing"         # optional — namespace for migrations / allow_migrate; else derived from __module__

    # Multi-database (keys must exist in setraft DATABASES / DATABASE):
    db_alias    = "analytics"       # optional — shared alias; use for_read / for_write to turn each half on/off
    for_read    = True              # optional — with db_alias: use it for SELECT (default True)
    for_write   = True              # optional — with db_alias: use it for writes (default True)
    db_for_read  = "replica"        # optional — explicit read alias (wins over db_alias + for_read)
    db_for_write = "default"        # optional — explicit write alias

    # Same semantics as DATABASE_ROUTERS hooks, declared on the model:
    allow_relation = None           # None | False | True — see Multi-database docs
    allow_migrate  = None           # False → block migrations for this app_label (any model with False blocks the app)
    allow_migrate_on_databases = ("default",)  # optional — if set, app_label migrations only on these aliases
```

**Default database:** If a model defines **no** `db_alias` / `db_for_read` / `db_for_write`, it behaves like Django: resolution starts from the **`"default"`** alias, then `DATABASE_ROUTERS` and `GUIDES` may redirect. With `DATABASES` configured, ensure a `"default"` entry exists unless you always route elsewhere.

**`db_alias` + `for_read` / `for_write`:** With `db_alias="analytics"` and `for_read=False`, reads fall through to routers / Guides / `"default"`; writes still use `analytics` if `for_write` is true (default). String `db_for_read` / `db_for_write` always win for their half.

When **Meta** picks an alias for an operation, **`DATABASE_ROUTERS`** and **`GUIDES`** are **skipped** for that half. **`.using("alias")`** still overrides everything.

**`allow_migrate` / `allow_migrate_on_databases`:** Checked after routers. Every registered model with this `app_label` is consulted. **`allow_migrate=False`** on **any** of them blocks migrations for that **`app_label`** everywhere. **`allow_migrate_on_databases=(...)`** adds a whitelist per model that sets it: the migration **must not** run on **`db`** if **`db`** is absent from **that** model's tuple — if **multiple** models in the app set tuples, **`db`** must satisfy **every** whitelist (logical AND across those models).

`app_label` (and `Model._meta.label` = `"{app_label}.{model_name}"`) is what migration files and `allow_migrate` routing use. See [Multi-database support](#multi-database-support).

### CheckConstraint and UniqueConstraint

Declare table-level constraints in `Meta.constraints`. They are picked up by `makemigrations` and rendered into the `CREATE TABLE` DDL as well as tracked as `AddConstraint` / `DropConstraint` migration operations when they change.

```python
from raftsql.orm import CheckConstraint, UniqueConstraint, Q

class Product(models.Model):
    id       = models.AutoField(primary_key=True)
    name     = models.CharField(max_length=200)
    price    = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=100)
    stock    = models.IntegerField(default=0)

    class Meta:
        db_table = "products"
        constraints = [
            # CHECK using a Q object — same syntax as filter()
            CheckConstraint(check=Q(price__gt=0), name="price_positive"),

            # CHECK using a raw SQL string
            CheckConstraint(check="stock >= 0", name="stock_non_negative"),

            # Multi-column UNIQUE
            UniqueConstraint(fields=["name", "category"], name="name_category_unique"),

            # Partial UNIQUE (only enforced where the condition matches)
            UniqueConstraint(
                fields=["name"],
                name="name_unique_active",
                condition=Q(stock__gt=0),
            ),
        ]
```

Generated DDL:

```sql
CONSTRAINT "price_positive"         CHECK ("price" > 0),
CONSTRAINT "stock_non_negative"     CHECK (stock >= 0),
CONSTRAINT "name_category_unique"   UNIQUE ("name", "category"),
CONSTRAINT "name_unique_active"     UNIQUE ("name") WHERE ("stock" > 0)
```

You can also call `.as_sql()` directly to inspect the generated SQL without running migrations:

```python
c = CheckConstraint(check=Q(price__gt=0), name="price_positive")
print(c.as_sql())
# CONSTRAINT "price_positive" CHECK ("price" > 0)

u = UniqueConstraint(fields=["name", "category"], name="name_cat")
print(u.as_sql())
# CONSTRAINT "name_cat" UNIQUE ("name", "category")
```

---

## Multi-table Inheritance

Multi-table inheritance (MTI) lets a child model extend a parent model. The parent and child each live in their own database table; the child table carries a pointer FK to the parent row. When you query the child model, RaftSQL automatically performs an `INNER JOIN` so parent-table columns are accessible as normal attributes.

### Defining an MTI hierarchy

```python
from raftsql import models

class Person(models.Model):
    id    = models.AutoField(primary_key=True)
    name  = models.CharField(max_length=100)
    email = models.CharField(max_length=200)

    class Meta:
        db_table = "persons"


class Employee(Person):          # inherits from Person — MTI kicks in automatically
    department = models.CharField(max_length=100)
    salary     = models.DecimalField(max_digits=12, decimal_places=2, null=True)

    class Meta:
        db_table = "employees"
```

RaftSQL detects the inheritance and:

- Adds a `persons_ptr_id` column to `employees` — a `NOT NULL` FK to `persons(id)` with `ON DELETE CASCADE`.
- Sets `Employee._pk = "persons_ptr_id"`.
- Stores `Employee._parent_model = Person` and `Employee._parent_fields = ["id", "name", "email"]`.

The required DDL for the two tables:

```sql
CREATE TABLE persons (
    id    SERIAL PRIMARY KEY,
    name  VARCHAR(100) NOT NULL,
    email VARCHAR(200) NOT NULL
);

CREATE TABLE employees (
    persons_ptr_id INTEGER NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    department     VARCHAR(100) NOT NULL,
    salary         NUMERIC(12,2)
);
```

### Saving MTI instances (sync and async)

`save()` / `asave()` transparently writes to both tables:

```python
# Sync
emp = Employee(name="Alice", email="alice@corp.com", department="Engineering", salary=90000)
emp.save()
# → INSERT INTO persons (name, email) → gets pk=1
# → INSERT INTO employees (persons_ptr_id, department, salary) VALUES (1, 'Engineering', 90000)

# Async
emp = Employee(name="Bob", email="bob@corp.com", department="HR", salary=70000)
await emp.asave()
```

### Querying MTI models

Filtering, ordering, and all QuerySet operations work normally. The `INNER JOIN` against the parent table is injected automatically so parent columns are always available:

```python
# Sync
employees = Employee.objects.filter(department="Engineering").all()
for e in employees:
    print(e.name, e.email, e.department, e.salary)
    # name / email come from the parent table via JOIN

# Async
employees = await Employee.objects.filter(salary__gte=80000).order_by("name").alist()

# get by ptr_id
emp = Employee.objects.get(**{Employee._ptr_col: 1})

# First / exists
senior = await Employee.objects.filter(salary__gte=100000).afirst()
has_hr = await Employee.objects.filter(department="HR").aexists()
```

### Deleting MTI instances

Deleting a child instance targets the parent table; the database `ON DELETE CASCADE` removes the child row automatically:

```python
emp.delete()    # DELETE FROM persons WHERE id = <ptr_id>  → cascades to employees row
await emp.adelete()
```

### MTI class attributes

| Attribute | Example value | Description |
|---|---|---|
| `Employee._ptr_col` | `"persons_ptr_id"` | Name of the FK/pointer column on the child table |
| `Employee._parent_model` | `Person` | Parent model class |
| `Employee._parent_fields` | `["id", "name", "email"]` | Columns inherited from the parent |

---

## GenericForeignKey

`GenericForeignKey` implements a polymorphic relation — a single model can point to a row in **any** other model without a fixed FK column. The target is identified by:

- A `content_type` column (stored as `"module.ClassName"`)
- An `object_id` column (the primary key of the target row)

No extra database table is required.

### Defining a model with a GenericForeignKey

```python
from raftsql import models
from raftsql.orm import GenericForeignKey

class Comment(models.Model):
    id             = models.AutoField(primary_key=True)
    content_type   = models.CharField(max_length=200)   # stores "myapp.models.Post"
    object_id      = models.IntegerField()
    body           = models.TextField()
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        db_table = "comments"
```

`GenericForeignKey("content_type", "object_id")` is a pure Python descriptor — it adds no column to the table and generates no DDL.

### Writing through the GFK

```python
post = Post.objects.get(pk=42)

comment = Comment(body="Great post!")
comment.content_object = post   # sets content_type + object_id automatically
comment.save()

# content_type stored as: "myapp.models.Post"
# object_id stored as:    42
```

```python
# Async
await comment.asave()
```

### Reading through the GFK

```python
saved = Comment.objects.get(pk=comment.id)
target = saved.content_object   # lazily fetches the Post (sync)
print(type(target).__name__)    # "Post"
print(target.id)                # 42
```

The resolved object is cached on the instance — repeated reads do not re-query.

### Async GFK resolution

GFK resolution uses the sync `objects.get()` internally. In async contexts, resolve the target manually using `.aget()`:

```python
saved = await Comment.objects.aget(pk=comment.id)
target = await Post.objects.aget(pk=saved.object_id)
```

### Clearing a GFK

```python
comment.content_object = None   # sets content_type=None, object_id=None, clears cache
comment.save()
```

### How model resolution works

`GenericForeignKey` resolves labels using the global `_MODEL_REGISTRY` that every `Model` subclass is automatically registered in at class-creation time. It matches by full label (`"module.ClassName"`) first, then by class name only:

```python
# Both of these resolve to the same class:
# "myapp.models.Post"   → full match
# "Post"                → short name match
```

---

## Migrations

RaftSQL uses a migration system similar to Django. It auto-discovers models and writes SQL migration files per app.

### generate (makemigrations)

```bash
raftsql generate
```

```
Auto-detecting apps in: /myproject
  App 'apps/posts': ['Post', 'Tag']
  App 'apps/users': ['User', 'Profile']
Created [apps/posts]:  apps/posts/migrations/0001_create_posts_tags.py
Created [apps/users]:  apps/users/migrations/0001_create_users_profiles.py
```

**With a custom name:**

```bash
raftsql generate --name add_published_flag
# → 0002_add_published_flag.py
```

**Dry-run (no files written):**

```bash
raftsql generate --dry-run
```

**CI check (exit non-zero if changes exist):**

```bash
raftsql generate --check
```

**Generated file example:**

```python
# apps/posts/migrations/0001_create_posts_tags.py
from raftsql.migrations.operations import CreateTable

operations = [
    CreateTable("posts", [
        ("id",        "SERIAL PRIMARY KEY"),
        ("title",     "VARCHAR(255) NOT NULL"),
        ("body",      "TEXT"),
        ("published", "BOOLEAN NOT NULL"),
        ("views",     "INTEGER NOT NULL"),
    ]),
    CreateTable("tags", [
        ("id",   "SERIAL PRIMARY KEY"),
        ("name", "VARCHAR(100) NOT NULL"),
    ]),
]
```

**Generated file with constraints:**

```python
from raftsql.migrations.operations import CreateTable, AddConstraint

operations = [
    CreateTable("products", [
        ("id",       "SERIAL PRIMARY KEY"),
        ("price",    "NUMERIC(10,2) NOT NULL"),
        ("stock",    "INTEGER NOT NULL"),
    ]),
    AddConstraint("products", "price_positive",   'CONSTRAINT "price_positive" CHECK ("price" > 0)'),
    AddConstraint("products", "stock_non_negative", 'CONSTRAINT "stock_non_negative" CHECK (stock >= 0)'),
]
```

**Migration filename convention:**

| Tables in migration | Generated filename |
|---|---|
| `posts` only | `0001_create_posts.py` |
| `authors` + `posts` | `0002_create_authors_posts.py` |
| `authors`, `categories`, `blogs` | `0001_create_authors_categories_blogs.py` |
| 4+ tables | `0001_create_authors_posts_and_3_more.py` |
| `--name my_name` | `0001_my_name.py` |

### apply (migrate)

```bash
raftsql apply
```

```
Applied: apps/posts/migrations/0001_create_posts_tags
Applied: apps/users/migrations/0001_create_users_profiles
```

Run again and it is a no-op:

```bash
raftsql apply
# → No pending migrations.
```

Additional flags:

```bash
raftsql apply --plan             # show pending migrations without running them
raftsql apply --fake             # mark all as applied without executing SQL
raftsql apply --zero apps/posts  # roll back all migrations for the posts app
```

RaftSQL tracks applied migrations in a `raftsql_migrations` table in your database. Every migration key is stored as a relative path (e.g. `apps/posts/migrations/0001_create_posts_tags`) which is globally unique even when multiple apps share the same migration number.

### Per-App Migrations

RaftSQL writes migration files **next to the models that generated them**, not in a global directory:

```
myproject/
├── apps/
│   ├── posts/
│   │   ├── models.py
│   │   └── migrations/
│   │       ├── __init__.py
│   │       └── 0001_create_posts.py   ← lives here
│   └── users/
│       ├── models.py
│       └── migrations/
│           ├── __init__.py
│           └── 0001_create_users.py   ← lives here
```

This means:

- No merge conflicts when two developers add models to different apps simultaneously.
- Each app can be migrated independently.
- Teams have clear ownership — posts team owns `apps/posts/migrations/`.

**App detection — no registration required.** Any directory that contains a `models.py` with at least one `Model` subclass is automatically treated as an app. You never need to list apps anywhere.

If you want explicit control, add `APPS` to `setraft.py`:

```python
# setraft.py — override auto-detection
APPS = [
    "apps.posts",
    "apps.users",
]
```

---

## Schema Introspection — inspect

`inspect` reads the live database schema and prints ready-to-use `Model` class definitions to stdout. It is the reverse of `generate` — useful for bootstrapping an ORM layer over an existing database.

### CLI usage

```bash
# Introspect every public table
raftsql inspect

# Introspect specific tables only
raftsql inspect users orders order_items

# Pipe straight into your models.py
raftsql inspect > apps/legacy/models.py
```

### Programmatic usage

```python
import raftsql
raftsql.setup()

from raftsql.management.inspectdb import inspectdb

# All tables
inspectdb(raftsql._global_config)

# Selected tables
inspectdb(raftsql._global_config, table_names=["users", "orders"])
```

### Example output

Given a `products` table with columns `id`, `name`, `price`, `supplier_id`:

```python
# Generated by RaftSQL inspectdb
# Paste into your models.py and review carefully before use.

from raftsql.orm import (
    Model, AutoField, IntegerField, BigIntegerField, SmallIntegerField,
    FloatField, DecimalField, BooleanField, CharField, TextField,
    DateField, DateTimeField, TimeField, JSONField, UUIDField, BinaryField,
    ForeignKey, CASCADE,
)


class Products(Model):
    class Meta:
        db_table = 'products'

    id       = AutoField(primary_key=True)
    name     = CharField(max_length=255)
    price    = DecimalField(max_digits=10, decimal_places=2)
    supplier = ForeignKey('Suppliers', on_delete=CASCADE)
```

### What inspectdb detects

| Database feature | Generated field |
|---|---|
| `SERIAL` / `nextval(...)` primary key | `AutoField(primary_key=True)` |
| `INTEGER`, `BIGINT`, `SMALLINT` | `IntegerField`, `BigIntegerField`, `SmallIntegerField` |
| `FLOAT`, `DOUBLE PRECISION` | `FloatField` |
| `NUMERIC(p, s)` / `DECIMAL` | `DecimalField(max_digits=p, decimal_places=s)` |
| `VARCHAR(n)` / `CHARACTER VARYING` | `CharField(max_length=n)` |
| `TEXT` | `TextField` |
| `BOOLEAN` | `BooleanField` |
| `DATE` | `DateField` |
| `TIMESTAMP` | `DateTimeField` |
| `TIME` | `TimeField` |
| `JSON` / `JSONB` | `JSONField` |
| `UUID` | `UUIDField` |
| `BYTEA` | `BinaryField` |
| Column ending in `_id` with FK constraint | `ForeignKey(RefModel, on_delete=CASCADE)` |
| `NOT NULL` | `null` omitted (defaults `False`) |
| nullable | `null=True` |

---

## Querying

All queries are built through `Model.objects`, which returns a `QuerySet`. QuerySets are **lazy** — no SQL is issued until you call an execution method (`.all()`, `.first()`, `.get()`, etc.).

### Basic Retrieval

```python
# All rows
posts = Post.objects.all()           # → list[Post]

# First row (None if empty)
post = Post.objects.first()          # → Post | None

# Single row by lookup — raises NotFound / MultipleObjects
post = Post.objects.get(pk=1)        # → Post
post = Post.objects.get(slug="hello")

# Async variants
posts = await Post.objects.alist()
post  = await Post.objects.afirst()
post  = await Post.objects.aget(pk=1)
```

### Filtering

```python
# Equality
posts = Post.objects.filter(published=True).all()

# Multiple conditions — ANDed together
posts = Post.objects.filter(published=True, views__gt=100).all()

# Chained filter calls — also ANDed
posts = (
    Post.objects
    .filter(published=True)
    .filter(views__gt=100)
    .all()
)

# Async
posts = await Post.objects.filter(published=True).alist()
```

### Lookup Expressions

Append a `__lookup` suffix to any field name in `.filter()` or `.exclude()`:

| Lookup | SQL equivalent | Example |
|---|---|---|
| _(none)_ | `= value` | `filter(name="Alice")` |
| `__exact` | `= value` | `filter(name__exact="Alice")` |
| `__ne` | `!= value` | `filter(status__ne="draft")` |
| `__iexact` | `ILIKE value` | `filter(name__iexact="alice")` |
| `__contains` | `LIKE '%val%'` | `filter(title__contains="SQL")` |
| `__icontains` | `ILIKE '%val%'` | `filter(title__icontains="sql")` |
| `__startswith` | `LIKE 'val%'` | `filter(name__startswith="Al")` |
| `__istartswith` | `ILIKE 'val%'` | `filter(name__istartswith="al")` |
| `__endswith` | `LIKE '%val'` | `filter(name__endswith="ice")` |
| `__iendswith` | `ILIKE '%val'` | `filter(name__iendswith="ICE")` |
| `__gt` | `> value` | `filter(price__gt=10)` |
| `__gte` | `>= value` | `filter(price__gte=10)` |
| `__lt` | `< value` | `filter(price__lt=100)` |
| `__lte` | `<= value` | `filter(price__lte=100)` |
| `__in` | `IN (...)` | `filter(id__in=[1, 2, 3])` |
| `__isnull` | `IS NULL` / `IS NOT NULL` | `filter(deleted_at__isnull=True)` |
| `__range` | `BETWEEN a AND b` | `filter(price__range=(10, 100))` |
| `__regex` | `~ 'pattern'` | `filter(slug__regex=r'^[a-z]+$')` |
| `__iregex` | `~* 'pattern'` | `filter(slug__iregex=r'^[A-Z]+$')` |

```python
# Case-insensitive prefix/suffix — new in this version
Post.objects.filter(title__istartswith="hello").all()
Post.objects.filter(slug__iendswith="draft").all()

# Not equal
Post.objects.filter(status__ne="archived").all()

# Regex (PostgreSQL ~ / ~* operators)
Post.objects.filter(slug__regex=r"^\d{4}-").all()
Post.objects.filter(title__iregex=r"python|django").all()

# Range + IN
Post.objects.filter(views__range=(100, 1000)).all()
Post.objects.filter(id__in=[1, 5, 10]).all()
```

### Q Objects — Complex Conditions

Use `Q` to compose complex `OR`, `AND`, and `NOT` conditions:

```python
from raftsql import Q

# OR
Post.objects.filter(Q(published=True) | Q(views__gt=1000)).all()

# AND (same as chaining .filter() calls)
Post.objects.filter(Q(published=True) & Q(author_id=1)).all()

# NOT
Post.objects.filter(~Q(published=False)).all()

# Nested
Post.objects.filter(
    Q(views__gt=500) | (Q(published=True) & ~Q(title__icontains="draft"))
).all()

# Mix Q with keyword args (ANDed together)
Post.objects.filter(Q(views__gt=100) | Q(published=True), author_id=1).all()

# Async
results = await Post.objects.filter(
    Q(title__istartswith="hello") | Q(title__iendswith="world")
).alist()
```

### F Objects — Column References

Use `F` to reference another column in a filter or update — no Python roundtrip:

```python
from raftsql import F

# Filter: rows where stock > reserved
Item.objects.filter(stock__gt=F("reserved")).all()

# Column-to-column equality
Post.objects.filter(views=F("likes")).all()

# Update: copy one column to another
Post.objects.filter(summary__isnull=True).update(summary=F("title"))

# Async update
await Post.objects.filter(summary__isnull=True).aupdate(summary=F("title"))
```

### exclude()

`exclude()` is the negation of `filter()` — it rejects rows that match the given conditions:

```python
# All posts that are NOT drafts
Post.objects.exclude(published=False).all()

# Combine with filter
Post.objects.filter(author_id=1).exclude(views__lt=100).all()

# Async
results = await Post.objects.exclude(status="archived").alist()
```

### Ordering

```python
# Ascending
Post.objects.order_by("title").all()

# Descending — prefix with "-"
Post.objects.order_by("-created_at").all()

# Multiple fields
Post.objects.order_by("-published", "title").all()

# Async
results = await Post.objects.filter(published=True).order_by("-views").alist()
```

### Slicing — limit() and offset()

```python
# First 10 rows
Post.objects.filter(published=True).limit(10).all()

# Pagination — page 3 of 10 per page
Post.objects.order_by("id").limit(10).offset(20).all()

# Async
page = await Post.objects.order_by("-created_at").limit(20).offset(40).alist()
```

### distinct()

```python
Post.objects.distinct().values("category").all()
```

### values() and values\_list()

Return lightweight dicts or tuples instead of full model instances:

```python
# Dicts
posts = Post.objects.values("id", "title").all()
# → [{"id": 1, "title": "Hello"}, ...]

# Tuples
posts = Post.objects.values_list("id", "title").all()
# → [(1, "Hello"), ...]

# Flat list
ids = Post.objects.values_list("id", flat=True).all()
# → [1, 2, 3, ...]

# Async
rows = await Post.objects.values("id", "title").alist()
```

### exists()

```python
# Sync
if Post.objects.filter(published=True).exists():
    print("There are published posts")

# Async
has_posts = await Post.objects.filter(published=True).aexists()
```

### count()

```python
# Sync
n = Post.objects.filter(published=True).count()  # → int

# Async
n = await Post.objects.filter(published=True).acount()
```

---

## Writing Data

### create()

```python
# Sync
post = Post.objects.create(
    title="Hello RaftSQL",
    body="Content here",
    published=True,
)
# → Post instance with id populated

# Async
post = await Post.objects.acreate(
    title="Async post",
    body="Created with asyncpg",
    published=True,
)
```

### save() and asave()

Call `save()` / `asave()` on an existing instance to INSERT (new) or UPDATE (existing) it:

```python
# Sync — INSERT when pk is None
post = Post(title="Draft", published=False)
post.save()
print(post.id)   # populated after INSERT

# UPDATE if pk is already set
post.title = "Published"
post.published = True
post.save()

# Async — INSERT
post = Post(title="Async draft")
await post.asave()

# Async — UPDATE
post.views = 100
await post.asave()
```

### update()

Updates matching rows in a single `UPDATE` statement. Returns the number of rows affected.

```python
# Sync
Post.objects.filter(pk=1).update(views=500)
Post.objects.filter(published=True).update(views=F("views") + 1)

# Async
await Post.objects.filter(published=True).aupdate(views=F("views") + 1)
```

### delete()

```python
# Sync — queryset delete
Post.objects.filter(pk=1).delete()
Post.objects.filter(published=False, views=0).delete()

# Async — queryset delete
await Post.objects.filter(published=False).adelete()

# Sync — instance delete (respects PROTECT/RESTRICT)
post = Post.objects.get(pk=1)
post.delete()

# Async — instance delete
await post.adelete()
```

### Raw SQL

```python
# Sync — returns model instances
posts = Post.objects.raw(
    "SELECT * FROM posts WHERE views > %s ORDER BY views DESC",
    [100],
)

# Async
posts = await Post.objects.araw(
    "SELECT * FROM posts WHERE title ILIKE %s",
    ["%python%"],
)
```

---

## Aggregation and Annotation

### aggregate()

Runs a single `SELECT` with aggregate functions and returns a plain `dict`:

```python
from raftsql import Count, Sum, Avg, Max, Min

# Sync
result = Post.objects.aggregate(
    total_posts   = Count("id"),
    total_views   = Sum("views"),
    average_views = Avg("views"),
    max_views     = Max("views"),
    min_views     = Min("views"),
)
# → {"total_posts": 42, "total_views": 18500, "average_views": 440.5, ...}

# Async
result = await Post.objects.filter(published=True).aaggregate(
    count = Count("id"),
    total = Sum("views"),
)
```

### annotate()

Adds a computed column to each row. Used with `.all()` / `.alist()` to return enriched model instances, or with `.values()` to return dicts:

```python
# Sync — count posts per author
from raftsql import Count

authors = (
    Author.objects
    .annotate(post_count=Count("posts__id"))
    .order_by("-post_count")
    .all()
)
for a in authors:
    print(a.name, a.post_count)

# Async — group + annotate
results = await (
    Post.objects
    .values("category")
    .annotate(total_views=Sum("views"))
    .order_by("-total_views")
    .alist()
)
# → [{"category": "python", "total_views": 9200}, ...]
```

### Available Aggregates

| Class | SQL | `distinct` support |
|---|---|---|
| `Count("col")` | `COUNT(col)` | `Count("col", distinct=True)` |
| `Sum("col")` | `SUM(col)` | — |
| `Avg("col")` | `AVG(col)` | — |
| `Max("col")` | `MAX(col)` | — |
| `Min("col")` | `MIN(col)` | — |

---

## Advanced Expressions

### Window Functions

Window functions compute values across a set of rows related to the current row, without collapsing them into groups.

```python
from raftsql import Window, RowNumber, Rank, DenseRank, Lag, Lead
from raftsql import Sum, Avg

# Sync — ROW_NUMBER() per partition
rows = (
    Sale.objects
    .annotate(row_num=Window(RowNumber(), partition_by=["region"], order_by=["-amount"]))
    .all()
)

# Async — Running total
rows = await (
    Sale.objects
    .annotate(running_total=Window(Sum("amount"), order_by=["sale_date"]))
    .alist()
)

# Sync — LAG / LEAD
rows = (
    Sale.objects
    .annotate(
        prev_amount=Window(Lag("amount", 1), order_by=["sale_date"]),
        next_amount=Window(Lead("amount", 1), order_by=["sale_date"]),
    )
    .all()
)

# Async — Custom frame
rows = await (
    Sale.objects
    .annotate(
        rolling_avg=Window(
            Avg("amount"),
            order_by=["sale_date"],
            frame="ROWS BETWEEN 6 PRECEDING AND CURRENT ROW",
        )
    )
    .alist()
)
```

**Window function constructor:**

```python
Window(
    expression,                    # any aggregate or window function
    partition_by = ["col1", ...],  # PARTITION BY (optional)
    order_by     = ["col", "-col"],# ORDER BY (optional)
    frame        = "ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW",  # optional
)
```

**Available window functions:**

| Function | SQL | Notes |
|---|---|---|
| `RowNumber()` | `ROW_NUMBER()` | Unique sequential number |
| `Rank()` | `RANK()` | Rank with gaps for ties |
| `DenseRank()` | `DENSE_RANK()` | Rank without gaps |
| `PercentRank()` | `PERCENT_RANK()` | Relative rank 0.0–1.0 |
| `CumeDist()` | `CUME_DIST()` | Cumulative distribution |
| `Ntile(n)` | `NTILE(n)` | Divide rows into n buckets |
| `Lag(col, offset)` | `LAG(col, offset)` | Value from previous row |
| `Lead(col, offset)` | `LEAD(col, offset)` | Value from next row |
| `FirstValue(col)` | `FIRST_VALUE(col)` | First value in window |
| `LastValue(col)` | `LAST_VALUE(col)` | Last value in window |
| `NthValue(col, n)` | `NTH_VALUE(col, n)` | Nth value in window |
| Any aggregate | `SUM(...) OVER (...)` | `Sum`, `Count`, `Avg`, `Max`, `Min` |

### COALESCE

Returns the first non-`NULL` value from the given arguments:

```python
from raftsql import Coalesce, Value

# Sync — column fallback
users = User.objects.annotate(
    label=Coalesce("display_name", "username")
).values("id", "label").all()

# Async — literal default
users = await User.objects.annotate(
    label=Coalesce("display_name", Value("Anonymous"))
).values("id", "label").alist()
```

### Subquery and OuterRef

**IN subquery (sync and async):**

```python
from raftsql import Subquery

published_post_ids = Post.objects.filter(published=True).values("id")

# Sync
Comment.objects.filter(post_id__in=Subquery(published_post_ids)).all()

# Async
await Comment.objects.filter(post_id__in=Subquery(published_post_ids)).alist()
```

**Correlated scalar subquery in annotate:**

```python
from raftsql import Subquery, OuterRef

latest_post = (
    Post.objects
    .filter(author_id=OuterRef("id"))
    .order_by("-created_at")
    .values("title")
    .limit(1)
)

# Sync
authors = Author.objects.annotate(latest_post_title=Subquery(latest_post)).all()

# Async
authors = await Author.objects.annotate(latest_post_title=Subquery(latest_post)).alist()

for a in authors:
    print(a.name, a.latest_post_title)
```

---

### Case / When

Conditional expressions in annotations — equivalent to SQL `CASE WHEN … THEN … END`:

```python
from raftsql import Case, When, Value

# Sync — label items by stock status
items = (
    Item.objects
    .annotate(
        status=Case(
            When(in_stock=True,  then=Value("Available")),
            When(in_stock=False, then=Value("Out of Stock")),
            default=Value("Unknown"),
        )
    )
    .all()
)

# Async — numeric bucketing
items = await (
    Item.objects
    .annotate(
        tier=Case(
            When(price__gte=100, then=Value("premium")),
            When(price__gte=50,  then=Value("mid")),
            default=Value("budget"),
        )
    )
    .alist()
)

for item in items:
    print(item.name, item.tier)
```

The `When` condition accepts the same lookup syntax as `filter()` — including `Q` objects:

```python
When(Q(price__gte=100) & Q(in_stock=True), then=Value("Premium In Stock"))
```

---

### Cast

Explicit type casting inside expressions:

```python
from raftsql import Cast, Coalesce, Value

# Sync — cast integer column to text
items = Item.objects.annotate(price_text=Cast("price", "TEXT")).all()

# Async — combine with Coalesce
results = await (
    Item.objects
    .annotate(label=Coalesce(Cast("price", "TEXT"), Value("N/A")))
    .alist()
)
```

---

## Relations

### ForeignKey — select\_related()

Fetches the related object in a single JOIN query instead of separate queries:

```python
# Without select_related — 1 + N queries
posts = Post.objects.all()
for p in posts:
    print(p.title, p.author.name)   # each triggers a separate SELECT

# With select_related — 1 query (JOIN)
posts = Post.objects.select_related("author").all()
for p in posts:
    print(p.title, p.author.name)   # no extra queries

# Async
posts = await Post.objects.select_related("author").alist()
```

Accessing an FK attribute directly also auto-fetches lazily (sync only):

```python
comment = Comment.objects.get(pk=1)
print(comment.post.title)   # auto-fetches Post in a separate query
print(comment.post_id)      # raw FK integer — no query
```

---

### Reverse FK Accessors

When you declare a `ForeignKey` or `OneToOneField` with a `related_name`, RaftSQL automatically attaches a reverse accessor on the related model:

```python
class Comment(models.Model):
    id   = models.AutoField(primary_key=True)
    body = models.TextField()
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")

    class Meta:
        db_table = "comments"
```

This auto-creates `Post.comments` as a reverse descriptor. You can query through it:

```python
# Sync — all comments for a post
post = Post.objects.get(pk=1)
comments = post.comments.filter(published=True).all()

# Async
comments = await post.comments.filter(published=True).alist()
```

If `related_name` is not specified, the default reverse name is `{child_model_snake}_set` (e.g. `comment_set`).

---

### ManyToMany — prefetch\_related()

```python
# Without prefetch — 1 + N queries
posts = Post.objects.all()
for p in posts:
    tags = p.tags.all(conn)   # extra query per post

# With prefetch_related — 2 queries total (both sync and async)
posts = Post.objects.prefetch_related("tags").all()
for p in posts:
    for tag in p._prefetched_tags:
        print(tag.name)

# Async
posts = await Post.objects.prefetch_related("tags").alist()
```

**Accessing M2M via the accessor (sync):**

```python
from raftsql.db.connection import Connection

with Connection(config) as conn:
    tags = post.tags.all(conn)    # all related tags
    post.tags.add(conn, tag)      # add a relation
    post.tags.remove(conn, tag)   # remove a relation
```

**Accessing M2M via the accessor (async):**

```python
from raftsql.db.async_connection import AsyncConnection

async with AsyncConnection(config) as conn:
    tags = await post.tags.aall(conn)
    await post.tags.aadd(conn, tag)
    await post.tags.aremove(conn, tag)
```

### ManyToMany with through= Model

Use `through=` with a Model class (not just a string table name) to define a junction model with extra columns. This gives you full access to the join table through the normal ORM API.

**Define the through model:**

```python
from raftsql import models

class Post(models.Model):
    id    = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    tags  = models.ManyToManyField("Tag", through=PostTag)  # forward ref resolved below

    class Meta:
        db_table = "posts"


class Tag(models.Model):
    id   = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "tags"


class PostTag(models.Model):
    id    = models.AutoField(primary_key=True)
    post  = models.ForeignKey(Post, on_delete=models.CASCADE)
    tag   = models.ForeignKey(Tag,  on_delete=models.CASCADE)
    order = models.IntegerField(default=0)   # extra column not possible with auto junction

    class Meta:
        db_table = "post_tags"
```

**Working with a through model:**

```python
# Sync — add a relation with extra data
PostTag.objects.create(post_id=post.id, tag_id=tag.id, order=1)

# Query the through model directly
featured = PostTag.objects.filter(order__lte=3).order_by("order").all()
for pt in featured:
    print(pt.post_id, pt.tag_id, pt.order)

# Async
await PostTag.objects.create(post_id=post.id, tag_id=tag.id, order=2)
entries = await PostTag.objects.filter(post_id=post.id).order_by("order").alist()
```

**Junction table is NOT auto-created** when `through` is a Model class — the through model participates in migrations normally via its own `Meta.db_table`. No separate junction table is auto-generated.

When `through` is a string, an auto-named junction table **is** created by `generate` (the standard behaviour):

```python
# string through — junction table auto-created by migrations
tags = models.ManyToManyField("Tag", through="post_tag_assignments")

# Model class through — no auto junction; manage via PostTag.objects
tags = models.ManyToManyField("Tag", through=PostTag)
```

---

## Serializers

RaftSQL ships with a DRF-inspired serializer layer — `Serializer` and `ModelSerializer` — for handling input/output at API boundaries. No Django or DRF dependency needed.

### Serializer

`Serializer` is the base class. Subclass it and implement `to_representation()`, `to_internal_value()`, `create()`, and `update()`:

```python
from raftsql import Serializer

class PostSerializer(Serializer):
    def to_representation(self, instance):
        return {"id": instance.id, "title": instance.title}

    def to_internal_value(self, data):
        return {"title": data["title"]}

    def create(self, validated_data):
        return Post.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        return instance
```

**Serialize (output):**

```python
# Single instance
s = PostSerializer(post_instance)
print(s.data)   # → {"id": 1, "title": "Hello"}

# Many / list
s = PostSerializer(queryset, many=True)
print(s.data)   # → [{"id": 1, ...}, ...]
```

**Deserialize + save (sync):**

```python
s = PostSerializer(data={"title": "Hello"})
if s.is_valid():
    post = s.save()
else:
    print(s.errors)
```

**Deserialize + save (async):**

```python
s = PostSerializer(data={"title": "Hello"})
if await s.is_valid_async():
    post = await s.asave()
```

**Partial update:**

```python
s = PostSerializer(post_instance, data={"title": "New Title"}, partial=True)
if s.is_valid():
    post = s.save()
```

**Per-field validation hooks:**

```python
class PostSerializer(Serializer):
    def validate_title(self, value):
        if len(value) < 3:
            raise ValueError("Title must be at least 3 characters.")
        return value

    def validate(self, data):
        # Cross-field validation
        return data
```

### ModelSerializer

`ModelSerializer` auto-discovers fields directly from the model's metadata — no manual field declarations needed:

```python
from raftsql import ModelSerializer
from apps.posts.models import Post

class PostSerializer(ModelSerializer):
    class Meta:
        model            = Post
        fields           = '__all__'          # or list of field names
        read_only_fields = ['id', 'created_at', 'updated_at']
        exclude          = []                 # column names to skip
```

`fields` accepts `'__all__'` or a list of column names or attribute names — both spellings work.

**Auto-handled field types:**

| Field type | Output in `.data` | Input on save |
|---|---|---|
| `FileField` / `ImageField` | URL string (via storage backend) | Upload object saved to storage automatically |
| `ForeignKey` / `OneToOneField` | raw ID integer | Accepts both `author_id` and `author` spellings |
| `DateTimeField` / `DateField` / `TimeField` | ISO-8601 string | Raw value |
| `auto_now` / `auto_now_add` | Read-only always | Never written by user input |

**Sync usage:**

```python
# Serialize
s = PostSerializer(post_instance)
return s.data

# Create
s = PostSerializer(data={"title": "Hello", "published": True})
if s.is_valid():
    post = s.save()

# Update
s = PostSerializer(post_instance, data={"title": "Updated"}, partial=True)
if s.is_valid():
    post = s.save()

# List
s = PostSerializer(queryset, many=True)
return s.data
```

**Async usage (FastAPI):**

```python
from fastapi import APIRouter, UploadFile, File, Form

router = APIRouter()

@router.post("/posts/")
async def create_post(
    title:     str        = Form(...),
    thumbnail: UploadFile = File(None),
):
    s = PostSerializer(data={"title": title, "thumbnail": thumbnail})
    if await s.is_valid_async():
        post = await s.asave()
        return s.data
    return s.errors

@router.put("/posts/{post_id}")
async def update_post(post_id: int, title: str = Form(...)):
    post = await Post.objects.aget(pk=post_id)
    s = PostSerializer(post, data={"title": title}, partial=True)
    if await s.is_valid_async():
        post = await s.asave()
        return s.data
    return s.errors
```

**Custom output / validation:**

```python
class PostSerializer(ModelSerializer):
    class Meta:
        model            = Post
        fields           = '__all__'
        read_only_fields = ['id', 'created_at']

    def validate_title(self, value):
        if len(value) < 3:
            raise ValueError("Title too short.")
        return value

    def validate(self, data):
        if data.get('title') == data.get('content'):
            raise ValueError("Title and content cannot be identical.")
        return data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['title_upper'] = data['title'].upper()
        return data
```

---

## Transactions

Wrap multiple ORM operations in a single atomic unit. All statements inside the block share the same connection and commit together on success. **Any exception raised inside the block automatically rolls back every statement in the block** — nothing is partially committed.

Use **`using="alias"`** on the context manager to tie the transaction to a specific entry in `DATABASES` (default: **`"default"`**). Queries in the block should use the same alias (for example via **`.using(alias)`**). See [Multi-database support](#multi-database-support).

Nested `atomic()` / `atomic_sync()` calls automatically use PostgreSQL `SAVEPOINT` so only the inner block rolls back on failure.

### Async transactions

#### Basic — commit on success, rollback on exception

```python
from raftsql import atomic

async with atomic() as tx:
    user = await User.objects.acreate(username="alice", email="alice@example.com")
    await Profile.objects.acreate(user_id=user.id, bio="Hello!")
    # If acreate raises for any reason, BOTH inserts are rolled back automatically.
```

#### Exception handling inside the block

Catch expected errors inside the block; any unhandled exception still triggers rollback:

```python
from raftsql import atomic

async def transfer_credits(from_id: int, to_id: int, amount: int):
    async with atomic() as tx:
        sender = await Wallet.objects.aget(id=from_id)
        if sender.balance < amount:
            raise ValueError("Insufficient balance")   # rolls back the whole block

        await Wallet.objects.filter(id=from_id).aupdate(balance=F("balance") - amount)
        await Wallet.objects.filter(id=to_id).aupdate(balance=F("balance") + amount)
        await Transaction.objects.acreate(
            from_wallet_id=from_id,
            to_wallet_id=to_id,
            amount=amount,
        )
        # All three statements commit together, or none of them do.
```

#### Dry-run / preview — force rollback without raising

```python
from raftsql import atomic

async def preview_order(cart_items: list, dry_run: bool = False):
    async with atomic() as tx:
        order = await Order.objects.acreate(status="pending")
        for item in cart_items:
            await OrderLine.objects.acreate(order_id=order.id, **item)

        total = await OrderLine.objects.filter(order_id=order.id).aaggregate(
            total=Sum("price")
        )

        if dry_run:
            tx.set_rollback(True)   # nothing written to DB; no exception raised
        
        return total["total"]   # caller receives the computed total regardless
```

#### Nested transactions — inner uses SAVEPOINT

```python
from raftsql import atomic

async with atomic() as outer:
    await Category.objects.acreate(name="Electronics")

    async with atomic() as inner:
        # This runs under a SAVEPOINT
        await Product.objects.acreate(name="Bad Item", sku=None)   # might fail
        # If this raises, only the inner SAVEPOINT is rolled back.

    # Outer transaction is still alive — "Electronics" will still commit.
    await Category.objects.filter(name="Electronics").aupdate(active=True)
```

To intentionally roll back only the inner block without raising:

```python
async with atomic() as outer:
    await Log.objects.acreate(event="started")

    async with atomic() as inner:
        await TempData.objects.acreate(payload="...")
        inner.set_rollback(True)   # only the SAVEPOINT is rolled back

    # outer block continues; "started" log will commit
```

---

### Sync transactions

#### Basic

```python
from raftsql import atomic_sync

with atomic_sync() as tx:
    user = User.objects.create(username="bob", email="bob@example.com")
    Profile.objects.create(user_id=user.id, bio="Hi!")
    # Both commit together; exception in either rolls back both.
```

#### With error handling

```python
from raftsql import atomic_sync

def create_invoice(order_id: int, lines: list[dict]):
    with atomic_sync() as tx:
        order = Order.objects.get(id=order_id)
        if order.status != "confirmed":
            raise ValueError(f"Order {order_id} is not confirmed")

        invoice = Invoice.objects.create(order_id=order_id)
        for line in lines:
            InvoiceLine.objects.create(invoice_id=invoice.id, **line)

        Order.objects.filter(id=order_id).update(status="invoiced")
        return invoice
```

#### Dry-run

```python
from raftsql import atomic_sync

def simulate_import(rows: list[dict], dry_run: bool = False) -> int:
    with atomic_sync() as tx:
        count = 0
        for row in rows:
            Product.objects.create(**row)
            count += 1

        if dry_run:
            tx.set_rollback(True)   # no changes persist; count still returned

        return count
```

#### Nested (sync)

```python
from raftsql import atomic_sync

with atomic_sync() as outer:
    Order.objects.create(ref="ORD-001")

    with atomic_sync() as inner:
        Payment.objects.create(ref="PAY-001", amount=100)
        inner.set_rollback(True)   # Payment rolled back (SAVEPOINT)

    # "ORD-001" still commits
```

---

### TransactionHandle

Both `atomic()` and `atomic_sync()` yield a `TransactionHandle` as `tx`:

| Method | Description |
|---|---|
| `tx.set_rollback(True)` | Force rollback on exit without raising an exception |
| `tx.set_rollback(False)` | Commit on exit (this is the default) |
| `tx.get_rollback()` | Return the current rollback flag (`bool`) |

> **Rule of thumb:** if you raise an exception inside the block, the rollback happens automatically. Use `set_rollback(True)` only when you want to discard DB writes but still return a value to the caller without raising.

---

## Connection Pooling

For production workloads, initialise a connection pool at startup to avoid opening and closing a connection per request.

### Async pool (asyncpg)

```python
import raftsql
from fastapi import FastAPI

app = FastAPI()

@app.on_event("startup")
async def startup():
    raftsql.setup()
    await raftsql.setup_async_pool(min_size=2, max_size=20)

@app.on_event("shutdown")
async def shutdown():
    await raftsql.teardown_async_pool()
```

### Sync pool (psycopg2)

```python
import raftsql

raftsql.setup()
raftsql.setup_sync_pool(min_conn=2, max_conn=10)

# On exit:
raftsql.teardown_sync_pool()
```

### Pool stats

```python
stats = raftsql.pool_stats()
# One key per initialised alias, e.g.
# {
#   "default":   {"async": {"min_size": 2, "max_size": 20, "size": 5, "idle": 3}, "sync": None},
#   "analytics": {"async": None, "sync": {"min_conn": 2, "max_conn": 10, "closed": False}},
# }
```

Multi-database: call **`setup_async_pool(using="analytics", ...)`** / **`setup_sync_pool(using="analytics", ...)`** once per alias you need pooled (see [Multi-database support](#multi-database-support)).

---

## Signals

RaftSQL dispatches Django-style signals around save and delete operations. Both sync and async receivers are supported.

### Available signals

| Signal | When fired | kwargs |
|---|---|---|
| `pre_save` | Before INSERT or UPDATE | `sender`, `instance`, `created` (bool) |
| `post_save` | After INSERT or UPDATE | `sender`, `instance`, `created` (bool) |
| `pre_delete` | Before DELETE | `sender`, `instance` |
| `post_delete` | After DELETE | `sender`, `instance` |

### Sync receivers

```python
from raftsql import pre_save, post_save, pre_delete, post_delete

def on_pre_save(sender, instance, created, **kwargs):
    print(f"About to {'create' if created else 'update'} {sender.__name__}")

# Receive from all models
pre_save.connect(on_pre_save)

# Receive from one model only
pre_save.connect(on_pre_save, sender=Post)

# Disconnect
pre_save.disconnect(on_pre_save, sender=Post)
```

### Async receivers

```python
from raftsql import post_save

async def on_post_save(sender, instance, created, **kwargs):
    if created:
        await notify_new_post(instance)

post_save.connect(on_post_save, sender=Post)
```

`send()` skips async receivers. `asend()` calls both sync and async receivers — async receivers are awaited.

### Custom signals

```python
from raftsql.orm.signals import Signal

my_signal = Signal("my_signal")
my_signal.connect(my_handler)
my_signal.send(sender=MyModel, some_kwarg="value")
await my_signal.asend(sender=MyModel, some_kwarg="value")
```

---

All QuerySet execution methods have an async counterpart, prefixed with `a`. Both share the exact same SQL building pipeline — only the final database call differs.

### Method Reference

| Sync | Async | Description |
|---|---|---|
| `.all()` | `.alist()` | Fetch all matching rows |
| `.first()` | `.afirst()` | Fetch first row or `None` |
| `.get(**kw)` | `.aget(**kw)` | Fetch exactly one row |
| `.create(**kw)` | `.acreate(**kw)` | Insert a new row |
| `instance.save()` | `await instance.asave()` | Insert or update one instance |
| `instance.delete()` | `await instance.adelete()` | Delete one instance (ORM-level on_delete) |
| `.update(**kw)` | `.aupdate(**kw)` | Update matching rows |
| `.delete()` | `.adelete()` | Delete matching rows |
| `.count()` | `.acount()` | Row count |
| `.exists()` | `.aexists()` | Boolean existence check |
| `.aggregate(**kw)` | `.aaggregate(**kw)` | Aggregate functions → dict |
| `.raw(sql, params)` | `.araw(sql, params)` | Raw SQL |
| `.using(alias)` | `.using(alias)` | Pin queryset / manager to `DATABASES` alias (bypasses routers & Guides) |

All chaining methods (`.filter()`, `.exclude()`, `.order_by()`, `.annotate()`, `.values()`, `.limit()`, `.offset()`, `.distinct()`, `.select_related()`, `.prefetch_related()`, **`.using(alias)`**) are shared and work identically for both sync and async execution.

### FastAPI Example

```python
import raftsql
from fastapi import FastAPI, Query, HTTPException, Form, UploadFile, File
from raftsql import Q, F, Count, Sum, Window, Rank, Coalesce, Value, Subquery, Case, When
from raftsql import atomic, ModelSerializer
from raftsql.orm import ProtectedError

app = FastAPI()

@app.on_event("startup")
async def startup():
    raftsql.setup()
    await raftsql.setup_async_pool(min_size=2, max_size=10)

@app.on_event("shutdown")
async def shutdown():
    await raftsql.teardown_async_pool()

from apps.posts.models import Post, Author

class PostSerializer(ModelSerializer):
    class Meta:
        model            = Post
        fields           = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

@app.get("/posts")
async def list_posts(
    search:    str  = Query(None),
    published: bool = Query(None),
    limit:     int  = Query(20, le=100),
    offset:    int  = Query(0),
):
    qs = Post.objects
    if search:
        qs = qs.filter(
            Q(title__icontains=search)
            | Q(title__istartswith=search)
            | Q(body__icontains=search)
        )
    if published is not None:
        qs = qs.filter(published=published)
    posts = await qs.order_by("-created_at").limit(limit).offset(offset).alist()
    return PostSerializer(posts, many=True).data


@app.get("/posts/stats")
async def stats():
    return await Post.objects.aaggregate(
        total  = Count("id"),
        views  = Sum("views"),
    )


@app.get("/posts/ranked")
async def ranked():
    return await (
        Post.objects
        .annotate(
            rank  = Window(Rank(), order_by=["-views"]),
            label = Coalesce("summary", Value("No summary")),
            tier  = Case(
                When(views__gte=10000, then=Value("viral")),
                When(views__gte=1000,  then=Value("popular")),
                default=Value("normal"),
            ),
        )
        .order_by("-views")
        .alist()
    )


@app.post("/posts")
async def create_post(
    title:     str        = Form(...),
    body:      str        = Form(None),
    thumbnail: UploadFile = File(None),
):
    s = PostSerializer(data={"title": title, "body": body, "thumbnail": thumbnail})
    if await s.is_valid_async():
        async with atomic():
            post = await s.asave()
        return s.data
    return s.errors


@app.put("/posts/{post_id}")
async def update_post(post_id: int, title: str = Form(...)):
    post = await Post.objects.aget(pk=post_id)
    s = PostSerializer(post, data={"title": title}, partial=True)
    if await s.is_valid_async():
        return (await s.asave()) and s.data
    return s.errors


@app.delete("/authors/{author_id}")
async def delete_author(author_id: int):
    author = await Author.objects.aget(pk=author_id)
    try:
        await author.adelete()   # raises ProtectedError if posts reference this author
    except ProtectedError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"deleted": True}


@app.delete("/posts/{post_id}")
async def delete_post(post_id: int):
    deleted = await Post.objects.filter(pk=post_id).adelete()
    return {"deleted": deleted}
```

---

## Project Structure

```
raftsql/
├── __init__.py           ← public API + setup(), setup_async_pool(), signals, Serializer
├── cli.py                ← raftsql generate / apply / status / sql / squash / inspect / flush
├── models.py             ← user-facing re-export: from raftsql import models
│
├── conf/
│   ├── config.py         ← Config dataclass (engine, host, port, user, password, dbname,
│   │                         media_root, media_url, alias)
│   └── loader.py         ← finds setraft.py; DATABASE / DATABASES, routers, GUIDES, MEDIA_*, APPS
│
├── routing.py            ← BaseDatabaseRouter, Guide, router/guide engines, allow_relation / allow_migrate helpers
│
├── db/
│   ├── connection.py     ← sync Connection context manager
│   ├── async_connection.py
│   ├── pool.py           ← asyncpg pool + psycopg2 ThreadedConnectionPool
│   ├── transaction.py    ← atomic() / atomic_sync() context managers + TransactionHandle
│   └── backends/
│       ├── base.py       ← Backend ABC
│       ├── registry.py   ← get_backend(engine_name)
│       └── postgresql/
│           ├── backend.py          ← PostgreSQLBackend
│           ├── connection.py       ← psycopg2 wrapper
│           └── async_connection.py ← asyncpg wrapper
│
├── orm/
│   ├── model.py          ← Model base class + ModelMeta + ProtectedError + _MODEL_REGISTRY
│   ├── fields.py         ← all field types: scalar, FileField, ImageField, FieldFile,
│   │                         ForeignKey, OneToOneField, ManyToManyField,
│   │                         CheckConstraint, UniqueConstraint
│   ├── manager.py        ← Manager + QuerySet (full API, MTI JOIN injection)
│   ├── queryset.py       ← NotFound, MultipleObjects exceptions
│   ├── relations.py      ← RelatedAccessor, ManyToManyAccessor, ReverseFKDescriptor
│   ├── q.py              ← Q objects
│   ├── f.py              ← F objects
│   ├── aggregates.py     ← Count, Sum, Avg, Max, Min
│   ├── expressions.py    ← Window, Coalesce, Value, Subquery, OuterRef,
│   │                         Case, When, Cast
│   ├── signals.py        ← pre_save, post_save, pre_delete, post_delete, Signal
│   └── contenttypes.py   ← GenericForeignKey descriptor
│
├── sql/
│   ├── builder.py        ← build_select, build_insert, build_update, build_delete
│   └── where.py          ← WHERE clause builder (20+ lookup expressions)
│
├── storage/
│   ├── base.py           ← Storage ABC (save, url, delete, exists, open)
│   ├── filesystem.py     ← FileSystemStorage (reads MEDIA_ROOT / MEDIA_URL)
│   └── __init__.py       ← default_storage singleton
│
├── serializers/
│   ├── base.py           ← Serializer base class
│   ├── model.py          ← ModelSerializer (auto-field discovery, FileField-aware)
│   └── __init__.py
│
├── migrations/
│   ├── makemigrations.py ← generate migration files per app (constraints diffing,
│   │                         rename detection)
│   ├── runner.py         ← apply migrations, handle all operation types
│   ├── schema.py         ← model → DDL, constraint → __c__ entries, MTI/through skipping
│   ├── operations.py     ← CreateTable, AddColumn, RenameColumn, DropColumn,
│   │                         AlterColumn, AddIndex, DropIndex,
│   │                         AddConstraint, DropConstraint, RenameTable, DropTable
│   ├── state.py          ← migration state reconstruction
│   └── writer.py         ← write / list / serialize migration .py files
│
├── management/
│   └── inspectdb.py      ← reverse-engineer DB schema into Model definitions
│
└── utils/
    └── discovery.py      ← auto-discover Model subclasses and app directories
```

---

## Exceptions

| Exception | Raised when |
|---|---|
| `raftsql.NotFound` | `.get()` / `.aget()` matches zero rows |
| `raftsql.MultipleObjects` | `.get()` / `.aget()` matches more than one row |
| `raftsql.orm.ProtectedError` | `.delete()` / `.adelete()` on an instance with related rows using `on_delete=PROTECT` or `RESTRICT` |
| `ValueError` | Invalid file upload (not a valid image for `ImageField`), bad field args, or disallowed cross-database relation on `save()` |
| `RuntimeError` | `raftsql.setup()` was not called before using the ORM |
| `AssertionError` | Accessing `.validated_data` or calling `.save()` before `.is_valid()` on a serializer |

```python
from raftsql import NotFound, MultipleObjects
from raftsql.orm import ProtectedError

try:
    post = Post.objects.get(pk=999)
except NotFound:
    print("Post does not exist")
except MultipleObjects:
    print("More than one match — tighten your query")

try:
    author.delete()
except ProtectedError as e:
    print(e)
    # "Cannot delete Author pk=1: 3 Article row(s) reference it via author (on_delete=PROTECT)"
```

---

## CLI Reference

```
raftsql <command> [options]
```

| Command | Description |
|---|---|
| `raftsql generate` | Scan all apps, generate migration files for new/changed models |
| `raftsql generate --name <name>` | Custom file name suffix |
| `raftsql generate --dry-run` | Show what would be generated without writing files |
| `raftsql generate --check` | Exit non-zero if model changes exist (CI mode) |
| `raftsql apply` | Apply pending migrations (**`--database` / `--db <alias>`** selects `DATABASES[alias]`; default: `default`) |
| `raftsql apply --plan` | Show pending migrations without running them |
| `raftsql apply --fake` | Mark migrations as applied without running SQL |
| `raftsql apply --fake-initial` | Fake-apply the first migration (useful after squash) |
| `raftsql apply --zero <app_dir>` | Roll back all migrations for an app |
| `raftsql status` | List all migrations and their applied / pending status |
| `raftsql sql <file>` | Print the SQL for a migration file without running it |
| `raftsql squash <app_dir>` | Squash all migrations for an app into one file |
| `raftsql flush` | TRUNCATE all model tables (rows only; schema untouched) |
| `raftsql flush --no-input` | Skip confirmation prompt |
| `raftsql inspect` | Introspect all public tables and print Model definitions |
| `raftsql inspect <table> ...` | Introspect specific tables only |

**generate** works by:
1. Finding `setraft.py` to locate the project root and database config
2. Walking the project tree for directories that contain `models.py` with `Model` subclasses
3. Comparing discovered tables and constraints against existing migration state
4. Writing one migration file per app for new tables or changed constraints

**apply** works by:
1. Finding `setraft.py` and ensuring **`raftsql.setup()`** ran (loads `DATABASE` / `DATABASES`, `DATABASE_ROUTERS`, `GUIDES`)
2. Opening a connection to **`raftsql.get_db(<alias>)`** where `<alias>` is from **`--database` / `--db`** (default **`default`**)
3. Discovering every `migrations/` directory under the project root
4. Comparing file-based migration keys against the `raftsql_migrations` tracking table — skipping apps when **`allow_migrate`** denies them for that alias
5. Running pending files in ascending numeric order; recording each as applied

**inspect** works by:
1. Connecting to the live database
2. Querying `information_schema.columns`, `pg_index`, and FK constraints for each table
3. Mapping PostgreSQL types to RaftSQL field classes
4. Printing `Model` class definitions to stdout

**flush** works by:
1. Discovering all model tables in the project
2. Prompting for confirmation (skippable with `--no-input`)
3. Running `TRUNCATE <table>, ... RESTART IDENTITY CASCADE` for all tables that exist in the database

---

## Changelog

See [changelogs/CHANGELOG.md](changelogs/CHANGELOG.md) for the full version history.

---

## License

MIT
