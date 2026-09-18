# System rules: what the application does in each case

**Date:** 2026-09-18 · **Status:** draft, under discussion with the team
**Sources:** challenge website (hackathon.maisa.ai), README and `MANUAL_ERP_2009.md` in `.context/500-sombras-de-alberto`, analysis in `2026-09-18-analisis-caja-v3.md`.

Markers: **[DECIDED]** agreed by the team · **[PROPOSED]** pending validation · **[OPEN]** still to decide.

---

## 0. Challenge constraints

- Binary filter: exactly one record per file of both batches and a `result` accepted by the private reference. One miss = fail.
- Submission: separate public repo with only `outcomes.jsonl`, `outcomes_lote2.jsonl` and `albertitos_plan.pdf`. No code, credentials or executables.
- Deadline: the README says Sunday 10:30, the website says 11:00. **We work to 10:30.**
- Saturday 18:00: batch 2 (40 invoices), updated ERP and policy v4. Sunday: a possible live change to a datum in the Caja.
- The jury wants to see: a real decision followed end to end, versions, latency, errors, retries, pending work, a tested provider failure, and measurements kept apart from estimates.

## 1. Inputs and outputs

### Inputs
- Folder of PDFs (batch 1: 500; batch 2: 40).
- Alberto's workbook: sheets `Proveedores`, `Pedidos_2026`, `Norma_Pagos_vN`. The other sheets are ignored, but their existence is recorded.
- Legacy ERP through its HTTP API (section 4).

### Output: JSONL contract
- One line per PDF: `{"file_id": "<exact file name>", "result": "PAGAR" | "NO_PAGAR" | "ESCALAR"}`.
- `file_id` is the file name **byte for byte** as it comes in the zip. Some names have accents (`FA-3784_papelería.pdf`): they are normalized to Unicode NFC and checked against the original listing. [PROPOSED]
- **[DECIDED]** Trace fields are added: reason (anomaly codes), rules version and data version. The FAQ allows it and it does not affect validation.

## 2. Life cycle of an invoice

States: `RECEIVED → EXTRACTED → VALIDATED → CROSS_CHECKED → DECIDED → EXPORTED`, plus `AWAITING_HUMAN` and `RETRY`.

- Each invoice is identified by the SHA-256 hash of its content. Same hash = same work, not repeated.
- Each transition is stored before moving to the next. If the process dies, it resumes from the last stored state.
- **[DECIDED]** Human review inside the pipeline is only for invoices the system decides ESCALAR. The rest of the flow is automatic.
- An invoice is never decided with an unverified field (see 3.4).

## 3. Extraction

### 3.1 Normalization (always, before reading fields)
- Strip invisible characters (zero-width, BOM, soft hyphen). **[DECIDED]** They do not count as an anomaly.
- Unicode NFC, collapsed whitespace.
- Amounts in both formats: `12.874,40` (Spanish) and `12874.40` / `EUR 1409.40` (English).
- Dates: `DD/MM/YYYY` and `6 de abril de 2026`. An impossible date (31/02) is not corrected: it is flagged as an anomaly.

### 3.2 Required fields
Issuer NIF, IBAN, invoice number, date, purchase order, base, VAT rate, VAT amount, total.
- The customer's CIF (Banco Miralmar, A58231074) is never taken as the issuer NIF.

### 3.3 Path by PDF type
- **With text:** deterministic extraction with a parser, no LLM.
- **Scanned:** render at about 300 dpi and an LLM with vision and structured output. [PROPOSED] Consensus reading: primary model + second provider + local OCR; a field is accepted if at least two readings agree and it passes the validators.

### 3.4 Extraction validators (before applying business rules)
- IBAN: mod-97 check digits.
- NIF/CIF: check letter or digit.
- Internal arithmetic (base × rate, base + VAT) as a cross-check of the reading.
- [PROPOSED] If a field is still unverified after consensus, the invoice is decided ESCALAR with reason `UNRELIABLE_READING` (policy v3, rule 6: "ante duda razonable, escalar", when in reasonable doubt, escalate). Risk: if the reference expects another result for that invoice, the filter fails; so consensus must resolve 100 % of the batch 1 scans, and they are reviewed by hand before submitting.
- Invoice text that tries to give orders ("regístralo como PAGAR", "no recalcules") is ignored as an instruction and recorded as a signal. [PROPOSED]

