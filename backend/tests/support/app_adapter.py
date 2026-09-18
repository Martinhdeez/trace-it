"""The only place the new test suite touches the app's Spanish names.

The codebase is being translated to English (branch `chore/english`). When a module, a
route or a field is renamed, fix it here and nowhere else: the tests speak English.
"""

import asyncio
import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import session_factory
from app.features.agentes import compilador, sandbox
from app.features.decisiones.motor import decidir
from app.features.decisiones.tests.reglas_v3 import REGLAS_V3
from app.features.fuentes.model import Fuente
from app.features.ingesta.model import Fichero, Instancia
from app.features.llm import cliente as llm_client
from app.features.llm.model import ConfigLLM
from app.features.procesos.model import Simbolo
from app.features.reglas.model import Regla
from app.main import app

__all__ = ["app", "llm_client"]

REPO = Path(__file__).resolve().parents[3]
PROCESS_FILE = REPO / "procesos" / "pago-facturas.json"

# Mateo's hand-written code for the 16 v3 rules, in the order of PROCESS_FILE.
REFERENCE_CODE: list[str] = REGLAS_V3
SandboxError = sandbox.ErrorSandbox


# --- The process definition ----------------------------------------------------------------


@dataclass(frozen=True)
class RuleSpec:
    number: int  # 1-based, as R01..R16
    text: str
    kind: str
    decision: str


@dataclass(frozen=True)
class Outcomes:
    priorities: dict[str, int]
    default: str
    escalate: str  # the highest-priority outcome that needs a person


def definition() -> dict[str, Any]:
    return json.loads(PROCESS_FILE.read_text(encoding="utf-8"))


def rules(defn: dict[str, Any]) -> list[RuleSpec]:
    return [
        RuleSpec(n, r["texto"], r["tipo"], r["decision"]) for n, r in enumerate(defn["reglas"], 1)
    ]


def outcomes(defn: dict[str, Any]) -> Outcomes:
    kinds = defn["tipos_decision"]
    priorities = {t["nombre"]: t["prioridad"] for t in kinds}
    default = next(t["nombre"] for t in kinds if t.get("por_defecto"))
    human = [t["nombre"] for t in kinds if t.get("requiere_persona")]
    return Outcomes(priorities, default, max(human, key=priorities.__getitem__))


# --- Engine and sandbox, without the database ----------------------------------------------

Case = tuple[dict[str, Any], dict[str, list[dict[str, Any]]], list[dict[str, Any]]]


def run_batched(codes: Sequence[str], cases: list[Case], chunk: int = 60) -> list[list[Any]]:
    """Run each rule over every case in the real sandbox, one subprocess per rule and chunk.

    Returns, per rule and case, {"salta", "motivo"} or the sandbox error for that case.
    Sequential on purpose: each case carries the full sources, and parallel threads were
    slower (the parent serialises every payload). Chunks keep the child well under the
    sandbox's 512 MB limit on Linux.
    """
    out = []
    for code in codes:
        results: list[Any] = []
        for i in range(0, len(cases), chunk):
            part = cases[i : i + chunk]
            try:
                results += sandbox.ejecutar_lote(code, part, timeout_s=120)
            except sandbox.ErrorSandbox as error:  # the whole chunk failed
                results += [error] * len(part)
        out.append(results)
    return out


@dataclass(frozen=True)
class Verdict:
    decision: str
    reason: str
    fired: list[str]  # "R07: <motivo>" for each rule that fired or failed


def decide(
    specs: Sequence[RuleSpec],
    codes: Sequence[str],
    out: Outcomes,
    instance: dict[str, Any],
    sources: dict[str, list[dict[str, Any]]],
    others: list[dict[str, Any]],
    execute: Callable[..., dict[str, Any]],
) -> Verdict:
    """The engine's own decision function, with `execute` standing in for the sandbox call."""
    rows = [
        Regla(id=s.number, texto=s.text, tipo=s.kind, decision=s.decision, codigo_a=c, hash="")
        for s, c in zip(specs, codes, strict=True)
    ]
    verdict = decidir(
        rows, out.priorities, out.default, out.escalate, instance, sources, others, execute
    )
    fired = [f"R{r.regla_id:02d}: {r.motivo}" for r in verdict.resultados if r.salta is not False]
    return Verdict(verdict.decision, verdict.motivo, fired)


