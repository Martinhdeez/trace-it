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
6. The cross-check happens at compile time only. At runtime the rule runs **one** code,
   agent A's (`Rule.code`); B's code and tests stay in the rule's report as the evidence
   that validated it. A code that fails at runtime escalates the instance with the reason
   (ADR 0016). Running both codes per instance was tried and dropped: it doubled the
   sandbox cost for a disagreement the compile-time check already rules out.

## Consequences
- Cost: two compilations per rule change, never per instance.
- Two agents that misread an ambiguous text the same way still pass; the impact report
  before activation (ADR 0008) is the backstop.
- A hand-written rule (`processes/rules-v3/`) has no second implementation: its report says
  `origin: hand-written` and it is trusted because a person wrote and tested it.

## Evidence
- `agents/compiler.py`: the `compiler` Agent whose output validator runs the sandbox check
  and the agent's own tests (a failure becomes a `ModelRetry`, ADR 0006), `validate` (pure
  cross-check), `compile_rule` (A and B via `asyncio.gather`, B kept in
  `report["alternative"]`).
- 8 unit tests in `agents/tests/test_compiler.py` with scripted models: agreement;
  cross-test failure; history disagreement; runtime error; `others` excludes the instance
  itself; end to end (both agents get the same context); one self-repair round whose retry
  prompt contains only the agent's own error; still broken after 2 repair rounds returns 502.
- `rules/service.activate` refuses a rule whose report is not `valid`.
- Engine cost, measured on the 500 invoices of batch 1 (`make demo`, Linux): 16 rules,
  one subprocess per rule, one code each: 1 s for the whole run.

## Related
ADR 0003, 0005, 0006, 0008, 0014, 0016.
