"""The only place the new test suite touches the app's module names, routes and fields.

When a module, a route or a field is renamed, fix it here and nowhere else.
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
from app.features.agents import compiler, sandbox
from app.features.decisions.engine import decide as engine_decide
from app.features.decisions.tests.rules_v3 import RULES_V3
from app.features.ingestion.model import File, Instance
from app.features.llm import client as llm_client
from app.features.llm.model import LLMConfig
from app.features.processes.definition import Definition, load_definition
from app.features.processes.model import Symbol
from app.features.rules.model import Rule
from app.features.sources.model import Source
from app.main import app

__all__ = ["app", "llm_client"]

REPO = Path(__file__).resolve().parents[3]
PACK = REPO / "processes"
PROCESS_FILE = PACK / "invoice-payment.json"

# Mateo's hand-written code for the 16 v3 rules (`processes/rules-v3/`), in definition order.
REFERENCE_CODE: list[str] = RULES_V3
SandboxError = sandbox.SandboxError


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
        RuleSpec(n, r["text"], r["type"], r["decision"]) for n, r in enumerate(defn["rules"], 1)
    ]


def outcomes(defn: dict[str, Any]) -> Outcomes:
    kinds = defn["decision_types"]
    priorities = {t["name"]: t["priority"] for t in kinds}
    default = next(t["name"] for t in kinds if t.get("is_default"))
    human = [t["name"] for t in kinds if t.get("requires_human")]
    return Outcomes(priorities, default, max(human, key=priorities.__getitem__))


# --- Engine and sandbox, without the database ----------------------------------------------

Case = tuple[dict[str, Any], dict[str, list[dict[str, Any]]], list[dict[str, Any]]]
OTHER_KEY = "_instance"  # how an entry of `others` names its instance


def others_of(instances: list[dict[str, Any]], me: dict[str, Any]) -> list[dict[str, Any]]:
    """What the engine passes as `others`: every other instance, tagged with its name."""
    return [{**o, OTHER_KEY: o["file_id"]} for o in instances if o is not me]


def run_batched(codes: Sequence[str], cases: list[Case], chunk: int = 60) -> list[list[Any]]:
    """Run each rule over every case in the real sandbox, one subprocess per rule and chunk.

    Returns, per rule and case, {"fires", "reason"} or the sandbox error for that case.
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
                results += sandbox.run_batch(code, part, timeout_s=120)
            except sandbox.SandboxError as error:  # the whole chunk failed
                results += [error] * len(part)
        out.append(results)
    return out


def verdict(result: Any) -> bool | None:
    """True/False if the rule fired or not, None if it failed."""
    if isinstance(result, dict) and isinstance(result.get("fires"), bool):
        return result["fires"]
    return None


def reason(result: Any) -> str:
    return str(result.get("reason", "")) if isinstance(result, dict) else str(result)


@dataclass(frozen=True)
class Verdict:
    decision: str
    reason: str
    fired: list[str]  # "R07: <reason>" for each rule that fired or failed


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
        Rule(id=s.number, text=s.text, type=s.kind, decision=s.decision, code_a=c, hash="")
        for s, c in zip(specs, codes, strict=True)
    ]
    v = engine_decide(
        rows, out.priorities, out.default, out.escalate, instance, sources, others, execute
    )
    fired = [f"R{r.rule_id:02d}: {r.reason}" for r in v.results if r.fires is not False]
    return Verdict(v.decision, v.reason, fired)


# --- The HTTP API --------------------------------------------------------------------------


async def create_user(api: AsyncClient, name: str, email: str, role: str) -> dict[str, str]:
    """Returns the headers that identify the new user. `role`: "manager" or "operator"."""
    r = await api.post("/users", json={"name": name, "email": email, "role": role})
    assert r.status_code in (200, 201), r.text
    return {"X-User-Id": str(r.json()["id"])}


async def list_rules(api: AsyncClient, process_id: int) -> list[dict[str, Any]]:
    r = await api.get(f"/processes/{process_id}/rules")
    assert r.status_code == 200, r.text
    return [{"id": x["id"], "text": x["text"], "status": x["status"]} for x in r.json()]


async def activate_rule(api: AsyncClient, rule_id: int, headers: dict[str, str]) -> str:
    r = await api.post(f"/rules/{rule_id}/activate", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["status"]


async def run_process(api: AsyncClient, process_id: int) -> dict[str, int]:
    r = await api.post(f"/processes/{process_id}/run")
    assert r.status_code == 200, r.text
    return r.json()["by_decision"]


async def list_instances(api: AsyncClient, process_id: int) -> dict[str, dict[str, Any]]:
    """By file name: {"id", "status", "decision"}."""
    r = await api.get(f"/processes/{process_id}/instances")
    assert r.status_code == 200, r.text
    return {
        i["name"]: {"id": i["id"], "status": i["status"], "decision": i["decision"]}
        for i in r.json()
    }


async def queue(api: AsyncClient, process_id: int) -> list[str]:
    r = await api.get(f"/processes/{process_id}/queue")
    assert r.status_code == 200, r.text
    return [i["name"] for i in r.json()]


def _history(detail: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "decision": d["decision"],
            "author": d["author"],
            "results": d["results"],
            "human_kind": d.get("human_kind", "<absent>"),
        }
        for d in detail["decisions"]
    ]


