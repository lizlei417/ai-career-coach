"""Same-origin API for the local career workspace. One process owns session memory."""
import secrets
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
from typing import Literal

from fastapi import Body, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from coach.config import ROOT, settings
from coach.errors import CoachError
from coach.i18n import LANGUAGES, STRINGS
from coach.job_links import import_job
from coach.knowledge import KnowledgeBase
from coach.llm import AIClient
from coach.models import Context, Turn
from coach.parsing import fingerprint, pdf_text, sources, validate_text
from coach.presentation import ObservedClient, connection_state
from coach.service import CareerCoach
from coach.state import new_interview
from coach.web_errors import translations

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
Language = Literal["en", "zh-CN", "zh-TW"]


class Materials(BaseModel):
    name: str = Field(max_length=120)
    role: str = Field(max_length=120)
    direction: str = Field(default="", max_length=160)
    resume: str = Field(max_length=24000)
    jd: str = Field(max_length=24000)
    filename: str = Field(default="", max_length=255)
    link: str = Field(default="", max_length=4096)
    language: Language = "en"


class Action(BaseModel):
    kind: Literal["optimize", "match", "question", "follow", "answer", "retry", "summary", "restart", "decision"]
    language: Language
    version: int
    answer: str = Field(default="", max_length=8000)
    id: str = Field(default="", max_length=160)
    choice: Literal["adopt", "keep", "edit"] = "adopt"
    edit: str = Field(default="", max_length=24000)


@dataclass
class Project:
    materials: Materials
    context: Context | None = None
    optimization: dict | None = None
    matching: dict | None = None
    interview: dict = field(default_factory=new_interview)
    decisions: dict = field(default_factory=dict)
    observed: dict = field(default_factory=dict)
    version: int = 0
    touched: float = field(default_factory=time.monotonic)
    lock: Lock = field(default_factory=Lock)


projects = {}
registry = Lock()
EXPIRED = "项目已过期，请重新创建。"
STALE = "请刷新页面以加载最新状态。"
STAGE = "当前面试阶段无法执行此操作。"


def prune():
    for token, p in list(projects.items()):
        if time.monotonic() - p.touched > 8 * 3600 and not p.lock.locked():
            del projects[token]


@contextmanager
def project_for(token):
    with registry:
        prune()
        p = projects.get(token)
        if p is None:
            raise CoachError(EXPIRED)
        p.touched = time.monotonic()
    with p.lock:
        with registry:
            if projects.get(token) is not p:
                raise CoachError(EXPIRED)
        yield p


def diagnostics(p=None):
    cfg = settings()
    kb = KnowledgeBase(cfg.knowledge_dir)
    return {"configured": bool(cfg.api_key), "model": cfg.model,
            "connection": connection_state(p.observed if p else {}, cfg),
            "guideCount": len(kb.guides), "guideFiles": sorted({g.filename for g in kb.guides}),
            "warnings": [translations(w) for w in kb.warnings]}


def view(p):
    return {"materials": p.materials, "context": p.context, "optimization": p.optimization,
            "matching": p.matching, "interview": p.interview, "decisions": p.decisions,
            "version": p.version, "status": diagnostics(p)}


def service(p, language):
    cfg = settings()
    connection_state(p.observed, cfg)
    return CareerCoach(ObservedClient(AIClient(cfg), p.observed), KnowledgeBase(cfg.knowledge_dir), LANGUAGES[language])


def prepare(p, coach):
    if p.context is None:
        m = p.materials
        p.context = coach.prepare(m.resume, m.jd, fingerprint(m.resume, m.jd))


def pack(result, guides, language, **extra):
    return {"data": result, "guides": [g for g in guides if g.id in result.guide_ids], "language": language, **extra}


@app.exception_handler(CoachError)
async def known_error(request, exc):
    message = str(exc)
    return JSONResponse({"errors": translations(message)}, status_code=410 if message == EXPIRED else 409 if message == STALE else 400)


@app.exception_handler(RequestValidationError)
async def invalid_input(request, exc):
    return JSONResponse({"errors": translations("请检查输入内容及长度。")}, status_code=422)


