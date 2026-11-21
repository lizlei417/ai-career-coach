"""Private workspace boundary. Roles, owner and application are chosen by the server."""

from contextlib import contextmanager
from contextvars import ContextVar
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from starlette._utils import get_route_path

load_dotenv(Path.home() / ".config/ai-career-coach/cloud.env")
from uuid import UUID, uuid4

import httpx
import psycopg
from psycopg.types.json import Jsonb
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

APP_ID = "claude"
identity = ContextVar("career_user")
BUCKET = "career-resumes-private"


def connect():
    return psycopg.connect(
        os.environ["DATABASE_URL"], prepare_threshold=None, connect_timeout=8
    )


@contextmanager
def workspace(write=False):
    with connect() as db:
        uid = identity.get()
        if write:
            db.execute(
                "select pg_advisory_xact_lock(hashtextextended(%s,0))", (uid + APP_ID,)
            )
        db.execute("set local role career_workspace")
        db.execute(
            "select set_config('career.uid',%s,true),set_config('career.app',%s,true)",
            (uid, APP_ID),
        )
        yield db


def counts(db):
    row = db.execute(
        """select count(*),count(*) filter(where user_id=%s and app_id='codex_v2')
        from career_private.calls where day=(current_timestamp at time zone 'Asia/Hong_Kong')::date""",
        (identity.get(),),
    ).fetchone()
    daily = int(os.getenv("V2_DAILY_LIMIT", "5"))
    site = int(os.getenv("SITE_DAILY_LIMIT", "20"))
    blocked = bool(db.execute("select 1 from career_private.billing").fetchone())
    return {
        "limit": daily,
        "remaining": max(0, daily - row[1]),
        "siteRemaining": max(0, site - row[0]),
        "blocked": blocked,
    }


def reserve_call():
    with connect() as db:
        db.execute("select pg_advisory_xact_lock(94576123)")
        status = counts(db)
        if status["blocked"]:
            raise HTTPException(402, "DeepSeek balance exhausted")
        if not status["siteRemaining"] or (
            APP_ID == "codex_v2" and not status["remaining"]
        ):
            raise HTTPException(429, "Daily AI request limit reached")
        return db.execute(
            """insert into career_private.calls(day,user_id,app_id)
            values ((current_timestamp at time zone 'Asia/Hong_Kong')::date,%s,%s) returning id""",
            (identity.get(), APP_ID),
        ).fetchone()[0]


def record_usage(call, tokens=None, blocked=False):
    with connect() as db:
        if blocked:
            db.execute("select pg_advisory_xact_lock(94576123)")
            db.execute(
                "insert into career_private.billing values(true) on conflict do nothing"
            )
        if type(tokens) is int:
            db.execute(
                "update career_private.calls set tokens=%s where id=%s", (tokens, call)
            )


def valid_id(value):
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", value):
        raise HTTPException(400, "Invalid project identifier")
    return value


class Snapshot(BaseModel):
    name: str = Field(max_length=120)
    revision: int = Field(ge=0)
    state: dict


def save(id, body):
    valid_id(id)
    with workspace(True) as db:
        row = db.execute(
            "select revision from career_private.projects where id=%s", (id,)
        ).fetchone()
        if (row[0] if row else 0) != body.revision:
            raise HTTPException(409, "Project changed. Reload before saving.")
        revision = db.execute(
            "select nextval('career_private.project_revisions')"
        ).fetchone()[0]
        db.execute(
            """insert into career_private.projects(user_id,app_id,id,name,revision,state)
            values (%s,%s,%s,%s,%s,%s) on conflict(user_id,app_id,id) do update
            set name=excluded.name,revision=excluded.revision,state=excluded.state""",
            (identity.get(), APP_ID, id, body.name, revision, Jsonb(body.state)),
        )
    return {"revision": revision}


