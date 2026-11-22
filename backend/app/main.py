"""FastAPI entry point."""
from __future__ import annotations

import logging
from typing import Any, Literal, Optional

from urllib.parse import urlsplit
from starlette._utils import get_route_path
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import m3 as coach, errors
from .config import FRONTEND_DIST, MAX_TEXT_CHARS, MAX_UPLOAD_BYTES, get_settings
from .errors import AppError
from .rag import index as kb
from .llm import ping
from .materials import fetch_job_posting, pdf_to_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("coach.api")

app = FastAPI(title="AI Career Coach API", version="1.0.0")
from . import cloud
cloud.install(app)

@app.middleware("http")
async def local_writes(request, call_next):
    origin = request.headers.get("origin")
    if request.method != "GET" and origin and urlsplit(origin).netloc != request.headers.get("host"):
        return JSONResponse(status_code=403, content={"error": {"code": "BAD_REQUEST"}})
    return await call_next(request)

Lang = Literal["zh-CN", "zh-TW", "en"]


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    log.info("request failed: %s", exc.code)  # code only; never payloads
    return JSONResponse(status_code=exc.status, content={"error": {"code": exc.code, "detail": exc.detail}})


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    log.error("unhandled error: %s", type(exc).__name__)
    return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL", "detail": ""}})


# ---------------------------------------------------------------- models

class PrepareReq(BaseModel):
    resume_format: Literal["pdf", "word", "text"] = "text"
    resume_text: str = Field(default="", max_length=MAX_TEXT_CHARS * 2)
    jd_text: str = Field(default="", max_length=MAX_TEXT_CHARS * 2)
    job_title: str = Field(default="", max_length=200)
    lang: Optional[Lang] = None
    user_stage: Optional[Literal["no_experience", "current_student", "recent_graduate"]] = None
    job_goal: Optional[Literal["internship", "job"]] = None


class FeatureReq(BaseModel):
    materials: dict[str, Any]
    lang: Optional[Lang] = None


class QuestionReq(FeatureReq):
    asked: list[dict[str, Any]] = []
    target_requirement: Optional[str] = None


class FeedbackReq(FeatureReq):
    question: dict[str, Any]
    answer: str = Field(default="", max_length=8000)
    history: list[dict[str, Any]] = []
    turns: list[dict[str, Any]] = []


class SummaryReq(BaseModel):
    materials: dict[str, Any] = {}
    lang: Optional[Lang] = None
    turns: list[dict[str, Any]]


class UrlReq(BaseModel):
    url: str


# ---------------------------------------------------------------- routes

@app.get("/api/health")
async def health():
    return {"ok": True, "llm": get_settings().public(), "kb": kb.status(), "prompts": coach.prompt_status()}


@app.get("/api/settings")
async def read_settings():
    return get_settings().public()


@app.post("/api/settings/test")
async def test_settings():
    return await ping()


@app.post("/api/extract/pdf")
async def extract_pdf(file: UploadFile = File(...), project_id:str=Form("workspace")):
    name = (file.filename or "").lower()
    if not (name.endswith(".pdf") or file.content_type == "application/pdf"):
        raise AppError(errors.FILE_TYPE, 415)
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    from starlette.concurrency import run_in_threadpool
    try:
        parsed = await run_in_threadpool(pdf_to_text,data)
    except AppError as error:
        if error.code!="PDF_NO_TEXT" or cloud.APP_ID!="codex_v3": raise
        from io import BytesIO
        from pypdf import PdfReader
        parsed={"text":"","pages":len(PdfReader(BytesIO(data)).pages),"warning":"PDF_NO_TEXT"}
    file_id=await run_in_threadpool(cloud.store_pdf,project_id,data)
    return {**parsed,"file_id":file_id}


@app.post("/api/extract/url")
async def extract_url(req: UrlReq):
    return await fetch_job_posting(req.url)


@app.get('/resume-font.ttf')
def resume_font():
    from .final_resume import FONT_PATH
    return FileResponse(FONT_PATH, media_type='font/ttf', headers={'Cache-Control': 'public, max-age=86400'})


@app.get('/api/workspaces/{id}/resume/final')
def final_resume(id: str):
    from .final_resume import compose
    return compose(cloud.read(id)['state'])


@app.get('/api/workspaces/{id}/resume/export')
def export_resume(id: str, format: Literal['pdf', 'docx'] = 'pdf'):
    from .final_resume import compose, pdf_bytes, docx_bytes
    text = compose(cloud.read(id)['state'])['text']
    content = pdf_bytes(text) if format == 'pdf' else docx_bytes(text)
    media = 'application/pdf' if format == 'pdf' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    return Response(content, media_type=media, headers={'Content-Disposition': f'attachment; filename="resume.{format}"'})


@app.post("/api/materials/prepare")
async def prepare(req: PrepareReq):
    return await coach.prepare_materials(req.resume_text, req.jd_text, req.job_title, req.lang, req.user_stage, req.job_goal, req.resume_format)


@app.post("/api/resume/optimize")
async def resume(req: FeatureReq):
    return await coach.resume_optimize(req.materials, req.lang)


@app.post("/api/match")
async def match(req: FeatureReq):
    return await coach.job_match(req.materials, req.lang)


@app.post("/api/interview/question")
async def iv_question(req: QuestionReq):
    return await coach.interview_question(req.materials, req.lang, req.asked, req.target_requirement)


@app.post("/api/interview/feedback")
async def iv_feedback(req: FeedbackReq):
    return await coach.interview_feedback(req.materials, req.lang, req.question, req.answer, req.history, req.turns)


@app.post("/api/interview/summary")
async def iv_summary(req: SummaryReq):
    return await coach.interview_summary(req.lang, req.turns, req.materials)


# ---- knowledge base (RAG)

@app.get("/api/kb")
async def kb_status():
    return kb.status()


@app.post("/api/kb/upload")
async def kb_upload(file: UploadFile = File(...)):
    raise AppError("KB_READ_ONLY", 403)


@app.delete("/api/kb/{name}")
async def kb_delete(name: str):
    raise AppError("KB_READ_ONLY", 403)


class SearchReq(BaseModel):
    task: Optional[Literal["resume_optimization", "job_matching", "mock_interview"]] = None
    query: str = Field(max_length=500)
    k: int = Field(default=4, ge=1, le=10)


@app.post("/api/kb/search")
async def kb_search(req: SearchReq):
    return {"connected": kb.status()["connected"], "results": kb.search(req.task or "", req.query, req.k)}


# ---------------------------------------------------------------- static frontend (production)

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    async def spa(path: str):
        if path.startswith("api/"): return JSONResponse({},404)
        target = FRONTEND_DIST / path
        if path and target.is_file() and FRONTEND_DIST in target.resolve().parents:
            return FileResponse(target)
        return FileResponse(FRONTEND_DIST / "index.html")
