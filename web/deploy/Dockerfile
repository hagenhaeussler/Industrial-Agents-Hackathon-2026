# Build from the repository root. .dockerignore excludes evaluation files and local build output.

FROM node:22-slim AS web
RUN npm install --global pnpm@11
WORKDIR /src
COPY packages/building-view packages/building-view
COPY web web
# The voice server's public URL. Railway passes the service variable of the same name.
ARG VITE_VOICE_SERVER
RUN cd packages/building-view && pnpm install --frozen-lockfile \
 && cd ../../web && pnpm install --frozen-lockfile && pnpm build

FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev
COPY building_api building_api
COPY building_db building_db
COPY building_tools building_tools
COPY data data
RUN uv run --no-sync python -m building_db import buildings.sqlite3 data/*/*/building.json > /dev/null && rm -rf data
COPY --from=web /src/web/dist web/dist
CMD uv run --no-sync python -m building_api serve buildings.sqlite3 --host 0.0.0.0 --port ${PORT:-8000} --web web/dist
