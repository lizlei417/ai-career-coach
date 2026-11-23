import asyncio
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4
import httpx
from fastapi import HTTPException
from app import positions, exploration


class ExplorationTests(TestCase):
    def setUp(self):
        self.id = str(uuid4())
        self.url = f"https://jobs.lever.co/crypto/{self.id}"
        self.raw = dict(
            id=self.id,
            hostedUrl=self.url,
            applyUrl="javascript:bad",
            text="Product Intern",
            categories={"location": "Hong Kong", "commitment": "Internship"},
            lists=[
                dict(text="Responsibilities", content="<ul><li>Analyze data</li></ul>")
            ],
        )

    def test_questions_and_reverse_scoring(self):
        self.assertEqual(exploration.scores([5] * 4 + [1] * 4 + [5] * 4), [100] * 4)
        self.assertEqual(exploration.scores([1] * 4 + [5] * 4 + [1] * 4), [0] * 4)
        self.assertEqual(exploration.scores([3] * 12), [50] * 4)
        with self.assertRaises(HTTPException):
            exploration.scores([0])

    def test_source_text_filters_and_safe_links(self):
        job = positions.normalize("crypto", self.raw)
        self.assertEqual(job["apply"], self.url)
        self.assertIn("Analyze data", job["jd"])
        self.assertNotIn("<li>", job["jd"])
        self.assertTrue(positions.eligible(job, "hk", "intern", "product", "crypto"))
        for query in [
            ("cn", "intern", "product", ""),
            ("hk", "graduate", "product", ""),
            ("hk", "intern", "engineering", ""),
        ]:
            self.assertFalse(positions.eligible(job, *query))
        self.assertFalse(
            positions.eligible(
                dict(job, jd="Requires 5+ years of experience"),
                "hk",
                "intern",
                "product",
                "",
            )
        )
        self.assertIsNone(
            positions.normalize(
                "crypto", dict(self.raw, hostedUrl="https://example.com")
            )
        )
        self.assertEqual(
            positions.normalize("crypto", dict(self.raw, lists=[]))["jd"], ""
        )

    def test_board_deduplication(self):
        async def run():
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(
                    lambda r: httpx.Response(200, json=[self.raw, self.raw])
                )
            ) as c:
                self.assertEqual(len(await positions.fetch_board(c, "crypto")), 1)

        asyncio.run(run())

    def test_closed_or_unavailable(self):
        client = httpx.AsyncClient
        for status, expected in [(404, 410), (503, 503)]:
            with patch.object(
                httpx,
                "AsyncClient",
                lambda **kw: client(
                    transport=httpx.MockTransport(lambda r: httpx.Response(status)),
                    **kw,
                ),
            ):
                with self.assertRaises(HTTPException) as caught:
                    asyncio.run(positions.detail("crypto", self.id))
                self.assertEqual(caught.exception.status_code, expected)

    def test_reject_unverified_quote(self):
        path = dict(
            name="Test",
            category="product",
            reason="Reason",
            evidence="Unwritten claim",
            transfer="Skill",
            gap="Practice",
        )
        with self.assertRaises(HTTPException):
            exploration.path_output({"paths": [path]}, "A different resume")
