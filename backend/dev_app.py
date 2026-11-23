"""Standalone V4 server with the same /v4/ routing as the combined gateway."""
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.main import app as career_app
app = FastAPI(docs_url=None, redoc_url=None)
app.mount('/v4', career_app)
@app.get('/')
def home():
    return RedirectResponse('/v4/')
