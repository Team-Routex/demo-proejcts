# RaftSQL Codebase Guide (Beginner‑Friendly)

**Who this is for:** Teammates who are new to RaftSQL **or** new to reading ORMs in general. This document explains **ideas first**, then **where the code lives**, with **examples** and **“you can answer this question after reading…”** checkpoints.

**How to read it**

1. **First time:** Read **top to bottom** (about one focused session).
2. **Later:** Use the [Table of contents](#table-of-contents), [Module map](#module-map-quick-lookup-table), or [FAQ](#faq-where-do-i-find-answers).

Keep **README.md** open for **public API**; this file is **how the internals work**.

---

## Table of contents

1. [Tiny glossary](#1-tiny-glossary-read-this-first-if-you-are-new-to-orms)
2. [Big picture analogy](#2-big-picture-one-analogy)
3. [Folders and what problem each solves](#3-folders-and-what-problem-each-solves)
4. [Tutorial path through the source](#4-tutorial-path-through-the-source-step-by-step)
   - [4.1 Application startup](#41-application-startup-entry-point)
   - [4.2 Loading settings](#42-loading-settings-users-setraftpy)
   - [4.3 Connection to PostgreSQL](#43-connection-to-postgresql)
   - [4.4 Defining a Model](#44-defining-a-model-classes-and-metaclass)
   - [4.5 Running a query](#45-running-a-query-from-modelobjects-to-rows)
   - [4.6 Choosing which database](#46-chosing-which-database-multi-database)
   - [4.7 Saving and relations](#47-saving-rows-and-loading-relations)
   - [4.8 Migrations](#48-migrations-generate-and-apply)
   - [4.9 Command line (`raftsql`)](#49-command-line-raftsql-cli)
5. [End-to-end example with file names](#5-one-full-example-written-on-the-wall)
6. [Module map (quick lookup table)](#module-map-quick-lookup-table)
7. [FAQ](#faq-where-do-i-find-answers)
8. [Contributing cheatsheet](#contributing-cheatsheet-what-to-touch)
9. [Debugging playbook](#debugging-playbook)

---

## 1. Tiny glossary (read this first if you are new to ORMs)

| Term | Plain meaning |
|------|----------------|
| **ORM** | A library that maps **Python classes** ↔ **database tables** so you use objects instead of raw SQL everywhere. RaftSQL **still builds SQL internally** — you rarely write `SELECT …` by hand for normal CRUD. |
| **Model** | A Python **`class`** that stands for **one table** (e.g. `Post` ↔ table `posts`). |
| **`Meta` inner class** | Extra instructions on **`class Meta:`** (`db_table`, `app_label`, `db_alias`, …). Not database columns — **configuration**. |
| **Field** | A Python attribute describing **one column** (`CharField`, `IntegerField`, `ForeignKey`, …). |
| **QuerySet** | A **lazy** object describing a query (**filters, order**, …). **Python runs zero SQL** until you call `.all()`, `.first()`, `.get()`, etc. |
| **Manager** | **`Model.objects`** — factory that builds **empty QuerySets** for that model. |
| **`setraft.py`** | The **project’s settings file**. RaftSQL finds it automatically. Holds `DATABASE` / `DATABASES`, pools, routers, guides, etc. |
| **Config (`Config`)** | One **immutable bundle** holding host, port, user, password, database **name**, and **alias** (`"default"`, `"analytics"`, …). |
| **Backend** | Thin layer around **PostgreSQL drivers** (`psycopg2`, `asyncpg`): quote identifiers, run SQL. |
| **Migration** | A **numbered Python file** that lists **operations** (“create table”, “add column”, …). Applying runs those operations against Postgres. |

---

## 2. Big picture: one analogy

Think of RaftSQL like a **restaurant**:

| Real life | RaftSQL piece |
|-----------|----------------|
| Guest menu (what dishes exist) | Your **Model classes** (`Post`, `User`) |
| Order ticket (“burger, no pickles”) | **QuerySet** (filters + ordering) |
| Kitchen recipe → actual cooking | **`sql/`** builders turn the ticket into **`SELECT …`** |
| Stove / gas line | **`db/`** opens a connection and runs SQL |
| “Use East kitchen vs West kitchen” | **`routing`** + **`Meta.db_*`** chooses **which `Config`/alias** |
| Updating the menu layout (tables) | **Migrations** (`migrations/` + CLI) |

Everything in the codebase supports one of those steps.

---

## 3. Folders and what problem each solves

```
raftsql/
├── __init__.py          # Starts the library: setup(), globals, exports
├── models.py            # Re-exports: from raftsql import models
├── routing.py           # “Which DATABASE alias?” (Meta, routers, guides)
├── conf/                # Find setraft.py, build Config dicts
├── db/                  # Talk to Postgres: conn, txn, pools, backends
├── orm/                 # Models, fields, QuerySet/Manager — ORM brain
├── sql/                 # Build SQL strings + WHERE from Q objects
├── migrations/          # Diff models, write migration files, run apply
├── cli.py               # The `raftsql` terminal command
├── serializers/       # Serialize/deserialize instances (often API-facing)
├── storage/             # Where FileField/ImageField bytes live
├── management/inspectdb.py
└── utils/discovery.py   # Find Model subclasses across the disk
```

---

## 4. Tutorial path through the source (step by step)

Read these **in order** the first time. Each subsection has:

- **Idea**
- **User-facing use case** (why the feature exists)
- **Where to read**
- **Mini checkpoint** (quiz yourself)

---

### 4.1 Application startup (`__init__.py`)

**Idea.** Before RaftSQL runs any query, it must:

1. Read **database settings**.
2. Build **`Config`** objects (one per **alias**, e.g. `"default"` + `"analytics"`).
3. (Optional) Register **DATABASE_ROUTERS** and **Guides**.

**Use case.** In the user app:

```python
import raftsql
raftsql.setup()
```

Without **`setup()`**, most ORM paths raise **“call setup() first”**.

**Where to read**

- **`raftsql/__init__.py`**
  - **`setup()`** — loads **`get_all_db_configs()`**, fills **`_global_configs`**, attaches routers/guides.
  - **`get_db("alias")`** — returns **`Config`** for debugging or manual connections.
  - **`_global_config`** — legacy shortcut to **`default`** **`Config`**.
  - **Bottom of file:** re‑exports (**`Model`**, **`atomic`**, **fields**) — convenience only.

**Important detail.** **`setup()` is idempotent:** if **`_global_configs`** is already non‑empty it **returns immediately**. That avoids double setup with **reloaders** (uvicorn `--reload`). If you tweak **`setraft.py`** and expect a rerun, restart the **process**.

**Checkpoint — you should now answer**

- Where does RaftSQL store all DB configs after setup? (**`_global_configs` in `__init__.py`**)
- What function must the user call first in a running app? (**`raftsql.setup()`**)

---

### 4.2 Loading settings (`conf/`: user `setraft.py`)

**Idea.** RaftSQL doesn’t bundle connection strings inside the repo. Each **project** has **`setraft.py`** beside the app — like Django’s **`settings.py`**.

**Use case.**

- **`DATABASE = { … }`** → treated as **`{"default": …}`**.
- **`DATABASES = {"default": …, "analytics": …}`** → multi‑database.

The loader walks **up** from Current Working Directory, then lightly **down** into subdirs, hunting **`setraft.py`**.

**Where to read**

- **`conf/loader.py`**
  - **`find_setraft_path()`** — discovery rules (`_SKIP_DIRS` avoids `venv`, `.git`, …).
  - **`load_setraft()`** — loads file as Python module, adds folder to **`sys.path`** so imports inside **`setraft.py`** work.
  - **`get_all_db_configs()`** — normalises **`DATABASE` vs `DATABASES`**.
  - **`get_media_config()`**, **`get_apps()`**, **`get_database_routers()`**, **`get_guides()`**.
- **`conf/config.py`**
  - **`Config`** dataclass — **`host`**, **`port`**, **`user`**, **`password`**, **`dbname`**, **`alias`**, **`media_root`**.

**Tiny example.**

```python
# In setraft.py (user code, not RaftSQL internals)
DATABASES = {
    "default": {
        "ENGINE": "postgresql",
        "HOST": "localhost",
        "PORT": 5432,
        "USER": "postgres",
        "PASSWORD": "",
        "NAME": "myapp",
    }
}
```

**Checkpoint**

- Which file parses **`DATABASES`**? (**`conf/loader.py` → `get_all_db_configs`**)
- What object holds **`host`/password** for one alias after setup? (**`conf.config.Config`**)

---

### 4.3 Connection to PostgreSQL (`db/`)

**Idea.** **SQLAlchemy‑style abstraction here is minimal:** RaftSQL chooses **sync** (**psycopg2**) vs **async** (**asyncpg**) wrappers.

**Use case.**

- **`with Connection(cfg) as conn:`** runs sync SQL.
- **`async with AsyncConnection(cfg) as conn:`** runs async SQL.
- **`atomic()` / `atomic_sync()`** bracket multiple statements — same connection, COMMIT / ROLLBACK.

**Where to read**

- **`db/connection.py`** — sync wrapper.
- **`db/async_connection.py`** — thin façade to Postgres async stack.
- **`db/transaction.py`** — **`ContextVar`** keyed by **`using=`** alias.
- **`db/pool.py`** — **one pool per alias** when you call **`setup_async_pool(using="…")`**.

**Backend chain (PostgreSQL)**

- **`db/backends/registry.py`** — **`get_backend("postgresql")`**.
- **`db/backends/postgresql/backend.py`** — quotes SQL identifiers safely; handles **`%s`** (psycopg2) vs **`$n`** (asyncpg) placeholders.
- **`db/backends/postgresql/connection.py`** — psycopg2 execute.
- **`db/backends/postgresql/async_connection.py`** — asyncpg execute.

**Checkpoint**

- If you wanted **SQLite**, what pattern would you follow? (Add **`db/backends/sqlite/`**, register it in **`registry.py`** — not included in RaftSQL today.)

---

### 4.4 Defining a Model (classes and metaclass)

**Idea.** When Python **defines** **`class Post(Model):`** the **`ModelMeta` metaclass** runs **once**. It collects fields, derives table name, builds **`Post._meta`**, attaches **`objects`**.

**Use case.**

```python
from raftsql import models

class Post(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100)

    class Meta:
        db_table = "posts"
```

After import **`Post`** has:

- **`Post._fields`** → list like **`["id", "title"]`**
- **`Post._meta.db_table`** → **`"posts"`**
- **`Post._meta.app_label`** → inferred or explicit (migrations routing)
- **`Post.objects`** → **`Manager`** that returns **`QuerySet(Post)`**

**Where to read**

- **`orm/model.py`**
  - **`ModelMeta.__new__`** — the **main blueprint** scanner.
  - **`_MODEL_REGISTRY`** — append every concrete model (**migrations** + reverse relations).
  - **`get_registered_models_for_app_label()`** — who shares an **`app_label`**.
  - **`Model.save` / `asave` / delete** — INSERT/UPDATE/DELETE paths (**not** QuerySet‑only).
- **`orm/options.py`**
  - **`Options`** reads **`Meta`**: **`db_alias`**, **`db_for_*`**, **`for_read`/`for_write`**, **`allow_relation`**, **`allow_migrate`**, …
  - **`routed_database_alias(operation)`** — **read vs write** alias from Meta.
- **`orm/fields.py`**
  - Field classes (**SQL snippets**, FK column naming, validators).

**Checkpoint**

- When is **`Post._relations`** populated? (**At class creation in **`ModelMeta`**, scanning **`ForeignKey`**.)

---

### 4.5 Running a query (from `Model.objects` to rows)

**Idea.**

1. **`Post.objects`** → blank **`QuerySet`**.
2. **`.filter(…)`** clones and appends **`Q`** nodes (**AND**‑like).
3. **`.all()`** **executes**: resolve **Config**, build SQL, run, hydrate **`Post`** rows.

Use case: **`Post.objects.filter(published=True).order_by("-id").limit(10).all()`**

**Where to read (in this order)**

1. **`orm/manager.py`**
   - **`_get_config(alias, model=…, operation="read"|"write")`** — routing entry.
   - **`QuerySet._clone`**, **`filter`**, **`_cfg_read`**, **`all`/`alist`/`create`/…** execution.
2. **`routing.py`** — **`resolve_default_database_alias(model_cls, …)`**.
3. **`orm/q.py`**, **`orm/f.py`** — boolean trees, references to columns.
4. **`sql/builder.py`** — **`build_select`**, **`build_insert`**, **`build_update`**, **`build_delete`**.
5. **`sql/where.py`** — converts **`filter(title__icontains="hello")`** into **`ILIKE`** fragment + **`%`** params.

**Lazy vs eager**

Until **`.all()` / `.alist()` / `.get()`**, the QuerySet is **only Python state** (**no Postgres round-trip**).

**Checkpoint**

- Where does **`ILIKE`** for **`__icontains`** get decided? (**`sql/where.py`**)
- Which function picks **analytics vs default** DB for a SELECT? (**`routing.resolve_default_database_alias`** → **`Options.routed_database_alias`** first.)

---

### 4.6 Choosing which database (multi-database)

**Idea.** Many apps hit **multiple Postgres clusters**. RaftSQL assigns each a **string alias** (`"default"`, `"replica"`). Resolution order when **not** using **`.using("alias")`**:

1. **`class Meta`** on the **model** (primary documented path — **`db_alias`**, halves, **`for_read`/`for_write`**).
2. Optional **`DATABASE_ROUTERS`** (**Django‑style**, class list in **`setraft.py`**).
3. Optional **Guides** (`GUIDES` / **`add_guide()`**).
4. Fallback starter alias (**usually `"default"`**).

Explicit **`.using("analytics")`** on a QuerySet **skips everything** above.

**Where to read**

- **`routing.py`** — **`resolve_default_database_alias`**, **`allow_relation_allowed`**, **`allow_migrate_allowed`**.
- **`orm/options.py`** — Meta fields wired into routing.
- **`orm/manager.py`** — **`QuerySet.using()`** sets **`_using_explicit`** so routers are bypassed.

**Checkpoint**

- How do you force one query onto replica only? (**`.using("replica")`** or **`Meta.db_for_read`** / routers.)

---

### 4.7 Saving rows and loading relations

**Idea.** Some operations work on **one row** (instance methods); others work on **many rows** (QuerySet methods). Relations use **descriptor** objects so **`post.author`** can trigger another SELECT.

**Use case.**

- **`post.save()`** — insert or update that row only.
- **`Post.objects.filter(x=1).delete()`** — delete every matching row.
- **`post.author`** — may load **`User`** from the DB on first access (**lazy**).

Bullets tied to files:

- **`save()` / `delete()`** on an **instance** live in **`orm/model.py`**.
- **`QuerySet.delete()`**, **`QuerySet.update()`**, **`QuerySet.create()`** live in **`orm/manager.py`**.
- **Foreign keys**: loading **`post.author`** may **lazy-fetch** related row (**read routing** applies to **`Author`** class).
- **`_assert_foreign_object_relations_allowed`** (`manager.py`) validates relations before INSERT/UPDATE paths that might cross databases.

**Where to read**

- **`orm/model.py`** — **`save`**, **`delete`**, **MTI** pointer tables.
- **`orm/manager.py`** — **`_assert_foreign_object_relations_allowed`**.
- **`orm/relations.py`** — accessors for reverse FK, M2M.

**Checkpoint**

- Where does the ORM enforce **PROTECT / RESTRICT** before the database sees a delete? (See **`ProtectedError`** and related logic in **`orm/model.py`** and **`orm/fields.py`**.)

---

### 4.8 Migrations (generate and apply)

**Idea.**

- **`generate` (CLI)** diffs Python models ↔ last recorded **state**.
- Writes **`000n_name.py`** with **`operations=[CreateTable(...), …]`**.
- **`apply`** walks **`migrations/`** directories, sorts by **`dependencies`** (e.g. `[("posts", "0001_initial")]`), runs SQL for each operation, records the migration key in **`raftsql_migrations`**.

**Use case.**

```bash
raftsql generate    # makemigrations
raftsql apply        # migrate
```

**Where to read**

- **`cli.py`** — **`cmd_makemigrations`**, **`cmd_migrate`**.
- **`utils/discovery.py`** — group models **per app folder**.
- **`migrations/makemigrations.py`** — **`makemigrations_per_app`**, **`_diff_models`**.
- **`migrations/writer.py`** — writes Python file (**`dependencies`**, **`app_label`** line, **`model_state`** snapshot).
- **`migrations/state.py`** / **`schema.py`** — reconstruct past schema + convert models to DDL.
- **`migrations/runner.py`** — **`migrate_all_apps`**, **`resolve_migration_app_label`**, **`allow_migrate_allowed`** skips.
- **`migrations/operations.py`** — dataclasses (**`CreateTable`**, **`AddColumn`**, …).

**Checkpoint**

- What Python structure is executed at apply-time? (**`operations`** list instances in migration module.**)

---

### 4.9 Command-line (`cli.py`)

**Idea.** The **`raftsql`** console script is **`cli.py`** with **argparse** subcommands. It:

1. Finds project root (**`setraft.py`**).
2. Calls **`raftsql.setup()`** once (**`_ensure_setup`**).
3. Dispatches (**generate**, **apply**, **inspect**, **flush**, …).

**Where to read**

- **`cli.py` top** — **`_load_project()`**, **`_ensure_setup()`**.
- **`if __name__ == "__main__"`** guard at bottom.

**Checkpoint**

- Why **`sys.path.insert(0, os.getcwd())`? (So imports such as **`apps.posts.models`** work when the CLI’s working directory is the project root.)

---

## 5. One full example (written on the wall)

**Goal:** Tie every layer to **one user line**.

```python
post = Post.objects.filter(pk=3).aget()
```

| Step | Happens internally | Primary file |
|------|---------------------|---------------|
| 1 | **`Post`** class already inspected by **`ModelMeta`** | **`orm/model.py`** |
| **`Post.objects`** | **`Manager._qs()`** builds **`QuerySet(Post)`** | **`manager.py`** |
| **`.filter(pk=3)`** | Clone + append **`Q`** | **`manager.py`**, **`q.py`** |
| **`.aget()`** | **`_cfg_read()`** picks **Post** routing | **`manager.py` → `_get_config`** |
| Routing | **`resolve_default_database_alias(Post,"read","default")`** | **`routing.py`**, **`options.py`** |
| SQL | **`build_select` + WHERE** fragment for pk | **`sql/builder.py`**, **`where.py`** |
| DB | **`AsyncConnection`** with chosen **`Config`** | **`async_connection.py`** + Postgres backend |
| Row | **`Post.from_row(dict)`** | **`model.py`** |

You can annotate this table in margins while reading **`manager.QuerySet.aget`**.

---

## Module map (quick lookup table)

| Question | Likely answer |
|-----------|---------------|
| Where does setup live? | `__init__.py` **`setup`** |
| Where is `DATABASES` parsed? | `conf/loader.py` **`get_all_db_configs`** |
| Where is Postgres executed? | `db/backends/postgresql/` + `Connection` / `AsyncConnection` |
| Where is SQL text built? | `sql/builder.py`, `sql/where.py` |
| Where is QuerySet? | `orm/manager.py` |
| Where is Model metaclass? | `orm/model.py` **`ModelMeta`** |
| Where is Meta interpreted? | `orm/options.py` |
| Which DB alias? | `routing.py` **`resolve_default_database_alias`** |
| Migrations runner? | `migrations/runner.py` **`migrate_all_apps`** |
| CLI? | `cli.py` |

---

## FAQ (where do I find answers?)

**Q:** “Why does **`setup()` do nothing when I rerun it?”**  
**A:** Guard on **`_global_configs`** — intentional for reload servers. Restart process after config edits.

**Q:** “Where is **`ILIKE`** defined?”  
**A:** **`sql/where.py`** — lookup‑compiler.

**Q:** “Where does **JOIN for `select_related`** come from?”  
**A:** **`orm/manager.py`** — **`QuerySet` builds `joins` list for `build_select`**.

**Q:** “How does **`allow_migrate`** on Meta affect CLI?”  
**A:** **`migrations/runner.py`** calls **`routing.allow_migrate_allowed`** → reads **`Meta` on registered models**.

**Q:** What is **`models.py`** at the repo root?  
**A:** A barrel module for **`from raftsql import models`**. Implementations live in **`orm/`**.

---

## Contributing cheatsheet (what to touch)

| Change | Likely files |
|--------|----------------|
| New field type | `orm/fields.py`, maybe `migrations/schema.py` |
| New filter **`__`** lookup | `sql/where.py` |
| Annotation / aggregate | `orm/expressions.py` / `orm/aggregates.py`, **`manager`** SELECT assemble |
| New migration op | `operations.py`, `runner.py`, maybe `writer.py` |
| New CLI subcmd | `cli.py` |
| New dialect | entire `db/backends/<engine>/` |

**Rule:** **`grep`** the symbol (**`build_select`**) before deleting “unused” helpers.

---

## Debugging playbook

1. **Confirm config:** `python -c "import raftsql as r; r.setup(); print(r.get_db())"`
2. **Confirm alias routing:** **`from raftsql.routing import resolve_default_database_alias`**.
3. **Log SQL temporarily:** prints near **`execute()`** inside **`postgresql/connection`** layers.
4. **Migration dry mental model:** **`raftsql sql path/to/file.py`** prints DDL.

---

## After you finish reading

You should be able to explain clearly:

- **Lifecycle:** **`setup()`** → **`Config`** → **`Connection`** / **`AsyncConnection`** → build SQL (**`sql/`**) → run on PostgreSQL.
- **Layers:** **`orm/`** holds models and QuerySets; **`sql/`** emits SQL strings; **`db/`** talks to the driver.
- **Lazy queries:** a **`QuerySet`** does not touch the DB until you call an execution method (**`.all()`**, **`.aget()`**, **`.get()`**, …).
- **Migrations:** each file exposes an **`operations`** list that **`migrations/runner.py`** executes.

Continue with **`README.md`** (user API) and **`changelogs/CHANGELOG.md`** (release notes).
