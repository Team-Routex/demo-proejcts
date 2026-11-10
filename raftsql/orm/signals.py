"""
Django-style model signals: pre_save, post_save, pre_delete, post_delete.

Usage (sync receiver)
---------------------
    from raftsql import pre_save

    def on_pre_save(sender, instance, created, **kwargs):
        print(f"About to save {sender.__name__} (created={created})")

    pre_save.connect(on_pre_save)                 # receive from all models
    pre_save.connect(on_pre_save, sender=MyModel) # receive from one model only

Usage (async receiver)
----------------------
    from raftsql import post_save

    async def on_post_save(sender, instance, created, **kwargs):
        await notify_something(instance)

    post_save.connect(on_post_save, sender=MyModel)

Signal kwargs
-------------
    pre_save  / post_save  → sender, instance, created (bool: True on INSERT)
    pre_delete / post_delete → sender, instance
"""
from __future__ import annotations

import inspect
from typing import Any, Callable, List, Optional, Tuple


class Signal:
    """
    A signal that can dispatch to a list of registered receivers.

    Each receiver is a callable ``fn(sender, **kwargs)``; async receivers are
    also supported via ``asend()``.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        # List of (sender_filter | None, receiver callable)
        self._receivers: List[Tuple[Optional[Any], Callable]] = []

    # ── Registration ─────────────────────────────────────────────────────────

    def connect(self, receiver: Callable, *, sender: Optional[Any] = None) -> None:
        """Register *receiver* for this signal.

        Args:
            receiver: callable ``fn(sender, **kwargs)``.  May be async.
            sender:   optional model class to filter on.  ``None`` means
                      "receive from every sender".
        """
        entry = (sender, receiver)
        if entry not in self._receivers:
            self._receivers.append(entry)

    def disconnect(self, receiver: Callable, *, sender: Optional[Any] = None) -> None:
        """Remove a previously registered receiver."""
        self._receivers = [
            (s, r) for s, r in self._receivers
            if not (r is receiver and s is sender)
        ]

    # ── Dispatch ─────────────────────────────────────────────────────────────

    def send(self, sender: Any, **kwargs: Any) -> List[Tuple[Callable, Any]]:
        """
        Dispatch to all *sync* receivers matching *sender*.
        Async receivers are skipped (use ``asend`` in async contexts).

        Returns a list of ``(receiver, return_value)`` pairs.
        """
        results: List[Tuple[Callable, Any]] = []
        for registered_sender, receiver in self._receivers:
            if registered_sender is not None and registered_sender is not sender:
                continue
            if inspect.iscoroutinefunction(receiver):
                continue   # skip async receivers in sync dispatch
            results.append((receiver, receiver(sender=sender, **kwargs)))
        return results

    async def asend(self, sender: Any, **kwargs: Any) -> List[Tuple[Callable, Any]]:
        """
        Dispatch to *all* receivers (sync and async) matching *sender*.

        Returns a list of ``(receiver, return_value)`` pairs.
        """
        results: List[Tuple[Callable, Any]] = []
        for registered_sender, receiver in self._receivers:
            if registered_sender is not None and registered_sender is not sender:
                continue
            if inspect.iscoroutinefunction(receiver):
                result = await receiver(sender=sender, **kwargs)
            else:
                result = receiver(sender=sender, **kwargs)
            results.append((receiver, result))
        return results

    def __repr__(self) -> str:
        return f"<Signal: {self.name} ({len(self._receivers)} receivers)>"


# ── Pre-defined signal instances ─────────────────────────────────────────────

pre_save = Signal("pre_save")
"""Fired *before* a model instance is saved (INSERT or UPDATE).
Kwargs: ``instance``, ``created`` (bool)."""

post_save = Signal("post_save")
"""Fired *after* a model instance is saved.
Kwargs: ``instance``, ``created`` (bool)."""

pre_delete = Signal("pre_delete")
"""Fired *before* a model instance is deleted.
Kwargs: ``instance``."""

post_delete = Signal("post_delete")
"""Fired *after* a model instance is deleted.
Kwargs: ``instance``."""
