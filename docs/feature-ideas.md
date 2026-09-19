# Feature ideas seen in the track

Features other solutions to the same challenge build, how they build them, and what each one
suggests for trace-it. Read from public repos on Saturday 19/09 morning; "Us" is our state on `dev`
at that time.

## Priority: adopt before the defence

Three features the strongest solutions show as their bonus. We adopt them as product features of the
invoice process, mentioned in passing; our bonus stays our own.

**Money at risk in the escalation queue.** Read-only summary over the escalated invoices: the total
amount at stake (each escalated file joined to its purchase order in the master), how many have no
known amount, and the queue ordered by amount with a running total and the share of money it covers.
The headline number is the smallest set of invoices that covers 80 % of the money (their run: 116,163.14
EUR in 45 escalations, 3 invoices cover 80 %, led by the 84,700 EUR outlier). No data shows
"PENDING", never a false zero. It never changes a decision. *Us:* `total` is already a symbol and the
escalation type is known, so this is a query and a panel on the queue; order the queue by it.

**Payment calendar and remittance draft.** For every PAGAR: due date = invoice date + the supplier's
payment terms from the master (30/45/60 days), grouped by ISO week, overdue marked against the cut-off
date (never the system clock). A remittance CSV per week with payee, IBAN, reference, amount and
execution date (max of due date and cut-off), control totals, and a warnings file for whatever cannot
be paid cleanly (missing terms or date, invalid or mismatched IBAN). Amounts with Decimal. Read-only.
Two facts from their run to know before building it: at the 18/09 cut-off 431 of 438 PAGAR are already
overdue, so the calendar shows mostly "overdue" unless the cut-off is moved; and none of the corpus
IBANs passes the mod-97 check digit, so a strict remittance is empty and theirs marks every line.
*Us:* no pack source reads the `Condiciones` column of the supplier sheet today; add it to the
workbook source, then the calendar is a read-only export beside `outcomes.jsonl`. Combined with the
money at risk, this is our prioritisation by due date and amount.

**What-if simulator.** Re-decides stored extractions in memory, without opening a document or calling a
model, under a named scenario: changed rule parameters ("tolerance 0.50"), changed policy thresholds,
or changed source data ("this ledger entry becomes PAGADA"). It lists the decisions that would change,
is saved as a scenario, and only an explicit "apply" turns it into real decisions (their 500 in 49 ms).
*Us:* the impact check on a rule change and the dry-run reprocess already do this for rules; what is
missing is overriding a source row or a threshold in a dry run, and naming and saving the scenario.

## Extraction

**Extraction ladder with per-rung numbers.** Each PDF climbs cheap to expensive: text layer, raster
plus QR, OCR with a calibrated word-confidence threshold, a local VLM, and a cloud model only for what
is left. Every rung records how many documents it resolved and its latency (471/500 stop at the text
layer in 0.4 ms). *Us:* double extraction with deterministic validators (ADR 0010). Worth adding: the
count and p50 per path in `scale-and-cost.md`, so the ladder is a number in the defence.

**Overlapping document detection.** On a scan, a fragment that names another supplier of the master
(exact name or tax id) raises a warning and the invoice goes to a person instead of being paid.
*Us:* not covered. Cheap as a rule over the extracted text if the scan text is kept as a symbol.

**Hardened master loading.** Amounts stored as text and duplicated purchase orders in the workbook are
normalised before anything decides. *Us:* check both cases against the workbook ingestion before batch 2.

**Same PDF under another name.** Identical bytes, different `file_id`. Solutions keyed only by sha256
overwrite the first file or stop, and either way one line is missing from the export. *Us:* files are
content-hashed (ADR 0008); add a test that two names with the same bytes give two instances and two
lines.

**Orchestrator agent per file and more input formats.** An agent receives any file, works out what it
is and plans its processing with tools. PDFs and images are read by a model with evidence and
confidence per field, XML invoices (Facturae) skip the reading, spreadsheets are mapped column by
column to suppliers, orders and ledger entries with learned profiles, and EML and ZIP files are opened
so each attachment goes back through the router. *Us:* the process is general, the inputs are PDF,
OCR and the workbook. Unpacking EML and ZIP and taking Facturae XML are cheap, and they answer the
rubric question about new file types with something that runs.

## Decision and review

**Review screen with the page beside the reading.** The escalated case shows the page image next to the
candidate values, and a person's correction to a field re-runs the decision. *Us:* decision review with
human approval (ADR 0021) and a document pane. Worth checking the pane shows the page image, not only
the text.

**Contingency at the deadline.** Any document still without facts when the export is due is escalated
with the reason "no validated facts", recorded and reversible, so the export is never blocked.
*Us:* covered by ADR 0016 (every instance gets a decision).

## Rules

**Rules read from messy workbooks.** An LLM reads spreadsheets, classifies what is a rule, drops
anything under 0.8 confidence, and has ten trap workbooks as tests. *Us:* the norm normalizer
(ADR 0017) plus compilation to tested code goes further. The one-line difference for the defence: they
read the rules of this process, we generate the whole process for any case.

**Live change and reprocess of the impacted.** In the demo the tribunal changes a value and the system
answers "N of 540 recalculated, M change". *Us:* impact check before activation and a dry-run
reprocess exist (`demo-logs/coverage/14-impact.json`, `15-reprocess-dry.json`); rehearse it live.

**Editable policy from the console.** The manager changes settings such as the extractor in use and
the reference date from the console, and the pipeline honours them on the next run. *Us:* runtime
configuration is versioned (ADR 0011); check the console exposes it.

## Resilience and delivery

**Failure switch in the demo.** A command takes the LLM down, new documents stay pending, nothing is
paid, and the circuit breaker shows on the dashboard; switching it back resumes without duplicates.
*Us:* fallback chain (ADR 0019) and ERP down run (`19-erp-down.json`). Worth a one-command version for
the stage.

**Audit gate before packaging.** The export refuses to be written while a delivery audit is red, and a
safe delivery of batch 1 is published early in the day. *Us:* export answers 409 while anything is
`PENDING`; consider publishing batch 1 before batch 2 arrives.

**Independent delivery verifier.** A separate tool that shares no code with the solution checks the
delivery from outside. It covers the contract (encoding, BOM, CRLF, strict JSON, exact `result`,
`file_id` normalisation, duplicates, missing and extra lines), runs seven plausible versions of the
organisers' private validator, fuzzes the JSONL with 40 mutations, rebuilds a second opinion per
invoice with its own parser and OCR, and checks the delivery repo (exactly three files, clean tree,
pushed). *Us:* golden e2e tests. Since validation is binary, the contract and repo checks are worth
copying before Sunday's 10:30 clone.

**Offline demo kit.** The demo database and cache travel to the presenting laptop with a manifest
checked on install, so the demo needs no network. *Us:* worth doing for the defence laptop.

## Presentation

**One source for every figure.** A single file lists each number the defence quotes with its source,
and a check fails if the script and the measured data disagree (15 of 15 checks). *Us:* numbers live in
`scale-and-cost.md`; a check against the defence script is cheap.

**Plain-language mode and one-step start.** The whole UI in the manager's words and a single launcher,
plus a desktop wrapper. *Us:* the console is already for the manager; the launcher is the useful part.

**Per-document pipeline and usage panel.** Each document shows its pipeline stages with durations, a
diff between results, and a panel of AI usage and cost. *Us:* spans and `GET /processes/{id}/metrics`
have the data; a cost-per-document view in the console supports the cost row of the rubric.
