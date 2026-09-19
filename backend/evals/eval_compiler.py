"""Opt-in evaluation of the LLM rule compiler against the hand-written v3 rules.

    make eval-compiler                                   # all 16 rules
    cd backend && uv run python -m evals.eval_compiler --rules 2,7

For each rule, the whole compile loop runs as the app would run it: with the invoice use
case's agent settings (`processes/invoice-payment/use-case.json`: models, guidance, limits,
examples; a role without a model uses `TRACE_<ROLE>_MODEL`) and keys from `.env`. The
generated code then runs in the real sandbox on every golden instance of batch 1 and is
compared with the reference code; the reference also runs on the tester's tests, which
measures the tester on its own. The report goes to `backend/evals/reports/compiler-<ts>.md`.

Without the keys the configured models need, it prints why and exits 0, so it never breaks
a default run.
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
# provider prefix of a `provider:model` string -> the env var its key comes from
KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
    "google-gla": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "helmcode": "HELMCODE_API_KEY",
}
MAX_LISTED = 8
Case = tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]


@dataclass
class RuleReport:
    rule: Rule
    compilation: compiler.Compilation | None = None
    traces: list[llm.Trace] = field(default_factory=list)
    error: str | None = None
    agreement: float | None = None  # % of golden instances equal to the reference
    discrepancies: list[str] = field(default_factory=list)
    reference_on_tests: str = ""  # does the reference pass the tester's tests?

    @property
    def valid(self) -> bool:
        return bool(self.compilation and self.compilation.report["valid"]) and (
            self.agreement == 100.0
        )


def setups() -> compiler.Setups:
    """How each role runs in the invoice use case, as the loaded pack would configure it."""
    return {role: llm.Setup(s) for role, s in pack.use_case().agents.items()}


def models(setups: compiler.Setups) -> dict[str, str]:
    return {
        role: str((setups[role].settings.model if role in setups else None) or llm.model_for(role))
        for role in compiler.ROLES
    }


def missing_keys(models: dict[str, str]) -> list[str]:
    """Env vars the configured models need and that are not set."""
    needed = {KEYS[p] for m in models.values() if (p := m.split(":")[0]) in KEYS}
    return sorted(k for k in needed if not os.environ.get(k))


async def compile_one(
    rule: Rule, defn: dict[str, Any], setups: compiler.Setups | None = None
) -> RuleReport:
    """The compile loop on one rule, with the context the app would give it."""
    report = RuleReport(rule)
    symbols = [Symbol(**s) for s in defn["symbols"]]
    runs = compiler.Runs(setups)
    description = pack.use_case().description
    try:
        report.compilation = await compiler.compile_text(
            rule, symbols, challenge.sources(), description, runs
        )
    except Exception as e:  # noqa: BLE001 - one failing rule must not stop the eval
        report.error = f"{type(e).__name__}: {e}"
    report.traces = runs.traces
    return report


def run_batched(code: str, cases: list[Case], chunk: int = 60) -> list[Any]:
    """`code` over every case in the real sandbox, chunked to stay under its memory limit."""
    results: list[Any] = []
    for i in range(0, len(cases), chunk):
        part = cases[i : i + chunk]
        try:
            results += sandbox.run_batch(code, part, timeout_s=120)
        except sandbox.SandboxError as error:  # the whole chunk failed
            results += [error] * len(part)
    return results


def fires(result: Any) -> bool | None:
    if isinstance(result, dict) and isinstance(result.get("fires"), bool):
        return result["fires"]
    return None


def describe(result: Any) -> str:
    v = fires(result)
    if v is None:
        return f"ERROR ({str(result)[:80]})"
    return f"fires ({str(result.get('reason'))[:60]})" if v else "does not fire"


def evaluate(report: RuleReport) -> RuleReport:
    """Score the compiled code against the reference on the golden instances, and the
    reference against the tester's tests."""
    c = report.compilation
    if c is None or c.code is None:
        return report
    rule = report.rule
    instances = golden.symbols()
    others = {
        s["file_id"]: [{**o, "_instance": o["file_id"]} for o in instances if o is not s]
        for s in instances
    }
    cases = [(s, challenge.sources(), others[s["file_id"]]) for s in instances]
    ref, generated = run_batched(rule.code, cases), run_batched(c.code, cases)
    same = 0
    for s, r, g in zip(instances, ref, generated, strict=True):
        if fires(r) is fires(g) and fires(g) is not None:
            same += 1
        elif len(report.discrepancies) < MAX_LISTED:
            report.discrepancies.append(
                f"`{s['file_id']}`: reference {describe(r)}, generated {describe(g)}"
            )
    report.agreement = round(100 * same / len(instances), 2)

    if c.tests:
        test_cases = [(t["instance"], t["sources"], t["others"]) for t in c.tests]
        ref_t = run_batched(rule.code, test_cases)
        passed = [fires(r) is t["fires"] for t, r in zip(c.tests, ref_t, strict=True)]
        report.reference_on_tests = f"{sum(passed)}/{len(c.tests)}"
        for t, p, r in zip(c.tests, passed, ref_t, strict=True):
            if not p and len(report.discrepancies) < 2 * MAX_LISTED:
                report.discrepancies.append(
                    f"reference fails tester test `{t['name']}` (expects "
                    f"{'fire' if t['fires'] else 'no fire'}, reference {describe(r)})"
                )
    return report


