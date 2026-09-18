# HTTP sources (`sources.json`)

A process pack declares the external APIs its rules read in `processes/<pack>/sources.json`
(for `processes/invoice-payment.json`: `processes/invoice-payment/sources.json`). One generic
connector (`backend/app/features/sources/http_connector.py`) reads that configuration. The
challenge ERP is its first configuration. ADR 0013 records why it works this way.

**Rules never call the API.** A sync downloads everything and writes one new `sources` row
(a snapshot). The engine reads the latest snapshot per source name.

## Running it

| Command | Does |
|---|---|
| `make erp` then `make erp-sync` | Start the challenge ERP, then sync `erp` for the invoice process |
| `uv run python -m app.cli sources sync ../processes/invoice-payment.json [--source erp]` | Same, from `backend/` |
| `POST /processes/{process_id}/sources/{name}/sync` | Same, from the API. Returns counts, retries and the diff. `502 source_unavailable` if the sync failed |
| `GET /processes/{process_id}/sources/{name}/diff` | Latest snapshot against the one before it: `added`, `removed`, `changed` (`key -> field -> [before, after]`) |
| `uv run python -m app.cli sources fallback ../processes/invoice-payment.json` | Hand-made snapshot, see below |

`sources.json` is read again on every sync. A changed rate limit, retry count or timeout
applies to the next sync without a restart. Credentials live only in `.env`: `sources.json`
names the variables (`TRACE_ERP_USER`, `TRACE_ERP_PASSWORD`, `TRACE_ERP_URL`). The process
environment wins over `.env`.

## Guarantees

- **All or nothing.** A new snapshot is written only when every page arrived, the record
  count equals the total the API reports, and no key appears twice. Otherwise nothing is
  written, the previous snapshot stays current, and a `sync_source_failed` event records
  why.
- **Deterministic.** Rows are sorted by the key. Two syncs of an unchanged source produce
  identical rows (same `rows_hash`).
- **Traced.** Every sync writes a `sync_source` event with pages, requests, retries,
  logins, 429s, transient errors by code, timeouts, invalid responses, unconvertible values,
  duration, the row hash, the status fields and the diff summary.
- **Origin.** `erp:<ISO timestamp>|<base url>` for an API snapshot, `erp:manual-fallback`
  for the hand-made one.

## Format

```jsonc
{
  "sources": {
    "erp": {
      "type": "http",
      "base_url": {"env": "TRACE_ERP_URL", "default": "http://127.0.0.1:8009"},
      "format": {"type": "xml", "encoding": "iso-8859-1", "error_code_path": "codigo"},
      "auth": {
        "type": "form_token",               // POST a form, read a token, send it as a header
        "login_path": "/erp/login",
        "credentials": {"usuario": "TRACE_ERP_USER", "clave": "TRACE_ERP_PASSWORD"},
        "token_path": "token", "token_header": "X-ERP-Token",
        "lifetime_seconds": 900, "lifetime_path": "caduca_en_segundos",
        "max_uses": 300, "max_uses_path": "usos_maximos",
        "renew_margin_seconds": 60, "renew_margin_uses": 10,
        "expired_codes": ["SES-401"]
      },
      "pagination": {
        "path": "/erp/asientos", "page_param": "pagina", "first_page": 1, "page_size": 20,
        "records_path": "asientos/asiento", "total_path": "meta/total", "pages_path": "meta/paginas"
      },
      "key": "entry_id",
      "fields": {
        "entry_id": {"source": "id"},
        "date": {"source": "fecha", "convert": "date_dmy"},
        "amount": {"source": "importe", "convert": "decimal_comma"}
        // ...
      },
      "retry": {"max_attempts": 6, "retry_statuses": [500, 502, 503, 504],
                "transient_codes": ["ORA-00600"], "backoff_seconds": 0.2, "backoff_max_seconds": 5},
      "rate_limit": {"requests_per_second": 6, "max_retry_after_seconds": 30},
      "timeouts": {"connect_seconds": 3, "read_seconds": 15},
      "status": {"path": "/erp/estado",
                 "fields": {"entries": "asientos", "update_loaded": "actualizacion_cargada"}}
    }
  }
}
```