def read(id):
    with workspace() as db:
        row = db.execute(
            "select name,revision,state from career_private.projects where id=%s",
            (valid_id(id),),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Project not found")
    return dict(id=id, name=row[0], revision=row[1], state=row[2])


def object_path(project, file_id):
    return f"{identity.get()}/{APP_ID}/{valid_id(project)}/{UUID(str(file_id))}.pdf"


def storage(method, path, data=None):
    secret = os.environ["SUPABASE_SECRET_KEY"]
    headers = {"apikey": secret, "Content-Type": "application/pdf"}
    if not secret.startswith("sb_secret_"):
        headers["Authorization"] = "Bearer " + secret
    return httpx.request(
        method,
        os.environ["SUPABASE_URL"].rstrip("/")
        + "/storage/v1/object/"
        + BUCKET
        + "/"
        + path,
        headers=headers,
        content=data,
        timeout=30,
    )


def store_pdf(project, data):
    file_id = uuid4()
    path = object_path(project, file_id)
    # Reserve the path before transmission so a lost acknowledgement is recoverable.
    with workspace(True) as db:
        db.execute(
            "insert into career_private.documents values(%s,%s,%s,%s)",
            (identity.get(), APP_ID, file_id, project),
        )
    with workspace(True) as db:
        if not db.execute(
            "select 1 from career_private.documents where id=%s", (file_id,)
        ).fetchone():
            raise HTTPException(409, "Workspace cleared")
        if not storage("POST", path, data).is_success:
            raise HTTPException(502, "PDF storage failed")
    return str(file_id)


def remove_object(path):
    response = storage("DELETE", path)
    if not response.is_success and response.status_code != 404:
        try:
            missing = str(response.json().get("statusCode")) == "404"
        except ValueError:
            missing = False
        if not missing:
            raise HTTPException(502, "Deletion incomplete. Retry.")


def erase(project=None):
    with workspace(True) as db:
        where, args = (" where project_id=%s", (project,)) if project else ("", ())
        rows = db.execute(
            "select id, project_id from career_private.documents" + where, args
        ).fetchall()
        for file_id, pid in rows:
            remove_object(object_path(pid, file_id))
        db.execute("delete from career_private.documents" + where, args)
        result = db.execute(
            "delete from career_private.projects" + (" where id=%s" if project else ""),
            args,
        )
        return {"deletedProjects": result.rowcount, "deletedDocuments": len(rows)}


async def verify(credential):
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            result = await client.get(
                os.environ["SUPABASE_URL"].rstrip("/") + "/auth/v1/user",
                headers={
                    "Authorization": credential,
                    "apikey": os.environ["SUPABASE_PUBLISHABLE_KEY"],
                },
            )
        if result.status_code != 200:
            raise HTTPException(
                401 if result.status_code in (401, 403) else 503, "Session unavailable"
            )
        user = result.json()
        if user.get("app_metadata", {}).get("coach_member") is not True:
            raise HTTPException(403, "Invitation required")
        return str(UUID(user["id"])), user["app_metadata"].get("coach_admin") is True
    except (ValueError, KeyError, httpx.HTTPError):
        raise HTTPException(503, "Authentication unavailable") from None


def install(app):
    @app.middleware("http")
    async def authorize(request: Request, next_handler):
        path = get_route_path(request.scope)
        if not path.startswith("/api/"):
            return await next_handler(request)
        credential = request.headers.get("Authorization", "")
        if not credential.startswith("Bearer "):
            return JSONResponse({}, 401)
        try:
            uid, admin = await verify(credential)
        except HTTPException as error:
            return JSONResponse({"detail": error.detail}, error.status_code)
        token = identity.set(uid)
        try:
            if (
                not admin
                and path.startswith("/api/kb")
                and request.method not in ("GET", "HEAD")
                and path != "/api/kb/search"
            ):
                return JSONResponse({"detail": "Administrator-managed guides"}, 403)
            response = await next_handler(request)
            response.headers["Cache-Control"] = "private, no-store"
            return response
        finally:
            identity.reset(token)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    @app.get("/auth-config")
    def config():
        key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
        if not key.startswith("sb_publishable_"):
            import base64, json

            try:
                payload = key.split(".")[1]
                if (
                    json.loads(
                        base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
                    ).get("role")
                    != "anon"
                ):
                    key = ""
            except Exception:
                key = ""
        return {"url": os.environ.get("SUPABASE_URL", ""), "key": key, "app": APP_ID}

    @app.get("/api/me")
    def me():
        return {"id": identity.get()}

    @app.get("/api/workspaces")
    def listing():
        with workspace() as db:
            return [
                dict(id=i, name=n)
                for i, n in db.execute(
                    "select id,name from career_private.projects order by id"
                )
            ]

    app.get("/api/workspaces/{id}")(read)

    @app.put("/api/workspaces/{id}")
    def write(id: str, body: Snapshot):
        if id != "draft":
            raise HTTPException(403, "Use the project editor")
        return save(id, body)

    @app.get("/api/documents/{file_id}")
    def download(file_id: UUID):
        with workspace() as db:
            row = db.execute(
                "select project_id from career_private.documents where id=%s",
                (file_id,),
            ).fetchone()
        if not row:
            raise HTTPException(404, "PDF not found")
        result = storage("GET", object_path(row[0], file_id))
        if not result.is_success:
            raise HTTPException(502, "PDF unavailable")
        return Response(result.content, media_type="application/pdf")

    @app.delete("/api/documents/{file_id}")
    def delete_document(file_id: UUID):
        with workspace(True) as db:
            row = db.execute(
                "select project_id from career_private.documents where id=%s",
                (file_id,),
            ).fetchone()
            if not row:
                raise HTTPException(404, "PDF not found")
            remove_object(object_path(row[0], file_id))
            db.execute("delete from career_private.documents where id=%s", (file_id,))
        return {"deletedDocuments": 1}

    if APP_ID == "codex_v2":

        @app.get("/api/quota")
        def quota():
            with connect() as db:
                return counts(db)

        @app.delete("/api/my-data")
        def clear_all():
            return erase()