def render(reports: list[RuleReport], models: dict[str, str], started: datetime) -> str:
    lines = [
        f"# Compiler eval {started:%Y-%m-%d %H:%M} UTC",
        "",
        "Models: " + ", ".join(f"`{role}` = `{m}`" for role, m in sorted(models.items())),
        f"Golden instances: {len(golden.symbols())} text PDFs of batch 1.",
        "Agreement = % of instances where the generated code fires exactly when the reference",
        "(the hand-written code) does. Ref on tests = the reference on the tester's tests.",
        "",
        "| Rule | Outcome | Valid | Loop | Agreement | Ref on tests | Attempts | Reviews "
        "| Cost $ | Latency s |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in reports:
        c = r.compilation
        loop = "error" if r.error else ("needs data" if c.code is None else str(c.report["valid"]))
        cost = sum(t.cost or 0 for t in r.traces)
        latency = sum(t.latency_ms for t in r.traces) / 1000
        agreement = "-" if r.agreement is None else f"{r.agreement:.1f}%"
        lines.append(
            f"| R{r.rule.id:02d} | {r.rule.decision} | {'yes' if r.valid else 'NO'} | {loop} "
            f"| {agreement} | {r.reference_on_tests or '-'} "
            f"| {c.report.get('attempts', '-') if c else '-'} "
            f"| {len(c.report.get('reviews', [])) if c else '-'} | {cost:.4f} | {latency:.1f} |"
        )
    total = sum(t.cost or 0 for r in reports for t in r.traces)
    lines += ["", f"Total cost: ${total:.4f}", ""]
    for r in reports:
        lines += [f"## R{r.rule.id:02d} ({r.rule.decision}, {r.rule.type})", "", r.rule.text, ""]
        if r.error:
            lines.append(f"- Failed to compile: {r.error[:300]}")
        if r.compilation:
            lines += [f"- Loop: {d}" for d in r.compilation.report["discrepancies"]]
            lines += [
                f"- Review of `{v['test']}`: {v['before']} -> {v['fires']} ({v['reason']})"
                for v in r.compilation.report.get("reviews", [])
            ]
        lines += [f"- {d}" for d in r.discrepancies] or ["- No discrepancies."]
        lines.append("")
    return "\n".join(lines)


async def run(numbers: list[int] | None) -> tuple[Path, list[RuleReport]] | None:
    load_dotenv(pack.REPO / ".env")
    configured_setups = setups()
    configured = models(configured_setups)
    if missing := missing_keys(configured):
        print(f"Configured models {configured} need {', '.join(missing)}; skipping.")
        return None

    defn = pack.definition()
    rules = [r for r in pack.rules(defn) if numbers is None or r.id in numbers]
    started = datetime.now(UTC)
    reports = []
    for rule in rules:
        compiled = await compile_one(rule, defn, configured_setups)
        report = await asyncio.to_thread(evaluate, compiled)
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
