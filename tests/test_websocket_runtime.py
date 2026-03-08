import asyncio
import json
import unittest

from raft import Raft


class WebSocketRuntimeTests(unittest.TestCase):
    def test_websocket_route_handles_path_params_and_messages(self) -> None:
        async def runner() -> list[dict]:
            app = Raft()

            @app.websocket("/ws/chat/{room}")
            async def room_chat(ws) -> None:
                room = ws.path_params["room"]
                await ws.join_room(room)
                await ws.send_json({"event": "joined", "room": room})
                msg = await ws.receive_text()
                await ws.send_room(room, f"echo:{msg}")

            outgoing: list[dict] = []
            incoming: list[dict] = [
                {"type": "websocket.connect"},
                {"type": "websocket.receive", "text": "hello"},
            ]

            async def receive() -> dict:
                if incoming:
                    return incoming.pop(0)
                return {"type": "websocket.disconnect", "code": 1000}

            async def send(message: dict) -> None:
                outgoing.append(message)

            scope = {
                "type": "websocket",
                "path": "/ws/chat/general",
                "query_string": b"",
                "headers": [],
            }
            await app(scope, receive, send)
            return outgoing

        sent = asyncio.run(runner())

        self.assertEqual(sent[0]["type"], "websocket.accept")
        payloads = [m for m in sent if m.get("type") == "websocket.send"]
        self.assertGreaterEqual(len(payloads), 2)

        first_payload = json.loads(payloads[0]["text"])
        self.assertEqual(first_payload["event"], "joined")
        self.assertEqual(first_payload["room"], "general")
        self.assertEqual(payloads[1]["text"], "echo:hello")

    def test_websocket_not_found_closes_with_4404(self) -> None:
        async def runner() -> list[dict]:
            app = Raft()
            outgoing: list[dict] = []

            async def receive() -> dict:
                return {"type": "websocket.connect"}

            async def send(message: dict) -> None:
                outgoing.append(message)

            scope = {
                "type": "websocket",
                "path": "/ws/missing",
                "query_string": b"",
                "headers": [],
            }
            await app(scope, receive, send)
            return outgoing

        sent = asyncio.run(runner())
        self.assertEqual(sent[0]["type"], "websocket.close")
        self.assertEqual(sent[0]["code"], 4404)


if __name__ == "__main__":
    unittest.main()
