# Resilience and recovery

The jury asks how trace-it keeps state, avoids duplicates, degrades the service and recovers
the work when a provider fails. Every row below was run live on 2026-09-19 against a fresh
database, `trace_resilience`. The API ran on :8031 and a copy of the challenge ERP on :8039.
The LLMs were the real Helmcode models, and Gemini was the real provider. The outputs are in
[`demo-logs/resilience/`](../demo-logs/resilience/).

## Evidence

| Rubric point | Mechanism | Where in the code | Live evidence | ADR |
|---|---|---|---|---|
| **Keep state:** restart mid-compile | A saved rule is stored as `compiling` before any LLM call. At startup, `lifespan` re-queues every rule left in `compiling`. | `rules/service.py` `resume_compilations`, `main.py` `lifespan` | [04](../demo-logs/resilience/04-kill-mid-compile.txt): `kill -9` 5 s into the compile left rule 17 in `compiling`. After the restart it compiled in 6 s: `draft`, valid, 10 tests. | 0004 §7 |
| **Keep state:** restart mid-ingestion | Each upload is one transaction (file, instance, `ingest_document` span), so a killed upload leaves nothing half-written. The instance is unique on (process, name, sha256). | `ingestion/process_service.py` `existing_document`, `attach_document`; migration unique `uq_instances_process_id_name_file_hash` | [01](../demo-logs/resilience/01-kill-mid-ingestion.txt): `kill -9` after 68 of 500 uploads left 68 instances. After the restart, uploading the same PDF twice returned instance 68 with `created: false`. The rerun ended with 500 instances for 500 (name, sha256) pairs. | 0008, 0022 |
| **Keep state:** backup and restore | `make backup` runs `pg_dump -Fc`. A restore into a new database gives the same history. | `Makefile` `backup`; `docs/runbook-batch2.md` (restore) | [03](../demo-logs/resilience/03-append-only-and-backup.txt): 7.2 MB dump restored into `trace_resilience_restore`. The 7 tables compared have the same row counts, and the md5 of all 503 decisions matches. The export from the restored copy matches the live export on all 500 lines. | 0008 |
| **Keep state:** append-only decisions | The only writes to `decisions` are two INSERTs (`_append` for the engine, `resolve` for a person). `reprocess` appends a row only when the outcome changes. Each row points to an `executions` row that holds its inputs. | `decisions/service.py` `_append`, `reprocess`; `versions/execution.py` `capture` | [03](../demo-logs/resilience/03-append-only-and-backup.txt): after an ERP change, `reprocess` appended rows 501-503 and kept the md5 of rows 1-500. Both rows of `2026-03-28_P002.pdf` are still there (NO_PAGAR, execution 1; PAGAR, execution 5). | 0008, 0015 |
| **No duplicates:** same PDF twice | A per-file advisory lock serializes the upload, and the unique index rejects a second instance. A re-upload returns the stored reading. | `ingestion/process_service.py` | [01](../demo-logs/resilience/01-kill-mid-ingestion.txt), [02](../demo-logs/resilience/02-avoid-duplicates.txt): a decided PDF uploaded twice gives the same instance, `created: false`, `cache_hit: true`, and still 1 decision. | 0008 |
| **No duplicates:** run twice | `run` decides only `PENDING` instances, so a second run is a no-op. `reprocess` appends only changed decisions, by design. | `decisions/service.py` `run`, `reprocess` | [02](../demo-logs/resilience/02-avoid-duplicates.txt): two runs gave `decided: 0`. `reprocess` gave 500 unchanged. The table still holds 500 decisions, none duplicated. | 0008, 0016 |
| **No duplicates:** export | The export has one line per file name. `check-outcomes` verifies it. | `decisions/service.py` `export`; `cli.py` `check-outcomes` | [02](../demo-logs/resilience/02-avoid-duplicates.txt): 500 lines, 500 unique `file_id`, `check-outcomes` OK, golden 471/471. | 0016 |
| **No duplicates:** OCR provider calls | An extraction cache keyed by sha256 and the reader options sits first. Below it, a journal per page image replays a complete answer and blocks an uncertain one. | `ingestion/service.py` (cache), `ingestion/ocr/journal.py` | [10](../demo-logs/resilience/10-ocr-journal-no-double-call.txt): a second process re-read a scan that Gemini had already read with 0 provider calls. [09](../demo-logs/resilience/09-ocr-provider-down-and-recovery.txt) part A: an uncertain call was not repeated (`blocked_uncertain`, `network_attempted=false`). | 0022 |
| **No duplicates:** alerts | `alerts` is unique on (`decision_id`, `after`), and detection inserts with `ON CONFLICT DO NOTHING`. | `alerts/model.py`, `alerts/service.py` `_detect` | [02](../demo-logs/resilience/02-avoid-duplicates.txt): one ERP change gave 2 alerts. Syncing again and running detection twice by hand still gave 2. | 0026 |
| **Degrade:** LLM down | Deciding never calls an LLM. The rules are code that runs in the sandbox. | `decisions/engine.py`, `agents/sandbox.py` | [05](../demo-logs/resilience/05-llm-down-degrade.txt): with every model unreachable, 500 invoices were uploaded, decided and exported. Golden 471/471, 0 `llm_run` spans, 0 tokens, `run_process` in 858 ms. | 0002 |
| **Degrade:** a new rule's compile fails | The rule ends `draft` with `report.error` and an error `compile_rule` span. The draft fails validation ("Rule 30 has no validated code"), so it cannot be published. The published version keeps deciding. | `rules/service.py` `compile_in_background`; `versions/service.py` `validate` | [05](../demo-logs/resilience/05-llm-down-degrade.txt): rule 30 ended `draft` with "every model failed: deepseek-v4-flash …; qwen3.6 …; glm5.3 …". `reprocess?dry_run` reported 500 unchanged. **Not** `blocked`/`RULE_COMPILE_FAILED`: see Gaps. | 0031 (supersedes 0020's fail-closed item) |
| **Degrade:** OCR or Gemini down | A failed reader adds a warning (`VLM_ERROR`, `FOCUSED_READER_ERROR`) and leaves the fields null. The required symbols are then missing, so the engine escalates and never pays. | `ingestion/pdf/committee.py`, `decisions/engine.py` (`MISSING_DATA`) | [09](../demo-logs/resilience/09-ocr-provider-down-and-recovery.txt): Gemini answered HTTP 400 to 15 calls. `scan_010`, `scan_011` and `fax_2026_0411` were decided `ESCALAR` with `MISSING_DATA: issuer_nif, iban, …`. | 0016, 0022, 0025 |
| **Degrade:** ERP down | 6 attempts with backoff, then the sync gives up (502 `source_unavailable`). No snapshot is written, so the previous one stays current. `ORA-00600` and 5xx are retried. | `sources/http_connector.py` `_request`; `sources/service.py` `sync` | [08](../demo-logs/resilience/08-erp-down.txt): with the ERP killed, the sync failed in 11 s and snapshot 15 stayed current. Every healthy sync retried `ORA-00600` 2-3 times and completed. | 0013 |
| **Degrade:** health | `GET /health/planes` reports `ok`, `degraded` (error rate ≥ 5% or p95 over its limit) or `down` (≥ 50%) per plane over 15 minutes. | `traces/service.py` `health` | [05](../demo-logs/resilience/05-llm-down-degrade.txt): `agents degraded 2/18 spans failed`. [09](../demo-logs/resilience/09-ocr-provider-down-and-recovery.txt): ingestion stayed `ok` with 80 errors among 4,853 spans (see Gaps). | 0018 |
| **Recover:** first model down | Each role runs a `FallbackModel` chain. A provider error or a cut answer moves to the next model. The `llm_run` span records `chain`, `failed_attempts` and the model that answered. | `agents/llm.py` `chain`, `run` | [07](../demo-logs/resilience/07-llm-fallback-chain.txt): with `make demo-llm-down`, deepseek failed with "Connection error" and `glm5.3` answered. | 0019 |
| **Recover:** truncated output | A response with `finish_reason == "length"` counts as a failure and moves to the next model. | `agents/llm.py` `chain.truncated` | [07](../demo-logs/resilience/07-llm-fallback-chain.txt): a stub primary answered `length`, `failed_attempts` recorded "output token limit hit", and `glm5.3` answered. | 0019 |
| **Recover:** Helmcode 429 | The OpenAI SDK retries a 429 twice and honours `Retry-After`. The chain then moves to the next model. | `agents/llm.py`; OpenAI SDK `max_retries=2` | [07](../demo-logs/resilience/07-llm-fallback-chain.txt): a stub primary answered 429 with `Retry-After: 1`. The stub saw 3 requests, the span recorded `ModelHTTPError: status_code: 429`, and `glm5.3` answered. | 0019, 0020 |
| **Recover:** every model down | The failed rule stays a `draft` with the error. Once the provider is back, `POST /rules/{id}/compile` compiles it. The manager validates and publishes the draft, and stale-decision alerts list what the new rule changes. | `rules/service.py` `compile_rule`; `versions/service.py` `publish`; `alerts/service.py` `after_publish` | [06](../demo-logs/resilience/06-llm-recover-rule.txt): the recompile gave a valid rule 30 (8 tests) with impact 38 changes. Publishing made version 2 and rule 30 `active`. `detect_stale_decisions` created 38 alerts (36 PAGAR→ESCALAR, 2 NO_PAGAR→ESCALAR) in 1.1 s. | 0004, 0031, 0026 |
| **Recover:** OCR provider refused | A definite HTTP refusal (4xx, 503) is journaled as `refused`, and the next call for the page tries again. A timeout, a dropped connection or a 2xx whose body failed validation stays `uncertain_or_failed` and blocks. **Fixed in this branch.** | `ingestion/ocr/journal.py` `_recorded_call`; test `test_a_refused_call_is_retried_once_the_provider_is_back` | [09](../demo-logs/resilience/09-ocr-provider-down-and-recovery.txt): part A (dev) recorded 15 `uncertain_or_failed`, and after recovery the pending `scan_012` was still blocked. Part B (fix) recorded 15 `refused`. After recovery, `scan_012` was re-read: 2 Gemini calls returned 200 and the warnings dropped to `FIELD_AMBIGUOUS`. | 0022 |