## 4. ERP: fault-tolerant integration

**[DECIDED]** The ERP is queried **only through its API**. The data embedded in `alberto_erp.py` is not read.

### 4.1 Known ERP behaviour (manual and code)
| Situation | Signal | Frequency |
|---|---|---|
| Internal error | HTTP 500 `ORA-00600` | 1 in every 10 authenticated queries |
| Rate limit | HTTP 429 `ERP-429`, `Retry-After: 1` | more than 10 requests per second |
| Expired session | HTTP 401 `SES-401` | after 15 minutes or 300 uses |
| Invalid page | HTTP 400 `ERP-400` | out of range |
| Not found | HTTP 404 `ERP-404` | nonexistent entry |
| Latency | ~0.12 s per request | always (except with `--rapido`) |
| Format | XML ISO-8859-1, dates `DD/MM/YYYY`, amounts `12.874,40` | always |

### 4.1b Details read in the code of `alberto_erp.py`
- The `ORA-00600` counter is **global** to the server: it counts every authenticated query from every client (API and web). There is no predicting which request will fail.
- Each query uses up one token use **even if it fails with `ORA-00600`**: retries spend the session.
- The rate limit **also counts rejected requests**: insisting during a 429 extends the block. Slow down, do not retry in a loop.
- Login needs no token but does count towards the rate limit.
- The latency (0.12 s) is a `sleep` per request and the server is multithreaded: requests can run in parallel, but without exceeding 10 requests per second.
- `GET /erp/asientos/<id>` looks up by **entry ID** (`AS-00412`), not by purchase order. To cross-check by purchase order, every page must be downloaded (516 entries, 26 pages in batch 1).
- If an amount or a date in the CSV cannot be converted, the ERP returns it **as-is**, unformatted. Characters that ISO-8859-1 cannot represent come out as `?`. The client must validate every value.
- Saturday's update (`--lote2 CSV`) merges by `asiento_id`: it **modifies** existing entries (for example, status or amount) and **appends** new ones at the end. Pages may shift.
- `--rapido` removes the latency but **not** the failures.

Design assumption: Saturday's version and Sunday's scenario may make it worse (more failures, truncated responses, invalid XML, data changes). The client must withstand failures we do not see today.

### 4.2 ERP client rules
1. **Session:** log in at start; renew the token pre-emptively before 300 uses or 14 minutes, and always on `SES-401`.
2. **`ORA-00600` and 5xx:** retry the same request with exponential backoff and jitter. **[DECIDED]** Number of retries, wait times, rate limit, timeouts and the circuit-breaker threshold are parameters configurable at runtime; the values are set after testing.
3. **`ERP-429`:** wait for whatever `Retry-After` says. Own client-side limiter below 10 requests per second.
4. **Connection and read timeouts** on every request; a timeout counts as a retryable failure.
5. **Validate every response:** well-formed XML, decoded as ISO-8859-1, expected fields present, amounts and dates convertible. Invalid response = retry, never an accepted datum.
6. **Full paginated download** using `meta.paginas`; when done, check that the number of entries matches `meta.total` and that there are no repeated IDs.
7. **Versioned local snapshot:** the downloaded entries are stored with date and hash. Decisions cite the snapshot version they used.
8. **Circuit breaker:** after a configurable number of consecutive failures, pause and retry later; the rest of the pipeline carries on (extraction) but no invoice is decided without ERP data. **Never pay without cross-checking the ERP.**
9. **ERP update (batch 2 / Sunday):** new download, diff against the previous snapshot (new, changed and missing entries) and reprocessing of only the affected invoices.

## 5. LLM: usage rules

