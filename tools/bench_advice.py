"""Latency benchmark of the escalation advice (docs/reviewer-agent.md, "Latency").

    make bench-advice DB=<database> [N=5]

It runs the decision assistant on the demo cases: the 10 % VAT rule, the duplicate order and
MISSING_DATA. It runs the reviewer agent on a resolved VAT case. The cases are found by their
engine reason in `DB`, a database where the invoice pack has run. Use a copy (`createdb -T`),
never a live stack's database: every call writes its spans there. The agents use the
`assistant` role of `processes/invoice-payment/use-case.json` in this checkout, so the same
command on two branches compares their settings and code.

It prints p50/p95/max latency, tokens, validator retries and fallbacks per case, plus one
sample answer per case. Each request carries a unique id: Helmcode caches identical
temperature-0 requests and would answer a repeat in 0.35 s. Without a key it skips.
"""

# ruff: noqa: E402 - the imports below need `sys.path` set first.
import argparse
import asyncio
import json
import os
import statistics
import sys
import time
import uuid
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "backend")]

from app.core.database import session_factory
from app.features.agents import assistant, llm
from app.features.decisions.model import ENGINE, Decision
from app.features.ingestion.model import Instance
from app.features.proposals.service import learnable
from app.features.use_cases.service import read_file
from app.features.versions import configuration
from sqlalchemy import select

CASES = {"vat": "VAT rate", "duplicate": "Same order as", "missing_data": "MISSING_DATA"}
KEYS = {"helmcode": "HELMCODE_API_KEY", "vercel": "AI_GATEWAY_API_KEY"}


def pack_role() -> llm.Setup:
    use_case = read_file(ROOT / "processes" / "invoice-payment" / "use-case.json")
    return llm.Setup(use_case.agents["assistant"])


def missing_keys(setup: llm.Setup) -> list[str]:
    models = [setup.settings.model or "", *setup.settings.fallback_models]
    keys = {KEYS[m.split(":", 1)[0]] for m in models if m.split(":", 1)[0] in KEYS}
    return sorted(k for k in keys if not os.environ.get(k))


SEEN: dict = {}


def instrument(role: llm.Setup) -> None:
    """The pack's role in place of the version's frozen one, a unique id per request, and
    what each run did."""
    frozen = configuration.setups

    def setups(snapshot):
        found = frozen(snapshot)
        own = found["assistant"]
        found["assistant"] = llm.Setup(
            settings=role.settings, config_id=own.config_id, execution_hash=own.execution_hash
        )
        return found

    run, chain, retry_prompts = llm.run, llm.chain, llm._retry_prompts

    async def unique(agent, role_name, user_prompt, **kw):
        user_prompt = user_prompt[:-1] + f', "request_id": "{uuid.uuid4().hex[:8]}"}}'
        output, trace = await run(agent, role_name, user_prompt, **kw)
        SEEN["trace"] = trace
        return output, trace

    def counted(setup, role_name, failed):
        SEEN["failed"] = failed
        return chain(setup, role_name, failed)

    def prompts(messages):
        SEEN["retries"] = len(found := retry_prompts(messages))
        return found

    configuration.setups, llm.run, llm.chain, llm._retry_prompts = setups, unique, counted, prompts


async def find_cases(session) -> dict[str, tuple[str, int]]:
    """{label: (agent, instance id)}: the escalated demo cases (both invoices of the
    duplicate order), and a resolved VAT case."""
    found: dict[str, tuple[str, int]] = {}
    latest: dict[int, list[Decision]] = {}
    for decision in await session.scalars(select(Decision).order_by(Decision.id)):
        latest.setdefault(decision.instance_id, []).append(decision)
    for instance_id, history in latest.items():
        engine = next((d for d in reversed(history) if d.author == ENGINE), None)
        if engine is None or engine.decision != "ESCALAR":
            continue
        for label, reason in CASES.items():
            if (engine.reason or "").startswith(reason):
                if history[-1].author == ENGINE:
                    if label == "duplicate":
                        label += "_2" if "duplicate_1" in found else "_1"
                    found.setdefault(label, ("assistant", instance_id))
                elif label == "vat":
                    found.setdefault("vat_rule", ("reviewer", instance_id))
    return found