@app.middleware("http")
async def private_api(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        origin = request.headers.get("origin")
        if request.method != "GET" and origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse({}, status_code=403)
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/api/bootstrap")
def bootstrap():
    return {"strings": STRINGS, "status": diagnostics()}


@app.post("/api/pdf")
async def read_pdf(request: Request):
    data = bytearray()
    async for part in request.stream():
        data.extend(part)
        if len(data) > 10 * 1024 * 1024:
            raise CoachError("PDF 超过 10 MB，请压缩或粘贴简历正文。")
    return {"text": await run_in_threadpool(pdf_text, bytes(data))}


@app.post("/api/import")
def read_url(url: str = Body(embed=True, max_length=4096)):
    return {"text": import_job(url.strip())}


def checked(m):
    m.role = m.role.strip()
    if not m.role:
        raise CoachError("请填写目标岗位名称。")
    m.name = m.name.strip() or m.role
    for key, label in [("resume", "简历"), ("jd", "JD")]:
        value = validate_text(getattr(m, key), label)
        if sum(c.isalpha() for c in value) < 12 or len(set(value.casefold())) < 6:
            raise CoachError("请提供可读的经历和岗位要求。")
        sources(value, key)
        setattr(m, key, value)
    return m


@app.post("/api/project")
def create(m: Materials):
    p = Project(checked(m))
    if settings().api_key:
        prepare(p, service(p, m.language))
    token = secrets.token_urlsafe(32)
    with registry:
        prune()
        if len(projects) >= 128:
            raise CoachError("当前项目数量已满，请稍后重试。")
        projects[token] = p
    return {"token": token, "project": view(p)}


@app.get("/api/project")
def current(x_project: str = Header(default="")):
    with project_for(x_project) as p:
        return view(p)


@app.put("/api/project")
def update(m: Materials, version: int, x_project: str = Header(default="")):
    m = checked(m)
    with project_for(x_project) as p:
        if version != p.version:
            raise CoachError(STALE)
        if (m.resume, m.jd) != (p.materials.resume, p.materials.jd):
            candidate = Project(m, observed=p.observed)
            if settings().api_key:
                prepare(candidate, service(candidate, m.language))
            p.context, p.optimization, p.matching = candidate.context, None, None
            p.decisions, p.interview = {}, new_interview()
        p.materials = m
        p.version += 1
        return view(p)


@app.delete("/api/project")
def clear(x_project: str = Header(default="")):
    with project_for(x_project):
        with registry:
            del projects[x_project]
    return {"ok": True}


def interview_action(p, a, coach):
    iv, kind = p.interview, a.kind
    turns = iv["turns"]
    if kind == "restart":
        p.interview = new_interview()
        return
    if iv["ended"] and (kind != "summary" or not turns):
        raise CoachError(STAGE)
    if kind in {"question", "follow"}:
        if iv["question"] and not iv["feedback"]:
            raise CoachError(STAGE)
        follow = None
        if kind == "follow":
            if not iv["feedback"] or not iv["feedback"].follow_up:
                raise CoachError(STAGE)
            follow = iv["feedback"].follow_up
        question, guides = coach.question(p.context, turns, follow, iv.get("feedbackLanguage") != a.language)
        iv.update(question=question, guides=pack(question, guides, a.language)["guides"], questionLanguage=a.language,
                  question_number=iv["question_number"] + 1, attempt=1, feedback=None, feedbackGuides=[])
    elif kind == "answer":
        if not iv["question"] or iv["feedback"] or len(turns) >= 30:
            raise CoachError(STAGE)
        feedback, guides = coach.feedback(p.context, iv["question"], a.answer)
        turns.append(Turn(question=iv["question"], feedback=feedback, answer=a.answer, attempt=iv["attempt"]))
        cited = pack(feedback, guides, a.language)["guides"]
        iv.setdefault("sourceArchive", {}).update({g.id: g for g in [*iv["guides"], *cited]})
        iv.update(feedback=feedback, feedbackLanguage=a.language, feedbackGuides=cited)
    elif kind == "retry":
        if not iv["feedback"] or len(turns) >= 30:
            raise CoachError(STAGE)
        iv.update(attempt=iv["attempt"] + 1, feedback=None, feedbackGuides=[])
    elif kind == "summary":
        if turns:
            summary, guides = coach.summarize(p.context, turns)
            iv["summary"] = pack(summary, guides, a.language)
        iv["ended"] = True


@app.post("/api/action")
def act(a: Action, x_project: str = Header(default="")):
    with project_for(x_project) as p:
        if p.version != a.version:
            raise CoachError(STALE)
        if a.kind == "decision":
            revisions = p.optimization["data"].revisions if p.optimization else []
            if a.id not in {r.id for r in revisions} or (a.choice == "edit" and not a.edit.strip()):
                raise CoachError("请检查输入内容及长度。")
            p.decisions[a.id] = {"choice": a.choice, "edit": a.edit.strip() if a.choice == "edit" else ""}
        else:
            coach = service(p, a.language)
            prepare(p, coach)
            if a.kind == "optimize":
                result, guides, blocked = coach.optimize(p.context)
                p.optimization = pack(result, guides, a.language, blocked=blocked)
                p.decisions = {}
            elif a.kind == "match":
                result, guides = coach.match(p.context)
                p.matching = pack(result, guides, a.language)
            else:
                interview_action(p, a, coach)
        p.version += 1
        return view(p)


@app.get("/art/atrium.svg")
def illustration():
    return FileResponse(ROOT / "assets/atrium.svg", media_type="image/svg+xml")


app.mount("/", StaticFiles(directory=ROOT / "frontend/dist", html=True, check_dir=False), name="web")

