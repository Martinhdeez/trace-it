# Mateo's tasks: decision engine and rule life cycle

## Before you start
- Branch from `dev` once the skeleton PR (`feat/esqueleto-backend`) is merged: `git switch dev && git pull`.
- Read `docs/team-guide.md` (git and structure) and, from `docs/application-blueprint.md`: 3.6, 3.7, 3.8, P3, P7, P14, P15, P18, P19, P21.

## Your area
`backend/app/features/rules/`, `features/decisions/`, `features/processes/`, `features/users/`.
You do not touch `features/agents/` (Martín) or `features/ingestion/`, `extraction/`, `sources/` (Álvaro).

## Contract you use from Martín
```python
agents.sandbox.run(code, instance, sources, others) -> {"fires": bool, "reason": str}
```
It raises an exception on any error. Until it is done, use a fake runner in your tests (a function that takes the code and returns the result).

## Tasks (in order, each on its own branch with its own PR into `dev`)

### 1. `feat/motor` — `features/decisions/engine.py`
Pure function, no database and no LLM:
```python
decide(rules, priorities: dict[str, int], default: str, escalate: str,
       instance: dict, sources: dict, others: list[dict], run) -> Verdict
```
- Runs **every** active rule, each with `code_a` and `code_b`.
- If the two versions disagree or either fails: `REVIEW` with a reason. It never decides without that rule.
- If none fires: `default`. If several fire: the highest priority wins.
- The verdict includes the result of each rule (`rule_id`, `hash`, `fires`, `reason`) and the hash of the rule set.
- Tests: none fires; several fire and priority wins; A/B disagreement to `REVIEW`; exception to `REVIEW`.

### 2. `feat/decisiones-api` — service and endpoints
- `POST /processes/{process_id}/run`: for each `PENDING` instance with symbols, calls the engine with the current sources (latest load per name). Stores a row in `decisions` (`author` = `engine`) or moves the instance to `REVIEW`. Returns the count per decision.
- `GET /processes/{process_id}/instances?status=` and `GET /instances/{instance_id}`. The detail includes symbols, the decision history with the result of each rule, and the events.
- `GET /processes/{process_id}/queue`: instances in `REVIEW` plus those whose decision's type has `requires_human`. Optional filter `?type=`. No decision name fixed in code: the types belong to the process (`DecisionType.requires_human`, added in PR #5).
- `POST /instances/{instance_id}/resolve` with `{decision, reason}`: new decision with author = current user. The history only appends rows, never edits.
- `GET /processes/{process_id}/export`: one line per instance with its name and its decision. The challenge format (`outcomes.jsonl`) is `{"file_id": name, "result": decision}`; the code knows nothing about invoices, it only uses those two field names. Returns 409 if any instance is still `PENDING` or in `REVIEW`.
  - **Which decision is exported [DECIDED]:** the latest **engine** decision. A person's decisions carry a kind: `resolution` (resolves a case whose type has `requires_human`; never changes what is exported, P4) or `review_correction` (corrects an instance that was in `REVIEW`; exported if there is no engine decision).
  - **Duplicate names [DECIDED]:** only the most recent instance of each `name` is exported, with a warning if there were duplicates.
  - Done in `fix/exportar-decision-motor` (`Decision.human_kind`, header `X-Duplicate-Names`).

### 3. `feat/auditoria` — `features/decisions/audit.py` + check on activation
- `audit.check(session, process_id, proposed)` re-runs the active rules + the new one over the stored symbols of every decided instance. It does not re-read PDFs or call the ERP.
- Sorts each instance into three groups:
  - unchanged;
  - change (an engine decision that would change);
  - conflict (contradicts a decision a person validated).
- For each past decision that would change, it produces a finding (`Finding`) with the recorded decision and the one that would come out now (for invoices: paid when it should not have been, not paid when it should have been). No decision name fixed in code. It never modifies the past.
- `rules.service.activate` (and `retire`) use it: if there are conflicts, 409 and the rule does not go in.
- `GET /processes/{process_id}/findings` and `GET /rules/{rule_id}/impact`.

### 4. ~~`feat/seed-facturas`~~ — done
Covered by the quick setup (PR #11): `processes/invoice-payment.json` + `make setup`.

## Definition of done for every PR
- `uv run ruff check .` and `uv run pytest` green.
- Endpoints visible in `/docs`.
- Someone else reviews it before the squash merge.

If you change a shared model (`rules`, `decisions`, `instances`), generate the migration with `alembic revision --autogenerate` and tell the group.
