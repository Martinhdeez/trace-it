# Runbook: batch 2, ERP update and norm v4 (Saturday 18:00)

What arrives: 40 invoice PDFs, an ERP update (`erp_export_lote2.csv` for
`alberto_erp.py --lote2`), and "norma v4" in loose natural language, maybe as a new sheet of
the workbook like `Norma_Pagos_v3`. What leaves: `outcomes_lote2.jsonl` (one line per batch-2
PDF) and, if batch 1 changed, a new `outcomes.jsonl`. Nothing already decided is edited:
every change is a new decision row (ADR 0008).

Rehearsed on 2026-09-19 on a scratch database (`trace_rehearsal`) with 10 batch-1 PDFs under
new names, a two-row ERP update and a v4 rule in Spanish. Timings are at the end.

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

```bash
API=http://localhost:${BACKEND_PORT:-8000}       # the backend `make setup` started
L2=$HOME/lote_2_sorpresa                         # the organisers' delivery, unpacked here
B1=.context/500-sombras-de-alberto/facturas      # batch 1
MANAGER='X-User-Id: 1'                           # check: curl -s $API/users (Martín, manager)
```

Keep the delivery **outside** the repository and never inside `.context/` (read-only
challenge inputs). The challenge Makefile expects the CSV at
`.context/lote_2_sorpresa/erp_export_lote2.csv`; we pass an absolute path instead.

## Steps

