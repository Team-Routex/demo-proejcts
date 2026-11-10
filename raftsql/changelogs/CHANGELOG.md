# Changelog

All notable changes to RaftSQL are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2026-05-11

Focus: **multi-database PostgreSQL**, **per-model `Meta` routing**, migration metadata alignment, documentation, and contributor onboarding.

### Multi-database configuration

- **`DATABASES`** in **`setraft.py`** — map string aliases (e.g. `default`, `analytics`, `replica`) to the same connection dict shape as legacy **`DATABASE`**.
- **`DATABASE = {…}`** remains supported; it is treated as **`DATABASES["default"]`**.
- **`raftsql.get_db(alias)`** returns **`Config`** for a given alias ( **`Config.alias`** identifies the pool / transaction slot).
- **`setup_async_pool` / `setup_sync_pool`** accept **`using="alias"`**; **`teardown_*_pool`** / **`teardown_all_*_pools`** close pools per alias.
- **`atomic()` / `atomic_sync()`** accept **`using="alias"`** with per-alias transaction state.

### Per-model routing and rules (`class Meta`)

- **`db_alias`** — default alias for reads and writes (subject to **`for_read`** / **`for_write`** gates).
- **`for_read`** / **`for_write`** — booleans (default **`True`** when **`db_alias`** is set): turn each half off to fall through to optional routers/guides / **`default`** starter.
- **`db_for_read`** / **`db_for_write`** — explicit alias strings per half (override **`db_alias`** gates for that half).
- **`allow_relation`** — **`None`** (default rules), **`False`** (same effective-write DB required with the other side), **`True`** (allow cross-database relations when routers do not forbid).
- **`allow_migrate`** — **`False`** on any registered model with that **`app_label`** vetoes migrations for that app everywhere (checked after routers).
- **`allow_migrate_on_databases`** — whitelist tuple/list of aliases; **`raftsql apply --db`** must satisfy every model’s list that sets this (AND across models sharing the **`app_label`**).

### Routing engine

- **`routing.resolve_default_database_alias(model_cls, operation, starter=...)`** — resolution order: **`Meta`**, then **`DATABASE_ROUTERS`**, then **Guides**, then starter (**`"default"`** for ordinary querysets).
- **`QuerySet.using(alias)` / `Manager.using(alias)`** bypasses **`Meta`**, routers, and Guides (explicit pin).
- Django-style **`DATABASE_ROUTERS`** and legacy **`Guide` / `GUIDES` / `add_guide()`** remain optional and apply only when **`Meta`** does not choose an alias for that read/write half.
- **`allow_relation_allowed`** uses effective write aliases (**`Meta` + routers + guides**).
- **`allow_migrate_allowed`** aggregates routers **and** **`Meta`** constraints via **`get_registered_models_for_app_label()`**.

### Migrations

- New migration files stamp **`app_label = "..."`** from model **`Meta`** (consensus with warning if mixed **`app_label`** in one directory).
- **`apply`** resolves **`allow_migrate`** using embedded **`app_label`** when present, else path-based inference (legacy).
- Migration **dependencies** use **`app_label`** read from the previous file when **`app_label =`** exists, otherwise the basename of the app directory containing **`migrations/`**.

### CLI

- **`raftsql apply --database <alias>`** / **`--db <alias>`** — apply pending migrations against **`DATABASES[alias]`** (default: **`default`**).

### Documentation

- **README** — Multi-database section rewritten **Meta-first**; **`Meta` Options** expanded for DB and migration fields.
- **`CODEREADGUIDE.md`** — beginner-oriented codebase walkthrough for contributors.

### API surface

- Public export: **`resolve_default_database_alias`**.
- **`orm.model.get_registered_models_for_app_label(app_label)`** for migration / routing introspection.

---

## [1.0.0] - 2026-03-06

First public release of **RaftSQL** — a minimal ORM built from scratch for PostgreSQL, supporting both synchronous and asynchronous workflows.

---

### Configuration

- **`setraft.py`** project settings file — `DATABASE`, `APPS`, `MEDIA_ROOT`, `MEDIA_URL`.
- `raftsql.setup()` auto-discovers `setraft.py` by walking up from `cwd`, then down into subdirectories (max depth 4). Safe to call multiple times (idempotent for `uvicorn --reload`).
- `BASE_DIR = Path(__file__).resolve().parent` pattern supported.
- Environment variables resolved inside `setraft.py` however the user prefers (`os.getenv`, `python-dotenv`, etc.) — RaftSQL only reads the resulting dict.
- `MEDIA_ROOT` / `MEDIA_URL` for file upload storage configuration.
- `APPS` list for explicit app registration (auto-detection falls back to scanning for `models.py` files).

