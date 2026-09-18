"""Opt-in evaluation of the LLM rule compiler against the hand-written v3 rules.

    make eval-compiler                                   # all 16 rules
    cd backend && uv run python -m evals.eval_compiler --rules 2,7

For each rule, both blind compiler agents run with the configured models (`TRACE_*_MODEL`,
keys from `.env`). Both generated codes then run in the real sandbox on every golden instance
of batch 1 (and on the compiler's own tests), and are compared with the reference code. The
report goes to `backend/evals/reports/compiler-<timestamp>.md`.

Without any LLM key it prints why and exits 0, so it never breaks a default run.
"""

import argparse
import asyncio
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.features.agents import compiler, llm, sandbox
from app.features.processes.model import Symbol
from app.features.rules.model import Rule
from tests.golden import golden
from tests.support import challenge, pack

REPORTS = Path(__file__).parent / "reports"
KEYS = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "google": "GOOGLE_API_KEY"}
MAX_LISTED = 8
Case = tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]


@dataclass
class Compiled:
    role: str
    code: str | None = None
    tests: list[dict[str, Any]] | None = None
    trace: llm.Trace | None = None
    error: str | None = None


@dataclass
class RuleReport:
    rule: Rule
    compiled: list[Compiled]
    agreement: dict[str, float] = field(default_factory=dict)  # role -> % equal to reference
    discrepancies: list[str] = field(default_factory=list)
    own_tests: dict[str, str] = field(default_factory=dict)  # role -> "passed/total"
    reference_on_tests: str = ""  # does the reference pass the agents' tests?

    @property
    def valid(self) -> bool:
        return all(c.code for c in self.compiled) and all(
            self.agreement.get(c.role) == 100.0 for c in self.compiled
        )


def models() -> dict[str, str]:
    return {role: str(llm.model_for(role)) for role in compiler.ROLES}


def missing_keys(models: dict[str, str]) -> list[str]:
    """Env vars the configured models need and that are not set."""
    needed = {KEYS[m.split(":")[0]] for m in models.values() if m.split(":")[0] in KEYS}
    return sorted(k for k in needed if not os.environ.get(k))


async def compile_both(rule: Rule, defn: dict[str, Any]) -> list[Compiled]:
    """Both blind compiler agents on one rule, with the context the app would give them."""
    symbols = [Symbol(**s) for s in defn["symbols"]]
    prompt = compiler.context(rule, symbols, challenge.sources(), defn.get("description", ""))
    answers = await asyncio.gather(
        *(llm.run(compiler.compiler, role, prompt) for role in compiler.ROLES),
        return_exceptions=True,
    )
    out = []
    for role, answer in zip(compiler.ROLES, answers, strict=True):
        if isinstance(answer, BaseException):
            out.append(Compiled(role, error=f"{type(answer).__name__}: {answer}"))
            continue
        proposal, trace = answer
        out.append(Compiled(role, proposal.code, compiler.tests_of(proposal), trace))
    return out


def run_batched(codes: list[str], cases: list[Case], chunk: int = 60) -> list[list[Any]]:
    """Each code over every case in the real sandbox, chunked to stay under its memory limit."""
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


def fires(result: Any) -> bool | None:
    if isinstance(result, dict) and isinstance(result.get("fires"), bool):
        return result["fires"]
    return None


def describe(result: Any) -> str:
    v = fires(result)
    if v is None:
        return f"ERROR ({str(result)[:80]})"
    return f"fires ({str(result.get('reason'))[:60]})" if v else "does not fire"


def evaluate(rule: Rule, compiled: list[Compiled]) -> RuleReport:
    report = RuleReport(rule, compiled)
    instances = golden.symbols()
    others = {
        s["file_id"]: [{**o, "_instance": o["file_id"]} for o in instances if o is not s]
        for s in instances
    }
    cases = [(s, challenge.sources(), others[s["file_id"]]) for s in instances]
    ok = [c for c in compiled if c.code]
    ref, *generated = run_batched([rule.code] + [c.code for c in ok], cases)
    for c, results in zip(ok, generated, strict=True):
        same = 0
        for s, r, g in zip(instances, ref, results, strict=True):
            if fires(r) is fires(g) and fires(g) is not None:
                same += 1
            elif len(report.discrepancies) < MAX_LISTED:
                report.discrepancies.append(
                    f"{c.role} on `{s['file_id']}`: reference {describe(r)}, "
                    f"generated {describe(g)}"
                )
        report.agreement[c.role] = round(100 * same / len(instances), 2)

    tests = [t for c in ok for t in c.tests or []]
    if tests:
        test_cases = [(t["instance"], t["sources"], t["others"]) for t in tests]
        ref_t, *gen_t = run_batched([rule.code] + [c.code for c in ok], test_cases)
        for c, results in zip(ok, gen_t, strict=True):
            passed = sum(fires(r) is t["fires"] for t, r in zip(tests, results, strict=True))
            report.own_tests[c.role] = f"{passed}/{len(tests)}"
        passed = [fires(r) is t["fires"] for t, r in zip(tests, ref_t, strict=True)]
        report.reference_on_tests = f"{sum(passed)}/{len(tests)}"
        for t, p in zip(tests, passed, strict=True):
            if not p and len(report.discrepancies) < 2 * MAX_LISTED:
                report.discrepancies.append(
                    f"reference fails agent test `{t['name']}` "
                    f"(expects {'fire' if t['fires'] else 'no fire'})"
                )
    return report