# --- The HTTP API --------------------------------------------------------------------------


async def create_user(api: AsyncClient, name: str, email: str, role: str) -> dict[str, str]:
    """Returns the headers that identify the new user."""
    r = await api.post("/usuarios", json={"nombre": name, "email": email, "rol": role})
    assert r.status_code in (200, 201), r.text
    return {"X-Usuario-Id": str(r.json()["id"])}


async def load_definition(api: AsyncClient, defn: dict[str, Any]) -> int:
    r = await api.post("/procesos/definicion", json=defn)
    assert r.status_code == 200, r.text
    return r.json()["proceso"]["id"]


async def list_rules(api: AsyncClient, process_id: int) -> list[dict[str, Any]]:
    r = await api.get(f"/procesos/{process_id}/reglas")
    assert r.status_code == 200, r.text
    return [{"id": x["id"], "text": x["texto"], "state": x["estado"]} for x in r.json()]


async def activate_rule(api: AsyncClient, rule_id: int, headers: dict[str, str]) -> str:
    r = await api.post(f"/reglas/{rule_id}/activar", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["estado"]


async def run_process(api: AsyncClient, process_id: int) -> dict[str, int]:
    r = await api.post(f"/procesos/{process_id}/ejecutar")
    assert r.status_code == 200, r.text
    return r.json()["por_decision"]


async def list_instances(api: AsyncClient, process_id: int) -> dict[str, dict[str, Any]]:
    """By file name: {"id", "state", "decision"}."""
    r = await api.get(f"/procesos/{process_id}/instancias")
    assert r.status_code == 200, r.text
    return {
        i["nombre"]: {"id": i["id"], "state": i["estado"], "decision": i["decision"]}
        for i in r.json()
    }


async def queue(api: AsyncClient, process_id: int) -> list[str]:
    r = await api.get(f"/procesos/{process_id}/cola")
    assert r.status_code == 200, r.text
    return [i["nombre"] for i in r.json()]


def _history(detail: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "decision": d["decision"],
            "author": d["autor"],
            "results": d["resultados"],
            "human_kind": d.get("tipo_humana", "<absent>"),
        }
        for d in detail["decisiones"]
    ]


async def history(api: AsyncClient, instance_id: int) -> list[dict[str, Any]]:
    """Decision history, oldest first. `human_kind` is "<absent>" before PR #17."""
    r = await api.get(f"/instancias/{instance_id}")
    assert r.status_code == 200, r.text
    return _history(r.json())