---

### Field Types

| Field | PostgreSQL type |
|---|---|
| `AutoField` | `SERIAL PRIMARY KEY` |
| `BigAutoField` | `BIGSERIAL PRIMARY KEY` |
| `IntegerField` | `INTEGER` |
| `SmallIntegerField` | `SMALLINT` |
| `PositiveIntegerField` | `INTEGER CHECK (col >= 0)` |
| `BigIntegerField` | `BIGINT` |
| `FloatField` | `DOUBLE PRECISION` |
| `DecimalField` | `NUMERIC(max_digits, decimal_places)` |
| `CharField` | `VARCHAR(max_length)` |
| `TextField` | `TEXT` |
| `SlugField` | `VARCHAR(50)` |
| `EmailField` | `VARCHAR(254)` |
| `URLField` | `VARCHAR(200)` |
| `UUIDField` | `UUID` |
| `BooleanField` | `BOOLEAN` |
| `DateField` | `DATE` |
| `TimeField` | `TIME` |
| `DateTimeField` | `TIMESTAMP` |
| `JSONField` | `JSONB` |
| `BinaryField` | `BYTEA` |
| `ArrayField(base_field)` | `{base_type}[]` |
| `FileField` | `VARCHAR(n)` — stores file path |
| `ImageField` | `VARCHAR(n)` — validates image via Pillow |

**Field options:** `null`, `blank`, `default`, `unique`, `db_column`, `db_index`, `max_length`, `upload_to`, `storage`.

---

### Relation Fields

- **`ForeignKey(to, on_delete)`** — `{attr}_id INTEGER` column; `instance.author` lazy-fetches the related object with per-instance cache.
- **`OneToOneField(to, on_delete)`** — same as ForeignKey with `UNIQUE` constraint.
- **`ManyToManyField(to)`** — no column on own table; auto-generates junction table in migrations. `instance.tags.all()`, `.add()`, `.remove()` + async variants.
- **`ManyToManyField(to, through=Model)`** — use an explicit through model for extra columns on the junction.
- **`on_delete` constants:** `CASCADE`, `SET_NULL`, `PROTECT`, `RESTRICT`, `DO_NOTHING`.
- `PROTECT` / `RESTRICT` enforced at ORM level — raises **`ProtectedError`** before any SQL if dependant rows exist.
- **`related_name`** — auto-registered on parent model as a `ReverseFKDescriptor`; `post.comments.all()` / `await post.comments.aall()`.

---

### Model API

- **`ModelMeta`** — metaclass that auto-builds `_fields`, `_relations`, `_m2m`, `_pk_col`, `_MODEL_REGISTRY`.
- **`Meta`** — inner class with `db_table`, `ordering`, `constraints` (`CheckConstraint`, `UniqueConstraint`).
- **`CheckConstraint(check, name)`** — `Q` object or raw SQL string; compiles to `CONSTRAINT "n" CHECK (...)`.
- **`UniqueConstraint(fields, name, condition=None)`** — optional `condition=Q(...)` produces a partial `UNIQUE ... WHERE` index.
- **`Model.save()`** / **`Model.asave()`** — INSERT or UPDATE based on whether pk is set; fires `pre_save` / `post_save` signals.
- **`Model.delete()`** / **`Model.adelete()`** — fires `pre_delete` / `post_delete` signals; enforces `PROTECT`/`RESTRICT`.
- `DoesNotExist` and `MultipleObjectsReturned` exceptions auto-created per model.

---

### QuerySet API

Full Django-like chainable API via `Model.objects`:

**Read:**
`all()`, `filter(*Q, **kwargs)`, `exclude(*Q, **kwargs)`, `get(**kwargs)`, `first()`, `last()`, `count()`, `exists()`

**Retrieval modifiers:**
`order_by(*fields)`, `limit(n)`, `offset(n)`, `distinct()`, `values(*fields)`, `values_list(*fields, flat=False)`

**Joins:**
`select_related(*fields)` — JOIN FK/O2O in one query, auto-attach related instances.
`prefetch_related(*fields)` — batch-fetch M2M after main query, attach to instances.

**Write:**
`create(**kwargs)`, `update(**kwargs)`, `delete()`, `bulk_create(instances)`

**Aggregation:**
`aggregate(**kwargs)` → dict, `annotate(**kwargs)` → per-row computed columns

