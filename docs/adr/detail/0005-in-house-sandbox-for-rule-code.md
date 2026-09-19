---
status: accepted
---

# Run rule code in an in-house sandbox: AST allowlist, restricted runtime, separate process

## Context
Rule code is written by our own LLM compilers (ADR 0003) and runs on every instance and in
every audit. It must be pure and deterministic, and it must not reach the network, disk,
clock or backend. The engine needs batches: 540 files × 12+ rules per run.

Threat model. The code is not written by an external attacker, but it is not trusted
either: (1) a model can write something harmful by mistake; (2) an indirect prompt
injection path exists: invoice text (e.g. `factura_1936`) → escalation assistant's
proposed rule → a manager approves it → compilers turn it into code. The manager's approval
and the blind tester (ADR 0004) reduce but do not close that path.

## Alternatives considered
- **Cloud sandboxes (E2B, Modal).**
  - Pros: strong isolation (microVMs), maintained by others.
  - Cons: network hop and cold starts per batch; an external dependency and API keys in
    the decision path; the offline demo breaks if the service is down.
- **RestrictedPython.**
  - Pros: mature compile-time restrictions.
  - Cons: same process as the backend (no timeout kill, no rlimits); needs guard functions
    for every attribute access; one more dependency to learn under deadline.
- **nsjail / bubblewrap / gVisor.**
  - Pros: kernel namespaces, real network and filesystem isolation.
  - Cons: Linux only (the team develops on macOS); setup time.
- **Container per run.**
  - Pros: strong isolation, `network_mode: none`.
  - Cons: ~1 s startup per run; needs the Docker socket inside the backend.
- **In-house: AST check + restricted builtins/imports + separate process (chosen).**
  - Pros: no dependency; milliseconds per batch; works on macOS and Linux; easy to test.
  - Cons: Python-level isolation only; an escape we did not foresee runs as the backend
    user with its network.

## Decision
`agents/sandbox.py`:
- **Static check** before running: imports only from `decimal, datetime, re, math,
  unicodedata`; no `open, exec, eval, compile, getattr, globals, __import__...`; no name or
  attribute starting with `_`; no frame attributes (`gi_frame`, `f_globals`, `tb_frame`...);
  must define `evaluate`.
- **Restricted runtime:** builtins without forbidden names; `__import__` returns allowed
  modules as namespaces of their public, non-module attributes (so `re.enum.sys` does not
  exist); stdout captured; fresh namespace and decimal context per case.
- **Separate process:** `python -I -S -B`, empty environment, temp cwd, wall timeout (kill),
  `RLIMIT_CPU`, `RLIMIT_FSIZE=0`, and on Linux `RLIMIT_AS` 512 MB.
- **Batch execution:** one subprocess for many cases; a bad case fails alone; a malformed
  result is an error, never "did not fire". `run_batch` takes explicit cases (compiler
  tests); `run_dataset` takes the instances plus the shared sources and population once,
  and the child derives each instance's `others`, so 500 instances cross the process
  boundary in one payload instead of 500 copies of the whole batch.

## Consequences
- No network, PID or filesystem namespace today. Accepted for code our own compilers write
  from approved rules during the hackathon.
- Next step: run the runner in a dedicated sandbox container with `network_mode: none`,
  read-only filesystem and no Docker socket, talking to the backend over stdin/stdout or a
  local socket. Move to nsjail or gVisor if untrusted code ever runs.
- Memory limit only on Linux (macOS has no `RLIMIT_AS`).

## Evidence
- 24 tests in `agents/tests/test_sandbox.py` (6 functions, parametrised): valid rule;
  malformed results and exceptions; forbidden code rejected before running (dunder and
  underscore names, frame attributes, non-allowlisted imports); `re.enum.sys` is not
  reachable; infinite loop killed by timeout; one bad case in a batch fails only that case.
- Measured on batch 1 (Linux): 500 instances × 16 rules through `run_dataset` in 1 s
  (`make demo`); `test_500_instances_run_each_rule_once` pins one subprocess per rule.
  Repeating the population per case (the earlier `run_batch` path) hit the 512 MB limit
  at 500 instances and escalated every invoice, which is why `run_dataset` exists.

## Related
ADR 0003, 0004, 0016.