## Gaps found live

1. **A failed compile no longer escalates.** ADR 0004 §7, ADR 0016, ADR 0020 ("Done") and
   the team guide say that a rule whose compile fails on save ends `blocked` and escalates
   every instance with `RULE_COMPILE_FAILED`. That was #64. Then #66 (ADR 0031, manager
   publication) removed `_block_failed`, and the rule now ends `draft` ([05](../demo-logs/resilience/05-llm-down-degrade.txt)).
   Nothing is enforced without a manager's publication, so the published rules keep
   deciding and the new check waits. ADR 0031 records this as intended ("replaces ADR 0020's
   automatic enforcement of failed draft compilations"). `RULE_COMPILE_FAILED` in
   `decisions/engine.py` is now reached only by rules blocked before #66. Code is unchanged.
   ADR 0019 is corrected here; the other documents still need it.
2. **A decided scan cannot be read again after an OCR outage.** In the delivery run
   (`trace_delivery`), Gemini answered 429 on `fax_2026_0411`, `scan_010` and `scan_011`,
   and all three were decided `ESCALAR` with `MISSING_DATA`. That fails closed. With the
   journal fix, a `PENDING` scan recovers on `POST /instances/{id}/extract`. A decided one
   does not: the extract returns 409 and a re-upload returns the stored reading ([09](../demo-logs/resilience/09-ocr-provider-down-and-recovery.txt)).
   The recovery path today is the escalation itself: a manager resolves the case.
   Proposal, not implemented because it changes the rule that a decided instance's evidence
   is final: let `extract` accept a `DECIDED` instance whose latest evidence carries a
   transient reader warning (`OCR_ERROR`, `VLM_ERROR`, `JEV_ERROR`,
   `FOCUSED_READER_ERROR`). It would append an `extract_document` span, and `reprocess`
   would append the new decision. The old decision keeps its inputs in `executions`, so no
   history is edited. Journal records written before this branch carry no HTTP status and
   still block. Delete them after checking their `provider_call` span (`http_status_code`
   4xx).
3. **The ingestion plane hides a provider outage.** Health is an error ratio over every
   span of the plane. 80 failed provider calls among 4,853 ingestion spans is 1.6%, so the
   plane shows `ok` ([09](../demo-logs/resilience/09-ocr-provider-down-and-recovery.txt)). A
   per-provider ratio, or `provider_call` spans counted on their own, would flag it. Not
   changed here: `traces/service.py` is being edited on `chore/mvp-polish`.
4. **Helmcode's limit is per key.** ADR 0020 cites 100 requests per minute per key and 5-10
   concurrent requests per model. Every model in the invoice chains uses the same Helmcode
   key, so falling back helps with a per-model concurrency 429 or one model being down, but
   not with the key's rate limit. Step H10 of ADR 0020 (a second key or provider in the
   chain) closes this.

## Live demo for the defense (5 commands)

After `make setup`, `make activate MANAGER_ID=1`, `make erp` (another terminal) and
`make demo`. `U` is Martín's id from `POST /login`.

```bash
# 1. Recover: the primary model is unreachable, the fallback answers (prints failed_attempts)
make demo-llm-down

# 2. No duplicates: the same PDF twice -> same instance_id, created=false
for i in 1 2; do curl -s -X POST localhost:8000/processes/1/files -H "X-User-Id: $U" \
  -F file=@.context/500-sombras-de-alberto/facturas/2026-01-08_P001.pdf | jq '{instance_id, created}'; done

# 3. No duplicate decisions: a second run decides nothing
curl -s -X POST localhost:8000/processes/1/run -H "X-User-Id: $U"      # {"decided":0,...}

# 4. Degrade: stop `make erp` (Ctrl+C), then sync -> fails, the previous snapshot stays current
make erp-sync

# 5. Health per plane: ok / degraded / down
curl -s localhost:8000/health/planes | jq -c '.[] | {plane, status, reason}'
```
