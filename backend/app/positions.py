"""Published vacancies from fixed company boards in the public Lever Postings API."""

import asyncio
import html
import re
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/positions")
BOARDS = {
    "crypto": "Crypto.com",
    "animocabrands": "Animoca Brands",
    "binance": "Binance",
}
BASE = "https://api.lever.co/v0/postings/"
cache = {}
lock = asyncio.Lock()
PATHS = {
    "product": r"product|产品|產品",
    "operations": r"operation|运营|運營|coordina",
    "analytics": r"analy|research|insight|分析|研究",
    "marketing": r"market|growth|content|community|营销|行銷|增长",
    "engineering": r"engineer|developer|software|开发|工程",
    "design": r"design|creative|设计|設計",
    "finance": r"finance|accounting|compliance|risk|财务|合规",
    "people": r"talent|recruit|people|human resources|招聘",
    "other": "",
}


class Plain(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data.strip())


def normalize(board, item):
    id = str(UUID(item["id"]))

    def link(key):
        url = item.get(key, "")
        parts = urlsplit(url)
        if (
            parts.scheme == "https"
            and parts.netloc == "jobs.lever.co"
            and parts.path.rstrip("/") in (f"/{board}/{id}", f"/{board}/{id}/apply")
        ):
            return url
        return ""

    if not link("hostedUrl"):
        return None
    categories = item.get("categories", {})
    sections = [item.get("descriptionPlain", "")]
    for section in item.get("lists", []):
        parser = Plain()
        parser.feed(section.get("content", ""))
        sections.extend([section.get("text", ""), *parser.parts])
    sections.append(item.get("additionalPlain", ""))
    jd = "\n".join(html.unescape(x) for x in sections if x)
    return dict(
        id=id,
        board=board,
        company=BOARDS[board],
        title=item["text"],
        location=categories.get("location", ""),
        team=categories.get("team", ""),
        kind=categories.get("commitment", ""),
        jd=jd,
        url=link("hostedUrl"),
        apply=link("applyUrl") or link("hostedUrl"),
    )


async def fetch_board(client, board):
    rows = {}
    for offset in range(0, 1000, 100):
        res = await client.get(
            BASE + board, params={"mode": "json", "limit": 100, "skip": offset}
        )
        res.raise_for_status()
        batch = res.json()
        for item in batch:
            job = normalize(board, item)
            if job:
                rows[job["id"]] = job
        if len(batch) < 100:
            break
    return list(rows.values())


def eligible(job, region, kind, path, keyword):
    location = job["location"].lower()
    hk = bool(re.search(r"hong kong|hongkong|香港", location))
    cn = (
        bool(
            re.search(
                r"china|beijing|shanghai|shenzhen|guangzhou|hangzhou|中国|内地|北京|上海|深圳",
                location,
            )
        )
        and not hk
    )
    if (
        region == "hk"
        and not hk
        or region == "cn"
        and not cn
        or region == "other"
        and (hk or cn)
    ):
        return False
    title = job["title"].lower()
    kind_text = (title + " " + job["kind"]).lower()
    if kind in ("intern", "graduate") and (
        re.search(
            r"\bsenior\b|\bsr\.|director|principal|head of|staff engineer|高级", title
        )
        or re.search(
            r"\b(?:[5-9]|\d{2})\+? years (?:of )?(?:relevant |professional )?experience",
            job["jd"],
            re.I,
        )
    ):
        return False
    pattern = {
        "intern": r"\bintern(?:ship)?\b|实习",
        "graduate": r"graduate|entry.level|early career|junior|校招",
        "full": r"full.time",
    }.get(kind, "")
    return bool(
        re.search(pattern, kind_text)
        and re.search(PATHS.get(path, ""), title + " " + job["team"], re.I)
        and keyword.lower()
        in (title + " " + job["company"] + " " + location + " " + job["team"]).lower()
    )


@router.get("")
async def listing(
    region: str = "",
    kind: str = "",
    path: str = "",
    keyword: str = Query("", max_length=100),
    page: int = Query(1, ge=1, le=1000),
    refresh: bool = False,
):
    async with lock:
        now = time.monotonic()
        if now - cache.get("time", -10000) >= (
            30 if refresh or cache.get("failed") else 600
        ):
            async with httpx.AsyncClient(timeout=12) as client:
                batches = await asyncio.gather(
                    *(fetch_board(client, b) for b in BOARDS), return_exceptions=True
                )
            failed = [
                board
                for board, batch in zip(BOARDS, batches)
                if isinstance(batch, Exception)
            ]
            cache.update(
                time=now,
                synced=datetime.now(timezone.utc).isoformat(),
                failed=failed,
                rows=[j for batch in batches if isinstance(batch, list) for j in batch],
            )
    if len(cache["failed"]) == len(BOARDS):
        raise HTTPException(503, "POSITIONS_UNAVAILABLE")
    rows = [j for j in cache["rows"] if eligible(j, region, kind, path, keyword)]
    return dict(
        total=len(rows),
        synced=cache["synced"],
        failed=cache["failed"],
        jobs=[
            {k: v for k, v in j.items() if k != "jd"}
            for j in rows[(page - 1) * 3 : page * 3]
        ],
    )


@router.get("/{board}/{id}")
async def detail(board: str, id: UUID):
    if board not in BOARDS:
        raise HTTPException(404)
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            res = await client.get(f"{BASE}{board}/{id}", params={"mode": "json"})
        if res.status_code == 404:
            raise HTTPException(410, "CLOSED")
        res.raise_for_status()
        job = normalize(board, res.json())
        if job:
            return job
    except (httpx.HTTPError, KeyError, ValueError):
        pass
    raise HTTPException(503, "POSITIONS_UNAVAILABLE")
