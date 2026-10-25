# Voice server image. Build from the repository root: docker build -f voice_agent/Dockerfile .
# Only the locked dependencies and voice_agent are copied, so no evaluation questions or answers enter the image.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY voice_agent ./voice_agent

# Railway sets PORT.
CMD ["sh", "-c", "exec uv run --no-sync python -m voice_agent serve --host 0.0.0.0 --port ${PORT:-8000}"]
