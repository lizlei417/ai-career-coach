"""FastAPI entry point."""
from __future__ import annotations

import logging
from typing import Any, Literal, Optional

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import coach, errors
from .config import FRONTEND_DIST, MAX_TEXT_CHARS, MAX_UPLOAD_BYTES, allow_runtime_config, clear_api_key, get_settings, update_settings
from .errors import AppError
from .kb import kb
from .llm import ping
from .materials import fetch_job_posting, pdf_to_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("coach.api")

app = FastAPI(title="AI Career Coach API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

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
    resume_text: str = Field(default="", max_length=MAX_TEXT_CHARS * 2)
    jd_text: str = Field(default="", max_length=MAX_TEXT_CHARS * 2)
    job_title: str = Field(default="", max_length=200)
    lang: Lang = "zh-CN"


class FeatureReq(BaseModel):
    materials: dict[str, Any]
    lang: Lang = "zh-CN"


class QuestionReq(FeatureReq):
    asked: list[dict[str, Any]] = []
    target_requirement: Optional[str] = None


class FeedbackReq(FeatureReq):
    question: dict[str, Any]
    answer: str = Field(default="", max_length=8000)
    history: list[dict[str, Any]] = []


class SummaryReq(BaseModel):
    lang: Lang = "zh-CN"
    turns: list[dict[str, Any]]


class UrlReq(BaseModel):
    url: str


class SettingsReq(BaseModel):
    provider: Optional[Literal["openai", "anthropic"]] = None
    model: Optional[str] = Field(default=None, max_length=120)
    base_url: Optional[str] = Field(default=None, max_length=300)
    api_key: Optional[str] = Field(default=None, max_length=400)
    timeout: Optional[float] = Field(default=None, ge=10, le=300)


# ---------------------------------------------------------------- routes

@app.get("/api/health")
async def health():
    return {"ok": True, "llm": get_settings().public(), "kb": kb.status(), "prompts": coach.prompt_status()}


@app.get("/api/settings")
async def read_settings():
    return get_settings().public()


@app.post("/api/settings")
async def write_settings(req: SettingsReq):
    if not allow_runtime_config():
        raise AppError(errors.RUNTIME_CONFIG_DISABLED, 403)
    if req.base_url and not req.base_url.startswith(("http://", "https://")):
        raise AppError(errors.BAD_REQUEST, 422, "base_url must be http(s)")
    s = update_settings(**req.model_dump())
    return s.public()


@app.delete("/api/settings/key")
async def delete_key():
    if not allow_runtime_config():
        raise AppError(errors.RUNTIME_CONFIG_DISABLED, 403)
    clear_api_key()
    return get_settings().public()


@app.post("/api/settings/test")
async def test_settings():
    return await ping()


@app.post("/api/extract/pdf")
async def extract_pdf(file: UploadFile = File(...)):
    name = (file.filename or "").lower()
    if not (name.endswith(".pdf") or file.content_type == "application/pdf"):
        raise AppError(errors.FILE_TYPE, 415)
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    return pdf_to_text(data)


@app.post("/api/extract/url")
async def extract_url(req: UrlReq):
    return await fetch_job_posting(req.url)


@app.post("/api/materials/prepare")
async def prepare(req: PrepareReq):
    return await coach.prepare_materials(req.resume_text, req.jd_text, req.job_title, req.lang)


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
    return await coach.interview_feedback(req.materials, req.lang, req.question, req.answer, req.history)


@app.post("/api/interview/summary")
async def iv_summary(req: SummaryReq):
    return await coach.interview_summary(req.lang, req.turns)


# ---- knowledge base (RAG)

@app.get("/api/kb")
async def kb_status():
    return kb.status()


@app.post("/api/kb/upload")
async def kb_upload(file: UploadFile = File(...)):
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise AppError(errors.FILE_TOO_LARGE, 413)
    return kb.add(file.filename or "", data)


@app.delete("/api/kb/{name}")
async def kb_delete(name: str):
    return kb.remove(name)


class SearchReq(BaseModel):
    query: str = Field(max_length=500)
    k: int = Field(default=4, ge=1, le=10)


@app.post("/api/kb/search")
async def kb_search(req: SearchReq):
    return {"connected": kb.status()["connected"], "results": kb.search(req.query, req.k)}


# ---------------------------------------------------------------- static frontend (production)

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    async def spa(path: str):
        target = FRONTEND_DIST / path
        if path and target.is_file() and FRONTEND_DIST in target.resolve().parents:
            return FileResponse(target)
        return FileResponse(FRONTEND_DIST / "index.html")
