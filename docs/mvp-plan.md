# trace-it: MVP plan

**Status:** proposal. Based on `docs/application-blueprint.md` (decisions P1-P23). Agents: `docs/agents-plan.md`.

## Goal
One process ("Invoice payment") working end to end in the application: ingestion, connectors, extraction, rules compiled by two agents, engine, history, escalation and export. Batch 1's `outcomes.jsonl` comes out of that flow and is correct. Everything specific to invoices (decision types, symbols, sources, rules) is entered as process data, not in code.

## Critical path (2026-09-19)
**The pass/fail filter comes first.** The critical path ends when comparing that `outcomes.jsonl` against the 433 clean cases and the 38 trap cases in `docs/invoice-payment-rules.md` shows no differences. That `outcomes.jsonl` comes from the hand-written v3 rules (`feat/reglas-v3-manuales`). Everything else ranks below that comparison.

While `data-ingestion` is not finished, we move forward on everything that does not depend on it:
1. **Mentor, first thing in the morning.** Confirm R01, R02, R07 and R08. Also confirm how to treat text with embedded instructions, with the files where our policy differs from hsdatos's: F26-2201_transportes, F26-3355, F26-7728, factura_5402, factura_6612, 2026-23904 and FA-3388. The list came from an external review; check it against the batch before taking it. Ask, do not copy another team's policy.
2. **Merge `feat/reglas-v3-manuales` and `fix/exportar-decision-motor` into `dev`.** They do not depend on `data-ingestion`.
3. **Generic HTTP API connector**, usable for any ERP (see "Sources: generic connector"). The challenge ERP is its first configuration.
4. **`outcomes.jsonl` with the hand-written rules**, in parallel with item 3. Until the real ERP snapshot exists, R12-R14 are evaluated against a snapshot prepared by hand from the challenge ERP data (it includes the 9 PAGADA orders). The final submission uses the real snapshot downloaded from the API, because the policy requires cross-checking with the ERP.
5. **If a check fails, the invoice never comes out PAGAR.** If the LLM fails, time runs out or a field is missing, the instance stays in `REVIEW` or is decided ESCALAR. It is a single check in the engine and is done together with item 4. The chaos tests (`--llm-down`, `--llm-429` and `--llm-timeout`) come later.
6. **Integrate `data-ingestion` when it is finished.** Merge it on its own, test the flow with a few invoices, then carry on.
7. **Regex templates for the native invoices left in `NEEDS_REVIEW` (202 of 501).** The LLM and human review are kept only for what is still open.

**Frozen until item 4 is out:** the travel-expenses process, the frontend and user roles.
**Off the critical path:** the two-agent compiler. It is shown in the demo, compared against the hand-written rules.
**Once the flow works:** chaos tests, cost in euros per invoice and per 10,000 invoices, ADRs 2-5 and the defence script (Varsovia).

### Sources: generic connector
No specific ERP goes into the code. A single HTTP API connector is configured per process in `sources.json` (see `docs/process-packs.md`). Each configuration declares:
- the base URL and authentication (expiring token with renewal);
- pagination;
- retries: transient errors, such as the challenge's ORA-00600, and 429 with `Retry-After`;
- the requests-per-second limit;
- the response format and its encoding (XML in ISO-8859-1 in the challenge);
- how each field maps to the columns the rules read.

The result is always a local snapshot stored as a new row of `sources`. Rules read that snapshot, never the API.

**Scope before H1:** the challenge ERP's configuration lives in `sources.json` from day one. The code only implements the options this ERP uses. When another ERP arrives, the code is extended behind the same configuration. That way the contract is already generic and the deadline risk is lower.

## Milestones
| Milestone | When | Definition of done |
|---|---|---|
| H0 Contracts | Friday night | `docker compose up` starts Postgres + FastAPI; schema created; signatures and endpoints agreed; everyone can work without waiting for anyone else |
| H1 Full flow | Saturday 10:00 | The 471 invoices with text go through ingestion, extraction, the v3 policy rules and the engine |
| H2 Batch 1 closed | Saturday 14:00 | 500 invoices, scans included, 0 in `REVIEW`, result reviewed against our analysis. Basic usable frontend |
| H3 Batch 2 | Saturday 18:00 onwards | Batch 2 + updated ERP + policy v4, all through the application |
| H4 Submission | Sunday 10:30 | Public repo with `outcomes.jsonl`, `outcomes_lote2.jsonl` and `albertitos_plan.pdf` |