async def history(api: AsyncClient, instance_id: int) -> list[dict[str, Any]]:
    """Decision history, oldest first."""
    r = await api.get(f"/instances/{instance_id}")
    assert r.status_code == 200, r.text
    return _history(r.json())


async def resolve(
    api: AsyncClient, instance_id: int, decision: str, why: str, headers: dict[str, str]
) -> list[dict[str, Any]]:
    r = await api.post(
        f"/instances/{instance_id}/resolve",
        json={"decision": decision, "reason": why},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    return _history(r.json())


async def export(api: AsyncClient, process_id: int) -> list[dict[str, Any]]:
    r = await api.get(f"/processes/{process_id}/export")
    assert r.status_code == 200, r.text
    return [json.loads(line) for line in r.text.splitlines()]


ENGINE_AUTHOR = "engine"


# --- In-process loading: the CLI's loader, and what ingestion and extraction will do -------


async def load_pack(defn: dict[str, Any]) -> int:
    """Load a definition the way `python -m app.cli load` does, so each rule's `code` file
    under `processes/` is installed validated (no compiler, no LLM). Returns the process id."""
    async with session_factory() as session:
        result = await load_definition(session, Definition.model_validate(defn), PACK)
        return result.process.id


async def load_sources(process_id: int, sources: dict[str, list[dict[str, Any]]]) -> None:
    async with session_factory() as session:
        for name, rows in sources.items():
            session.add(Source(process_id=process_id, name=name, origin="tests", rows=rows))
        await session.commit()


async def add_instances(process_id: int, files: dict[str, tuple[bytes, dict[str, Any]]]) -> None:
    """One extracted instance per file: {file_id: (pdf bytes, symbols)}.

    Symbols are stored flat ({name: value}), which is what the engine hands to the rules.
    """
    async with session_factory() as session:
        for name, (content, symbols) in files.items():
            digest = hashlib.sha256(content).hexdigest()
            if await session.get(File, digest) is None:
                session.add(File(hash=digest, name=name, content=content, text=None))
            session.add(
                Instance(process_id=process_id, file_hash=digest, name=name, symbols=symbols)
            )
        await session.commit()


# --- What the compiler eval needs ----------------------------------------------------------

COMPILER_ROLES: tuple[str, ...] = tuple(compiler.ROLES)


async def configured_models() -> dict[str, str]:
    """The model each compiler role uses, from the app's `llm_config` table."""
    async with session_factory() as session:
        rows = await session.scalars(select(LLMConfig).where(LLMConfig.role.in_(COMPILER_ROLES)))
        return {r.role: r.model for r in rows}


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


def fake_llm_reply(code: str, tests: list[dict[str, Any]], role: str) -> Any:
    """What the LLM client returns, carrying a compiler proposal. For harness tests."""
    proposal = {
        "code": code,
        "tests": [
            {
                "name": t["name"],
                "instance_json": json.dumps(t["instance"]),
                "sources_json": json.dumps(t["sources"]),
                "others_json": json.dumps(t["others"]),
                "fires": t["fires"],
            }
            for t in tests
        ],
    }
    return llm_client.Reply(json.dumps(proposal), f"fake/{role}", 0.001, 5)


def patch_llm(monkeypatch: Any, reply: Callable[[str], Any]) -> None:
    """Replace the LLM call with `reply(role)`."""

    async def fake(session: Any, role: str, messages: Any, response_format: Any = None) -> Any:
        return reply(role)

    monkeypatch.setattr(llm_client, "complete", fake)


async def compile_rule(
    spec: RuleSpec, defn: dict[str, Any], sources: dict[str, list[dict[str, Any]]]
) -> list[Compiled]:
    """Both blind compiler agents on one rule, with the context the app would give them.

    Calls the compiler's agents directly rather than `compile_rule`, which reads the
    history from the database in a different symbol shape than the engine uses.
    """
    rule = Rule(id=spec.number, process_id=0, text=spec.text, type=spec.kind,
                decision=spec.decision)  # fmt: skip
    symbols = [
        Symbol(name=s["name"], type=s["type"], description=s.get("description", ""))
        for s in defn["symbols"]
    ]
    context = compiler._context(rule, symbols, sources, defn.get("description", ""))
    async with session_factory() as session:
        # Loaded first so both concurrent agents find their config in the identity map.
        configs = list(
            await session.scalars(select(LLMConfig).where(LLMConfig.role.in_(COMPILER_ROLES)))
        )
        answers = await asyncio.gather(
            *(compiler._agent(session, role, context) for role in COMPILER_ROLES),
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
            Compiled(role, code, tests, trace.get("model"), trace.get("repairs"),
                     trace.get("cost"), trace.get("latency_ms"))
        )  # fmt: skip
    return out


def cases_of(tests: list[dict[str, Any]]) -> list[Case]:
    return [(t["instance"], t["sources"], t["others"]) for t in tests]


def fires_of(test: dict[str, Any]) -> bool:
    return test["fires"]


def name_of(test: dict[str, Any]) -> str:
    return test["name"]
