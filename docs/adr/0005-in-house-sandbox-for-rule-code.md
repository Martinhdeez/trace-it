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
and the blind double compilation (ADR 0004) reduce but do not close that path.

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
`agentes/sandbox.py`:
- **Static check** before running: imports only from `decimal, datetime, re, math,
  unicodedata`; no `open, exec, eval, compile, getattr, globals, __import__...`; no name or
  attribute starting with `_`; no frame attributes (`gi_frame`, `f_globals`, `tb_frame`...);
  must define `evaluate`.
- **Restricted runtime:** builtins without forbidden names; `__import__` returns allowed
  modules as namespaces of their public, non-module attributes (so `re.enum.sys` does not
  exist); stdout captured; fresh namespace and decimal context per case.
- **Separate process:** `python -I -S -B`, empty environment, temp cwd, wall timeout (kill),
  `RLIMIT_CPU`, `RLIMIT_FSIZE=0`, and on Linux `RLIMIT_AS` 512 MB.
- **Batch execution** (`ejecutar_lote`): one subprocess for many cases; a bad case fails
  alone; a malformed result is an error, never "did not fire".

## Consequences
- No network, PID or filesystem namespace today. Accepted for code our own compilers write
  from approved rules during the hackathon.
- Next step: run the runner in a dedicated sandbox container with `network_mode: none`,
  read-only filesystem and no Docker socket, talking to the backend over stdin/stdout or a
  local socket. Move to nsjail or gVisor if untrusted code ever runs.
- Memory limit only on Linux (macOS has no `RLIMIT_AS`).

## Evidence
- 24 tests in `agentes/tests/test_sandbox.py` (6 functions, parametrised): valid rule;
  malformed results and exceptions; forbidden code rejected before running (dunder and
  underscore names, frame attributes, non-allowlisted imports); `re.enum.sys` is not
  reachable; infinite loop killed by timeout; one bad case in a batch fails only that case.
- Measured locally (macOS): one batch of 540 cases in ~0.1 s; ~20 ms per case when each
  case gets its own subprocess (`ejecutar`).

## Related
ADR 0003, 0004, 0010 (compiled extractors would reuse it). Plan P8; `docs/agents-plan.md` §5.
