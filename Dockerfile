FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app


ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1


COPY pyproject.toml uv.lock ./


RUN uv sync --frozen --no-install-project


COPY . .


ENV PYTHONPATH=/app/src:/app


CMD ["python", "scripts/start_qllm.py"]