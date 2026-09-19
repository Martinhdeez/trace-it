---
status: accepted
---

# Compile each rule's text to free Python code with agents, not to a closed DSL

## Context
Rules are written in natural language by the business (the invoice pack has 16 rules for
norma v3; norma v4 arrives on Saturday 18:00, and a live change is possible on Sunday).
Rules are added, removed and reworded all the time, and the application must serve any
process (a second pack, `travel-expenses`, exists to prove it) without code changes. ADR 0002
requires rules to execute deterministically.

## Alternatives considered
- **Closed catalogue of primitives / rule DSL (rules as data: `equals`, `in_source`,
  `tolerance`...).** Proposed in `.artifacts/archive/2026-09-18-reglas-sistema.md` §6.
  - Pros: no generated code to secure; easy to render and diff; no LLM needed at runtime
    or at compile time.
  - Cons: every new kind of rule (duplicate across instances, cross-source discrepancy,
    date arithmetic) needs a new primitive written by a developer; a new process usually
    needs new primitives; defeats "no code changes per process".
- **Interpret the rule text with an LLM at runtime.** Rejected by ADR 0002.
- **Agents compile each rule to a free Python function (chosen).**
  - Pros: any rule expressible in Python; new processes need no code; compile cost is paid
    once per rule change, not per instance.
  - Cons: generated code must be sandboxed (ADR 0005) and verified (ADR 0004); code is
    harder to review than a DSL expression.

## Decision
Every rule is stored with its text, its kind and the decision type it produces, and is
compiled to one function with a fixed contract, identical for all rules and processes:

```python
def evaluate(instance: dict, sources: dict[str, list[dict]], others: list[dict]) -> dict:
    # returns {"fires": bool, "reason": str}
```

- `instance`: the instance's symbols. `sources`: latest load of each source of truth, by
  name. `others`: symbols of the other instances of the process (each with its name), for
  rules across instances such as "duplicate order".
- Pure: no network, disk, clock or randomness. A cut-off date is a source row, not
  `today()`.
- Rule kinds: a **requirement** fires when it does NOT hold; a **prohibition** fires when
  it holds.
- **The code never returns the decision.** It only says whether the rule fires and why.
  The decision type is a field of the rule, approved by a person. A compiler cannot make a
  rule PAY when the approved rule says NO_PAGAR.
- The process description (shared conventions: normalisation, units, tolerances, missing
  values) is given to the compiler with every rule, so rules do not repeat it.
- Compilation runs when a rule is created or changed (`POST /rules/{id}/compile`, chained
  by the UI; 30-60 s because of LLM calls).

## Consequences
- We run LLM-written code. That is only acceptable with ADR 0004 (verification) and
  ADR 0005 (sandbox).
- A rule's meaning is its text; the code is a derived artefact, identified by
  `hash(text, code)` and recompiled when the text changes.
- Ambiguous text produces ambiguous code. The fix is to clarify the text, not to edit
  code by hand.

## Evidence
- Contract enforced by the sandbox: `_validate` in `agents/sandbox.py` rejects any result
  that is not exactly `{"fires": bool, "reason": str}`.
- Compiler prompt and context: `agents/compiler.py` (`SYSTEM`, `_context`).
- Decision from the rule, not the code: `engine.decide` reads `rule.decision`.
- The 16 v3 rules hand-written against the same contract pass through the real sandbox
  and engine (`decisions/tests/test_rules_v3.py`, 5 tests).

## Related
ADR 0002, 0004, 0005, 0007. Plan P1, P8, P18, P19.
