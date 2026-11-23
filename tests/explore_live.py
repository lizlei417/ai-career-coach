"""Explicit live integration using fictional inputs, real ATS/model, isolated PostgreSQL, synthetic identity."""

import os
from pathlib import Path
import sys
from unittest.mock import patch, AsyncMock
from uuid import uuid4

if not os.environ.get("DATABASE_URL", "").startswith(
    "postgresql://postgres@127.0.0.1:28547/coachtest_"
):
    raise SystemExit("Use a disposable local QA database")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from fastapi.testclient import TestClient
from app.main import app
from app import cloud, exploration
import httpx


def main():
    account = str(uuid4())

    async def verify(token):
        return (account if token == "Bearer A" else other, False)

    other = str(uuid4())
    with patch.object(cloud, "verify", verify), TestClient(
        app, headers={"Authorization": "Bearer A"}
    ) as c:

        def ok(r):
            assert r.is_success, (r.status_code, r.text[:300])
            return r.json()

        assert not ok(c.get("/api/workspaces"))
        cv = "Helped organize a campus careers fair, coordinated five volunteers and analyzed attendee feedback in Excel.\nCreated two weekly event reports and presented findings to the organizing committee."
        ok(c.put("/api/workspaces/qa", json=dict(name="QA", revision=0, state={})))
        q = ok(
            c.post(
                "/api/explore/draft", json=dict(answers=[4, 3, 2, 1, 4, 5], cursor=6)
            )
        )
        assert ok(c.get("/api/explore/draft"))[0]["answers"] == q["answers"]
        answers = q["answers"] * 2
        h = ok(
            c.post(
                "/api/explore/assessment/" + str(uuid4()), json=dict(answers=answers)
            )
        )
        h2 = ok(
            c.post(
                "/api/explore/assessment/" + str(uuid4()), json=dict(answers=answers)
            )
        )
        assert h["scores"] == h2["scores"] and h["id"] != h2["id"]
        assert (
            c.delete(
                "/api/explore/assessment/" + h["id"],
                params=dict(revision=h["revision"]),
                headers={"Authorization": "Bearer B"},
            ).status_code
            == 409
        )
        assert ok(c.get("/api/quota"))["used"] == 0
        print(
            "PASS draft, deterministic scoring, history and account isolation",
            flush=True,
        )
        jobs = ok(c.get("/api/positions", params=dict(path="product")))
        assert jobs["total"] > 0, jobs
        job = jobs["jobs"][0]
        data = ok(c.get("/api/positions/" + job["board"] + "/" + job["id"]))
        assert len(data["jd"]) > 100
        r = httpx.get(data["apply"], timeout=25, follow_redirects=True)
        r.raise_for_status()
        print(
            "PASS live Lever",
            jobs["total"],
            job["company"],
            job["title"],
            job["location"],
            r.status_code,
            flush=True,
        )
        args = dict(lang="en", resume=cv, goal="internship", assessment=h["id"])
        rec = ok(c.post("/api/explore/paths/qa", json=args))
        assert all(p["evidence"] in cv for p in rec["paths"])
        assert (
            ok(c.post("/api/explore/paths/qa", json=args))["revision"]
            == rec["revision"]
        )
        assert ok(c.get("/api/quota"))["used"] == 1
        print(
            "PASS real DeepSeek recommendations, evidence, cache and quota", flush=True
        )
        review = dict(
            date="2026-11-22",
            role="Operations Intern",
            questions=[
                {
                    "question": "How did you organize the event?",
                    "answer": "I coordinated five volunteers.",
                },
                {"question": "How would you measure retention?"},
                {
                    "question": "How did you use feedback?",
                    "answer": "I summarized attendee feedback and presented two reports.",
                },
            ],
        )
        url = "/api/explore/review/" + str(uuid4())
        saved = ok(c.post(url, json=dict(review=review, revision=0)))

        def analyze(entry):
            return c.post(
                url + "/analyze", json=dict(revision=entry["revision"], lang="en")
            )

        first = ok(analyze(saved))
        assert first["history"][0]["result"]["items"][1]["evaluation"] == ""
        review["questions"][0]["answer"] += " I assigned one person to check-in."
        changed = ok(c.post(url, json=dict(review=review, revision=first["revision"])))
        assert changed["review"] != changed["history"][0]["input"]
        assert not ok(
            c.get("/api/explore/review", headers={"Authorization": "Bearer B"})
        )
        second = ok(analyze(changed))
        assert len(second["history"]) == 2
        with patch.object(
            exploration.llm, "_request", AsyncMock(side_effect=httpx.ReadTimeout("QA"))
        ):
            try:
                analyze(second)
            except httpx.ReadTimeout:
                pass
        assert ok(c.get("/api/explore/review"))[0]["revision"] == second["revision"]
        cloud.identity.set(account)
        events = exploration.records("usage")
        print(
            "PASS real review, missing answer, edits, regeneration, failure recovery. Actual usage:",
            [
                (
                    e["feature"],
                    e["usage"].get("prompt_tokens"),
                    e["usage"].get("completion_tokens"),
                )
                for e in events
                if e["success"]
            ],
            flush=True,
        )


if __name__ == "__main__":
    main()
