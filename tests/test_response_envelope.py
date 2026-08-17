import json
import unittest

from raft.core.response import Response


class ResponseEnvelopeTests(unittest.TestCase):
    def test_ok_omits_errors_key(self) -> None:
        raw = Response.success(message="Success", data={"x": 1})
        payload = json.loads(raw.body.decode())
        self.assertTrue(payload["status"])
        self.assertNotIn("errors", payload)

    def test_created_omits_errors_key(self) -> None:
        raw = Response.created(data={"id": 1})
        payload = json.loads(raw.body.decode())
        self.assertTrue(payload["status"])
        self.assertNotIn("errors", payload)

    def test_failure_with_errors_includes_key(self) -> None:
        raw = Response.bad_request(
            message="Bad", errors=["name: required", "email: invalid"]
        )
        payload = json.loads(raw.body.decode())
        self.assertFalse(payload["status"])
        self.assertEqual(payload["errors"], ["name: required", "email: invalid"])

    def test_failure_empty_or_blank_errors_omits_key(self) -> None:
        raw = Response.bad_request(message="Bad", errors=[])
        payload = json.loads(raw.body.decode())
        self.assertFalse(payload["status"])
        self.assertNotIn("errors", payload)

        raw2 = Response.bad_request(message="Bad", errors=["", "  ", "ok"])
        payload2 = json.loads(raw2.body.decode())
        self.assertEqual(payload2["errors"], ["ok"])

    def test_error_primary_api(self) -> None:
        raw = Response.error(message="Bad", errors=["x: y"], http_status=422)
        payload = json.loads(raw.body.decode())
        self.assertFalse(payload["status"])
        self.assertEqual(payload["errors"], ["x: y"])
        self.assertEqual(raw.status_code, 422)

    def test_custom_success_never_includes_errors_even_if_passed(self) -> None:
        raw = Response.custom(
            status=True,
            message="OK",
            data=None,
            errors=["should be ignored"],
            http_status=200,
        )
        payload = json.loads(raw.body.decode())
        self.assertTrue(payload["status"])
        self.assertNotIn("errors", payload)


if __name__ == "__main__":
    unittest.main()
