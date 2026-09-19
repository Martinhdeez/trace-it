# Langfuse as an optional OTLP export target (deferred)

Decided by Martín on 2026-09-19: not now. Recorded so it can be picked up later without
re-deciding.

## Idea

Send the spans we already emit (ADR 0018) to Langfuse as one more optional OpenTelemetry
target, the same way Phoenix (`OTEL_EXPORTER_OTLP_ENDPOINT`) and Logfire (`LOGFIRE_TOKEN`)
are optional today. No new span, no schema change: only where the OTLP exporter sends them.

## Why it is deferred

- It covers the LLM plane only (normalizer, tester, coder, assistant runs). Ingestion and
  execution spans would arrive but Langfuse has no useful view for them.
- It would be a fourth observability tool next to the `events` table, Phoenix and Logfire.
- It needs an account (cloud) or a heavy self-hosted stack (Postgres, ClickHouse, Redis, S3).
- Phoenix already shows the same LLM traces locally, in one container, with no account.

## How to add it later

Environment configuration only, in `configure_observability` (`backend/app/core/events.py`):

- When `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set, export OTLP/HTTP to
  `${LANGFUSE_HOST:-https://cloud.langfuse.com}/api/public/otel`.
- Authenticate with basic auth: header
  `Authorization: Basic base64(LANGFUSE_PUBLIC_KEY:LANGFUSE_SECRET_KEY)`.
- Neither key set: nothing changes, nothing leaves the process.
- Document both variables in `.env.example` next to `LOGFIRE_TOKEN`, and add a line to
  ADR 0018 saying the alternative was adopted.

Equivalent without code: `OTEL_EXPORTER_OTLP_ENDPOINT=<host>/api/public/otel` and
`OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic%20<base64>`, but that replaces Phoenix as
the target, so the two keys above are the better switch.
