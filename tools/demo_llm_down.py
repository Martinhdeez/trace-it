"""Resilience demo (ADR 0019): the primary model's provider is down, the fallback answers.

    make demo-llm-down

The invoice use case's normalizer runs on a one-sentence norm with its real settings and
fallback chain, except that the primary model is sent to an unreachable address
(`OPENAI_BASE_URL`, set by the make target). The `llm_run` span shows the failed attempt and
the model that answered. It is also written to the `events` table when the database is up
and migrated; if not, the demo still prints it.
"""

# ruff: noqa: E402 - the imports below need `sys.path` set first.
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "backend")]

from app.core import events
from app.features.agents import llm, normalizer
from app.features.use_cases.service import read_file

NORM = "An invoice above 50000 euros is escalated to a person."


async def main() -> None:
    logging.getLogger("app.core.events").setLevel(logging.CRITICAL)  # no DB: no traceback
    pack = json.loads((ROOT / "processes/invoice-payment.json").read_text(encoding="utf-8"))
    use_case = read_file(ROOT / "processes/invoice-payment/use-case.json")
    settings = use_case.agents["normalizer"]
    primary = settings.model.removeprefix("helmcode:")
    down = settings.model_copy(update={"model": f"openai:{primary}"})
    print(f"primary openai:{primary} at {os.environ.get('OPENAI_BASE_URL')} (unreachable)")
    print(f"fallbacks {settings.fallback_models}\n")

    defaults = {"is_default": False, "requires_human": False}
    types = [SimpleNamespace(**{**defaults, **t}) for t in pack["decision_types"]]
    symbols = [SimpleNamespace(**{"description": "", **s}) for s in pack["symbols"]]
    with events.span("demo_llm_down") as demo:
        output, _ = await normalizer.normalize(
            NORM, use_case.description, types, symbols, {}, [], llm.Setup(down)
        )
    run = next(r["data"] for r in demo.rows if r["step"] == "llm_run")
    print("llm_run span (trace", demo.trace_id + "):")
    for key in ("chain", "failed_attempts", "model", "requests", "retries", "output_tokens"):
        print(f"  {key}: {json.dumps(run.get(key), ensure_ascii=False)}")
    for sentence in output.norm_rules:
        for check in sentence.checks:
            print(f"  -> {check.type} {check.decision}: {check.text}")


asyncio.run(main())
