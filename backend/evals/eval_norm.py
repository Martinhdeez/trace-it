"""Opt-in end-to-end evaluation from the client's original norm (ADR 0017).

    make eval-norm

No hand translation and no database: the six sentences of `Norma_Pagos_v3` (the challenge
workbook) go to the normalizer with the invoice process's decision types, symbols and
sources and no existing rules; every check it proposes is compiled by the tester and the
coder (ADR 0004); the valid checks decide the 471 text invoices of batch 1 with the real
engine and sandbox; the decisions are compared with the golden outcomes. Agents run with
the invoice use case's settings (`processes/invoice-payment/use-case.json`) and keys from
`.env`. The report, grouped by norm rule, goes to `backend/evals/reports/norm-<ts>.md`.

Without the keys the configured models need, it prints why and exits 0.
"""

import asyncio
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import openpyxl
from dotenv import load_dotenv

from app.features.agents import compiler, llm, normalizer, sandbox
from app.features.decisions.engine import Verdict, decide
from app.features.processes.model import DecisionType, Symbol
from app.features.rules.model import Rule
from app.features.rules.service import rule_hash
from evals.eval_compiler import missing_keys
from tests.golden import golden
from tests.support import challenge, pack

REPORTS = Path(__file__).parent / "reports"
SHEET = "Norma_Pagos_v3"
PARALLEL = 4  # checks compiled at once (Helmcode allows 100 requests per minute)
ROLES = ("normalizer", *compiler.ROLES)


@dataclass
class CheckResult:
    label: str  # "<norm rule number>.<check number>"
    norm_rule: int
    check: normalizer.Check
    rule: Rule
    compilation: compiler.Compilation | None = None
    traces: list[llm.Trace] = field(default_factory=list)
    error: str | None = None

    @property
    def valid(self) -> bool:
        return bool(self.compilation and self.compilation.report["valid"])

    @property
    def outcome(self) -> str:
        if self.error:
            return "error"
        if self.compilation.code is None:
            return "needs data"
        return "valid" if self.valid else "not valid"


@dataclass
class Result:
    norm: str
    normalization: normalizer.Normalization
    checks: list[CheckResult]
    verdicts: dict[str, Verdict]  # file_id -> what the valid checks decided
    traces: list[llm.Trace]  # every agent run
    seconds: float

    def mismatches(self) -> list[tuple[str, str, Verdict]]:
        expected = golden.expected()
        return [
            (fid, expected[fid]["expected"], v)
            for fid, v in sorted(self.verdicts.items())
            if v.decision != expected[fid]["expected"]
        ]


def norm_text() -> str:
    """The numbered sentences of the norm sheet, as the client wrote them."""
    workbook = openpyxl.load_workbook(challenge.WORKBOOK, read_only=True)
    cells = [str(c) for row in workbook[SHEET].iter_rows(values_only=True) for c in row if c]
    return "\n".join(c.strip() for c in cells if re.match(r"\d+\.", c.strip()))


def process() -> tuple[list[DecisionType], list[Symbol]]:
    defn = pack.definition()
    types = [
        DecisionType(
            name=t["name"],
            priority=t["priority"],
            is_default=t.get("is_default", False),
            requires_human=t.get("requires_human", False),
        )
        for t in defn["decision_types"]
    ]
    return types, [Symbol(**s) for s in defn["symbols"]]


async def _compile(
    check: CheckResult, symbols: list[Symbol], setups: compiler.Setups, limit: asyncio.Semaphore
) -> None:
    runs = compiler.Runs(setups)
    async with limit:
        try:
            check.compilation = await compiler.compile_text(
                check.rule, symbols, challenge.sources(), pack.use_case().description, runs
            )
        except Exception as e:  # noqa: BLE001 - one failing check must not stop the eval
            check.error = f"{type(e).__name__}: {e}"
    check.traces = runs.traces
    if check.compilation and check.compilation.code:
        check.rule.code = check.compilation.code
        check.rule.hash = rule_hash(check.rule.text, check.rule.code)
    print(f"{check.label} {check.check.decision}: {check.outcome}", flush=True)


def _decide(rules: list[Rule]) -> dict[str, Verdict]:
    instances = golden.symbols()
    dataset = [(s["file_id"], s) for s in instances]
    population = [(s["file_id"], {**s, "_instance": s["file_id"]}) for s in instances]

    def run_dataset(code: str, part: list, sources: dict, everyone: list) -> list[Any]:
        return sandbox.run_dataset(code, part, sources, everyone, timeout_s=120)

    verdicts = decide(rules, pack.outcomes(), dataset, challenge.sources(), population, run_dataset)
    return {s["file_id"]: v for s, v in zip(instances, verdicts, strict=True)}


async def evaluate(setups: compiler.Setups) -> Result:
    """Norm -> normalizer -> compiler -> engine on batch 1, with these agent setups."""
    started = time.perf_counter()
    norm = norm_text()
    types, symbols = process()
    description = pack.use_case().description
    normalization, trace = await normalizer.normalize(
        norm, description, types, symbols, challenge.sources(), [], setups.get("normalizer")
    )
    print(f"Normalizer: {sum(len(s.checks) for s in normalization.norm_rules)} checks", flush=True)
    checks = [
        CheckResult(
            f"{s.number}.{k}",
            s.number,
            c,
            Rule(id=100 * s.number + k, text=c.text, type=c.type, decision=c.decision),
        )
        for s in normalization.norm_rules
        for k, c in enumerate(s.checks, 1)
    ]
    limit = asyncio.Semaphore(PARALLEL)
    await asyncio.gather(*(_compile(c, symbols, setups, limit) for c in checks))
    valid = [c.rule for c in checks if c.valid]
    verdicts = await asyncio.to_thread(_decide, valid)
    traces = [trace, *(t for c in checks for t in c.traces)]
    return Result(norm, normalization, checks, verdicts, traces, time.perf_counter() - started)


