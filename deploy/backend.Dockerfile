FROM python:3.12-slim-bookworm
ARG REVISION=local
LABEL org.opencontainers.image.source="https://github.com/Martinhdeez/trace-it" \
      org.opencontainers.image.revision=$REVISION
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 poppler-utils \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.10.10 /uv /bin/uv
WORKDIR /srv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./
COPY processes /processes
COPY tools/hiring_demo.py /srv/hiring_demo.py
COPY deploy/backend-start.sh /srv/backend-start.sh
COPY docs/production-api.md /docs/production-api.md
RUN useradd --uid 10001 --create-home trace \
    && mkdir -p /srv/.data /srv/.models \
    && chmod 755 /srv/backend-start.sh \
    && chown -R trace:trace /srv/.data /srv/.models
USER 10001:10001
CMD ["/srv/backend-start.sh"]
