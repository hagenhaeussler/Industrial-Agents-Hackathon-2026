# Voice server image. Build from the repository root: docker build -f voice_agent/Dockerfile .
# Only locked dependencies, the code the server runs and the building.json files are copied. Evaluation questions and
# answers never enter the image: .dockerignore and .railwayignore keep them out of the build context.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY building_db ./building_db
COPY building_tools ./building_tools
COPY voice_agent ./voice_agent

# The buildings a conversation can select. The build context holds only building.json files from data/.
COPY data ./data

# Railway sets PORT.
CMD ["sh", "-c", "exec uv run --no-sync python -m voice_agent serve data --host 0.0.0.0 --port ${PORT:-8000}"]