def _cost(traces: list[llm.Trace]) -> float:
    return sum(t.cost or 0 for t in traces)


def render(result: Result, models: dict[str, str], started: datetime) -> str:
    by_id = {c.rule.id: c for c in result.checks}
    mismatches = result.mismatches()
    total = len(result.verdicts)
    lines = [
        f"# Norm eval {started:%Y-%m-%d %H:%M} UTC",
        "",
        "Models: " + ", ".join(f"`{r}` = `{m}`" for r, m in sorted(models.items())),
        f"Agreement with the golden outcomes: **{total - len(mismatches)}/{total}** text "
        "invoices of batch 1, deciding with the valid checks only (what would activate).",
        f"Total cost: ${_cost(result.traces):.4f}. Wall time: {result.seconds / 60:.1f} min. "
        f"Agent runs: {len(result.traces)}, "
        f"{sum(t.input_tokens for t in result.traces)} input and "
        f"{sum(t.output_tokens for t in result.traces)} output tokens (a provider without a "
        "known price reports cost 0).",
        "",
        "## Norm",
        "",
        *(f"> {line}" for line in result.norm.splitlines()),
        "",
    ]

    def winners(v: Verdict) -> list[CheckResult]:
        return [
            by_id[r.rule_id]
            for r in v.results
            if r.fires and by_id[r.rule_id].rule.decision == v.decision
        ]

    for s in result.normalization.norm_rules:
        own = [c for c in result.checks if c.norm_rule == s.number]
        fired = sum(
            any(r.fires for r in v.results if r.rule_id in {c.rule.id for c in own})
            for v in result.verdicts.values()
        )
        wrong = [m for m in mismatches if any(c.norm_rule == s.number for c in winners(m[2]))]
        lines += [
            f"## Norm rule {s.number}",
            "",
            f"> {s.text}",
            "",
            f"Its checks fired on {fired} invoices; {len(wrong)} of the mismatches below "
            "were decided by them.",
            "",
            "| Check | Type | Kind | Decision | Compile | Attempts | Cost $ | Text |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for c in own:
            attempts = c.compilation.report.get("attempts", "-") if c.compilation else "-"
            lines.append(
                f"| {c.label} | {c.check.type} | {c.check.kind} | {c.check.decision} "
                f"({c.check.decision_source}) | {c.outcome} | {attempts} "
                f"| {_cost(c.traces):.4f} | {c.check.text} |"
            )
        lines.append("")
        lines += [f"- **{c.label}** interpretation: {c.check.interpretation}" for c in own]
        lines += [f"- **{c.label}** kind: {c.check.kind_reason}" for c in own]
        for c in own:
            if c.error:
                lines.append(f"- **{c.label}** failed: {c.error[:300]}")
            elif c.compilation:
                lines += [f"- **{c.label}** {d}" for d in c.compilation.report["discrepancies"]]
        lines += [f"- Policy: {p}" for p in s.policies]
        lines.append("")

    expected = golden.expected()
    groups: dict[str, list[str]] = {}
    for fid, want, v in mismatches:
        won = winners(v)
        key = ", ".join(sorted({f"norm rule {c.norm_rule}" for c in won})) or (
            "engine" if v.decision != pack.outcomes().default else "no check fired"
        )
        fired = (
            " | ".join(
                f"{by_id[r.rule_id].label}: {r.reason}" for r in v.results if r.fires is not False
            )
            or "-"
        )
        groups.setdefault(key, []).append(
            f"| `{fid}` | {want} | {v.decision} | {fired[:200]} | {expected[fid]['why'][:120]} |"
        )
    lines += [f"## Mismatches ({len(mismatches)})", ""]
    for key, rows in sorted(groups.items()):
        lines += [
            f"### Decided by {key} ({len(rows)})",
            "",
            "| File | Expected | Got | Fired checks | Golden why |",
            "|---|---|---|---|---|",
            *rows,
            "",
        ]
    return "\n".join(lines)


async def run() -> tuple[Path, Result] | None:
    load_dotenv(pack.REPO / ".env")
    setups = {role: llm.Setup(s) for role, s in pack.use_case().agents.items()}
    models = {
        r: str((setups[r].settings.model if r in setups else None) or llm.model_for(r))
        for r in ROLES
    }
    if missing := missing_keys(models):
        print(f"Configured models {models} need {', '.join(missing)}; skipping.")
        return None
    started = datetime.now(UTC)
    result = await evaluate(setups)
    REPORTS.mkdir(exist_ok=True)
    path = REPORTS / f"norm-{started:%Y%m%dT%H%M%SZ}.md"
    path.write_text(render(result, models, started), encoding="utf-8")
    total = len(result.verdicts)
    print(
        f"Agreement {total - len(result.mismatches())}/{total}, "
        f"${_cost(result.traces):.4f}, {result.seconds / 60:.1f} min. Report: {path}"
    )
    return path, result


if __name__ == "__main__":
    asyncio.run(run())
