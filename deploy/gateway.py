"""Mount the original applications under separate URL and Python namespaces."""

import importlib
import importlib.util
import os
from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

root = Path(os.environ.get("COACH_APPS", "/srv/apps"))
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


def codex(name):
    path = root / name / "backend/app/__init__.py"
    spec = importlib.util.spec_from_file_location("career_" + name, path)
    package = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = package
    spec.loader.exec_module(package)
    return importlib.import_module(spec.name + ".main").app


app.mount("/v1", codex("v1"))
app.mount("/v2", codex("v2"))
app.mount("/v3", codex("v3"))
app.mount("/v4", codex("v4"))
sys.path.insert(0, str(root / "claude"))
from server import app as claude_app

app.mount("/claude", claude_app)


@app.get("/healthz")
def health():
    return {"ok": True, "applications": ["v1", "v2", "v3", "v4", "claude"]}


@app.get("/")
def home():
    return RedirectResponse("/v3/")