| # | Command | Expect | If it fails |
|---|---|---|---|
| 1 | `git switch dev && git pull && make setup` | migrations up to date, `Ready: API at ...` | Port taken: `BACKEND_PORT=8001 make setup`. Never `make reset-db` |
| 1b | `curl -s $API/processes/1/summary \| python3 -m json.tool \| head -20` | `by_status: {"DECIDED": 500}`, no `PENDING` | Pending instances: `curl -X POST $API/processes/1/run` first |
| 1c | `make export-batch FILES=$B1 OUT=output/friday/outcomes.jsonl` | `OK: one line per file ...` with Friday's counts | This is the reference to diff against later |
| 2 | `make backup` | `backups/trace-<time>.dump`, about 5 MB | Container name: `docker ps --format '{{.Names}}' \| grep db`, then `make backup DB_CONTAINER=<name>` |
| 3 | `ls $L2/facturas \| wc -l`; `comm -12 <(ls $B1 \| sort) <(ls $L2/facturas \| sort)` | `40`; nothing printed | A name shared with batch 1: stop and ask the organisers. Export keeps only the newest instance of a name (`X-Duplicate-Names`), so batch 1's file would change |
| 4 | Stop `make erp` (Ctrl+C), then `make -C .context/500-sombras-de-alberto erp-lote2 LOTE2_ERP=$L2/erp_export_lote2.csv` (keep it running) | `actualizacion cargada: N asientos nuevos, M actualizados` | `faltan columnas`: the CSV is not the ERP export format; ask. Port busy: `ERP_PORT=8010` and `TRACE_ERP_URL=http://127.0.0.1:8010` |
| 4b | `make -C .context/500-sombras-de-alberto erp-status`, then `make erp-sync` | `<actualizacion_cargada>SI`; sync `vs snapshot K: {'added': N, 'removed': 0, 'changed': M}` and one line per changed entry | Sync failed: nothing was written, the previous snapshot is still current (`docs/sources-http.md`); rerun. `SI` missing: the ERP started without `--lote2` |
| 5 | `curl -s -X POST "$API/processes/1/reprocess?dry_run=true" \| python3 -m json.tool` | `unchanged`, `changes` (batch-1 invoices the ERP update changes, each with before/after/reason), `conflicts: []` | Conflicts: a person decided that invoice; the manager looks at each (`GET /instances/{id}`) and resolves again if needed. Reprocess never overrides a person |
| 5b | Same without `?dry_run=true` | same body; each change is a new engine decision, the old one stays | Run it **before step 7**: once batch 2 is in, it takes part in batch 1's duplicate check (R16) |
| 6 | `python3 -c 'import json,sys; print(json.dumps({"text": open(sys.argv[1]).read()}))' $L2/norma_v4.txt > /tmp/norm.json` then `curl -s -X POST $API/processes/1/norm -H "$MANAGER" -H 'Content-Type: application/json' --data @/tmp/norm.json \| python3 -m json.tool` | One norm rule per sentence, each with its `checks` (English text, decision, `interpretation`, `rule_id`) and `policies` | Norm arrives in the workbook: copy the sheet's text to `norma_v4.txt`. 502: the normalizer's model failed; retry once, then write the rule yourself (6d) |
| 6b | `curl -s $API/processes/1/rules \| python3 -c 'import json,sys; [print(r["id"], r["status"], r["decision"], (r["report"] or {}).get("activation"), r["text"][:70]) for r in json.load(sys.stdin) if r["status"] != "active" or r["norm_rule_id"]]'` every 15 s | No `compiling` after about 20 s per rule | Still `compiling` after 4 min: `POST $API/rules/{id}/compile` (waits for it) |
| 6c | For each new rule, by status: | | |
| | `active` | Compiled, tests passed, changes at most 5 % of past decisions: already enforced | Read its `interpretation` anyway (`GET /rules/{id}`) |
| | `draft` with `activation.auto: false` | Valid code, but it changes more than 5 % of batch 1 (rehearsal: 38/500) | `curl -s $API/rules/{id}/impact`: if every change is what the norm says, `curl -X POST $API/rules/{id}/activate -H "$MANAGER"`: it becomes active and writes the audit findings (`GET $API/processes/1/findings`) |
| | `draft` with `valid: false` or `report.error` | Tests failed, or the model was down | `POST $API/rules/{id}/compile`; still failing: 6d |
| | `blocked` | The rule needs a symbol or source the process lacks (`report.needs_data`) | Enforced as ESCALAR for every instance it runs on. Decide before step 7: provide the data (new source / symbol) and recompile, or retire it (`POST /rules/{id}/retire`) if the norm does not really need it |
| 6d | Fallback: `curl -X POST $API/processes/1/rules -H 'Content-Type: application/json' -d '{"text": "<the condition in English, symbols in backticks>", "type": "prohibition", "decision": "ESCALAR"}'` | status `compiling`, then as 6c | Retire the failed check first so it does not also run |
| 7 | `cd backend && uv run python ../tools/demo_run.py --invoices $L2/facturas --output ../output/lote2-run; cd ..` (add `--book $L2/<new>.xlsx` if a new workbook came) | `extraction: N read ..., M scans ...`, `erp sync: ...`, `run: {'decided': 40, ...}` | `--output` must not be `output/`: that holds Friday's files. Export refused (409): something is PENDING; step 8 |
| 7' | Álvaro's API instead: `for f in $L2/facturas/*.pdf; do curl -s -X POST $API/processes/1/files -H "$MANAGER" -F file=@"$f" > /dev/null; done; curl -s -X POST $API/processes/1/run` | 201 per file; `{"decided": 40, ...}` | Use the path batch 1 went through on the live database, so both batches are read the same way. Without `.models/`, scans come back with every symbol `None` (ESCALAR, `MISSING_DATA`), same as the demo path |
| 8 | `curl -s $API/processes/1/summary \| python3 -m json.tool \| head -12`; `curl -s "$API/processes/1/instances?status=PENDING"` | `PENDING` absent, `[]` | PENDING = no symbols: `POST /instances/{id}/extract` (Álvaro), then `POST /processes/1/run` |
| 8b | `curl -s "$API/processes/1/queue" \| python3 -c 'import json,sys; from collections import Counter; print(Counter(i["reason"][:40] for i in json.load(sys.stdin)))'` | ESCALAR reasons: `MISSING_DATA` (scans), the v4 rule, R16 duplicates, IBAN | Any `RULE_ERROR` or `RULE_NEEDS_DATA`: a rule failed or is blocked; fix it (6c) and step 9 |
| 9 | Only if a rule was fixed after step 7: `curl -s -X POST "$API/processes/1/reprocess?dry_run=true" -H 'Content-Type: application/json' -d "$(python3 -c 'import json,os,sys; print(json.dumps({"names": os.listdir(sys.argv[1])}))' $L2/facturas)"`, then without `dry_run` | Only batch-2 changes | `names` keeps batch 1 out of it |
| 10 | `make export-batch FILES=$L2/facturas OUT=output/delivery/outcomes_lote2.jsonl` | `40 lines for 40 PDFs`, `OK: one line per file, valid results {...}` | `missing`: a PDF with no instance (step 7 skipped it); `not a file of the batch (same as ... once normalised)`: accent spelled differently, tell Álvaro |
| 10b | `make export-batch FILES=$B1 OUT=output/delivery/outcomes.jsonl`; `diff <(sort output/friday/outcomes.jsonl) <(sort output/delivery/outcomes.jsonl)` | `500 lines`, `OK`; the diff shows exactly the changes of step 5 | A difference not listed in step 5: stop |
| 11 | Delivery: copy `output/delivery/outcomes.jsonl`, `outcomes_lote2.jsonl` and `albertitos_plan.pdf` to the root of `la-caja-outcomes`, `make check-outcomes OUT=<repo>/outcomes_lote2.jsonl FILES=$L2/facturas` (and batch 1), commit, push | Three files at the root, nothing else | Never commit them to this repo (`output/` is ignored) |

