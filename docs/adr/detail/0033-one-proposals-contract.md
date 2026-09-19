---
status: accepted
---

# Send every agent proposal to the manager through one contract

## Context
Three agents propose changes to the manager, each with its own workflow: the escalation
assistant suggests a decision for an escalated case, the definition chat proposes rules,
sources and process settings, and the learning agent proposes new norms from resolved cases.
Before integration each had its own endpoints and screens, so the manager had three inboxes
and the audit had three shapes. The rule stays that an agent never changes a published
process or a decision by itself (ADR 0002).

## Alternatives considered
- **Keep one API and screen per channel.**
  - Pros: no new table; each workflow stays as it is.
  - Cons: three inboxes; three ways to trace who accepted what.
- **Merge the three workflows into one.**
  - Pros: a single code path.
  - Cons: resolving a case, reviewing a chat draft and adopting a learned norm have different
    checks; merging them would weaken each.
- **One proposal record and one inbox; accepting calls the channel's own workflow (chosen).**
  - Pros: one list, one accept and reject, one span shape; each workflow keeps its checks.
  - Cons: a thin dispatch layer and one more table.

## Decision
- One table, `proposals`: `channel` (`escalation`, `chat`, `learning`) × `kind`
  (`decision`, `rule`, `context`, `input`, `source`), with summary, rationale, evidence, the
  payload that accepting applies, and the agent that proposed it. Content never changes;
  only the settlement is written, once (`accepted`, `rejected` or `superseded`).
- Endpoints: `POST /instances/{id}/proposal`, `GET /processes/{id}/proposals`,
  `POST /proposals/{id}/accept`, `POST /proposals/{id}/reject`. Manager only.
- Accepting calls the channel's workflow: a decision resolves the instance (a new decision
  row); a chat item is reviewed on its draft; a learned rule must pass validation against
  past cases first; context and input changes are staged into the version draft. Nothing is
  published until the manager publishes the draft (ADR 0031).
- Every accept and reject writes an `accept_proposal` or `reject_proposal` span.

## Consequences
- The manager works one inbox (Revisión) whatever the agent.
- A `source` proposal records the idea; loading the source is still a separate action.
- Proposals are advice with evidence. Only the manager's action changes state.

## Evidence
- `backend/app/features/proposals/` (`model.py`, `service.py`, `router.py`), migration
  `0015_proposals.py`; 7 tests in `proposals/tests/test_api.py`.
- Producers: `proposals.service.propose_decision` (escalation), `processes/drafts.py`
  (chat), `learning/service.py` (learning).
- Console: Revisión, proposals inbox and explained escalation options (#119, #106).

## Related
ADR 0002, 0021, 0024, 0031, 0032; `docs/learning.md`, `docs/api.md`.
