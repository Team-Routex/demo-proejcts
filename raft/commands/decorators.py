"""
raft.commands.decorators
~~~~~~~~~~~~~~~~~~~~~~~~

``@command`` — register a function as a project management command.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any

COMMAND_META_ATTR = "_raft_command_meta"


def command(
    name: str | None = None,
    *,
    help: str = "",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Mark a function as a project command discoverable from ``commands/``.

    Usage::

        @command(help="Seed the database")
        def seed():
            ...

        @command("rebuild-cache", help="Clear and warm caches")
        def rebuild_cache():
            ...

    Add Click options by stacking decorators **below** ``@command``::

        @command(help="Seed with options")
        @click.option("--force", is_flag=True)
        def seed(force: bool):
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        cmd_name = (name or func.__name__).replace("_", "-")
        meta = {"name": cmd_name, "help": help or (func.__doc__ or "").strip().split("\n")[0]}
        setattr(func, COMMAND_META_ATTR, meta)

        # Preserve Click command metadata when stacked
        if hasattr(func, "__click_params__"):
            wrapped = func
        else:
            wrapped = func

        @functools.wraps(wrapped)
        def marker(*args: Any, **kwargs: Any) -> Any:
            return wrapped(*args, **kwargs)

        setattr(marker, COMMAND_META_ATTR, meta)
        if hasattr(wrapped, "__click_params__"):
            marker.__click_params__ = wrapped.__click_params__  # type: ignore[attr-defined]
            marker.callback = wrapped  # type: ignore[attr-defined]
        return marker

    return decorator


def get_command_meta(obj: Any) -> dict[str, str] | None:
    """Return command metadata when *obj* is a registered command."""
    meta = getattr(obj, COMMAND_META_ATTR, None)
    if isinstance(meta, dict) and meta.get("name"):
        return meta
    return None
