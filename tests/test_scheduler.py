import asyncio
import unittest

from raft import Raft
from raft.tasks.scheduler import TaskScheduler


class TaskSchedulerTests(unittest.TestCase):
    def test_scheduler_repeats_when_repeat_true(self) -> None:
        async def runner() -> tuple[int, int, bool]:
            scheduler = TaskScheduler()
            counts: dict[str, int] = {"async": 0, "sync": 0}

            @scheduler.task(every=0.05, repeat=True, run_immediately=True)
            async def async_job() -> None:
                counts["async"] += 1

            def sync_job() -> None:
                counts["sync"] += 1

            scheduler.add_task(sync_job, every=0.05, repeat=True, run_immediately=True)

            await scheduler.start()
            await asyncio.sleep(0.16)
            await scheduler.stop()
            return counts["async"], counts["sync"], scheduler.is_running

        async_count, sync_count, is_running = asyncio.run(runner())
        self.assertGreaterEqual(async_count, 2)
        self.assertGreaterEqual(sync_count, 2)
        self.assertFalse(is_running)

    def test_scheduler_runs_once_when_repeat_false(self) -> None:
        async def runner() -> int:
            scheduler = TaskScheduler()
            counts = {"once": 0}

            @scheduler.task(every=0.05, repeat=False, run_immediately=True)
            async def run_once() -> None:
                counts["once"] += 1

            await scheduler.start()
            await asyncio.sleep(0.16)
            await scheduler.stop()
            return counts["once"]

        count = asyncio.run(runner())
        self.assertEqual(count, 1)


    def test_app_scheduler_lifecycle_hooks(self) -> None:
        async def runner() -> tuple[int, bool]:
            app = Raft()
            ran = {"count": 0}

            @app.task(every=0.05, repeat=True, run_immediately=True)
            async def heartbeat() -> None:
                ran["count"] += 1

            await app._run_lifecycle_handlers(app._startup_handlers)
            await asyncio.sleep(0.12)
            await app._run_lifecycle_handlers(app._shutdown_handlers)
            return ran["count"], app.scheduler.is_running

        count, is_running = asyncio.run(runner())
        self.assertGreaterEqual(count, 1)
        self.assertFalse(is_running)


    def test_scheduler_rejects_non_positive_interval(self) -> None:
        scheduler = TaskScheduler()

        with self.assertRaises(ValueError):
            scheduler.add_task(lambda: None, every=0)


if __name__ == "__main__":
    unittest.main()
