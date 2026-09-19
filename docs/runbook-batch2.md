# Runbook: batch 2, ERP update and norm v4 (Saturday 18:00)

What arrives: 40 invoice PDFs, an ERP update (`erp_export_lote2.csv` for
`alberto_erp.py --lote2`), and "norma v4" in loose natural language, maybe as a new sheet of
the workbook like `Norma_Pagos_v3`. What leaves: `outcomes_lote2.jsonl` (one line per batch-2
PDF) and, if batch 1 changed, a new `outcomes.jsonl`. Nothing already decided is edited:
every change is a new decision row (ADR 0008).

**Which rules decide.** The delivery runs on the rule set compiled from `Norma_Pagos_v3` and
frozen on 2026-09-19 (`processes/invoice-payment/frozen/2026-09-19/`, 12 checks, 471/471 on
the golden). It lives in its own process, `Invoice payment - frozen 2026-09-19`, loaded by
`make load-frozen` with no LLM. The process named `Invoice payment` holds the hand-written
rules: never deliver from it, and never run `make demo` or `make activate` on the live
database (they activate the hand-written rules). Every command below names the frozen process:
`$P` over the API, `PACK=$FROZEN` for `make export-batch`.

Rehearsed on 2026-09-19 at 11:10 on a scratch database (`trace_freeze`) with the full OCR
path (local OCR, Gemini and Jev): batch 1 ingested through the API, then 40 batch-1 PDFs (30
text, 10 scans) under new names and with changed bytes as batch 2, an ERP sync and both
exports. Timings and what the rehearsal fixed are at the end.

## Roles

| Who | Does |
|---|---|
| **Driver** (one laptop, the one with the live database) | Types every command below, nothing else touches the database meanwhile |
| **Checker** | Reads each step's expected output aloud against what appeared; owns "stop" |
| **Álvaro** | Ingestion questions: scans, a PDF that does not read, the upload API |
| **Delivery** | The separate public repo `la-caja-outcomes` (never this repo) |

Rule of the evening: if an output differs from "Expect", stop and read the "If it fails"
column before typing anything else.

## 0. Variables

Run everything from the repository root.

```bash
API=http://localhost:${BACKEND_PORT:-8000}       # the backend `make setup` started
L2=$HOME/lote_2_sorpresa                         # the organisers' delivery, unpacked here
B1=.context/500-sombras-de-alberto/facturas      # batch 1
MANAGER='X-User-Id: 1'                           # check: curl -s $API/users (Martín, manager)
FROZEN=../processes/invoice-payment/frozen/2026-09-19/invoice-payment.json   # relative to backend/
P=$(curl -s $API/processes | python3 -c 'import json,sys; print(next(p["id"] for p in json.load(sys.stdin) if p["name"] == "Invoice payment - frozen 2026-09-19"))')
echo "frozen process: $P"                        # empty or an error: step 1 not done
```

Keep the delivery **outside** the repository and never inside `.context/` (read-only
challenge inputs). The challenge Makefile expects the CSV at
`.context/lote_2_sorpresa/erp_export_lote2.csv`; we pass an absolute path instead.

## Steps

