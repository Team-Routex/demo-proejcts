"""
raft.tasks.scheduler
~~~~~~~~~~~~~~~~~~~~

Lightweight in-process task scheduler for periodic background jobs.

This scheduler is intentionally simple and framework-native. It is useful for
housekeeping jobs (cleanup, cache refresh, periodic sync) and can be attached
to a Raft app lifecycle.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

logger = logging.getLogger("raft.scheduler")

TaskCallable = Callable[[], Any]
TASK_OPTIONS_ATTR = "__raft_task_options__"


def periodic_task(
    *,
    every: float,
    repeat: bool = True,
    name: str | None = None,
    run_immediately: bool = False,
) -> Callable[[TaskCallable], TaskCallable]:
    """Mark a callable for Raft task autodiscovery.

    Example::

        @periodic_task(every=60, repeat=True)
        async def cleanup_task():
            ...
    """

    if every <= 0:
        raise ValueError("Task interval 'every' must be greater than 0")

    def decorator(func: TaskCallable) -> TaskCallable:
        setattr(
            func,
            TASK_OPTIONS_ATTR,
            {
                "every": float(every),
                "repeat": repeat,
                "name": name,
                "run_immediately": run_immediately,
            },
        )
        return func

    return decorator


@dataclass(slots=True)
class ScheduledTask:
    """Configuration for one periodic task."""

    name: str
    func: TaskCallable
    every: float
    repeat: bool = True
    run_immediately: bool = False


class TaskScheduler:
    """In-process periodic task scheduler.

    Register tasks with ``@scheduler.task(every=...)`` and call ``start()`` to
    launch loops. Each task runs in its own asyncio task.
    """

    def __init__(self) -> None:
        self._definitions: list[ScheduledTask] = []
        self._workers: list[asyncio.Task[None]] = []
        self._running: bool = False

    @property
    def is_running(self) -> bool:
        """Return True if scheduler loops are running."""
        return self._running

    @property
    def tasks(self) -> list[ScheduledTask]:
        """Return a snapshot of registered task definitions."""
        return list(self._definitions)

    def add_task(
        self,
        func: TaskCallable,
        *,
        every: float,
        repeat: bool = True,
        name: str | None = None,
        run_immediately: bool = False,
    ) -> TaskCallable:
        """Register a periodic task callable.

        Parameters:
            func: Sync or async callable with no arguments.
            every: Execution interval in seconds; must be > 0.
                repeat: If True, run forever at each interval. If False,
                    run once (immediately or after one interval delay).
            name: Optional human-friendly task name.
            run_immediately: Run once immediately on scheduler start.
        """
        if every <= 0:
            raise ValueError("Task interval 'every' must be greater than 0")

        task_name = name or getattr(func, "__name__", "task")
        self._definitions.append(
            ScheduledTask(
                name=task_name,
                func=func,
                every=float(every),
                repeat=repeat,
                run_immediately=run_immediately,
            )
        )
        return func

    def task(
        self,
        *,
        every: float,
        repeat: bool = True,
        name: str | None = None,
        run_immediately: bool = False,
    ) -> Callable[[TaskCallable], TaskCallable]:
        """Decorator form of ``add_task``.

        Usage::

            @scheduler.task(every=60, repeat=True, run_immediately=True)
            async def refresh_cache():
                ...
        """

        def decorator(func: TaskCallable) -> TaskCallable:
            return self.add_task(
                func,
                every=every,
                repeat=repeat,
                name=name,
                run_immediately=run_immediately,
            )

        return decorator

    async def start(self) -> None:
        """Start all task loops if not already running."""
        if self._running:
            return
        self._running = True

        for definition in self._definitions:
            worker = asyncio.create_task(
                self._run_task_loop(definition),
                name=f"raft-task:{definition.name}",
            )
            self._workers.append(worker)

        logger.info("Task scheduler started with %d task(s)", len(self._definitions))

    async def stop(self) -> None:
        """Stop all running task loops and wait for cancellation."""
        if not self._running:
            return

        self._running = False
        workers = list(self._workers)
        self._workers.clear()

        for worker in workers:
            worker.cancel()

        if workers:
            await asyncio.gather(*workers, return_exceptions=True)

        logger.info("Task scheduler stopped")

    async def _run_task_loop(self, definition: ScheduledTask) -> None:
        """Run one task once or forever based on ``repeat`` flag."""
        try:
            if definition.run_immediately:
                await self._execute(definition)
                if not definition.repeat:
                    return

            while self._running:
                await asyncio.sleep(definition.every)
                if not self._running:
                    break
                await self._execute(definition)
                if not definition.repeat:
                    break
        except asyncio.CancelledError:
            raise

    async def _execute(self, definition: ScheduledTask) -> None:
        """Execute one task and log failures without stopping the scheduler."""
        try:
            if inspect.iscoroutinefunction(definition.func):
                await definition.func()
            else:
                await asyncio.to_thread(definition.func)
            logger.debug("Task %s executed", definition.name)
        except Exception:
            logger.exception("Scheduled task failed: %s", definition.name)
