FROM oven/bun:1 AS web
WORKDIR /web
COPY web/ ./
COPY scripts/build-device-gate.ts /scripts/build-device-gate.ts
RUN set -eu; \
    if [ -f app/package.json ]; then app_dir=app; \
    elif [ -f mobile/package.json ]; then app_dir=mobile; \
    else echo 'No frontend package found in web/app or web/mobile' >&2; exit 1; fi; \
    cd "$app_dir"; \
    bun install --frozen-lockfile; \
    bun run build; \
    if [ "$app_dir" = app ] && [ -f src/camera/ar/deviceGatePage.ts ]; then bun /scripts/build-device-gate.ts; fi; \
    cp -R dist /web-dist

FROM python:3.12-slim AS app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
# The filtered context includes new packages when their owners publish them;
# optional core/bench/agent/demo/fixtures directories need not exist at M01.
COPY . .
RUN uv sync --frozen --no-dev
COPY --from=web /web-dist /app/web/app/dist
ENV STATE_DIR=/state \
    DATA_DIR=/app/data \
    TYB_PROFILE=kit_1_1_0 \
    PYTHONUNBUFFERED=1
EXPOSE 8000
# A single process owns WebSocket fan-out and SQLite coordination.
CMD ["sh", "-c", "exec uv run --no-sync uvicorn server.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