## Does norm v4 re-decide batch 1?

Not by itself. Activating a rule never edits a past decision: it records audit findings
(what would change, `GET /processes/1/findings`). Batch 1's export changes only if we run
`reprocess` after activating it. **Default: do not** (the norm is for new invoices; the
findings show the team what it would have changed). If the norm or the organisers say it
applies to batch 1 too: step 5 again after step 6, with `names` = batch 1.

## Sunday: a datum of La Caja changes

1. `make backup`.
2. The new datum in its source: ERP (restart with the new CSV, `make erp-sync`, read the
   diff) or workbook (`--book` in `demo_run.py` / `POST /processes/1/sources/workbook`). A
   corrected PDF is a new file (new hash): ingest it; export keeps the newest instance of a
   name.
3. `POST /processes/1/reprocess?dry_run=true`: the changes must be exactly the invoices that
   datum touches. Then without `dry_run`.
4. Steps 10, 10b, 11.

## Rollback

- **A rule** (v4 or a fallback) was wrong: `POST /rules/{id}/retire -H "$MANAGER"` (checked
  against past decisions like an activation), then `reprocess` to undo its decisions. The
  wrong decisions stay in the history, followed by the right ones.
- **The database** is wrong beyond that: restore the dump of step 2 into a new database and
  point the backend at it, so the broken one stays for the post-mortem:

  ```bash
  docker exec trace-pay-db-1 psql -U trace -d trace -c "create database trace_restored"
  docker exec -i trace-pay-db-1 pg_restore -U trace --no-owner -d trace_restored < backups/trace-<time>.dump
  # .env: TRACE_DATABASE_URL=postgresql+psycopg://trace:trace@db:5432/trace_restored, then make setup
  ```
- **The ERP**: restart it without `--lote2` and `make erp-sync`; the snapshot before stays
  in the history either way.

## Rehearsal timings (2026-09-19, MacBook, local Postgres, ERP with its 0.12 s latency)

| Step | Time | Notes |
|---|---:|---|
| Batch 1 from scratch (`demo_run.py`, 500 PDFs) | 28 s | PAGAR 433 / NO_PAGAR 36 / ESCALAR 31, as the golden |
| 2. `make backup` | 0.5 s | 5.3 MB dump |
| Restore of that dump into a new database | 0.3 s | 500 decisions back |
| 4. ERP restart with `--lote2` | 1 s | `517 asientos`, `actualizacion_cargada SI` |
| 4b. `make erp-sync` | 6 s | 26 pages, 2 `ORA-00600` retried; diff `added 1, changed 1` (`AS-00042 PENDIENTE -> PAGADA`) |
| 5. `reprocess` dry run, then for real | 1 s each | 499 unchanged, 1 change (`2026-01-12_P010.pdf` PAGAR -> NO_PAGAR, order paid) |
| 6. `POST /norm` (Helmcode `deepseek-v4-flash`) | 6 s | one norm rule, one check: `total` over 10,000 EUR -> ESCALAR; 2 policies |
| 6b. Compilation to a status | 15 s | `draft`: valid, but changes 38/500 past decisions (limit 5 %) |
| 6c. Impact, activate | 1 s each | 36 PAGAR -> ESCALAR, 2 NO_PAGAR -> ESCALAR; 38 findings |
| 7. `demo_run.py` over 10 batch-2 PDFs | 8 s | 9 read, 1 scan; all 10 ESCALAR (copies share their order with batch 1: R16) |
| 7'. Upload API, one text PDF / one scan | 0.06 s / 0.55 s | symbols filled / all `None` (no local OCR models) |
| 10, 10b. `make export-batch` | under 1 s each | `OK` for 10/10 and 500/500 |

For 40 PDFs, from the organisers' zip to the two checked files: about 15 minutes of commands
and reading, most of it step 6c (reading what v4 changes).

Found by the rehearsal and fixed in this change: `demo_run.py` crashed on a batch-2 PDF with
the same bytes as a batch-1 one (the file is now stored once); there was no way to re-decide
decided instances (`reprocess`) nor to export one batch (`make export-batch`).
