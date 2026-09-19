"""Isolated execution of generated rule code (P8). Owner: Martín.

The code comes from an LLM, so it is checked and then run away from the backend:

- Static check (`check`): imports only from `ALLOWED_IMPORTS`, no names in `FORBIDDEN_NAMES`
  (`open`, `exec`, `eval`, `getattr`...), no `_`-prefixed names or attributes (blocks
  `().__class__.__bases__`-style escapes) and no frame attributes (`gi_frame`, `f_globals`...).
- Separate process: `python -I -S -B`, empty environment, cwd in a fresh temp dir, time
  limit (killed on timeout). On POSIX: CPU seconds, no file writes (RLIMIT_FSIZE=0) and,
  on Linux, 512 MB of address space (macOS does not support RLIMIT_AS).
- Inside that process the code gets builtins without the forbidden names, and an
  `__import__` that only returns the allowed modules as namespaces of their public,
  non-module attributes (so `re.enum.sys` does not exist). Stdout is captured, so `print`
  cannot corrupt the result.
- Determinism: no clock, randomness, disk or environment is reachable, since `time`,
  `random`, `os`... are not importable. Each case runs in a fresh namespace with a fresh
  decimal context.

Not isolated: there is no network, PID or filesystem namespace. Network and disk are
blocked only by the import allowlist and the builtins filter; a Python-level escape we did
not foresee would run with the backend's user and network.
# ponytail: import allowlist + rlimits is enough for code our own compiler generates during
# the hackathon; to run untrusted code, move the runner into nsjail or a throwaway container.
"""

import ast
import json
import subprocess
import sys
import tempfile
from typing import Any

from app.common.exceptions import TraceError

ALLOWED_IMPORTS = {"decimal", "datetime", "re", "math", "unicodedata"}
FORBIDDEN_NAMES = {
    "__import__", "exec", "eval", "compile", "open", "input", "globals", "locals", "vars",
    "getattr", "setattr", "delattr", "breakpoint", "help", "exit", "quit",
}  # fmt: skip
FORBIDDEN_ATTRIBUTES = {
    "gi_frame", "gi_code", "cr_frame", "cr_code", "ag_frame", "ag_code", "tb_frame",
    "tb_next", "f_back", "f_globals", "f_locals", "f_builtins", "f_code",
}  # fmt: skip
MAX_MEMORY = 512 * 1024 * 1024
MAX_MESSAGE = 500

# Runs in the child. Accepts either explicit cases or a compact shared dataset, and writes
# one result per evaluated instance on stdout.
_RUNNER = """
import builtins, decimal, io, json, sys, types
ALLOWED_IMPORTS = %r
FORBIDDEN_NAMES = %r
_import = builtins.__import__

def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level or name not in ALLOWED_IMPORTS:
        raise ImportError("import not allowed: " + name)
    module = _import(name)
    return types.SimpleNamespace(**{
        k: v for k, v in vars(module).items()
        if not k.startswith("_") and not isinstance(v, types.ModuleType)
    })

safe = {k: v for k, v in vars(builtins).items() if k not in FORBIDDEN_NAMES}
safe["__import__"] = safe_import
class MissingValidationSymbol(Exception):
    def __init__(self, name):
        self.name = name

class ValidationInstance(dict):
    def __init__(self, values, missing):
        super().__init__(values)
        self._missing = set(missing)

    def __getitem__(self, key):
        if key in self._missing:
            raise MissingValidationSymbol(key)
        return super().__getitem__(key)

    def get(self, key, default=None):
        if key in self._missing:
            raise MissingValidationSymbol(key)
        return super().get(key, default)

    def __contains__(self, key):
        if key in self._missing:
            raise MissingValidationSymbol(key)
        return super().__contains__(key)

out, sys.stdout = sys.stdout, io.StringIO()
data = json.load(sys.stdin)
code = compile(data["code"], "<rule>", "exec")
if "cases" in data:
    cases = data["cases"]
else:
    sources = data["sources"]
    population = data["population"]
    missing = data.get("validation_missing", {})
    cases = (
        (ValidationInstance(instance, missing[str(key)]) if str(key) in missing else instance,
         sources, [
             ValidationInstance(symbols, missing[str(other_key)])
             if str(other_key) in missing else symbols
             for other_key, symbols in population if other_key != key
         ])
        for key, instance in data["instances"]
    )
results = []
for instance, sources, others in cases:
    decimal.setcontext(decimal.Context())
    try:
        ns = {"__builtins__": safe, "__name__": "rule"}
        exec(code, ns)
        results.append(json.dumps({"ok": ns["evaluate"](instance, sources, others)}))
    except MissingValidationSymbol as e:
        results.append(json.dumps({"missing_validation_symbol": e.name}))
    except BaseException as e:
        results.append(json.dumps({"error": (type(e).__name__ + ": " + str(e))[:%d]}))
out.write("[" + ",".join(results) + "]")
""" % (ALLOWED_IMPORTS, FORBIDDEN_NAMES, MAX_MESSAGE)  # noqa: UP031


