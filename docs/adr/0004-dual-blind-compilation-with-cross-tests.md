---
status: accepted
---

# Verify generated rule code with two blind compilers and cross-tests

## Context
Rule code is written by an LLM (ADR 0003). A single model can misread the rule, write a
bug, or write tests that confirm its own bug. Nobody on the team can review every
generated function before the batch 2 deadline, and one wrong outcome fails the challenge.

## Alternatives considered
- **One agent, its own tests.**
  - Pros: half the cost and latency.
  - Cons: code and tests share the same misreading; passing own tests proves little.
- **One agent plus human code review.**
  - Pros: a person sees the code.
  - Cons: does not scale to every rule change; managers do not read Python.
- **Golden examples written by a person.**
  - Pros: independent ground truth.
  - Cons: someone must write them for every rule; not available for new rules at runtime.
- **Two blind agents with cross-tests and history agreement (chosen).**
  - Pros: interpretation differences surface as failing tests; independent of human time.
  - Cons: two compilations per rule change; a shared misreading still passes.

## Decision
1. Agents A and B (ideally different providers, including their fallback models) each
   write code and at least 6 tests **from the rule text and process context only**.
   Neither sees the other's work.
2. Self-repair: each agent may retry (2 rounds) and only sees **its own** errors (syntax,
   sandbox rejection, its own failing tests). It never sees the other agent's output.
3. Every test (A's and B's) runs against **both** codes. Cross failures reveal differences
   of interpretation; own failures reveal bugs.
4. Both codes run on the whole process history and must agree on every instance.
5. The rule can be activated only if the report is valid; otherwise the previous rule stays
   active and the manager clarifies the text and recompiles. We do not auto-pick a winner:
   a failing test does not say whether the code or the test is wrong.
6. At runtime both codes run; if they disagree or one fails, the instance goes to REVIEW
   with the reason. A failure or disagreement is our doubt, never an outcome: it is not
   mapped to a decision type such as ESCALAR (ADR 0009, 0014).

## Consequences
- Cost: two compilations per rule change, never per instance.
- Two agents that misread an ambiguous text the same way still pass; the impact report
  before activation (ADR 0008) is the backstop.
- **Known gap:** the engine today runs only code A (`engine.decide` calls
  `run(rule.code_a, ...)`), starts one subprocess per instance and rule, and sends
  a failed rule to the highest `requires_human` type (ESCALAR) instead of REVIEW. Fix
  pending in a PR for Mateo: run A and B with one `run_batch` per rule and code,
  compare, REVIEW on failure or disagreement.

## Evidence
- `agents/compiler.py`: `_agent` (blind agent and repair loop), `validate` (pure
  cross-check), `compile_rule` (A and B via `asyncio.gather`).
- 8 unit tests in `agents/tests/test_compiler.py`: agreement; cross-test failure;
  history disagreement; runtime error; `others` excludes the instance itself; end to end
  (both agents get the same context); one self-repair round whose repair message contains
  only the agent's own work; still broken after 2 repair rounds returns 502.
- `rules/service.activate` refuses a rule whose report is not `valid`.
- Engine cost of the fix, measured locally (macOS, `sandbox.run_batch`): today ~20 ms
  per case per rule with one subprocess each (≈2 min for 540 files × 12 rules, blocking the
  API); one batch per rule runs 540 cases in ~40 ms (~0.27 s with the full `others` list),
  so running both codes stays well under a second per rule.

## Related
ADR 0003, 0005, 0006, 0008, 0009, 0014. Plan P9, P21; `docs/plan-agentes.md` §3.1.
