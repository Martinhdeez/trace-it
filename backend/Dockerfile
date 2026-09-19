FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /srv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv PATH=/opt/venv/bin:$PATH
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ .
COPY processes/ /processes/
CMD ["sh", "-c", "alembic upgrade head && python -m app.cli seed-hiring /processes/travel-expenses.json && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
