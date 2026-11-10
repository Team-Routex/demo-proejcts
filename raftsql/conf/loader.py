"""
Finds and loads the user's setraft.py settings file.

Search order:
  1. Upward from cwd (cwd → parent → grandparent → ...)
  2. Downward into cwd subdirectories (max depth 4)

Skips: env/, venv/, .venv/, __pycache__/, node_modules/, .git/, dist/, build/
"""
import importlib.util
import os
import sys
from typing import Any, Optional

_SKIP_DIRS = {
    "env", "venv", ".venv", "ENV", "VENV",
    "__pycache__", "node_modules", ".git",
    "dist", "build", "site-packages",
    ".mypy_cache", ".pytest_cache",
}

_SETRAFT_FILE = "setraft.py"


def find_setraft_path() -> Optional[str]:
    """
    Search for setraft.py — first upward from cwd, then downward into subdirs.
    Returns absolute path if found, else None.
    """
    cwd = os.getcwd()

    # 1. Search upward
    current = cwd
    while True:
        candidate = os.path.join(current, _SETRAFT_FILE)
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    # 2. Search downward (max depth 4 to avoid scanning the whole disk)
    for root, dirs, files in os.walk(cwd):
        dirs[:] = [
            d for d in dirs
            if d not in _SKIP_DIRS and not d.startswith(".")
        ]
        depth = root[len(cwd):].count(os.sep)
        if depth > 4:
            dirs.clear()
            continue
        if _SETRAFT_FILE in files:
            return os.path.join(root, _SETRAFT_FILE)

    return None