**Raw:**
`raw(sql, params)` — run raw SQL, return model instances.

**Full async variants:**
`alist()`, `aget()`, `afirst()`, `alast()`, `acreate()`, `acount()`, `aexists()`, `aupdate()`, `adelete()`, `aaggregate()`, `araw()`

---

### Lookup Expressions (20 total)

`exact`, `ne`, `gt`, `gte`, `lt`, `lte`, `contains`, `icontains`, `startswith`, `istartswith`, `endswith`, `iendswith`, `regex`, `iregex`, `in`, `isnull`, `range`, `iexact`, and bare equality.

---

### Q Objects

`Q(field=value)` — combine with `|` (OR), `&` (AND), negate with `~`:

```python
filter(Q(status="active") | ~Q(role="guest"))
```

---

### F Objects

Column-to-column comparisons and arithmetic:

```python
filter(stock__gt=F("reserved"))
update(views=F("views") + 1)
```

---

### Aggregate Functions

`Count`, `Sum`, `Avg`, `Max`, `Min` — all support `distinct=True`.

---

### Advanced Expressions

- **`Window(expr, partition_by, order_by, frame)`** — full `OVER (...)` support.
  - Pure window functions: `RowNumber`, `Rank`, `DenseRank`, `PercentRank`, `CumeDist`, `Ntile(n)`, `Lag`, `Lead`, `FirstValue`, `LastValue`, `NthValue`.
  - Any aggregate (`Sum`, `Count`, `Avg`, …) usable inside `Window()`.
- **`Coalesce(*fields)`** — `COALESCE(col1, col2, ...)`.
- **`Value(literal)`** — embed a literal SQL parameter inside expressions.
- **`Subquery(queryset)`** — correlated subquery in `filter()` or `annotate()`.
- **`OuterRef(field)`** — reference outer query column inside a `Subquery`.
- **`Case(*When, default)`** — `CASE WHEN ... THEN ... ELSE ... END`.
- **`When(condition, then)`** — individual `WHEN ... THEN ...` clause.
- **`Cast(field, output_field)`** — `CAST(col AS type)`.

---

### Multi-table Inheritance (MTI)

- A child model inheriting a non-`object` `Model` subclass is automatically treated as MTI.
- `ModelMeta` detects the hierarchy, adds a `{parent_table}_ptr_id` FK column to the child table.
- `save()` / `asave()` inserts into the parent first, then the child.
- Queries auto-inject `INNER JOIN parent ON child.ptr_col = parent.id`.
- `delete()` / `adelete()` targets the parent; `ON DELETE CASCADE` removes the child row.

---

### GenericForeignKey

- `GenericForeignKey(ct_field, fk_field)` — pure Python descriptor; no column or DDL generated.
- `__set__`: stores `"module.ClassName"` in `ct_field` and pk in `fk_field`.
- `__get__`: resolves from `_MODEL_REGISTRY`, lazy-fetches via `objects.get()`, caches per-instance.
- Async resolution supported via `await instance.resolve_gfk(field)`.

---

### File Fields and Storage

- **`FileField(upload_to, max_length, storage)`** — saves uploaded files; stores path in DB.
- **`ImageField`** — extends `FileField`; validates image format via Pillow before saving.
- **`FieldFile`** — proxy returned when reading the field: `.name`, `.url`, `.open()`, `.read()`, `.delete()`.
- Accepts `UploadFile` (FastAPI), file-like objects (`BytesIO`), or raw `bytes` on assignment.
- **`Storage` ABC** — pluggable backend (`read`, `save`, `delete`, `exists`, `url`).
- **`FileSystemStorage`** — default; reads `MEDIA_ROOT` / `MEDIA_URL` from `setraft.py`.
- **`default_storage`** — lazy singleton; resolved once on first use.

---

### Serializers

- **`Serializer`** — base class; declare `SerializerField` instances on the class body.
  - `is_valid()` / `is_valid_async()` — validates input data; populates `validated_data` or `errors`.
  - `save()` / `asave()` — calls `create()` or `update()` depending on whether `instance` is set.
  - `create()` / `acreate()`, `update()` / `aupdate()` — override for custom write logic.
  - `to_representation()` — override for custom output shape.
  - `to_internal_value()` — override for custom input parsing.
  - `validate_<field>()` per-field hooks and `validate()` cross-field hook.
  - `many=True` — wrap in a list serializer.
  - `partial=True` — skip required-field validation for PATCH.