## Repo structure
See `docs/team-guide.md` (organized by feature under `backend/app/features/`).

## Tables (source of truth: `backend/app/models.py` and the migrations)
- `users`: name, email, role (`manager`/`operator`).
- `processes`: id, name, description.
- `decision_types`: process, name, priority, default (`is_default`), requires a human (`requires_human`).
- `symbols`: process, name, type, description.
- `files`: hash (key), original name, bytes, extracted text, ingestion date.
- `sources`: process, source name (for invoices: `suppliers`, `orders`, `erp`, `parameters`), originating file or download, rows (`jsonb`).
- `instances`: process, file, name, status (`PENDING`, `REVIEW`, `DECIDED`), review reason, agreed symbols (`jsonb`).
- `extractions`: instance, role (`extractor_1`/`extractor_2`), symbols (`jsonb`), cost, latency.
- `rules`: process, text, type (`requirement`/`prohibition`), decision when it fires, code A, code B, tests A, tests B, hash, status (`draft`, `rejected`, `active`, `retired`), validation report, activation date.
- `decisions`: instance, result of each rule (`jsonb`), decision, hash of the rules applied, author (`engine` or a person), human kind (`resolution`/`review_correction`), reason.
- `findings`: decision, type (today `different_decision`), detail, rule that produced it.
- `events`: trace of everything (step, input, output, latency, retries, cost).
- `agent_config`: configuration versions of each agent role (model chain in PydanticAI `provider:model` format, settings, retries, request limit, prompt); rows are only appended and there is one active per role. Replaces `llm_config` (see `docs/agents-plan.md` §4).

## Division of work
| Person | Area | Deliverable |
|---|---|---|
| Martín | Agents: compiler (two agents, cross-tests), sandbox, escalation assistant (the F12 corrector is iteration 2); agent infrastructure on PydanticAI and its configuration (`docs/agents-plan.md`). Text of the v3 policy rules. Owns the filter | `features/agents/`, `features/llm/`, v3 rules |
| Mateo | Rules and decisions: rule life cycle, engine, decisions API, audit and findings; processes and users. Tasks in `docs/tasks-mateo.md` | `features/rules/`, `features/decisions/`, `features/processes/`, `features/users/` |
| Álvaro | Everything that comes in: ingestion (hash, `pdftotext`, render/OCR of scans), symbol extraction (double extraction with a PydanticAI agent on `features/llm/`, validators that never retry the model; `docs/agents-plan.md` §3.3), workbook connector (normalization). The generic HTTP API connector (ERP) is still unassigned, because Álvaro is on OCR | `features/ingestion/`, `features/extraction/`, `features/sources/` |
| Varsovia | Product and ideas: demo, ADRs, `albertitos_plan.pdf`, expected-results sheet for verification | Demo script, ADRs |
| Carlos | Frontend against the H0 endpoints (mock data until H1): processes, instances with trace, adding a rule that chains create → compile showing progress (compiling takes 30-60 s) and the report, manager's queue (types with `requires_human` and `REVIEW`), export | `frontend/` |

## Critical path and risks
1. **Text of the v3 policy rules (Martín, with Varsovia reviewing, before H1).** Deciding what each anomaly produces (NO_PAGAR or ESCALAR) is the biggest risk for the filter. There are open cases in `.artifacts/specs/2026-09-18-reglas-sistema.md`. Ask a mentor with concrete examples.
2. **Scans (29).** Besides the double extraction, they are reviewed by hand before H2.
3. **Final check before exporting:**
   - One line per file.
   - Exact names.
   - 0 instances in `REVIEW`.
   - Differences against the expected-results sheet reviewed one by one.
