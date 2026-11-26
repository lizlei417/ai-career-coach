import unittest
from unittest.mock import AsyncMock, patch
from app.llm import parse_completion, ping
from app.errors import AppError

class ResponseTests(unittest.IsolatedAsyncioTestCase):
    async def test_probe(self):
        for value in (1, "true", None):
            with patch("app.llm._request", AsyncMock(return_value=({"ok":value}, {}))):
                with self.assertRaises(AppError) as e: await ping()
                self.assertEqual(e.exception.detail, "invalid_probe_flag")

    def test_payloads(self):
        def envelope(text, reason):
            return {"choices":[{"finish_reason":reason,"message":{"content":text}}]}
        self.assertEqual(parse_completion(envelope('{"ok":true,"extra":42}', 'stop')), ({"ok":True,"extra":42},{}))
        for data, code in [({}, "unexpected_envelope"), (envelope("", "stop"), "empty"),
            (envelope("   ","stop"), "whitespace"), (envelope("[]","stop"), "expected_object"),
            (envelope("{","stop"), "invalid_json"), (envelope("{","length"), "output_limit")]:
            with self.assertRaises(AppError) as e: parse_completion(data)
            self.assertEqual(e.exception.detail, code)