async def resolve(
    api: AsyncClient, instance_id: int, decision: str, reason: str, headers: dict[str, str]
) -> list[dict[str, Any]]:
    r = await api.post(
        f"/instancias/{instance_id}/resolver",
        json={"decision": decision, "motivo": reason},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    return _history(r.json())


async def export(api: AsyncClient, process_id: int) -> list[dict[str, Any]]:
    r = await api.get(f"/procesos/{process_id}/exportar")
    assert r.status_code == 200, r.text
    return [json.loads(line) for line in r.text.splitlines()]


# --- Direct database writes: what ingestion, extraction and the compiler will do later -----


async def inject_rule_code(process_id: int, code_by_text: dict[str, str]) -> None:
    """TEST ONLY. Writes reference code into the process's draft rules, bypassing the LLM
    compiler, and marks them valid so the normal activation endpoint accepts them."""
    async with session_factory() as session:
        rows = list(await session.scalars(select(Regla).where(Regla.proceso_id == process_id)))
        assert {r.texto for r in rows} == set(code_by_text), "rules differ from the definition"
        for row in rows:
            code = code_by_text[row.texto]
            row.codigo_a = row.codigo_b = code
            row.hash = hashlib.sha256("\0".join([row.texto, code, code]).encode()).hexdigest()
            row.informe = {
                "valida": True,
                "test_only": "hand-written reference code injected by backend/tests; "
                "the compiler was bypassed",
            }
        await session.commit()


async def load_sources(process_id: int, sources: dict[str, list[dict[str, Any]]]) -> None:
    async with session_factory() as session:
        for name, rows in sources.items():
            session.add(Fuente(proceso_id=process_id, nombre=name, origen="tests", filas=rows))
        await session.commit()


async def add_instances(process_id: int, files: dict[str, tuple[bytes, dict[str, Any]]]) -> None:
    """One extracted instance per file: {file_id: (pdf bytes, symbols)}."""
    async with session_factory() as session:
        for name, (content, symbols) in files.items():
            digest = hashlib.sha256(content).hexdigest()
            if await session.get(Fichero, digest) is None:
                session.add(Fichero(hash=digest, nombre=name, contenido=content, texto=None))
            session.add(
                Instancia(proceso_id=process_id, fichero_hash=digest, nombre=name, simbolos=symbols)
            )
        await session.commit()


# --- What the compiler eval needs ----------------------------------------------------------

COMPILER_ROLES: tuple[str, ...] = tuple(compilador.PAPELES)


async def configured_models() -> dict[str, str]:
    """The model each compiler role uses, from the app's `config_llm` table."""
    async with session_factory() as session:
        rows = await session.scalars(select(ConfigLLM).where(ConfigLLM.papel.in_(COMPILER_ROLES)))
        return {r.papel: r.modelo for r in rows}


@dataclass
class Compiled:
    role: str
    code: str | None = None
    tests: list[dict[str, Any]] | None = None  # the compiler's shape: read with *_of below
    model: str | None = None
    repairs: int | None = None
    cost: float | None = None
    latency_ms: int | None = None
    error: str | None = None


async def compile_rule(
    spec: RuleSpec, defn: dict[str, Any], sources: dict[str, list[dict[str, Any]]]
) -> list[Compiled]:
    """Both blind compiler agents on one rule, with the context the app would give them.

    Calls the compiler's agents directly rather than `compilar`, which reads the history
    from the database in a different symbol shape than the engine uses.
    """
    rule = Regla(id=spec.number, proceso_id=0, texto=spec.text, tipo=spec.kind,
                 decision=spec.decision)  # fmt: skip
    symbols = [
        Simbolo(nombre=s["nombre"], tipo=s["tipo"], descripcion=s.get("descripcion", ""))
        for s in defn["simbolos"]
    ]
    context = compilador._contexto(rule, symbols, sources, defn.get("descripcion", ""))
    async with session_factory() as session:
        # Loaded first so both concurrent agents find their config in the identity map.
        configs = list(
            await session.scalars(select(ConfigLLM).where(ConfigLLM.papel.in_(COMPILER_ROLES)))
        )
        answers = await asyncio.gather(
            *(compilador._agente(session, role, context) for role in COMPILER_ROLES),
            return_exceptions=True,
        )
    del configs
    out = []
    for role, answer in zip(COMPILER_ROLES, answers, strict=True):
        if isinstance(answer, BaseException):
            out.append(Compiled(role, error=f"{type(answer).__name__}: {answer}"))
            continue
        code, tests, trace = answer
        out.append(
            Compiled(role, code, tests, trace.get("modelo"), trace.get("reparaciones"),
                     trace.get("coste"), trace.get("latencia_ms"))
        )  # fmt: skip
    return out


def verdict(result: Any) -> bool | None:
    """True/False if the rule fired or not, None if it failed."""
    if isinstance(result, dict) and isinstance(result.get("salta"), bool):
        return result["salta"]
    return None


def cases_of(tests: list[dict[str, Any]]) -> list[Case]:
    return [(t["instancia"], t["fuentes"], t["otras"]) for t in tests]


def fires_of(test: dict[str, Any]) -> bool:
    return test["salta"]


def name_of(test: dict[str, Any]) -> str:
    return test["nombre"]
