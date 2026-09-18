"""Opt-in evaluation of the LLM rule compiler against Mateo's hand-written v3 rules.

    make eval-compiler                                   # all 16 rules
    cd backend && uv run python -m evals.eval_compiler --rules 2,7

For each rule, both blind compiler agents run with the real configured models (`llm_config`
in the app database, keys from `.env`). Both generated codes then run in the real sandbox on
every golden instance of batch 1 (and on the compiler's own tests), and are compared with the
reference code. The report goes to `backend/evals/reports/compiler-<timestamp>.md`.

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

from tests.golden import golden
from tests.support import app_adapter as adapter
from tests.support import challenge

REPORTS = Path(__file__).parent / "reports"
KEYS = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY"}
MAX_LISTED = 8


@dataclass
class RuleReport:
    spec: adapter.RuleSpec
    compiled: list[adapter.Compiled]
    agreement: dict[str, float] = field(default_factory=dict)  # role -> % equal to reference
    discrepancies: list[str] = field(default_factory=list)
    own_tests: dict[str, str] = field(default_factory=dict)  # role -> "passed/total"
    reference_on_tests: str = ""  # does the reference pass the agents' tests?

    @property
    def valid(self) -> bool:
        return all(c.code for c in self.compiled) and all(
            self.agreement.get(c.role) == 100.0 for c in self.compiled
        )


def missing_keys(models: dict[str, str]) -> list[str]:
    """Env vars the configured models need and that are not set."""
    needed = {KEYS[m.split("/")[0]] for m in models.values() if m.split("/")[0] in KEYS}
    return sorted(k for k in needed if not os.environ.get(k))


def evaluate(spec: adapter.RuleSpec, compiled: list[adapter.Compiled]) -> RuleReport:
    report = RuleReport(spec, compiled)
    reference = adapter.REFERENCE_CODE[spec.number - 1]
    sources = challenge.sources()
    instances = golden.symbols()
    cases = [(s, sources, adapter.others_of(instances, s)) for s in instances]
    ok = [c for c in compiled if c.code]
    ref, *generated = adapter.run_batched([reference] + [c.code for c in ok], cases)
    for c, results in zip(ok, generated, strict=True):
        same = 0
        for s, r, g in zip(instances, ref, results, strict=True):
            if adapter.verdict(r) is adapter.verdict(g) and adapter.verdict(g) is not None:
                same += 1
            elif len(report.discrepancies) < MAX_LISTED:
                report.discrepancies.append(
                    f"{c.role} on `{s['file_id']}`: reference {describe(r)}, generated "
                    f"{describe(g)}"
                )
        report.agreement[c.role] = round(100 * same / len(instances), 2)

    tests = [t for c in ok for t in c.tests or []]
    if tests:
        codes = [reference] + [c.code for c in ok]
        ref_t, *gen_t = adapter.run_batched(codes, adapter.cases_of(tests))
        for c, results in zip(ok, gen_t, strict=True):
            passed = sum(
                adapter.verdict(r) is adapter.fires_of(t)
                for t, r in zip(tests, results, strict=True)
            )
            report.own_tests[c.role] = f"{passed}/{len(tests)}"
        passed = [
            adapter.verdict(r) is adapter.fires_of(t) for t, r in zip(tests, ref_t, strict=True)
        ]
        report.reference_on_tests = f"{sum(passed)}/{len(tests)}"
        for t, p in zip(tests, passed, strict=True):
            if not p and len(report.discrepancies) < 2 * MAX_LISTED:
                report.discrepancies.append(
                    f"reference fails agent test `{adapter.name_of(t)}` "
                    f"(expects {'fire' if adapter.fires_of(t) else 'no fire'})"
                )
    return report


def describe(result: Any) -> str:
    v = adapter.verdict(result)
    if v is None:
        return f"ERROR ({str(result)[:80]})"
    return f"fires ({adapter.reason(result)[:60]})" if v else "does not fire"


def render(reports: list[RuleReport], models: dict[str, str], started: datetime) -> str:
    lines = [
        f"# Compiler eval {started:%Y-%m-%d %H:%M} UTC",
        "",
        "Models: " + ", ".join(f"`{role}` = `{m}`" for role, m in sorted(models.items())),
        f"Golden instances: {len(golden.symbols())} text PDFs of batch 1.",
        "Agreement = % of instances where the generated code fires exactly when the reference",
        "(Mateo's hand-written code) does.",
        "",
        "| Rule | Outcome | Valid | Agreement A | Agreement B | Own tests A | Own tests B "
        "| Ref on agent tests | Repairs A/B | Cost $ | Latency s |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in reports:
        by = {c.role: c for c in r.compiled}
        a, b = (by.get(role) for role in adapter.COMPILER_ROLES)
        cost = sum(c.cost or 0 for c in r.compiled)
        latency = max((c.latency_ms or 0) for c in r.compiled) / 1000
        lines.append(
            f"| R{r.spec.number:02d} | {r.spec.decision} | {'yes' if r.valid else 'NO'} "
            f"| {pct(r, a)} | {pct(r, b)} | {r.own_tests.get(a.role, '-')} "
            f"| {r.own_tests.get(b.role, '-')} | {r.reference_on_tests or '-'} "
            f"| {a.repairs}/{b.repairs} | {cost:.4f} | {latency:.1f} |"
        )
    total = sum(c.cost or 0 for r in reports for c in r.compiled)
    lines += ["", f"Total cost: ${total:.4f} (tokens are not reported by the LLM client)", ""]
    for r in reports:
        lines += [
            f"## R{r.spec.number:02d} ({r.spec.decision}, {r.spec.kind})",
            "",
            r.spec.text,
            "",
        ]
        for c in r.compiled:
            if c.error:
                lines.append(f"- `{c.role}` failed to compile: {c.error[:300]}")
        lines += [f"- {d}" for d in r.discrepancies] or ["- No discrepancies."]
        lines.append("")
    return "\n".join(lines)


def pct(report: RuleReport, compiled: adapter.Compiled | None) -> str:
    if compiled is None or compiled.role not in report.agreement:
        return "failed"
    return f"{report.agreement[compiled.role]:.1f}%"


async def run(numbers: list[int] | None) -> tuple[Path, list[RuleReport]] | None:
    load_dotenv(adapter.REPO / ".env")
    if not any(os.environ.get(k) for k in KEYS.values()):
        print(f"No LLM API key set ({', '.join(KEYS.values())}); skipping the compiler eval.")
        return None
    try:
        models = await adapter.configured_models()
    except Exception as error:  # the database is where the models are configured
        print(f"Cannot read the configured models from the database ({error}); skipping.")
        return None
    if missing := missing_keys(models):
        print(f"Configured models {models} need {', '.join(missing)}; skipping.")
        return None

    defn = adapter.definition()
    specs = [s for s in adapter.rules(defn) if numbers is None or s.number in numbers]
    started = datetime.now(UTC)
    reports = []
    for spec in specs:
        compiled = await adapter.compile_rule(spec, defn, challenge.sources())
        report = await asyncio.to_thread(evaluate, spec, compiled)
        reports.append(report)
        print(f"R{spec.number:02d}: {'valid' if report.valid else 'NOT valid'} {report.agreement}")

    REPORTS.mkdir(exist_ok=True)
    path = REPORTS / f"compiler-{started:%Y%m%dT%H%M%SZ}.md"
    path.write_text(render(reports, models, started), encoding="utf-8")
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
