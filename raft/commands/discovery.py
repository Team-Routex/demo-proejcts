"""
raft.commands.discovery
~~~~~~~~~~~~~~~~~~~~~~~

Discover and build Click commands from a project's ``commands/`` folder.
"""

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Any

import click

from raft.commands.decorators import COMMAND_META_ATTR, get_command_meta
from raft.config.settings import settings

logger = logging.getLogger("raft.commands")

_loaded: dict[str, click.Command] | None = None


def _commands_dir(root: Path | None = None) -> Path:
    base = root or settings.BASE_DIR
    if not isinstance(base, Path):
        base = Path.cwd()
    return base / str(getattr(settings, "COMMANDS_MODULE_DIR", "commands"))


def _load_module_from_path(file_path: Path) -> Any | None:
    path_hash = hashlib.md5(str(file_path.resolve()).encode("utf-8")).hexdigest()[:8]
    module_name = f"raft_user_commands_{file_path.stem}_{path_hash}"
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        logger.exception("Failed to import command module: %s", file_path)
        return None
    return module


def _to_click_command(func: Any, meta: dict[str, str]) -> click.Command:
    """Wrap a user function as a Click command (supports async)."""
    if isinstance(func, click.Command):
        func.name = meta["name"]
        if meta.get("help"):
            func.help = meta["help"]
        return func

    # Already decorated with @click.option (stacked below @command)
    if hasattr(func, "__click_params__"):
        callback = getattr(func, "callback", func)
        return click.Command(
            name=meta["name"],
            callback=callback,
            params=getattr(func, "__click_params__", []),
            help=meta.get("help") or None,
        )

    name = meta["name"]
    help_text = meta.get("help") or None

    if inspect.iscoroutinefunction(func):

        @click.command(name=name, help=help_text)
        def async_runner(*args: Any, **kwargs: Any) -> None:
            asyncio.run(func(*args, **kwargs))

        return async_runner

    return click.command(name=name, help=help_text)(func)


def _extract_commands(module: Any) -> list[tuple[str, click.Command]]:
    found: list[tuple[str, click.Command]] = []
    mod_name = getattr(module, "__name__", "")

    for attr_name, obj in inspect.getmembers(module):
        if attr_name.startswith("_"):
            continue
        if getattr(obj, "__module__", None) != mod_name:
            continue

        meta = get_command_meta(obj)
        if meta is None:
            continue

        cmd = _to_click_command(obj, meta)
        found.append((meta["name"], cmd))

    return found


def discover_commands(*, root: Path | None = None, force_reload: bool = False) -> dict[str, click.Command]:
    """Scan ``commands/*.py`` and return ``{name: click.Command}``."""
    global _loaded
    if _loaded is not None and not force_reload:
        return _loaded

    commands_dir = _commands_dir(root)
    registry: dict[str, click.Command] = {}

    if not commands_dir.is_dir():
        _loaded = registry
        return registry

    for file_path in sorted(commands_dir.glob("*.py")):
        if file_path.name.startswith("_"):
            continue
        module = _load_module_from_path(file_path)
        if module is None:
            continue
        for name, cmd in _extract_commands(module):
            if name in registry:
                logger.warning("Duplicate command %r in %s — skipping", name, file_path.name)
                continue
            registry[name] = cmd

    _loaded = registry
    return registry


def list_command_names(*, root: Path | None = None) -> list[str]:
    return sorted(discover_commands(root=root).keys())


def get_command(name: str, *, root: Path | None = None) -> click.Command | None:
    return discover_commands(root=root).get(name)


def reset_command_cache() -> None:
    """Clear discovery cache (tests)."""
    global _loaded
    _loaded = None
