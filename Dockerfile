# Frontend output is architecture-independent; build tools run natively even
# when verifying a different target architecture (esbuild cannot run under QEMU).
FROM --platform=$BUILDPLATFORM node:22-bookworm-slim AS build
WORKDIR /build
COPY versions/v1 /build/v1
COPY versions/v2 /build/v2
COPY versions/v3 /build/v3
COPY versions/claude /build/claude
COPY . /build/v4
RUN set -eu; for app in v1 v2 v3 v4 claude; do \
    cd /build/$app/frontend; npm ci; npm run build -- --base=/$app/; \
    done

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
COPY --from=build /build/v4/backend /srv/apps/v4/backend
COPY --from=build /build/v4/frontend/dist /srv/apps/v4/frontend/dist
COPY deploy/gateway.py /srv/gateway.py
RUN useradd -m coach && chown -R coach:coach /srv
USER coach
CMD ["sh","-c","exec uvicorn gateway:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1 --no-access-log"]
