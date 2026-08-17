"""Multipart parsing via python-multipart."""

from __future__ import annotations

import asyncio
import unittest

from raft.core.request import RaftRequest, UploadedFile


class MultipartRequestTests(unittest.TestCase):
    def _multipart_request(self, body: bytes) -> RaftRequest:
        messages = [{"type": "http.request", "body": body, "more_body": False}]

        async def receive():
            return messages.pop(0)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/upload",
            "query_string": b"",
            "headers": [
                (b"content-type", b"multipart/form-data; boundary=----raft"),
            ],
            "path_params": {},
            "client": ("127.0.0.1", 12345),
        }
        return RaftRequest(scope, receive)

    def test_parses_fields_and_files(self) -> None:
        body = (
            b"------raft\r\n"
            b'Content-Disposition: form-data; name="title"\r\n\r\n'
            b"hello\r\n"
            b"------raft\r\n"
            b'Content-Disposition: form-data; name="file"; filename="note.txt"\r\n'
            b"Content-Type: text/plain\r\n\r\n"
            b"file-bytes\r\n"
            b"------raft--\r\n"
        )

        async def run() -> None:
            req = self._multipart_request(body)
            form = await req.form()
            files = await req.files()
            self.assertEqual(form["title"], "hello")
            self.assertIn("file", files)
            uploaded = files["file"]
            self.assertIsInstance(uploaded, UploadedFile)
            self.assertEqual(uploaded.filename, "note.txt")
            self.assertEqual(uploaded.body, b"file-bytes")

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