- **`ModelSerializer`** — auto-builds fields from a `Model` class via `Meta.fields`, `Meta.exclude`, `Meta.read_only_fields`.
  - Handles `FileField` / `ImageField` — accepts upload objects on input; returns URL on output.
  - `_apply_to_instance()` — maps validated data back onto model attributes for update.

---

### Transactions

- **`atomic()`** — async context manager; all statements share one connection; commits on exit, rolls back on any exception.
- **`atomic_sync()`** — synchronous equivalent.
- Nested calls automatically use PostgreSQL `SAVEPOINT`.
- **`TransactionHandle`** — yielded as `tx`; `tx.set_rollback(True)` forces rollback without raising (dry-run pattern); `tx.get_rollback()` reads current flag.

---

### Connection Pooling

- **`setup_async_pool(min_size, max_size)`** / **`teardown_async_pool()`** — asyncpg pool.
- **`setup_sync_pool(min_conn, max_conn)`** / **`teardown_sync_pool()`** — psycopg2 `ThreadedConnectionPool`.
- **`pool_stats()`** — returns size / free / min / max for both pools.

---

### Signals

- Built-in signals: `pre_save`, `post_save`, `pre_delete`, `post_delete`.
- **`Signal`** class — `connect(receiver)`, `disconnect(receiver)`, `send(sender, **kwargs)` (sync), `asend(sender, **kwargs)` (async).
- Receivers can be plain functions or `async def` coroutines.
- Signals fire automatically from `save()` / `asave()` / `delete()` / `adelete()`.
- Custom signals: `my_signal = Signal(); my_signal.connect(handler)`.

---

### Migrations

- **`raftsql generate`** (`makemigrations`) — diffs model state vs. migration history; emits versioned migration files next to each app's `models.py`.
  - Detects: `CreateTable`, `DropTable`, `AddColumn`, `DropColumn`, `RenameField`, `AlterField`, `AddConstraint`, `DropConstraint`, `CreateIndex`, `DropIndex`.
  - Django-accurate rename detection (ask prompt / `--non-interactive` flag).
  - `--dry-run` — print SQL without writing files.
  - `--check` — exit with non-zero if migrations would be generated.
  - `--app` — target a single app.
- **`raftsql apply`** (`migrate`) — applies pending migrations in dependency order.
  - `--plan` — show what will be applied without running.
  - `--fake` — mark migrations as applied without executing SQL.
  - `--fake-initial` — skip first migration if table already exists.
  - `--zero <app_dir>` — unapply all migrations for an app.
- **`raftsql status`** (`showmigrations`) — list applied / unapplied migrations per app.
- **`raftsql sql <app> <migration>`** (`sqlmigrate`) — print SQL for a specific migration.
- **`raftsql squash <app> <from> <to>`** (`squashmigrations`) — squash a range of migrations into one.
- **`raftsql flush`** — drop all tables and re-run all migrations (development reset).
- Per-app migration directories — no global migrations folder; each app owns its own `migrations/`.
- Auto-detects apps without explicit registration.

---

### Schema Introspection

- **`raftsql inspect`** (`inspectdb`) — queries `information_schema.columns`, `pg_index`, and FK constraints; prints ready-to-use `Model` class definitions to stdout.
  - `raftsql inspect` — all public tables.
  - `raftsql inspect TABLE [TABLE ...]` — specific tables.
  - Auto-detects PKs (`AutoField`), FK columns (`ForeignKey`), nullability, `max_length`.

---

### CLI Reference

| Command | Description |
|---|---|
| `raftsql generate` | Generate migration files from model changes |
| `raftsql apply` | Apply pending migrations to the database |
| `raftsql status` | Show applied / unapplied migrations |
| `raftsql sql <app> <migration>` | Print SQL for a migration |
| `raftsql squash <app> <from> <to>` | Squash a range into one migration |
| `raftsql flush` | Drop all tables and re-apply all migrations |
| `raftsql inspect [TABLE ...]` | Introspect DB and generate model code |

---

### Exceptions

| Exception | When raised |
|---|---|
| `Model.DoesNotExist` | `get()` / `aget()` returns no rows |
| `Model.MultipleObjectsReturned` | `get()` / `aget()` returns more than one row |
| `ProtectedError` | Deleting an instance that is referenced by a `PROTECT`/`RESTRICT` FK |
| `ValueError` | Invalid image file assigned to `ImageField` |
| `AssertionError` | Serializer `.save()` called without calling `is_valid()` first |

---
