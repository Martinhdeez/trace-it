# Other Maisa teams and where we stand

Snapshot of Saturday 19/09 at 10:15, read from each team's public repo and the hackspain feed. It is a
snapshot: re-check before the defence.

## Our positioning

**Our headline feature is that trace-it is not an invoice system.** While solving Alberto's process it
builds a general one: a process pack in plain language (ADR 0007), agents that compile each rule to
Python and test it blind (ADR 0003, 0004), and a deterministic engine that runs any pack. A new process
is a new JSON file plus one compilation (the invoice norm, 6 sentences to 11 active rules, took 103 s,
`docs/scale-and-cost.md`), and `processes/travel-expenses.json` is the proof. This is
also what Maisa sells (digital workers described in natural language, with code generated and run in a
sandbox), so the tribunal knows exactly what it is looking at.

Layered extraction, prioritisation by due date and amount, and reprocessing only what a change impacts
go in the defence **in passing**, as things the system also does. Other teams already lead with them
(table below), so they cannot be what we are remembered for.

## Each team's headline feature

| Team (repo) | Headline feature | Batch 1 (PAGAR / NO_PAGAR / ESCALAR) | Overlap with us |
|---|---|---:|---|
| guluc3m (`guluc3m/hackspain26`) | 5-rung extraction ladder with measured numbers (text layer solves 471/500), and a review screen with the page image beside the reading, where Alberto's correction re-decides the invoice. Bonus: escalations ranked by money at risk (116,163.14 € in 45, 3 invoices cover 80 %) | 433 / 22 / 45 | Layered extraction, prioritisation by amount |
| hsdatos (`javiersaguar/HS-Maisa`) | Live `reprocess --impacted`: the tribunal changes a value and they show "N of 540 recalculated, M change", plus `chaos --llm-down` live. Motto: "the LLM extracts, the norm decides". Planned bonus: due-date calendar and remittance file | 443 / 9 / 48 (438 / 9 / 53 with their ADR-0011) | Reprocessing, prioritisation by due date, LLM never decides |
| la_interseccion (`lszefner/hackspain`) | `rules_ingestion`: reads messy Excel workbooks with an LLM, classifies rules, drops those under 0.8 confidence, 10 trap workbooks in tests | 431 / 20 / 49 | **Closest to our headline**: rules taken from documents instead of code |
| hUMAnos (`vegonza/Hackspain`) | Product web app: PDF viewer with extracted fields beside it, pipeline stages per document, result diff, AI usage panel | no outcomes seen | Console |
| De Despeñaperros Pabajo (`alexcerezo/maisa`) | None yet (DB model, `reglas.toml`) | none | none |

UPISTAS, Bacon queso and SebastianRicci have nothing that works yet.

## What this means for the defence

- **Show generalisation live.** Load a second process in front of the tribunal and let the agents compile
  its rules. If it only appears on a slide, la_interseccion's rule ingestion will look like the same idea.
- **Say the difference with la_interseccion in one line**: they read rules for this process; we generate
  the whole process, rules as tested code included, for any process.
- **Name the passing features with numbers**, since guluc3m and hsdatos will quote theirs.

## Traps other teams expect in batch 2

- The same PDF under another name (same sha256, different `file_id`): hsdatos cannot handle it today and
  calls it "a very plausible trap".
- Amounts as text and duplicated orders in the master workbook: guluc3m hardened their loader for both.
- Whether the final batch 1 delivery must use the new rule and ERP v2: hsdatos asked the mentors, no
  answer yet.