def load_setraft(path: str) -> Any:
    """
    Dynamically load setraft.py as a module and return it.
    The directory containing setraft.py is added to sys.path so that
    any imports inside setraft.py (e.g. dotenv, os) resolve correctly.
    """
    setraft_dir = os.path.dirname(os.path.abspath(path))
    if setraft_dir not in sys.path:
        sys.path.insert(0, setraft_dir)

    spec = importlib.util.spec_from_file_location("setraft", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load setraft.py from: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def get_settings() -> Any:
    """
    Find and load setraft.py. Raises RuntimeError with a helpful message if not found.
    """
    path = find_setraft_path()
    if path is None:
        raise RuntimeError(
            "setraft.py not found.\n\n"
            "Create a setraft.py in your project root:\n\n"
            "    import os\n"
            "    from dotenv import load_dotenv\n\n"
            "    load_dotenv()\n\n"
            "    DATABASE = {\n"
            '        "ENGINE":   "postgresql",\n'
            '        "HOST":     os.getenv("DB_HOST", "localhost"),\n'
            '        "PORT":     int(os.getenv("DB_PORT", 5432)),\n'
            '        "USER":     os.getenv("DB_USER", "postgres"),\n'
            '        "PASSWORD": os.getenv("DB_PASSWORD", ""),\n'
            '        "NAME":     os.getenv("DB_NAME", "mydb"),\n'
            "    }\n"
        )
    return load_setraft(path)


def get_project_root() -> str:
    """
    Return the project root directory.
    
    If setraft.py defines BASE_DIR, use that (converted to string).
    Otherwise, fall back to the directory containing setraft.py.
    
    Raises RuntimeError if setraft.py cannot be found.
    """
    path = find_setraft_path()
    if path is None:
        raise RuntimeError(
            "setraft.py not found.\n\n"
            "Create a setraft.py in your project with:\n\n"
            "    from pathlib import Path\n"
            "    BASE_DIR = Path(__file__).resolve().parent\n\n"
            "    DATABASE = {...}"
        )
    
    settings = load_setraft(path)
    base_dir = getattr(settings, "BASE_DIR", None)
    
    if base_dir is not None:
        # BASE_DIR might be a Path object or string - convert to string
        return str(base_dir)
    else:
        # Fall back to directory containing setraft.py
        return os.path.dirname(os.path.abspath(path))


def get_db_config() -> dict:
    """Return the DATABASE dict from setraft.py with validated keys (legacy single-db helper)."""
    settings = get_settings()
    db = getattr(settings, "DATABASE", None)
    if not db or not isinstance(db, dict):
        raise RuntimeError(
            "setraft.py must define a DATABASE dict, e.g.:\n"
            '    DATABASE = {"ENGINE": "postgresql", "HOST": "localhost", ...}'
        )
    required = {"ENGINE", "HOST", "PORT", "USER", "PASSWORD", "NAME"}
    missing = required - set(db.keys())
    if missing:
        raise RuntimeError(f"DATABASE in setraft.py is missing keys: {missing}")
    return db


def get_all_db_configs() -> dict:
    """
    Return {alias: db_dict} for all configured databases.

    Supports two styles in setraft.py:

    **Multi-database (new):**

        DATABASES = {
            "default":   {"ENGINE": "postgresql", "HOST": "localhost", ...},
            "analytics": {"ENGINE": "postgresql", "HOST": "pg-analytics", ...},
        }

    **Single database (legacy — backward compatible):**

        DATABASE = {"ENGINE": "postgresql", "HOST": "localhost", ...}

    The legacy form is transparently mapped to ``{"default": DATABASE}``.
    Raises ``RuntimeError`` if neither key is found, or if required keys are missing.
    """
    settings = get_settings()
    required = {"ENGINE", "HOST", "PORT", "USER", "PASSWORD", "NAME"}

    # --- new multi-db style: DATABASES = {"default": {...}, "analytics": {...}} ---
    databases = getattr(settings, "DATABASES", None)
    if databases and isinstance(databases, dict):
        for alias, db in databases.items():
            if not isinstance(db, dict):
                raise RuntimeError(
                    f"DATABASES['{alias}'] in setraft.py must be a dict."
                )
            missing = required - set(db.keys())
            if missing:
                raise RuntimeError(
                    f"DATABASES['{alias}'] in setraft.py is missing keys: {missing}"
                )
        return dict(databases)

    # --- legacy single-db style: DATABASE = {...} → alias "default" ---
    db = get_db_config()
    return {"default": db}


def get_media_config() -> dict:
    """Return MEDIA_ROOT and MEDIA_URL from setraft.py (with safe defaults)."""
    settings = get_settings()
    return {
        "MEDIA_ROOT": getattr(settings, "MEDIA_ROOT", "media"),
        "MEDIA_URL":  getattr(settings, "MEDIA_URL",  "/media/"),
    }


def get_migrations_dir() -> str:
    """Return MIGRATIONS_DIR from setraft.py (default: 'migrations')."""
    settings = get_settings()
    return getattr(settings, "MIGRATIONS_DIR", "migrations")


def get_database_routers() -> list:
    """
    Return router instances declared as ``DATABASE_ROUTERS`` in setraft.py
    (same entry point as Django).

    Each item may be an instance or a class (instantiated with no arguments).

        class LogRouter(BaseDatabaseRouter):
            ...

        DATABASE_ROUTERS = [LogRouter()]
    """
    settings = get_settings()
    raw = getattr(settings, "DATABASE_ROUTERS", None)
    if not raw:
        return []
    if not isinstance(raw, (list, tuple)):
        raise RuntimeError(
            "DATABASE_ROUTERS in setraft.py must be a list, "
            'e.g. DATABASE_ROUTERS = [MyRouter()]'
        )
    result = []
    for entry in raw:
        if isinstance(entry, type):
            result.append(entry())
        else:
            result.append(entry)
    return result


def get_guides() -> list:
    """
    Return the list of Guide instances declared as ``GUIDES`` in setraft.py.

    Each entry may be:
      * An already-instantiated ``Guide`` instance  (recommended)
      * A ``Guide`` subclass — it will be instantiated with no arguments

    Returns an empty list if ``GUIDES`` is not defined.

    Example setraft.py::

        from raftsql import Guide

        class MyGuide(Guide):
            def read(self, model, **hints):
                return "replica"
            def write(self, model, **hints):
                return "default"

        GUIDES = [MyGuide()]
    """
    settings = get_settings()
    guides_raw = getattr(settings, "GUIDES", None)
    if not guides_raw:
        return []

    if not isinstance(guides_raw, (list, tuple)):
        raise RuntimeError(
            "GUIDES in setraft.py must be a list of Guide instances, e.g.:\n"
            "    GUIDES = [MyGuide()]"
        )

    from raftsql.routing import Guide
    result = []
    for i, entry in enumerate(guides_raw):
        if isinstance(entry, Guide):
            result.append(entry)
        elif isinstance(entry, type) and issubclass(entry, Guide):
            result.append(entry())   # instantiate class with no args
        else:
            raise RuntimeError(
                f"GUIDES[{i}] in setraft.py is not a Guide instance or subclass. "
                f"Got: {type(entry).__name__}"
            )
    return result


def get_apps() -> Optional[list]:
    """
    Return explicit app directory paths when APPS is defined in setraft.py,
    or None to signal auto-detection via the models.py convention.

    APPS in setraft.py uses dot-notation module paths relative to the project root:
        APPS = ["apps.inventory", "apps.blogs"]

    Each entry is resolved to an absolute directory path before being returned.
    """
    path = find_setraft_path()
    if path is None:
        return None
    settings = load_setraft(path)
    apps = getattr(settings, "APPS", None)
    if apps is None:
        return None  # auto-detect mode

    project_root = get_project_root()
    result = []
    for app in apps:
        # "apps.inventory" → "<project_root>/apps/inventory"
        app_dir = os.path.join(project_root, app.replace(".", os.sep))
        result.append(os.path.abspath(app_dir))
    return result
