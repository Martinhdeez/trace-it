"""A hiring process born on stage: discovery from CVs, a messy policy and a workbook.

    make hiring-demo                          # interactive: you answer the agent's questions
    make hiring-demo HIRING_ARGS="--auto"     # manager-notes.md answers for you

Talks to a running backend (`make setup`) whose `.env` has the agents' keys. The invoice
process is not involved. Steps, each written to the report
(`docs/evaluations/hiring-screening-<date>.md` unless `--report` says otherwise):

1. Log in as the manager, created if missing.
2. Start a discovery draft, upload `processes/hiring-screening/data/hiring-reference.xlsx`
   and paste `policy.md` in revise mode.
3. While the plan has questions: show them, take the manager's answers (the terminal, or
   `manager-notes.md` with `--auto`) and send them in revise mode. `--max-rounds` bounds it.
4. Show every proposal and accept or reject each one (the terminal, or accept all).
5. Prepare (the agents compile and test the rules, the acceptance examples run) and publish.
6. Upload the 44 CVs, run the engine, export. Compare symbols and outcomes with
   `expected.jsonl`, per category.
7. Resolve a few REVIEW cases by hand and ask the learner for norms (`--skip-learning`).

Nothing here decides: the driver only carries the manager's answers and approvals. The
report keeps every question, answer, proposal, review, preview result, mismatch and HTTP
error verbatim: it is the friction log of mapping a new problem onto trace-it.

Every stage also reports what the agents actually did, read from the backend's own audit
trail (`GET /traces`, ADR 0018): per model call the agent, the model that answered,
requests, rejected outputs, tokens, latency and its trace id; per batch the steps, their
time and their failures. `GET /traces/{trace_id}` then returns that tree in full, with the
exact instructions and output of each call.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "processes" / "hiring-screening"
DATA = PACK / "data"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

PREFACE = (
    "This is our hiring screening. Each CV is one case: a PDF from our ATS with a "
    '"Candidate profile" block of `Label: value` lines near the top. The workbook I uploaded '
    "holds our three sources of truth: positions, applicant_history and parameters (the "
    "screening date). Below is the policy exactly as our Head of People wrote it, an email "
    "thread. Propose the process. Before proposing rules, ask me whatever the thread leaves "
    "unclear or contradictory; I will answer.\n\n--- policy.md ---\n\n"
)
AUTO_FOLLOW_UP = (
    "My notes above are the answers. Where they are silent, follow the policy thread as "
    "written and keep the outcome it states; do not soften a check the thread settles. Ask "
    "again only if a fact you need is genuinely missing from the workbook or the notes."
)
# Human resolutions for the learning round: category -> (decision, reason). A person
# disagreeing with the engine on a pattern is what the learner looks for.
RESOLUTIONS = {
    "SALARY_OVER_CAP": (
        "INTERVIEW",
        "Cap is negotiable for strong seniors; CEO wants to see them.",
    ),
    "RECENT_REAPPLY": ("REJECT", "Nothing changed since the last application."),
}


class ApiError(Exception):
    def __init__(self, status: int, body: str):
        super().__init__(f"HTTP {status}: {body[:300]}")
        self.status, self.body = status, body


class Report:
    """Prints as it goes and keeps the same text, plus JSON details, for the Markdown file."""

    def __init__(self, path: Path):
        self.path = path
        self.lines: list[str] = []
        self.friction: list[str] = []
        self.started = time.monotonic()

    def say(self, text: str = "") -> None:
        print(text, flush=True)
        self.lines.append(text)

    def section(self, title: str) -> None:
        self.say(f"\n## {title}\n")

    def detail(self, title: str, payload) -> None:
        text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
        if len(text) > 12000:
            text = text[:12000] + "\n... (truncated)"
        self.lines += [
            f"<details><summary>{title}</summary>\n",
            "```json",
            text,
            "```",
            "</details>\n",
        ]

    def error(self, text: str) -> None:
        self.friction.append(text)
        self.say(f"ERROR {text}")

    def write(self, header: list[str]) -> None:
        minutes = (time.monotonic() - self.started) / 60
        body = [*header, "", *self.lines, "", "## Friction log", ""]
        body += [f"- {f}" for f in self.friction] or ["- No HTTP errors."]
        body += ["", f"Wall clock: {minutes:.1f} min."]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("\n".join(body) + "\n", encoding="utf-8")
        print(f"\nreport: {self.path}")


class Manager:
    """The person the agent talks to: someone at the terminal, or manager-notes.md."""

    def __init__(self, auto: bool, notes: str):
        self.auto, self.notes = auto, notes

    def answer(self, questions: list[str], round_: int) -> str:
        if self.auto:
            return self.notes if round_ == 1 else AUTO_FOLLOW_UP
        print("\nThe agent asks (answer, then an empty line; 'notes' pastes manager-notes.md):")
        for i, q in enumerate(questions, 1):
            print(f"  {i}. {q}")
        text = read_block()
        return self.notes if text.strip() == "notes" else text

    def review(self, key: str, summary: str) -> tuple[str, str]:
        if self.auto:
            return "accepted", "Accepted as proposed."
        answer = input(f"  {key}: {summary}\n    accept? [Y/n, or an objection] ").strip()
        if answer in ("", "y", "Y", "yes"):
            return "accepted", "Accepted as proposed."
        return "rejected", answer if len(answer) > 1 else "Rejected by the manager."

    def confirm(self, prompt: str) -> bool:
        return self.auto or input(f"{prompt} [y/N] ").strip().lower() in ("y", "yes")


def read_block() -> str:
    lines = []
    for line in sys.stdin:
        if not line.strip():
            break
        lines.append(line.rstrip("\n"))
    return (
        "\n".join(lines) or "I have nothing to add; decide conservatively and escalate to REVIEW."
    )


class Api:
    def __init__(self, base_url: str, report: Report):
        self.http = httpx.AsyncClient(base_url=base_url, timeout=httpx.Timeout(60, read=None))
        self.report = report
        self.marker = 0  # highest span id already reported

    async def call(self, method: str, path: str, expected: tuple[int, ...] = (), **kwargs):
        """One request; a failure is logged verbatim unless its status is `expected`."""
        response = await self.http.request(method, path, **kwargs)
        if response.status_code >= 400:
            if response.status_code not in expected:
                self.report.error(
                    f"{method} {path} -> {response.status_code}: {response.text[:800]}"
                )
            raise ApiError(response.status_code, response.text)
        if response.headers.get("content-type", "").startswith("application/json"):
            return response.json()
        return response.text

    async def login(self, email: str, name: str) -> dict:
        try:
            user = await self.call("POST", "/login", expected=(404,), json={"email": email})
        except ApiError as error:
            if error.status != 404:
                raise
            user = await self.call(
                "POST", "/users", json={"name": name, "email": email, "role": "manager"}
            )
        self.http.headers["X-User-Id"] = str(user["id"])
        return user

    async def since_last(self) -> list[dict]:
        """The spans the backend recorded since the previous call: the audit trail of the
        step that just ran (ADR 0018). Oldest first."""
        spans = await self.call("GET", "/traces", params={"limit": 1000})
        fresh = sorted((s for s in spans if s["id"] > self.marker), key=lambda s: s["id"])
        self.marker = max([s["id"] for s in spans] + [self.marker])
        return fresh


# --- observability ---------------------------------------------------------------------------


def model_calls(spans: list[dict]) -> list[dict]:
    return [s for s in spans if s["step"] == "llm_run"]


def totals(calls: list[dict]) -> dict:
    """What the agents spent, from the `llm_run` spans themselves."""
    data = [s["data"] or {} for s in calls]
    return {
        "calls": len(calls),
        "requests": sum(d.get("requests") or 0 for d in data),
        "retries": sum(d.get("retries") or 0 for d in data),
        "input_tokens": sum(d.get("input_tokens") or 0 for d in data),
        "output_tokens": sum(d.get("output_tokens") or 0 for d in data),
        "cached_tokens": sum(d.get("cached_tokens") or 0 for d in data),
        "seconds": round(sum(s.get("duration_ms") or 0 for s in calls) / 1000, 1),
        "failed_over": sum(len(d.get("failed_attempts") or []) for d in data),
    }


def agent_table(report: Report, spans: list[dict], title: str) -> None:
    """One row per model call: who ran, which model answered, what it cost, its trace."""
    calls = model_calls(spans)
    errors = [s for s in spans if s["status"] == "error"]
    if not calls and not errors:
        return
    report.say(f"\n**{title}**\n")
    if calls:
        report.say("| agent | model | requests | retries | in | out | cached | ms | trace |")
        report.say("|---|---|---|---|---|---|---|---|---|")
        for span in calls:
            d = span["data"] or {}
            report.say(
                f"| {d.get('agent') or d.get('role') or '?'} | {d.get('model', '?')} "
                f"| {d.get('requests', '')} | {d.get('retries', '')} "
                f"| {d.get('input_tokens', '')} | {d.get('output_tokens', '')} "
                f"| {d.get('cached_tokens', '')} | {span.get('duration_ms', '')} "
                f"| `{span['trace_id'][:12]}` |"
            )
        report.say(f"\ntotals: {totals(calls)}")
        for span in calls:
            d = span["data"] or {}
            if d.get("failed_attempts"):
                tried = "; ".join(
                    f"{f.get('model')}: {f.get('error')}" for f in d["failed_attempts"]
                )
                report.say(f"- fell back after {tried} (ADR 0019)")
            if d.get("retry_prompts"):
                report.say(f"- output rejected {len(d['retry_prompts'])}x: {d['retry_prompts']}")
    for span in errors:
        report.say(f"- ERROR span `{span['step']}`: {json.dumps(span['data'], default=str)[:400]}")


def step_table(report: Report, spans: list[dict], title: str) -> None:
    """The whole batch as steps: how many of each, how long, how many failed."""
    if not spans:
        return
    counts: dict[str, list] = {}
    for span in spans:
        row = counts.setdefault(span["step"], [0, 0, 0])
        row[0] += 1
        row[1] += span.get("duration_ms") or 0
        row[2] += span["status"] == "error"
    report.say(f"\n**{title}**\n")
    report.say("| step | count | total ms | errors |\n|---|---|---|---|")
    for step, (count, ms, failed) in sorted(counts.items(), key=lambda kv: -kv[1][1]):
        report.say(f"| `{step}` | {count} | {ms} | {failed} |")
    for span in (s for s in spans if s["status"] == "error"):
        report.say(f"- ERROR `{span['step']}`: {json.dumps(span['data'], default=str)[:300]}")


# --- discovery -----------------------------------------------------------------------------


def describe(plan: dict) -> list[str]:
    out = [f"**{plan.get('name') or '(no name yet)'}**: {plan.get('summary', '')}"]
    if plan.get("decision_types"):
        out.append("- outcomes: " + ", ".join(
            f"{t['name']} (p{t['priority']}{', default' if t.get('is_default') else ''}"
            f"{', human' if t.get('requires_human') else ''})"
            for t in plan["decision_types"]
        ))  # fmt: skip
    for s in plan.get("symbols", []):
        labels = ", ".join((s.get("extraction") or {}).get("labels") or [])
        out.append(
            f"- symbol `{s['name']}` {s['type']}{' required' if s.get('required') else ''}"
            f"{' labels: ' + labels if labels else ''}"
        )
    for s in plan.get("sources", []):
        where = f"{s.get('sheet')}!{s.get('first_row')}-{s.get('last_row')} {s.get('columns')}"
        out.append(
            f"- source `{s['name']}` ({s['kind']}) {where if s['kind'] == 'workbook' else ''}"
        )
    for r in plan.get("rules", []):
        out.append(f"- rule `{r['name']}` [{r['type']} -> {r['decision']}]: {r['text']}")
    for g in plan.get("guidance", []):
        out.append(f"- guidance `{g['name']}`: {g['text']}")
    for e in plan.get("examples", []):
        out.append(f"- example `{e['name']}` -> {e['decision']}: {e['explanation']}")
    return out


def proposal_keys(plan: dict) -> list[str]:
    return [
        "setup",
        *[f"source:{s['name']}" for s in plan.get("sources", [])],
        *[f"rule:{r['name']}" for r in plan.get("rules", [])],
        *[f"guidance:{g['name']}" for g in plan.get("guidance", [])],
        *[f"example:{e['name']}" for e in plan.get("examples", [])],
    ]


def proposal_summary(plan: dict, key: str) -> str:
    kind, _, name = key.partition(":")
    if kind == "setup":
        return f"{plan.get('name')}: {len(plan.get('symbols', []))} symbols, " + ", ".join(
            t["name"] for t in plan.get("decision_types", [])
        )
    items = {"source": "sources", "rule": "rules", "guidance": "guidance", "example": "examples"}
    item = next(i for i in plan.get(items[kind], []) if i["name"] == name)
    return item.get("text") or item.get("explanation") or json.dumps(item)[:120]


async def discover(api: Api, manager: Manager, report: Report, args) -> int | None:
    report.section("Discovery")
    draft = await api.call("POST", "/process-drafts", json={"name": args.name})
    draft_id = draft["id"]
    report.say(f"draft {draft_id} started for a new process '{args.name}'")

    with (DATA / "hiring-reference.xlsx").open("rb") as stream:
        draft = await api.call(
            "POST",
            f"/process-drafts/{draft_id}/workbooks",
            files={"file": ("hiring-reference.xlsx", stream, XLSX)},
            data={"revision": str(draft["revision"])},
        )
    report.say(f"workbook uploaded: {[d.get('name') for d in draft['documents']]}")

    policy = (PACK / "policy.md").read_text(encoding="utf-8")
    report.say("policy.md pasted (revise mode); waiting for the agent...")
    draft = await api.call(
        "POST",
        f"/process-drafts/{draft_id}/messages",
        json={"revision": draft["revision"], "mode": "revise", "message": PREFACE + policy},
    )

    for round_ in range(1, args.max_rounds + 1):
        plan = draft["plan"]
        report.say(f"\n### Proposal, round {round_}\n")
        for line in describe(plan):
            report.say(line)
        agent_table(report, await api.since_last(), f"What the agent did, round {round_}")
        report.detail(f"plan after round {round_}", plan)
        questions = plan.get("questions", [])
        if not questions:
            break
        report.say("\nThe agent asks:")
        for i, question in enumerate(questions, 1):
            report.say(f"{i}. {question}")
        answer = manager.answer(questions, round_)
        report.say("\nThe manager answers:\n")
        report.say("> " + answer.replace("\n", "\n> "))
        draft = await api.call(
            "POST",
            f"/process-drafts/{draft_id}/messages",
            json={"revision": draft["revision"], "mode": "revise", "message": answer},
        )
    else:
        plan = draft["plan"]
        if plan.get("questions"):
            report.error(
                f"{len(plan['questions'])} questions still open after {args.max_rounds} rounds; "
                "stopping. The agent could not settle the process from these inputs."
            )
            return None

    plan = draft["plan"]
    report.section("Review")
    report.say("Each proposal, accepted or rejected by the manager:\n")
    for key in proposal_keys(plan):
        disposition, explanation = manager.review(key, proposal_summary(plan, key))
        report.say(f"- {disposition} `{key}`: {explanation}")
        draft = await api.call(
            "POST",
            f"/process-drafts/{draft_id}/reviews",
            json={
                "revision": draft["revision"],
                "proposal": key,
                "disposition": disposition,
                "explanation": explanation,
            },
        )
    if any(v == "rejected" for v in draft["reviews"].values()):
        report.error("Some proposals were rejected; revise the draft in the console and rerun.")
        return None

    report.section("Prepare")
    report.say("compiling, testing and validating; this takes minutes...")
    draft = await api.call(
        "POST", f"/process-drafts/{draft_id}/prepare", json={"revision": draft["revision"]}
    )
    preview = draft["preview"] or {}
    for c in preview.get("compilations", []):
        valid = c.get("report", {}).get("valid")
        report.say(
            f"- rule `{c.get('name', c.get('text', '')[:60])}`: {'valid' if valid else 'NOT VALID'}"
        )
    for e in preview.get("examples", []):
        mark = "passed" if e.get("passed") else f"FAILED (got {e.get('actual')}: {e.get('reason')})"
        report.say(f"- example `{e['name']}` expected {e['expected']}: {mark}")
    report.say(f"- source rows: {preview.get('source_counts')}")
    report.say(f"- candidate valid: {preview.get('valid')}")
    agent_table(report, await api.since_last(), "What the agents did while preparing")
    report.detail("preview", preview)
    if not preview.get("valid"):
        report.error("The candidate failed preparation; nothing published.")
        return None

    report.section("Publish")
    if not manager.confirm("Publish this process?"):
        report.say("The manager did not publish.")
        return None
    draft = await api.call(
        "POST", f"/process-drafts/{draft_id}/publish", json={"revision": draft["revision"]}
    )
    process_id = draft["published_process_id"]
    report.say(f"published as process {process_id}")
    step_table(report, await api.since_last(), "Publication steps")
    return process_id


# --- the batch -----------------------------------------------------------------------------


def expected_rows() -> list[dict]:
    lines = (DATA / "expected.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def plain(symbols: dict | None) -> dict:
    return {
        k: (v.get("value") if isinstance(v, dict) and "value" in v else v)
        for k, v in (symbols or {}).items()
    }


async def screen(api: Api, report: Report, process_id: int, args) -> dict[str, dict]:
    report.section("CVs")
    rows = {row["file_id"]: row for row in expected_rows()}
    instances: dict[str, dict] = {}
    for path in sorted((DATA / "cvs").glob("*.pdf")):
        with path.open("rb") as stream:
            data = {"ocr": "true"} | ({"mode": args.mode} if args.mode else {})
            upload = await api.call(
                "POST",
                f"/processes/{process_id}/files",
                files={"file": (path.name, stream, "application/pdf")},
                data=data,
            )
        instances[path.name] = upload
        print(f"  {path.name}: {upload['status']}", flush=True)
    report.say(f"{len(instances)} CVs uploaded")
    step_table(report, await api.since_last(), "Extraction steps over the 44 CVs")

    # Symbols: what the reader got right, per symbol, text CVs and scanned CVs apart. Only
    # the symbols this process declared: the manager may have named or modelled them
    # differently from the answer key, and a field nobody asked for is not a misreading.
    declared = {name for i in instances.values() for name in plain(i.get("symbols"))}
    truth = list(next(iter(rows.values()))["symbols"])
    names = [name for name in truth if name in declared]
    if skipped := [name for name in truth if name not in declared]:
        report.say(f"\nnot declared by the published process, so not compared: {skipped}")
    if extra := sorted(declared - set(truth)):
        report.say(f"declared beyond the answer key, so not compared: {extra}")
    hits = {name: [0, 0, 0, 0] for name in names}  # text ok, text total, scan ok, scan total
    misses = []
    for file_id, row in rows.items():
        got = plain(instances[file_id].get("symbols"))
        offset = 2 if row["scanned"] else 0
        for name in names:
            hits[name][offset + 1] += 1
            if str(got.get(name)) == str(row["symbols"][name]) or (
                got.get(name) is None and row["symbols"][name] is None
            ):
                hits[name][offset] += 1
            else:
                misses.append(f"{file_id} [{row['category']}] {name}: expected "
                              f"{row['symbols'][name]!r}, read {got.get(name)!r}")  # fmt: skip
    report.say("\n| symbol | text CVs | scanned CVs |\n|---|---|---|")
    for name, (t_ok, t_n, s_ok, s_n) in hits.items():
        report.say(f"| `{name}` | {t_ok}/{t_n} | {s_ok}/{s_n} |")
    if misses:
        report.say("\nMisread or missing:\n")
        for miss in misses:
            report.say(f"- {miss}")

    report.section("Decisions")
    summary = await api.call("POST", f"/processes/{process_id}/run")
    report.say(f"run: {summary}")
    try:
        export = await api.call("GET", f"/processes/{process_id}/export")
    except ApiError:
        report.say("export refused (an instance is pending or awaiting review); comparing what ran")
        listed = await api.call("GET", f"/processes/{process_id}/instances")
        export = "\n".join(
            json.dumps({"file_id": i["name"], "result": i["decision"]}) for i in listed
        )
    exported = [json.loads(line) for line in export.splitlines() if line.strip()]
    got = {line["file_id"]: line["result"] for line in exported}
    by_category: dict[str, list] = {}
    for file_id, row in rows.items():
        by_category.setdefault(row["category"], []).append(
            (file_id, row["expected"], got.get(file_id))
        )
    report.say("\n| category | expected | matched | got |\n|---|---|---|---|")
    wrong = []
    for category, items in by_category.items():
        counts: dict[str, int] = {}
        for _, _, result in items:
            counts[str(result)] = counts.get(str(result), 0) + 1
        matched = sum(1 for _, exp, res in items if exp == res)
        report.say(f"| {category} | {items[0][1]} | {matched}/{len(items)} | {counts} |")
        wrong += [(fid, exp, res) for fid, exp, res in items if exp != res]
    if wrong:
        report.say("\nMismatches, with the rules that fired:\n")
        listed = {i["name"]: i for i in await api.call("GET", f"/processes/{process_id}/instances")}
        for file_id, expected, result in wrong:
            detail = await api.call("GET", f"/instances/{listed[file_id]['id']}")
            engine = next(
                (d for d in reversed(detail["decisions"]) if d["author"] == "engine"), None
            )
            fired = [r["reason"] for r in (engine or {}).get("results", []) if r.get("fires")]
            why = "; ".join(fired) or (engine or {}).get("reason") or "-"
            category = rows[file_id]["category"]
            report.say(f"- {file_id} [{category}] expected {expected}, got {result}: {why}")
    total = sum(1 for fid, row in rows.items() if got.get(fid) == row["expected"])
    report.say(f"\n**{total}/{len(rows)} CVs decided as the policy implies.**")
    return {fid: {**rows[fid], "got": got.get(fid), "instance": instances[fid]} for fid in rows}


async def learn(api: Api, manager: Manager, report: Report, process_id: int, cases: dict):
    report.section("Learning")
    listed = {i["name"]: i for i in await api.call("GET", f"/processes/{process_id}/instances")}
    resolved = 0
    for file_id, case in cases.items():
        if case["got"] != "REVIEW" or case["category"] not in RESOLUTIONS:
            continue
        decision, reason = RESOLUTIONS[case["category"]]
        await api.call(
            "POST",
            f"/instances/{listed[file_id]['id']}/resolve",
            json={"decision": decision, "reason": reason},
        )
        report.say(f"- {file_id} [{case['category']}] resolved by hand: {decision} ({reason})")
        resolved += 1
    if not resolved:
        report.say("no REVIEW case of a learnable category; nothing resolved by hand")
    analysis = await api.call("POST", f"/processes/{process_id}/learning", json={"case_limit": 30})
    report.say(f"\nanalysis {analysis['id']}: {analysis.get('reasoning', '')[:600]}")
    for proposal in analysis.get("proposals", []):
        report.say(f"\n- proposal {proposal['id']} ({proposal['kind']}): {proposal['text']}")
        report.say(f"  limitations: {proposal.get('limitations', '')}")
        if proposal["kind"] != "deterministic":
            continue
        try:
            validation = await api.call("POST", f"/norm-proposals/{proposal['id']}/validate")
        except ApiError:
            continue
        valid = validation["report"].get("valid")
        report.say(f"  validation {validation['id']}: {'valid' if valid else 'NOT valid'}")
        report.detail(f"validation {validation['id']}", validation["report"])
        if valid and manager.confirm(f"Approve norm {proposal['id']}?") and not manager.auto:
            await api.call(
                "POST",
                f"/norm-proposals/{proposal['id']}/approve",
                json={"validation_id": validation["id"], "reason": "Approved after review."},
            )
            report.say("  approved and published as rules")
    agent_table(report, await api.since_last(), "What the learner did")
    report.detail("analysis", analysis)


# --- main ----------------------------------------------------------------------------------


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--email", default="marta.ruiz@nortedigital.example")
    parser.add_argument(
        "--manager", default="Marta Ruiz", help="name for a manager created on the fly"
    )
    parser.add_argument("--name", default="Hiring screening", help="the new process's name")
    parser.add_argument("--process", type=int, help="skip discovery; screen with this process")
    parser.add_argument("--auto", action="store_true", help="manager-notes.md answers, accept all")
    parser.add_argument("--max-rounds", type=int, default=4)
    parser.add_argument("--mode", choices=["local", "hybrid", "api"], help="per-upload OCR mode")
    parser.add_argument("--skip-learning", action="store_true")
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "docs" / "evaluations" / f"hiring-screening-{datetime.now(UTC):%Y-%m-%d}.md",
    )
    return parser.parse_args(argv)


async def main(argv=None) -> int:
    args = parse_args(argv)
    report = Report(args.report)
    manager = Manager(args.auto, (PACK / "manager-notes.md").read_text(encoding="utf-8"))
    api = Api(args.base_url, report)
    header = [
        f"# Hiring screening: discovery run, {datetime.now(UTC):%d %B %Y}",
        "",
        f"`tools/hiring_demo.py` against `{args.base_url}`, "
        f"{'manager-notes.md answering (--auto)' if args.auto else 'a person answering'}. "
        "Inputs: `processes/hiring-screening/` (policy.md, manager-notes.md, data/). "
        "What the agent proposed, what the manager answered and where it broke, verbatim. "
        "Each stage also carries its audit trail; fetch any tree with "
        "`GET /traces/{trace_id}`.",
    ]
    code = 0
    try:
        user = await api.login(args.email, args.manager)
        report.say(f"manager: {user['name']} (id {user['id']})")
        await api.since_last()  # baseline: this run's tables start here, not at the epoch
        process_id = args.process
        if process_id is None:
            process_id = await discover(api, manager, report, args)
        if process_id is None:
            code = 1
        else:
            cases = await screen(api, report, process_id, args)
            if not args.skip_learning:
                await learn(api, manager, report, process_id, cases)
    except ApiError:
        code = 1
    except KeyboardInterrupt:
        report.say("interrupted")
        code = 130
    finally:
        await api.http.aclose()
        report.write(header)
    return code


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
