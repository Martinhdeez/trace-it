# Feature ideas seen in the track

Features other solutions to the same challenge build, how they build them, and what each one
suggests for trace-it. Read from public repos on Saturday 19/09 morning; "Us" is our state on `dev`
at that time.

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

## Decision and review

**Review screen with the page beside the reading.** The escalated case shows the page image next to the
candidate values, and a person's correction to a field re-runs the decision. *Us:* decision review with
human approval (ADR 0021) and a document pane. Worth checking the pane shows the page image, not only
the text.

**Escalations ranked by money at risk.** The escalation queue is ordered by amount, with the total at
stake and "reviewing these N invoices covers 80 % of the money". *Us:* planned as prioritisation by due
date and amount; mention it in passing.

**Due-date calendar and remittance file.** Payment due dates (30/45/60 days from the master's terms)
for the PAGAR invoices and a remittance file ready for the bank. *Us:* not built; fits the same
prioritisation work.

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

## Resilience and delivery

**Failure switch in the demo.** A command takes the LLM down, new documents stay pending, nothing is
paid, and the circuit breaker shows on the dashboard; switching it back resumes without duplicates.
*Us:* fallback chain (ADR 0019) and ERP down run (`19-erp-down.json`). Worth a one-command version for
the stage.

**Audit gate before packaging.** The export refuses to be written while a delivery audit is red, and a
safe delivery of batch 1 is published early in the day. *Us:* export answers 409 while anything is
`PENDING`; consider publishing batch 1 before batch 2 arrives.

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