def render(reports: list[RuleReport], models: dict[str, str], started: datetime) -> str:
    lines = [
        f"# Compiler eval {started:%Y-%m-%d %H:%M} UTC",
        "",
        "Models: " + ", ".join(f"`{role}` = `{m}`" for role, m in sorted(models.items())),
        f"Golden instances: {len(golden.symbols())} text PDFs of batch 1.",
        "Agreement = % of instances where the generated code fires exactly when the reference",
        "(the hand-written code) does.",
        "",
        "| Rule | Outcome | Valid | Agreement A | Agreement B | Own tests A | Own tests B "
        "| Ref on agent tests | Retries A/B | Cost $ | Latency s |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in reports:
        by = {c.role: c for c in r.compiled}
        a, b = (by[role] for role in compiler.ROLES)
        cost = sum((c.trace.cost or 0) for c in r.compiled if c.trace)
        latency = max((c.trace.latency_ms if c.trace else 0) for c in r.compiled) / 1000
        retries = "/".join(str(c.trace.retries) if c.trace else "-" for c in (a, b))
        lines.append(
            f"| R{r.rule.id:02d} | {r.rule.decision} | {'yes' if r.valid else 'NO'} "
            f"| {pct(r, a)} | {pct(r, b)} | {r.own_tests.get(a.role, '-')} "
            f"| {r.own_tests.get(b.role, '-')} | {r.reference_on_tests or '-'} "
            f"| {retries} | {cost:.4f} | {latency:.1f} |"
        )
    total = sum((c.trace.cost or 0) for r in reports for c in r.compiled if c.trace)
    lines += ["", f"Total cost: ${total:.4f}", ""]
    for r in reports:
        lines += [f"## R{r.rule.id:02d} ({r.rule.decision}, {r.rule.type})", "", r.rule.text, ""]
        for c in r.compiled:
            if c.error:
                lines.append(f"- `{c.role}` failed to compile: {c.error[:300]}")
        lines += [f"- {d}" for d in r.discrepancies] or ["- No discrepancies."]
        lines.append("")
    return "\n".join(lines)


def pct(report: RuleReport, compiled: Compiled) -> str:
    if compiled.role not in report.agreement:
        return "failed"
    return f"{report.agreement[compiled.role]:.1f}%"


async def run(numbers: list[int] | None) -> tuple[Path, list[RuleReport]] | None:
    load_dotenv(pack.REPO / ".env")
    if not any(os.environ.get(k) for k in KEYS.values()):
        print(f"No LLM API key set ({', '.join(KEYS.values())}); skipping the compiler eval.")
        return None
    configured = models()
    if missing := missing_keys(configured):
        print(f"Configured models {configured} need {', '.join(missing)}; skipping.")
        return None

    defn = pack.definition()
    rules = [r for r in pack.rules(defn) if numbers is None or r.id in numbers]
    started = datetime.now(UTC)
    reports = []
    for rule in rules:
        compiled = await compile_both(rule, defn)
        report = await asyncio.to_thread(evaluate, rule, compiled)
        reports.append(report)
        print(f"R{rule.id:02d}: {'valid' if report.valid else 'NOT valid'} {report.agreement}")

    REPORTS.mkdir(exist_ok=True)
    path = REPORTS / f"compiler-{started:%Y%m%dT%H%M%SZ}.md"
    path.write_text(render(reports, configured, started), encoding="utf-8")
    print(f"Report: {path}")
    return path, reports


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m evals.eval_compiler")
    parser.add_argument("--rules", help="comma-separated rule numbers, e.g. 2,7 (default: all)")
    args = parser.parse_args()
    numbers = [int(n) for n in args.rules.split(",")] if args.rules else None
    asyncio.run(run(numbers))


if __name__ == "__main__":
    main()
