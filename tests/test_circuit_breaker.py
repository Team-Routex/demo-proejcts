"""Tests for raft.resilience.circuit_breaker."""

from __future__ import annotations

import asyncio
import time
import unittest

from raft import CircuitBreaker, CircuitOpenError, CircuitState, get_circuit, reset_circuits


class CircuitBreakerTests(unittest.TestCase):
    def tearDown(self) -> None:
        reset_circuits()

    def test_opens_after_failure_threshold(self) -> None:
        breaker = CircuitBreaker("svc", failure_threshold=3, recovery_timeout=60)

        def boom() -> None:
            raise RuntimeError("down")

        for _ in range(3):
            with self.assertRaises(RuntimeError):
                breaker.call(boom)

        self.assertEqual(breaker.state, CircuitState.OPEN)
        with self.assertRaises(CircuitOpenError) as ctx:
            breaker.call(lambda: "ok")
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(ctx.exception.name, "svc")

    def test_success_resets_failure_streak(self) -> None:
        breaker = CircuitBreaker("svc", failure_threshold=3, recovery_timeout=60)
        fails = {"n": 0}

        def flaky() -> str:
            fails["n"] += 1
            if fails["n"] < 3:
                raise RuntimeError("x")
            return "ok"

        with self.assertRaises(RuntimeError):
            breaker.call(flaky)
        with self.assertRaises(RuntimeError):
            breaker.call(flaky)
        self.assertEqual(breaker.call(flaky), "ok")
        self.assertEqual(breaker.state, CircuitState.CLOSED)
        self.assertEqual(breaker.failure_count, 0)

    def test_half_open_then_close_on_success(self) -> None:
        breaker = CircuitBreaker(
            "svc",
            failure_threshold=1,
            recovery_timeout=0.05,
            half_open_success_threshold=1,
        )

        with self.assertRaises(RuntimeError):
            breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("x")))

        self.assertEqual(breaker.state, CircuitState.OPEN)
        time.sleep(0.06)
        self.assertEqual(breaker.state, CircuitState.HALF_OPEN)
        self.assertEqual(breaker.call(lambda: "recovered"), "recovered")
        self.assertEqual(breaker.state, CircuitState.CLOSED)

    def test_half_open_failure_reopens(self) -> None:
        breaker = CircuitBreaker("svc", failure_threshold=1, recovery_timeout=0.05)

        with self.assertRaises(RuntimeError):
            breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("x")))
        time.sleep(0.06)
        self.assertEqual(breaker.state, CircuitState.HALF_OPEN)

        with self.assertRaises(RuntimeError):
            breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("still down")))
        self.assertEqual(breaker.state, CircuitState.OPEN)

    def test_excluded_exceptions_do_not_trip(self) -> None:
        breaker = CircuitBreaker(
            "svc",
            failure_threshold=1,
            recovery_timeout=60,
            excluded_exceptions=(ValueError,),
        )
        with self.assertRaises(ValueError):
            breaker.call(lambda: (_ for _ in ()).throw(ValueError("bad input")))
        self.assertEqual(breaker.state, CircuitState.CLOSED)

    def test_async_acall_and_decorator(self) -> None:
        breaker = CircuitBreaker("async-svc", failure_threshold=2, recovery_timeout=60)

        async def boom() -> str:
            raise ConnectionError("timeout")

        async def run() -> None:
            with self.assertRaises(ConnectionError):
                await breaker.acall(boom)
            with self.assertRaises(ConnectionError):
                await breaker.acall(boom)
            self.assertEqual(breaker.state, CircuitState.OPEN)
            with self.assertRaises(CircuitOpenError):
                await breaker.acall(boom)

            @breaker
            async def blocked() -> str:
                return "nope"

            with self.assertRaises(CircuitOpenError):
                await blocked()

        asyncio.run(run())

    def test_get_circuit_registry_shares_instance(self) -> None:
        a = get_circuit("shared", failure_threshold=2)
        b = get_circuit("shared", failure_threshold=99)
        self.assertIs(a, b)
        self.assertEqual(a.failure_threshold, 2)

    def test_circuit_open_in_raft_view_returns_503(self) -> None:
        from raft import Raft

        app = Raft(
            debug=True,
            auto_discover_routes=False,
            auto_discover_middleware=False,
            auto_discover_tasks=False,
        )
        breaker = CircuitBreaker("dep", failure_threshold=1, recovery_timeout=60)

        @app.get("/proxy")
        async def proxy(request):
            def boom() -> None:
                raise RuntimeError("x")

            breaker.call(boom)
            return {"ok": True}  # unreachable after first failure path

        # Trip the breaker first outside the request
        with self.assertRaises(RuntimeError):
            breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("x")))

        @app.get("/proxy2")
        async def proxy2(request):
            return breaker.call(lambda: "ok")

        sent: list[dict] = []
        messages = [{"type": "http.request", "body": b"", "more_body": False}]

        async def receive() -> dict:
            if messages:
                return messages.pop(0)
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict) -> None:
            sent.append(message)

        async def run() -> None:
            await app(
                {
                    "type": "http",
                    "method": "GET",
                    "path": "/proxy2",
                    "query_string": b"",
                    "headers": [],
                    "client": ("127.0.0.1", 1),
                },
                receive,
                send,
            )

        asyncio.run(run())
        self.assertEqual(sent[0]["status"], 503)
        body = sent[1]["body"].decode()
        self.assertIn("open", body.lower())


if __name__ == "__main__":
    unittest.main()