async def call(agent: str, instance_id: int):
    async with session_factory() as session:
        if agent == "assistant":
            return await assistant.suggest(session, instance_id)
        from app.features.versions.model import ProcessVersion

        instance = await session.get(Instance, instance_id)
        history = list(
            await session.scalars(
                select(Decision).where(Decision.instance_id == instance_id).order_by(Decision.id)
            )
        )
        engine = next(d for d in reversed(history) if d.author == ENGINE)
        snapshot = (await session.get(ProcessVersion, engine.version_id)).snapshot
        human = {t["name"] for t in snapshot["process"]["decision_types"] if t["requires_human"]}
        rules = {r.id: r.decision for r in configuration.rules(snapshot)}
        outcomes = configuration.outcomes(snapshot)
        rule_id, why = learnable(
            engine.reason, engine.results, rules, outcomes, human, history[-1].decision
        )
        if rule_id is None:
            raise RuntimeError(why)
        return await assistant.suggest_rule(session, instance, engine, history[-1], rule_id)


def pct(values: list[float], p: int) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(p / 100 * (len(ordered) - 1)))]


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-n", type=int, default=5, help="calls per case")
    args = parser.parse_args()
    role = pack_role()
    if missing := missing_keys(role):
        print(f"bench-advice skipped: no {', '.join(missing)}")
        return 0
    instrument(role)
    async with session_factory() as session:
        cases = await find_cases(session)
    if not cases:
        print("bench-advice skipped: no escalated demo case in this database")
        return 0
    s = role.settings
    print(
        f"model {s.model} -> {s.fallback_models}, timeout {s.timeout_seconds} s, "
        f"retries {s.retries}, limits {s.limits}, n={args.n}\n"
    )
    print(
        f"{'case':14} {'agent':9} {'ok':>4} {'p50 s':>6} {'p95 s':>6} {'max s':>6} "
        f"{'in':>6} {'out':>5} {'retries':>7} {'fallbacks':>9}"
    )
    samples, every = {}, []
    for label, (agent, instance_id) in cases.items():
        rows = []
        for _ in range(args.n):
            SEEN.clear()
            start = time.perf_counter()
            try:
                answer, error = await call(agent, instance_id), None
            except Exception as e:  # noqa: BLE001 - a failed call is a measurement too
                answer, error = None, f"{type(e).__name__}: {str(e)[:200]}"
            trace = SEEN.get("trace")
            row = {
                "case": label,
                "agent": agent,
                "seconds": round(time.perf_counter() - start, 2),
                "model": trace.model if trace else None,
                "input_tokens": trace.input_tokens if trace else 0,
                "output_tokens": trace.output_tokens if trace else 0,
                "retries": SEEN.get("retries", 0),
                "fallbacks": len(SEEN.get("failed", [])),
                "error": error,
                "answer": answer.model_dump() if answer else None,
            }
            rows.append(row)
            if answer and label not in samples:
                samples[label] = row["answer"]
        every += rows
        seconds = [r["seconds"] for r in rows]
        ok = [r for r in rows if not r["error"]]
        print(
            f"{label:14} {agent:9} {len(ok):>2}/{len(rows):<2}{pct(seconds, 50):>6.1f} "
            f"{pct(seconds, 95):>6.1f} {max(seconds):>6.1f} "
            f"{statistics.mean(r['input_tokens'] for r in rows):>6.0f} "
            f"{statistics.mean(r['output_tokens'] for r in rows):>5.0f} "
            f"{sum(r['retries'] for r in rows):>7} {sum(r['fallbacks'] for r in rows):>9}"
        )
        answers = [r["answer"] for r in ok]
        decisions = Counter(
            a.get("decision") or ("no rule" if not a["text"] else "rule") for a in answers
        )
        print(f"{'':14} decisions: {dict(decisions)}")
        for r in rows:
            if r["error"]:
                print(f"{'':14} error: {r['error']}")
    seconds = [r["seconds"] for r in every]
    print(
        f"\nall: {len(every)} calls, p50 {pct(seconds, 50):.1f} s, p95 {pct(seconds, 95):.1f} s, "
        f"max {max(seconds):.1f} s, {sum(1 for r in every if r['error'])} errors"
    )
    print("\nOne answer per case:")
    for label, answer in samples.items():
        print(f"- {label}: {json.dumps(answer, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
    sys.exit(asyncio.run(main()))
