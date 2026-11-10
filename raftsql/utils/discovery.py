"""
Auto-discovers all Model subclasses in the project by scanning Python files.
Used by the CLI (raftsql makemigrations) so no manual model listing is needed.

Per-app discovery
─────────────────
discover_models_by_app() returns {app_dir: [models]} grouped by the directory
that contains at least one Python file with Model subclasses (the "app root").

Convention: ANY .py file (not just models.py) that contains a RaftSQL Model
subclass is detected automatically.  Users can name their model files anything
they like — items.py, entities.py, schemas.py, hello.py, etc.

Explicit: pass app_dirs=["/abs/path/apps/inventory", ...] to restrict
scanning to specific directories (from APPS in setraft.py).
"""
import os
import sys
import importlib.util
from typing import Dict, List, Optional, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from ..orm.model import Model

_SKIP_DIRS = {
    "env", "venv", ".venv", "ENV", "VENV",
    "__pycache__", "node_modules", ".git",
    "dist", "build", "site-packages",
    ".mypy_cache", ".pytest_cache", "migrations",
}

_SKIP_FILES = {
    "setraft.py", "manage.py", "setup.py", "conf.py",
    "conftest.py", "wsgi.py", "asgi.py",
}


def discover_models(project_root: str) -> List[Type]:
    """
    Flat list of all Model subclasses found anywhere under project_root.
    Kept for backward compatibility (used internally by discover_models_by_app).
    """
    by_app = discover_models_by_app(project_root)
    seen, result = set(), []
    for models in by_app.values():
        for m in models:
            t = m._get_table()
            if t not in seen:
                seen.add(t)
                result.append(m)
    return result


def discover_models_by_app(
    project_root: str,
    app_dirs: Optional[List[str]] = None,
) -> Dict[str, List[Type]]:
    """
    Return {app_dir: [model_classes]} grouped by the directory that contains
    at least one Python file with valid Model subclasses.

    app_dirs=None  → auto-detect: every directory that has any .py file with
                     at least one valid Model subclass becomes an app.
    app_dirs=[...] → explicit list of absolute app directory paths (from APPS
                     in setraft.py).  All .py files inside those dirs are scanned.
    """
    from ..orm.model import Model

    dirs_to_scan = app_dirs if app_dirs is not None else _find_app_dirs(project_root)

    result: Dict[str, List[Type]] = {}
    for app_dir in dirs_to_scan:
        found: dict = {}
        for fname in sorted(os.listdir(app_dir)):
            if not fname.endswith(".py"):
                continue
            if fname in _SKIP_FILES or fname.startswith("__"):
                continue
            fpath = os.path.join(app_dir, fname)
            if os.path.isfile(fpath):
                _try_import_and_collect(fpath, project_root, Model, found)
        if found:
            result[os.path.abspath(app_dir)] = list(found.values())

    return result


def _find_app_dirs(project_root: str) -> List[str]:
    """
    Walk project_root and return every directory that contains at least one
    .py file (excluding skip files).  Skips env dirs, migrations dirs, etc.
    """
    app_dirs = []
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [
            d for d in dirs
            if d not in _SKIP_DIRS and not d.startswith(".")
        ]
        py_files = [
            f for f in files
            if f.endswith(".py") and f not in _SKIP_FILES and not f.startswith("__")
        ]
        if py_files:
            app_dirs.append(root)
    return app_dirs


def _try_import_and_collect(filepath: str, project_root: str, Model, found: dict) -> None:
    try:
        rel = os.path.relpath(filepath, project_root)
        module_name = rel.replace(os.sep, ".")[:-3]

        if module_name in sys.modules:
            mod = sys.modules[module_name]
        else:
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            if spec is None or spec.loader is None:
                return
            mod = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = mod
            spec.loader.exec_module(mod)

        for obj in mod.__dict__.values():
            if (
                isinstance(obj, type)
                and issubclass(obj, Model)
                and obj is not Model
                and _is_valid_model(obj)
            ):
                table = obj._get_table()
                if table not in found:
                    found[table] = obj

    except Exception:
        pass


def _is_valid_model(cls) -> bool:
    meta = getattr(cls, "Meta", None)
    if meta is None:
        return False
    if not getattr(meta, "db_table", None):
        return False
    return bool(getattr(cls, "_fields", None))
