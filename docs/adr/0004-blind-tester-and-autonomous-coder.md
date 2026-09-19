---
status: accepted
---

# Verify generated rule code against a blind tester, and activate it by impact

## Context
Rule code is written by an LLM (ADR 0003). A single model can misread the rule, write a
bug, or write tests that confirm its own bug. Nobody on the team can review every
generated function before the batch 2 deadline, and one wrong outcome fails the challenge.
We also want rule changes (policy v4 on Saturday) to go in without a person reading code
or approving each rule: a person should only see what the system could not settle.

The first version ran two blind agents that each wrote code and tests, cross-ran
everything and kept code A. At runtime only one code ran anyway (ADR 0016), so the second
implementation only served as a test oracle, at the price of a second full compilation.

## Alternatives considered
- **One agent, its own tests.**
  - Pros: cheapest.
  - Cons: code and tests share the same misreading; passing its own tests proves little.
- **Two blind agents writing code + tests, cross-checked (previous version).**
  - Pros: interpretation differences surface as failing tests.
  - Cons: two implementations for one runtime code; on a failing cross-test nobody can
    say whether the code or the test is wrong, so every disagreement needs a person.
- **One agent plus human code review.**
  - Pros: a person sees the code.
  - Cons: does not scale; managers do not read Python.
- **A blind tester and a coder that iterates, with disputes and an impact gate (chosen).**
  - Pros: the oracle (tests) is written by an agent that never sees code; the coder
    fixes itself against it; disagreements are argued from the rule text and settled
    by the test's author; activation is automatic when the effect on history is small.
  - Cons: a misreading shared by both agents still passes; the impact gate and the
    decision history (ADR 0008) are the backstop.

## Decision
1. **Tester** (`TRACE_TESTER_MODEL`): writes at least 6 tests from the rule text, the
   process description, the symbols and a sample of the sources. It never sees code. Its
   output validator rejects malformed JSON, duplicated names, one-sided suites (every
   test fires, or none does) and instance keys that are not symbols.
2. **Coder** (`TRACE_COMPILER_MODEL`): gets the same context plus the tests and writes
   `evaluate`. Its output validator rejects code the sandbox refuses (`ModelRetry`,
   2 repairs). The code then runs on the tests in the sandbox; failures go back to the
   coder with its previous code (up to 4 attempts).
3. **Disputes**: the coder may object to a failing test, quoting the rule text. The
   tester re-reads the text (never the code) and keeps or corrects the expected result
   (up to 2 review rounds). Every review is kept in the report.
4. **Missing data**: either agent may answer `NeedsData` (which symbol or source is
   missing) instead of inventing a field. No code is stored; the manager sees why.
5. **Missing values**: a `None` the rule text and description do not cover makes the
   code raise, and the engine escalates the instance with `RULE_ERROR` (ADR 0016). The
   code never guesses, and a failure never pays.
6. **Activation**: a rule whose tests pass activates by itself when the impact check
   (ADR 0008) finds no decision taken by a person that would change, and changes at most
   `TRACE_AUTO_ACTIVATE_MAX_CHANGE` (5%) of the decisions already taken. Otherwise it
   stays a draft with the reason in `report.activation`, for a person to decide.
7. Models are `provider:model` strings; any PydanticAI provider works, and
   `helmcode:<model>` uses Helmcode's OpenAI-compatible API. The tester should be a
   different model family from the coder, so a shared misreading is less likely.

## Consequences
- Cost per rule: 1 tester run + 1 to 4 coder runs + 0 to 2 reviews; never per instance.
- A person is involved only by exception: no agreement, needs data, or high impact.
- The report (`rules.report`) holds the tests with their results, the attempts, the
  reviews and the activation decision: the audit trail of how the code was accepted.
- A hand-written rule (`processes/rules-v3/`) keeps `origin: hand-written` and is
  trusted because a person wrote and tested it.

## Evidence
- `agents/compiler.py`: `tester`, `coder` and `reviewer` Agents; `compile_text` (the
  loop, without the database); `run_tests`.
- `rules/service.py`: `_auto_activation` (impact gate) in `compile_rule`.
- 10 unit tests in `agents/tests/test_compiler.py` with scripted models: green on the
  first attempt (and the tester never sees code); the coder iterates on failing tests; a
  disputed test corrected by the tester; no agreement leaves the rule invalid; NeedsData
  from either agent; unknown symbols rejected; one-sided suites rejected; sandbox repair;
  still broken after the repairs returns 502.
- 3 API tests in `decisions/tests/test_audit.py`: a rule that changes nothing activates
  itself; one that changes 2 of 3 decisions waits for a person; NeedsData stays a draft
  without code.
- `make eval-compiler` runs the loop with real models on the 16 invoice rules and scores
  the code against the hand-written reference on the 471 golden instances, and the
  reference against the tester's tests.

## Related
ADR 0003, 0005, 0006, 0008, 0016.