class SandboxError(TraceError):
    status_code = 422
    code = "sandbox_error"


class MissingValidationSymbol(SandboxError):
    """Validation-only signal: code actually read a newly required absent symbol."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(name)


def check(code: str) -> None:
    """Static check. Raises SandboxError if the code must not run."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise SandboxError(f"Syntax error: {e}") from e
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [node.module or ""] if node.level == 0 else ["." * node.level]
        else:
            modules = []
        for m in modules:
            if m not in ALLOWED_IMPORTS:
                raise SandboxError(f"Import not allowed: {m}")
        if isinstance(node, ast.Name) and (node.id in FORBIDDEN_NAMES or node.id.startswith("_")):
            raise SandboxError(f"Name not allowed: {node.id}")
        if isinstance(node, ast.Attribute) and (
            node.attr in FORBIDDEN_ATTRIBUTES or node.attr.startswith("_")
        ):
            raise SandboxError(f"Attribute not allowed: {node.attr}")
    if not any(isinstance(n, ast.FunctionDef) and n.name == "evaluate" for n in tree.body):
        raise SandboxError("Missing function evaluate")


def _limit(cpu_s: int) -> None:
    import resource

    resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    if sys.platform == "linux":
        resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY, MAX_MEMORY))


def _validate(r: dict[str, Any]) -> dict[str, Any] | SandboxError:
    if "missing_validation_symbol" in r:
        return MissingValidationSymbol(r["missing_validation_symbol"])
    if "error" in r:
        return SandboxError(f"The rule failed: {r['error']}")
    v = r.get("ok")
    if (
        not isinstance(v, dict)
        or set(v) != {"fires", "reason"}
        or type(v["fires"]) is not bool
        or not isinstance(v["reason"], str)
    ):
        return SandboxError(f"Malformed result: {repr(v)[:MAX_MESSAGE]}")
    return v


def run_batch(
    code: str,
    cases: list[tuple[dict[str, Any], dict[str, list[dict[str, Any]]], list[dict[str, Any]]]],
    timeout_s: float = 10.0,
) -> list[dict[str, Any] | SandboxError]:
    """Run `evaluate` on every case in ONE subprocess. Returns, per case, the result or the
    SandboxError for that case. Raises SandboxError if the code is rejected or the whole
    batch fails (timeout, crash, unreadable output)."""
    check(code)
    stdin = json.dumps({"code": code, "cases": cases})
    return _run(stdin, len(cases), timeout_s)


def _run(
    stdin: str, expected_results: int, timeout_s: float
) -> list[dict[str, Any] | SandboxError]:
    """Run an already validated and serialized request in a fresh child process."""
    limits = None if sys.platform == "win32" else (lambda: _limit(int(timeout_s) + 1))
    with tempfile.TemporaryDirectory() as cwd:
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-S", "-B", "-c", _RUNNER],
                input=stdin,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env={},
                cwd=cwd,
                preexec_fn=limits,
            )
        except subprocess.TimeoutExpired as e:
            raise SandboxError(f"Timed out ({timeout_s}s)") from e
    if proc.returncode != 0:
        raise SandboxError(f"The process failed ({proc.returncode}): {proc.stderr[-MAX_MESSAGE:]}")
    try:
        results = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise SandboxError("Unreadable sandbox output") from e
    if not isinstance(results, list) or len(results) != expected_results:
        raise SandboxError("Number of results differs from number of cases")
    return [_validate(r) for r in results]


def run_dataset(
    code: str,
    instances: list[tuple[int, dict[str, Any]]],
    sources: dict[str, list[dict[str, Any]]],
    population: list[tuple[int, dict[str, Any]]],
    timeout_s: float = 10.0,
    *,
    validation_missing: dict[int, list[str]] | None = None,
) -> list[dict[str, Any] | SandboxError]:
    """Run one rule over instances that share sources and a population.

    The population crosses the process boundary once. The child derives each instance's
    `others` list by key, avoiding the quadratic JSON payload produced by `run_batch`.
    """
    check(code)
    stdin = json.dumps(
        {
            "code": code,
            "instances": instances,
            "sources": sources,
            "population": population,
            **({"validation_missing": validation_missing} if validation_missing else {}),
        }
    )
    return _run(stdin, len(instances), timeout_s)
