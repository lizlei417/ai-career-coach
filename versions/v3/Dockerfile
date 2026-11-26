FROM node:22-bookworm-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /build
RUN git clone https://github.com/lizlei417/ai-career-coach-codex.git v1 && cd v1 && git checkout 6c7d74aefea1f4b14f9f44d0e6f14530550b7b84 && rm -rf .git
RUN git clone https://github.com/lizlei417/ai-career-coach-claude.git claude && cd claude && git checkout 4ef883244d9f11af0549b44e7fb341955a9151cc && rm -rf .git
RUN git clone https://github.com/lizlei417/ai-career-coach-codex.git v2 && cd v2 && git checkout b176cccb5121b783d7a163fafc9a7ae30218275c && rm -rf .git
COPY . /build/v3
RUN for app in v1 v2 v3 claude; do cd /build/$app/frontend && npm ci && npm run build -- --base=/$app/; done

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 COACH_APPS=/srv/apps
WORKDIR /srv
COPY deploy/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --from=build /build/v1/backend /srv/apps/v1/backend
COPY --from=build /build/v1/frontend/dist /srv/apps/v1/frontend/dist
COPY --from=build /build/v2/backend /srv/apps/v2/backend
COPY --from=build /build/v2/frontend/dist /srv/apps/v2/frontend/dist
COPY --from=build /build/claude/coach /srv/apps/claude/coach
COPY --from=build /build/claude/server.py /srv/apps/claude/server.py
COPY --from=build /build/claude/prompts /srv/apps/claude/prompts
COPY --from=build /build/claude/assets /srv/apps/claude/assets
COPY --from=build /build/claude/frontend/dist /srv/apps/claude/frontend/dist
COPY --from=build /build/v3/backend /srv/apps/v3/backend
COPY --from=build /build/v3/frontend/dist /srv/apps/v3/frontend/dist
COPY deploy/gateway.py /srv/gateway.py
RUN useradd -m coach && chown -R coach:coach /srv
USER coach
CMD ["sh","-c","exec uvicorn gateway:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1 --no-access-log"]
