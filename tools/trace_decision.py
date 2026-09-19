"""Follow one invoice through the API, as text: state, decisions, evidence, latency, errors,
retries and pending work. Read-only; stdlib only.

    make trace-decision FILE=scan_002.pdf [PROCESS=<id>]
    python3 tools/trace_decision.py scan_002.pdf --api-url http://127.0.0.1:8000
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API = ""


def get(path: str):
    with urllib.request.urlopen(API + path, timeout=30) as response:
        return json.load(response)


def walk(nodes: list[dict], depth: int = 0):
    for node in nodes:
        yield depth, node
        yield from walk(node.get("children", []), depth + 1)


def ms(value) -> str:
    return "-" if value is None else f"{value:.0f} ms"


def find(name: str, process: int | None) -> dict:
    processes = get("/processes")
    if process is not None:
        processes = [p for p in processes if p["id"] == process]
    matches = [
        (p, i)
        for p in processes
        for i in get(f"/processes/{p['id']}/instances")
        if i["name"] == name
    ]
    if not matches:
        sys.exit(f"No instance named {name!r}" + (f" in process {process}" if process else ""))
    for p, i in matches[:-1]:
        print(f"(also instance {i['id']} in process {p['id']} '{p['name']}'; PROCESS=<id>)")
    return max(matches, key=lambda m: m[1]["id"])


def main() -> None:
    global API
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", help="the PDF's name (file_id), or an instance id")
    parser.add_argument("--process", type=int, help="default: the newest instance of that name")
    port = os.getenv("BACKEND_PORT", "8000")
    parser.add_argument("--api-url", default=f"http://127.0.0.1:{port}")
    args = parser.parse_args()
    API = args.api_url.rstrip("/")

    if args.file.isdigit():
        trace = get(f"/instances/{args.file}/trace")
        process = get(f"/processes/{trace['process_id']}")
    else:
        process, instance = find(args.file, args.process)
        trace = get(f"/instances/{instance['id']}/trace")
    pid = process["id"]

    print(f"== {trace['name']}  (instance {trace['id']}, process {pid} '{process['name']}')")
    print(f"state: {trace['status']}   exported result: {trace['exported_decision'] or '-'}")
    if trace["file"]:
        f = trace["file"]
        print(f"file: sha256 {f['hash'][:12]}, {f['size_bytes']} bytes, read {f['ingested_at']}")

    print("\n-- Decisions (oldest first; history is append-only)")
    versions = {}
    for d in trace["decisions"]:
        vid = d.get("version_id")
        if vid and vid not in versions:
            versions[vid] = get(f"/process-versions/{vid}")
        v = versions.get(vid)
        print(f"#{d['id']} {d['created_at'][:19]}  {d['decision']}  by {d['author']}")
        print(f"   reason: {d['reason'] or '-'}")
        version = (
            f"v{v['number']} (published by {v['author']}: {v['reason']}; "
            f"content {v['content_hash'][:12]})"
            if v
            else "-"
        )
        print(f"   process version: {version}   rules hash: {d['rules_hash'][:12]}")
        for r in d.get("rule_results", []):
            if r["fires"] is not False:
                state = "FIRED" if r["fires"] else "COULD NOT EVALUATE"
                code = (r["hash"] or "-")[:12]
                print(f"   {state} rule {r['rule_id']} (code {code}): {r['reason']}")
                print(f"      text: {(r['rule_text'] or '')[:110]}")
        if not any(r["fires"] is not False for r in d.get("rule_results", [])):
            print(f"   no rule fired: default decision ({len(d['results'])} rules evaluated)")

    print("\n-- Evidence: symbols and their origin")
    symbols = trace["symbols"] or {}
    for name, s in sorted(symbols.items()):
        value = str(s["value"]).replace("\n", " ")
        value = value if len(value) <= 40 else value[:37] + "..."
        print(f"   {name:15} {value:40} {s['origin']}")
    origins = [s["origin"].split(":") for s in symbols.values()]
    if any(o[0] == "scan" for o in origins):
        unconfirmed = [n for n, s in symbols.items() if s["origin"].count(":") > 1]
        print(f"   scan (no text layer, ADR 0025); not confirmed by its readers: {unconfirmed}")

    spans = trace["spans"]
    print("\n-- Latency per step (spans of this instance, ADR 0018)")
    for depth, s in walk(spans):
        if s["step"] == "evaluate_rule":
            continue  # summarised on the run line; per-rule runtime below
        data = s["data"] or {}
        note = ""
        if s["step"] == "run_process":
            note = f"  (batch: {data.get('instances')} instances, {data.get('rules')} rules)"
        elif s["step"] == "ocr":
            note = f"  (page {data.get('page')}, reader {data.get('reader')})"
        elif s["step"] == "decision":
            note = f"  -> {data.get('decision')}"
        step = "  " * depth + s["step"]
        print(f"   {step:24} {s['status']:5} {ms(s['duration_ms'])}{note}")

    print("\n-- Errors and retries")
    errors = [s for _, s in walk(spans) if s["status"] == "error"]
    for s in errors:
        print(f"   ERROR {s['step']}: {(s['data'] or {}).get('error', '')[:150]}")
    for _, s in walk(spans):
        if s["step"] == "extraction":
            d = s["data"] or {}
            print(
                f"   extraction {d.get('extraction_id', '')[:12]}: {d.get('ocr_calls', 0)} OCR, "
                f"{d.get('vlm_calls', 0)} vision, {d.get('jev_calls', 0)} judge calls; "
                f"warnings {d.get('warnings', 0)} {d.get('warning_codes') or ''}"
            )
    latest = trace["decisions"][-1] if trace["decisions"] else None
    plain, runtime_errors = [], 0
    for r in latest["rule_results"] if latest else []:
        rule = get(f"/rules/{r['rule_id']}/trace")
        runtime_errors += rule["runtime"]["errors"]
        runs = [n for c in rule["compilations"] for _, n in walk([c]) if n["step"] == "llm_run"]
        if not runs:
            plain.append(r["rule_id"])
            continue
        retries = sum((n["data"] or {}).get("retries", 0) for n in runs)
        failed = sum(len((n["data"] or {}).get("failed_attempts") or []) for n in runs)
        bad = sum(n["status"] == "error" for n in runs)
        models = ", ".join(sorted({(n["data"] or {}).get("model") or "?" for n in runs}))
        print(
            f"   rule {r['rule_id']}: {len(rule['compilations'])} compilation(s), {len(runs)} LLM "
            f"runs, {retries} retries, {failed} provider fallbacks, {bad} failed ({models})"
        )
    if plain:
        print(f"   rules {plain}: no LLM compilation (hand-written or loaded from a pack)")
    if latest:
        print(f"   rule runtime errors across their runs: {runtime_errors}")
    if latest:  # the source syncs the decision read: the latest one of each source before it
        syncs = get(f"/traces?process_id={pid}&name=sync_source&limit=50")
        seen = set()
        for s in syncs:
            d = s["data"] or {}
            if s["started_at"] > latest["created_at"] or d.get("source") in seen:
                continue
            seen.add(d.get("source"))
            print(
                f"   {d.get('source')} sync {s['started_at'][:19]} ({s['status']}): "
                f"{d.get('requests')} requests, {d.get('retries')} retries, "
                f"{d.get('timeouts')} timeouts, {ms(s['duration_ms'])}"
            )
    m = get(f"/processes/{pid}/metrics")
    for llm in m["llm"]:
        print(
            f"   process LLM {llm['role']} on {llm['model']}: {llm['calls']} calls, "
            f"{llm['retries']} retries, {llm['fallbacks']} fallbacks, {llm['errors']} errors"
        )
    if not errors:
        print("   no error span on this instance")

    print("\n-- Pending work")
    escalated = latest and latest["decision"] == "ESCALAR" and latest["author"] == "engine"
    if trace["status"] == "PENDING":
        print("   not decided yet: waiting for a process run")
    elif escalated:
        print(f"   ESCALATED, waiting for a person: {latest['reason']}")
        print(f"   resolve: POST /instances/{trace['id']}/resolve (manager)")
    else:
        print(f"   not escalated (latest decision by {latest['author']})")
    alerts = [a for a in get(f"/processes/{pid}/alerts") if a["instance_id"] == trace["id"]]
    for a in alerts:
        t, e = a["trigger"], a["evidence"]
        cause = ", ".join(s["name"] for s in t.get("sources", [])) or f"version v{t.get('version')}"
        print(
            f"   alert {a['id']} [{a['status']}] {a['created_at'][:19]}: "
            f"decision #{a['decision_id']} {a['before']} -> {a['after']} "
            f"after {t['kind']} ({cause}); reason was "
            f"{e['before'].get('reason')!r}, would be {e['after'].get('reason') or 'default'!r}"
        )
        for row in t.get("rows", {}).get("after", []):
            before = next(
                (
                    b
                    for b in t["rows"].get("before", [])
                    if b.get("entry_id") == row.get("entry_id")
                ),
                {},
            )
            diff = {k: f"{before.get(k)} -> {v}" for k, v in row.items() if before.get(k) != v}
            print(f"      row {row.get('entry_id', '')}: {diff}")
    if not alerts:
        print("   no stale-decision alert on this instance (ADR 0026)")
    execution = get(f"/processes/{pid}/metrics/execution")
    print(
        f"   process: {m['escalated']} escalated, {m['pending']} pending, "
        f"{execution.get('open_alerts', 0)} open alerts; decisions {m['decisions_by_outcome']}"
    )
    health = ", ".join(
        f"{h['plane']} {h['status']}" + (f" ({h['reason']})" if h["reason"] else "")
        for h in get("/health/planes")
    )
    print(f"   planes now: {health}")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as e:
        sys.exit(f"API {e.url}: HTTP {e.code}: {e.read()[:300]!r}")
    except urllib.error.URLError as e:
        sys.exit(f"API not reachable ({e.reason}); start it with `make setup` or pass --api-url")