| # | Command | Expect | If it fails |
|---|---|---|---|
| 1 | `git switch dev && git pull && make setup && make load-frozen`, then set `P` (section 0) | migrations up to date, `Ready: API at ...`; `Process 'Invoice payment - frozen 2026-09-19' (id N) ... 12 active in the process` | Port taken: `BACKEND_PORT=8001 make setup`. Never `make reset-db`. `load-frozen` runs the CLI on the host: it needs `.env` without a `TRACE_DATABASE_URL` pointing elsewhere |
| 1a | Only if the frozen process has no instances yet (`curl -s $API/processes/$P/summary`): `make erp` in another terminal, then `uv run --project backend --locked --env-file .env python tools/demo_run.py --api-url $API --process $P --output output/friday-run` | `run: {'decided': 500, ...}`; about 10 min, of which about 8 on the 29 scans | Without `--process $P` the driver picks the process named `Invoice payment` (hand-written rules). Check `.models/` and both manifests first (`docs/ingestion/setup.md`) |
| 1b | `curl -s $API/processes/$P/summary \| python3 -m json.tool \| head -20` | `by_status: {"DECIDED": 500}`, no `PENDING` | Pending instances: `curl -X POST $API/processes/$P/run` first |
| 1c | `make export-batch PACK=$FROZEN FILES=$B1 OUT=output/friday/outcomes.jsonl` | `OK: one line per file ...` with Friday's counts | Without `PACK=$FROZEN` it exports the hand-written process. This file is the reference to diff against later |
| 2 | `make backup` | `backups/trace-<time>.dump`, about 6.5 MB | Container name: `docker ps --format '{{.Names}}' \| grep db`, then `make backup DB_CONTAINER=<name>` |
| 3 | `ls $L2/facturas \| wc -l`; `comm -12 <(ls $B1 \| sort) <(ls $L2/facturas \| sort)` | `40`; nothing printed | A name shared with batch 1: stop and ask the organisers. Export keeps only the newest instance of a name (`X-Duplicate-Names`), so batch 1's file would change |
| 4 | Stop `make erp` (Ctrl+C), then `make -C .context/500-sombras-de-alberto erp-lote2 LOTE2_ERP=$L2/erp_export_lote2.csv` (keep it running) | `actualizacion cargada: N asientos nuevos, M actualizados` | `faltan columnas`: the CSV is not the ERP export format; ask. Port busy: `ERP_PORT=8010` and `TRACE_ERP_URL=http://127.0.0.1:8010` |
| 4b | `make -C .context/500-sombras-de-alberto erp-status`, then `curl -s -X POST $API/processes/$P/sources/erp/sync \| python3 -m json.tool` | `<actualizacion_cargada>SI`; sync `rows` (516 before the update), `stats.status.update_loaded: "SI"`, `diff` with `added` and `changed` entries | Not `make erp-sync`: it syncs the process named `Invoice payment` only. 502: nothing was written, the previous snapshot is still current (`docs/sources-http.md`); rerun. `SI` missing: the ERP started without `--lote2` |
| 5 | `curl -s -X POST "$API/processes/$P/reprocess?dry_run=true" \| python3 -m json.tool` | `unchanged`, `changes` (batch-1 invoices the ERP update changes, each with before/after/reason), `conflicts: []` | Conflicts: a person decided that invoice; the manager looks at each (`GET /instances/{id}`) and resolves again if needed. Reprocess never overrides a person |
| 5b | Same without `?dry_run=true` | same body; each change is a new engine decision, the old one stays | Run it **before step 7**: once batch 2 is in, it takes part in batch 1's duplicate check (same order on two invoices) |
| 6 | `python3 -c 'import json,sys; print(json.dumps({"text": open(sys.argv[1]).read()}))' $L2/norma_v4.txt > /tmp/norm.json` then `curl -s -X POST $API/processes/$P/norm -H "$MANAGER" -H 'Content-Type: application/json' --data @/tmp/norm.json \| python3 -m json.tool` | One norm rule per sentence, each with its `checks` (English text, decision, `interpretation`, `rule_id`) and `policies` | Norm arrives in the workbook: copy the sheet's text to `norma_v4.txt`. 502: the normalizer's model failed; retry once, then write the rule yourself (6d). If v4 repeats all of v3, send only the new sentences: the frozen checks already cover v3 |
| 6b | `curl -s $API/processes/$P/rules \| python3 -c 'import json,sys; [print(r["id"], r["status"], r["decision"], (r["report"] or {}).get("activation"), r["text"][:70]) for r in json.load(sys.stdin) if r["status"] != "active" or r["norm_rule_id"]]'` every 15 s | No `compiling` after about 2 min (the v3 norm took 105 s for 12 checks) | Still `compiling` after 4 min: `POST $API/rules/{id}/compile` (waits for it). Until none is `compiling`, `run` and `reprocess` answer 409 |
| 6c | For each new rule, by status: | | |
| | `active` | Compiled, tests passed: already enforced. The invoice use case has no share limit (`auto_activate_max_change: 1.0`, ADR 0004), so a valid rule activates whatever it changes; its impact is recorded as audit findings | Check, not a gate: read its `interpretation` (`GET /rules/{id}`) and what it changes (`GET $API/processes/$P/findings`). A wrong reading: retire it (`POST /rules/{id}/retire`) and use 6d |
| | `draft` with `activation.auto: false` | Valid code, but a decision taken by a person would change | `curl -s $API/rules/{id}/impact`: resolve those instances again, then `curl -X POST $API/rules/{id}/activate -H "$MANAGER"` |
| | `draft` with `valid: false` or `report.error` | Tests failed, or the model was down | `POST $API/rules/{id}/compile`; still failing: 6d |
| | `blocked` | The rule needs a symbol or source the process lacks (`report.needs_data`) | Enforced as ESCALAR for every instance it runs on. Decide before step 7: provide the data (new source / symbol) and recompile, or retire it (`POST /rules/{id}/retire`) if the norm does not really need it |
| 6d | Fallback: `curl -X POST $API/processes/$P/rules -H 'Content-Type: application/json' -d '{"text": "<the condition in English, symbols in backticks>", "type": "prohibition", "decision": "ESCALAR"}'` | status `compiling`, then as 6c | Retire the failed check first so it does not also run |
| 7 | `uv run --project backend --locked --env-file .env python tools/demo_run.py --api-url $API --process $P --invoices "$L2/facturas" --output output/lote2-run` (add `--book "$L2/<new>.xlsx"` if a new workbook came) | `workbook`, `erp sync`, upload progress, `run: {'decided': 40, ...}`; one to ten minutes depending on how many scans (about 10 s each, up to 66 s) | `--process $P` is mandatory (see step 1a). The driver also re-uploads the workbook and syncs the ERP: harmless, a new snapshot. `--output` must not be `output/`: that holds Friday's files. Export refused (409): something is PENDING; step 8 |
| 7' | Manual API alternative: `for f in $L2/facturas/*.pdf; do curl --fail-with-body -sS "$API/processes/$P/files" -H "$MANAGER" -F "file=@$f" -F 'ocr=true' > /dev/null; done; curl --fail-with-body -sS -X POST "$API/processes/$P/run"` | 201 per file; `{"decided": 40, ...}` | Check `.models/` and both manifests before scans; without weights, extraction may leave values unresolved. Preserve each response if OCR evidence is needed |
| 8 | `curl -s $API/processes/$P/summary \| python3 -m json.tool \| head -12`; `curl -s "$API/processes/$P/instances?status=PENDING"` | `PENDING` absent, `[]` | PENDING = no symbols: `POST /instances/{id}/extract` (Álvaro), then `POST /processes/$P/run` |
| 8b | `curl -s "$API/processes/$P/queue" \| python3 -c 'import json,sys; from collections import Counter; print(Counter(i["reason"][:40] for i in json.load(sys.stdin)))'` | ESCALAR reasons: `MISSING_DATA` (a scan field OCR could not corroborate: NIF, IBAN or order), `Same order as: ...` (duplicate order), the v4 rule | Any `RULE_ERROR` or `RULE_NEEDS_DATA`: a rule failed or is blocked; fix it (6c) and step 9 |
| 9 | Only if a rule was fixed after step 7: `curl -s -X POST "$API/processes/$P/reprocess?dry_run=true" -H 'Content-Type: application/json' -d "$(python3 -c 'import json,os,sys; print(json.dumps({"names": os.listdir(sys.argv[1])}))' $L2/facturas)"`, then without `dry_run` | Only batch-2 changes | `names` keeps batch 1 out of it |
| 10 | `make export-batch PACK=$FROZEN FILES=$L2/facturas OUT=output/delivery/outcomes_lote2.jsonl` | `40 lines for 40 PDFs`, `OK: one line per file, valid results {...}` | `missing`: a PDF with no instance (step 7 skipped it); `not a file of the batch (same as ... once normalised)`: accent spelled differently, tell Álvaro |
| 10b | `make export-batch PACK=$FROZEN FILES=$B1 OUT=output/delivery/outcomes.jsonl`; `diff <(sort output/friday/outcomes.jsonl) <(sort output/delivery/outcomes.jsonl)` | `500 lines`, `OK`; the diff shows exactly the changes of step 5 | A difference not listed in step 5: stop |
| 11 | Delivery: copy `output/delivery/outcomes.jsonl`, `outcomes_lote2.jsonl` and `albertitos_plan.pdf` to the root of `la-caja-outcomes`, `make check-outcomes OUT=<repo>/outcomes_lote2.jsonl FILES=$L2/facturas` (and batch 1), commit, push | Three files at the root, nothing else | Never commit them to this repo (`output/` is ignored) |

