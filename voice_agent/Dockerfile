# Voice server image. Build from the repository root: docker build -f voice_agent/Dockerfile .
# Only locked dependencies, the code the server runs and one building.json are copied. Evaluation questions and
# answers never enter the image.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY building_db ./building_db
COPY building_tools ./building_tools
COPY voice_agent ./voice_agent

# The demo building the deployed agent talks about. Override with --build-arg BUILDING=data/<split>/<id>/building.json.
ARG BUILDING=data/dev/proc-factory-dev-003/building.json
COPY ${BUILDING} ./building.json

# Railway sets PORT.
CMD ["sh", "-c", "exec uv run --no-sync python -m voice_agent serve building.json --host 0.0.0.0 --port ${PORT:-8000}"]
