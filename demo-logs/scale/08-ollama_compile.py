"""One real compile (tester + coder + tests) of two invoice rules on a local Ollama model."""

import asyncio
import sys
import time

from app.core.database import session_factory
from app.features.agents import compiler, llm
from app.features.decisions import service as decisions
from app.features.processes.model import Symbol
from tests.support import pack

MODEL = sys.argv[1]
NUMBERS = [int(n) for n in sys.argv[2].split(",")]


async def main() -> None:
    async with session_factory() as session:
        sources = await decisions.current_sources(session, 1)
    use_case = pack.use_case()
    setups = {}
    for role, s in use_case.agents.items():
        settings = s.model_copy(update={"model": MODEL, "fallback_models": [], "timeout_seconds": 900})
        setups[role] = llm.Setup(settings)
    defn = pack.definition()
    symbols = [Symbol(**s) for s in defn["symbols"]]
    for rule in [r for r in pack.rules(defn) if r.id in NUMBERS]:
        runs = compiler.Runs(setups)
        t = time.perf_counter()
        try:
            c = await compiler.compile_text(rule, symbols, sources, use_case.description, runs)
            result = f"valid={c.report.get('valid')} tests={len(c.tests)} " + str(
                c.report.get("discrepancies", ""))[:300]
        except Exception as e:  # noqa: BLE001
            result = f"FAILED {type(e).__name__}: {str(e)[:300]}"
        wall = time.perf_counter() - t
        print(f"R{rule.id:02d} {MODEL}: {wall:.0f} s, {result}")
        for tr in runs.traces:
            print(f"  {tr.role}: {tr.latency_ms / 1000:.1f} s, {tr.input_tokens} in / "
                  f"{tr.output_tokens} out, retries {tr.retries}, "
                  f"{tr.output_tokens / max(tr.latency_ms / 1000, 0.001):.1f} out tok/s")


asyncio.run(main())