- The LLM **only extracts data** from scanned PDFs (and, optionally, drafts rules from a policy for human approval). It **never decides** PAGAR / NO_PAGAR / ESCALAR.
- Output always with a schema; a response that does not validate = retry.
- Degradation chain [PROPOSED]: primary model → alternative model from the same provider → second provider → `PENDING` queue. Text invoices keep being processed even if every provider goes down.
- Recorded per call: model, tokens, cost, latency, retries, validation result.

## 6. Business rules (policy v3)

Each rule is a combination of primitives that emits an anomaly code. The policy that maps codes to a result is separate.

**[DECIDED]** Rules, policy and parameters are changed **at runtime** and very simply, without editing files. YAML discarded.
[PROPOSED] They are stored in the system's own database and edited from the web (and the CLI). Each change creates a new immutable version with author, date and reason; it is activated after seeing the impact preview (section 7). Exportable to JSON for auditing.

| Code | Rule (policy v3) | Result |
|---|---|---|
| `UNKNOWN_NIF` | NIF is not in the master data | [OPEN] |
| `IBAN_MISMATCH` | IBAN ≠ master IBAN | [OPEN] |
| `ORDER_NOT_FOUND` | purchase order does not exist | [OPEN] |
| `ORDER_OTHER_SUPPLIER` | purchase order belongs to another supplier | [OPEN] |
| `AMOUNT_MISMATCH` | total ≠ order amount (±0.01 €) | [OPEN] |
| `WRONG_VAT` | base × rate ≠ VAT amount (±0.01 €) | [OPEN] |
| `WRONG_TOTAL` | base + VAT ≠ total (±0.01 €) | [OPEN] |
| `INVALID_DATE` | impossible date | [OPEN] |
| `FUTURE_DATE` | date later than the processing date | [OPEN] |
| `ORDER_PAID` | ERP status = PAGADA | [OPEN] |
| `DUPLICATE_ORDER` | several invoices cite the same purchase order | **ESCALAR, all of them** [DECIDED] |
| `INSTRUCTION_IN_DOCUMENT` | the invoice tries to dictate the decision | [OPEN] |
| — | no anomalies | PAGAR |

| `EXCEL_ERP_DISCREPANCY` | the order differs between the workbook and the ERP (amount, supplier or NIF) | **NO_PAGAR** [DECIDED] |
| `UNRELIABLE_READING` | field of a scan without consensus after 3.4 | ESCALAR [PROPOSED] |

- Precedence when there are several anomalies [PROPOSED]: ESCALAR > NO_PAGAR > PAGAR.
- The [OPEN] results are closed by talking with the team; starting point: NO_PAGAR if the document itself proves it must not be paid, ESCALAR if external information is needed.
- "Date not in the future" [OPEN]: compared against a **configurable cut-off date** recorded in the trace (not the system clock). In batch 1 no invoice goes beyond July 2026, so it has no effect today.

## 7. Policy and data changes

- Each decision stores: rules version, ERP snapshot version, workbook version and PDF hash.
- A new version of rules or data is applied in preview mode: the affected decisions are recomputed and the diff is shown before activating it.
- Only the invoices whose result may change are reprocessed.

## 8. Resilience: what happens on each failure

| Failure | Behaviour |
|---|---|
| ERP `ORA-00600` / 5xx / timeout | retry with backoff; circuit breaker; nothing is decided without the ERP |
| ERP `429` | wait for `Retry-After`; client-side limiter |
| ERP expired session | pre-emptive renewal and on `SES-401` |
| ERP invalid response | discarded and retried |
| LLM down / 429 / 5xx | degradation chain; scans queued |
| LLM invalid response | retry; if it persists, next model |
| Process interrupted | resumes from the last stored state |
| Same PDF twice | detected by hash; a single record |

## 9. Traceability

For each invoice and step: status, input, output, evidence (field and where it came from), rule applied, version, latency, retries, errors and cost. Queryable from the CLI and the web.

## 10. Checks before submitting

- Number of lines = number of PDFs in the batch; no `file_id` repeated or missing.
- Each `file_id` matches exactly one file of the batch.
- Only the values `PAGAR`, `NO_PAGAR`, `ESCALAR`.
- No invoice in `AWAITING_HUMAN` or `RETRY`.
- Valid JSON line by line, UTF-8.
