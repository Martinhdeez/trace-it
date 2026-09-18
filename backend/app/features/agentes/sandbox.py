"""Isolated execution of generated rule code (P8). Owner: Martín.

The code comes from an LLM, so it is checked and then run away from the backend:

- Static check (`comprobar`): imports only from `PERMITIDOS`, no names in `PROHIBIDOS`
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

PERMITIDOS = {"decimal", "datetime", "re", "math", "unicodedata"}
PROHIBIDOS = {
    "__import__", "exec", "eval", "compile", "open", "input", "globals", "locals", "vars",
    "getattr", "setattr", "delattr", "breakpoint", "help", "exit", "quit",
}  # fmt: skip
ATRIBUTOS_PROHIBIDOS = {
    "gi_frame", "gi_code", "cr_frame", "cr_code", "ag_frame", "ag_code", "tb_frame",
    "tb_next", "f_back", "f_globals", "f_locals", "f_builtins", "f_code",
}  # fmt: skip
MEMORIA_MAX = 512 * 1024 * 1024
MAX_MENSAJE = 500

# Runs in the child. Reads {"codigo", "casos"} on stdin, writes one result per case on stdout.
_RUNNER = """
import builtins, decimal, io, json, sys, types
PERMITIDOS = %r
PROHIBIDOS = %r
_import = builtins.__import__

def importar(nombre, globals=None, locals=None, fromlist=(), level=0):
    if level or nombre not in PERMITIDOS:
        raise ImportError("import no permitido: " + nombre)
    modulo = _import(nombre)
    return types.SimpleNamespace(**{
        k: v for k, v in vars(modulo).items()
        if not k.startswith("_") and not isinstance(v, types.ModuleType)
    })

seguros = {k: v for k, v in vars(builtins).items() if k not in PROHIBIDOS}
seguros["__import__"] = importar
salida, sys.stdout = sys.stdout, io.StringIO()
datos = json.load(sys.stdin)
codigo = compile(datos["codigo"], "<regla>", "exec")
resultados = []
for instancia, fuentes, otras in datos["casos"]:
    decimal.setcontext(decimal.Context())
    try:
        ns = {"__builtins__": seguros, "__name__": "regla"}
        exec(codigo, ns)
        resultados.append(json.dumps({"ok": ns["evaluar"](instancia, fuentes, otras)}))
    except BaseException as e:
        resultados.append(json.dumps({"error": (type(e).__name__ + ": " + str(e))[:%d]}))
salida.write("[" + ",".join(resultados) + "]")
""" % (PERMITIDOS, PROHIBIDOS, MAX_MENSAJE)  # noqa: UP031


class ErrorSandbox(TraceError):
    status_code = 422
    code = "sandbox_error"


def comprobar(codigo: str) -> None:
    """Static check. Raises ErrorSandbox if the code must not run."""
    try:
        arbol = ast.parse(codigo)
    except SyntaxError as e:
        raise ErrorSandbox(f"Error de sintaxis: {e}") from e
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos = [a.name for a in nodo.names]
        elif isinstance(nodo, ast.ImportFrom):
            modulos = [nodo.module or ""] if nodo.level == 0 else ["." * nodo.level]
        else:
            modulos = []
        for m in modulos:
            if m not in PERMITIDOS:
                raise ErrorSandbox(f"Import no permitido: {m}")
        if isinstance(nodo, ast.Name) and (nodo.id in PROHIBIDOS or nodo.id.startswith("_")):
            raise ErrorSandbox(f"Nombre no permitido: {nodo.id}")
        if isinstance(nodo, ast.Attribute) and (
            nodo.attr in ATRIBUTOS_PROHIBIDOS or nodo.attr.startswith("_")
        ):
            raise ErrorSandbox(f"Atributo no permitido: {nodo.attr}")
    if not any(isinstance(n, ast.FunctionDef) and n.name == "evaluar" for n in arbol.body):
        raise ErrorSandbox("Falta la función evaluar")


def _limitar(cpu_s: int) -> None:
    import resource

    resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    if sys.platform == "linux":
        resource.setrlimit(resource.RLIMIT_AS, (MEMORIA_MAX, MEMORIA_MAX))


def _validar(r: dict[str, Any]) -> dict[str, Any] | ErrorSandbox:
    if "error" in r:
        return ErrorSandbox(f"La regla falló: {r['error']}")
    v = r.get("ok")
    if (
        not isinstance(v, dict)
        or set(v) != {"salta", "motivo"}
        or type(v["salta"]) is not bool
        or not isinstance(v["motivo"], str)
    ):
        return ErrorSandbox(f"Resultado con forma incorrecta: {repr(v)[:MAX_MENSAJE]}")
    return v


def ejecutar_lote(
    codigo: str,
    casos: list[tuple[dict[str, Any], dict[str, list[dict[str, Any]]], list[dict[str, Any]]]],
    timeout_s: float = 10.0,
) -> list[dict[str, Any] | ErrorSandbox]:
    """Run `evaluar` on every case in ONE subprocess. Returns, per case, the result or the
    ErrorSandbox for that case. Raises ErrorSandbox if the code is rejected or the whole
    batch fails (timeout, crash, unreadable output)."""
    comprobar(codigo)
    entrada = json.dumps({"codigo": codigo, "casos": casos})
    limites = None if sys.platform == "win32" else (lambda: _limitar(int(timeout_s) + 1))
    with tempfile.TemporaryDirectory() as cwd:
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-S", "-B", "-c", _RUNNER],
                input=entrada,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env={},
                cwd=cwd,
                preexec_fn=limites,
            )
        except subprocess.TimeoutExpired as e:
            raise ErrorSandbox(f"Tiempo agotado ({timeout_s}s)") from e
    if proc.returncode != 0:
        raise ErrorSandbox(f"El proceso falló ({proc.returncode}): {proc.stderr[-MAX_MENSAJE:]}")
    try:
        resultados = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise ErrorSandbox("Salida ilegible del sandbox") from e
    if not isinstance(resultados, list) or len(resultados) != len(casos):
        raise ErrorSandbox("Número de resultados distinto al de casos")
    return [_validar(r) for r in resultados]


def ejecutar(
    codigo: str,
    instancia: dict[str, Any],
    fuentes: dict[str, list[dict[str, Any]]],
    otras: list[dict[str, Any]],
    timeout_s: float = 2.0,
) -> dict[str, Any]:
    """Run `evaluar(instancia, fuentes, otras)` from `codigo` in the sandbox. Returns
    {"salta": bool, "motivo": str}; raises ErrorSandbox on any error, timeout or malformed
    result. Callers must never decide without the result."""
    [resultado] = ejecutar_lote(codigo, [(instancia, fuentes, otras)], timeout_s)
    if isinstance(resultado, ErrorSandbox):
        raise resultado
    return resultado