Paths such as `meta/total` are ElementTree paths inside the response document. The file is
validated whole (pydantic, unknown keys rejected) before anything is requested.

| Section | Behaviour |
|---|---|
| `auth` | Logs in before the first call. Renews the token early: `renew_margin_seconds` before it expires, or when only `renew_margin_uses` uses are left. When the login response states a lifetime or a use limit, the lower of that value and the configured one applies. Every authenticated request counts as a use, failed ones included, because the ERP counts them too. An `expired_codes` answer (or a 401 without a code) forces a new login and a retry |
| `pagination` | Requests pages from `first_page` until the page count at `pages_path`. That page count is the only stop condition implemented. A page must hold exactly the records its position implies (`page_size`, or the rest on the last page). A short page counts as a truncated response and is retried. If `total` or the page count change between pages, the sync aborts, because the source changed during the download |
| `fields` | Maps API elements to the column names the rules read. Conversions: `text` (trimmed), `decimal_comma` (`12.874,40` → `12874.40`), `date_dmy` (`31/01/2026` → `2026-01-31`). A value that does not convert is kept raw, and its column goes into the row's `_invalid` list. A missing element makes the response invalid |
| `retry` | `retry_statuses`, `transient_codes`, timeouts, transport errors and invalid responses (malformed XML, wrong structure, short page) are retried with exponential backoff and full jitter. After `max_attempts` failed attempts in a row the sync aborts; this is the circuit breaker. Any other non-200 answer (`ERP-400`, `ERP-404`, bad credentials) aborts at once |
| `rate_limit` | Spaces request starts at least `1 / requests_per_second` apart, logins and retries included. A 429 pauses every request for `Retry-After` seconds (capped at `max_retry_after_seconds`). The ERP also counts rejected requests, so the client never retries a 429 early |
| `timeouts` | Connect and read timeouts on every request. A timeout is retried |
| `status` | Optional unauthenticated health resource, read once per sync. Its fields go into the trace. If it fails, the error goes into the trace and the sync continues. For the ERP this shows whether the batch 2 update is loaded (`update_loaded: SI`) and how many entries it holds |

## Measured against the challenge ERP (batch 1, with its 0.12 s latency)

516 rows (507 `PENDIENTE`, 9 `PAGADA`) in 26 pages, about 5.3 s. 30 to 31 requests: status,
login, 26 pages and 2 to 3 retries of `ORA-00600`. No 429, no unconvertible values.
`make erp-sync` twice in a row gives an empty diff.

## Saturday update and Sunday changes

Restart the ERP with the update (`make erp-lote2` inside `.context/500-sombras-de-alberto`,
or `python3 alberto_erp.py --lote2 <csv>`), then sync again. The response and the `diff`
endpoint list the added, removed and changed entries. The trace shows
`status.update_loaded == "SI"`.

## Hand-made fallback (`erp:manual-fallback`)

`sources fallback` builds the `erp` rows from the data embedded in `alberto_erp.py`. The
file is read as text, never imported or modified. The rows match what the API returns
after conversion, and a test checks that. The fallback is for tests and for emergencies
only, for example running rules R13 to R15 while the ERP is down. **The final delivery
must use a snapshot downloaded from the API**, because the norm requires checking the ERP,
and the ERP changes during the weekend while the embedded data does not.

## Not generic yet

Each item below needs new code behind the same configuration once a second API needs it:
- auth other than form login returning a token in the body (OAuth, API keys, basic auth);
- cursor or offset pagination, or a stop condition other than a reported page count;
- JSON or CSV bodies;
- concurrent page downloads (sequential is fast enough at 10 req/s);
- incremental syncs (every sync downloads everything);
- a status field that invalidates a sync (it is only recorded).