## Does norm v4 re-decide batch 1?

Not by itself. Activating a rule never edits a past decision: it records audit findings
(what would change, `GET /processes/$P/findings`). Batch 1's export changes only if we run
`reprocess` after activating it. **Default: do not** (the norm is for new invoices; the
findings show the team what it would have changed). If the norm or the organisers say it
applies to batch 1 too: step 5 again after step 6, with `names` = batch 1.

## Sunday: a datum of La Caja changes

1. `make backup`.
2. The new datum in its source: ERP (restart with the new CSV,
   `curl -X POST $API/processes/$P/sources/erp/sync`, read the diff) or workbook (`--book` in
   `demo_run.py` / `POST /processes/$P/sources/workbook`). A corrected PDF is a new file (new
   hash): ingest it; export keeps the newest instance of a name.
3. `POST /processes/$P/reprocess?dry_run=true`: the changes must be exactly the invoices that
   datum touches. Then without `dry_run`.
4. Steps 10, 10b, 11.

## Rollback

- **A rule** (v4 or a fallback) was wrong: `POST /rules/{id}/retire -H "$MANAGER"` (checked
  against past decisions like an activation), then `reprocess` to undo its decisions. The
  wrong decisions stay in the history, followed by the right ones.
- **The frozen set itself**: it is in git. On a new database, `make load-frozen` gives the
  same 12 checks with the same hashes (`manifest.json`); `test_frozen_rules.py` proves 471/471.
- **The database** is wrong beyond that: restore the dump of step 2 into a new database and
  point the backend at it, so the broken one stays for the post-mortem:

  ```bash
  docker exec trace-pay-db-1 psql -U trace -d trace -c "create database trace_restored"
  docker exec -i trace-pay-db-1 pg_restore -U trace --no-owner -d trace_restored < backups/trace-<time>.dump
  # .env: TRACE_DATABASE_URL=postgresql+psycopg://trace:trace@db:5432/trace_restored, then make setup
  ```
- **The ERP**: restart it without `--lote2` and sync again (step 4b); the snapshot before
  stays in the history either way.

## Rehearsal timings (2026-09-19, MacBook, local Postgres, ERP with its 0.12 s latency)

Full OCR path: local OCR (PP-OCRv5 primary and verifier), Gemini `gemini-3.1-flash-lite`,
Jev `jev-1.13.0`. The API ran from the host (`uvicorn`, port 8060) on `trace_freeze`,
not in Docker; the commands are the same.

| Step | Time | Notes |
|---|---:|---|
| Norm v3 from the sheet: normalize | 112 s | 6 norm rules, 12 checks (Helmcode `deepseek-v4-flash`) |
| Norm v3: compile all checks to a status | 105 s | 12/12 `active` at the first attempt; 471/471 on the golden |
| 1. `make load-frozen` | 1.8 s | 12 checks active, no LLM |
| 1a. Batch 1 through the API, full OCR (500 PDFs) | 564 s | 471 text PDFs in 2 s of extraction; 29 scans 478 s (p50 9.5 s, max 66 s, `fax_2026_0411.pdf`). PAGAR 450 / NO_PAGAR 42 / ESCALAR 8; the 471 text PDFs as the golden |
| 1b. Summary | 0.1 s | |
| 1c. `make export-batch` batch 1 | 0.9 s | `OK` 500/500 |
| 2. `make backup` | 0.6 s | 6.6 MB dump |
| 3. Name checks | 0.02 s | 40, no shared name |
| 4. ERP restart with `--lote2` | not run | No update CSV in the rehearsal and the ERP on :8009 was shared; measured before at 1 s |
| 4b. ERP status + API sync | 5.5 s | 516 rows, 26 pages, 3 `ORA-00600` retried, diff empty (no update loaded) |
| 5 / 5b. `reprocess` dry run, then for real | 0.9 s each | 500 unchanged (the ERP did not change) |
| 6. Norm v4 | not run | No v4 text; the v3 figures above are the reference |
| 7. `demo_run.py` over 40 PDFs (30 text, 10 scans) | 39 s | 10 scans in 28 s: faster than batch 1 because the pages were already read once (same images, new bytes). New scans: count about 10 s each. All 40 ESCALAR: each copy shares its order with its batch-1 original |
| 8 / 8b. Summary, pending, queue | 0.2 s | no PENDING; reasons `Same order as` and `MISSING_DATA` |
| 10. `make export-batch` batch 2 | 1.2 s | `OK` 40/40 |
| 10b. Export batch 1 and diff with Friday | 0.9 s | `OK` 500/500, no difference |
| 11. `make check-outcomes` both | 1.7 s | `OK` both |

For 40 PDFs, from the organisers' zip to the two checked files: about 15 minutes of commands
and reading, plus the norm v4 (about 4 minutes of models) and the scans (about 10 s each).

Found by the rehearsals and fixed:
- 2026-09-19 (first): the former `demo_run.py` crashed on a batch-2 PDF with the same bytes
  as a batch-1 one (the file is now stored once); there was no way to re-decide decided
  instances (`reprocess`) nor to export one batch (`make export-batch`).
- 2026-09-19 (full OCR): every command hard-coded process 1, and `demo_run.py` without
  `--process`, `make export-batch` without `PACK` and `make erp-sync` all act on the process
  named `Invoice payment`, which holds the hand-written rules, not the frozen set. The runbook
  now names the frozen process everywhere (`$P`, `PACK=$FROZEN`, sync through the API);
  batch-1 ingestion on a fresh database is step 1a; the scan timings are measured.
