"""Build the audit page of a decided process: one HTML file, no server. See README.md.

    uv run --project backend python tools/audit_page/build.py --output output/audit.html

Reads the running API (`make setup`), so it shows what the application actually decided:
per instance the decision, its reason, every rule with its verdict, the symbols and the
source rows the rules compared against. The original PDFs are embedded from the corpus.
"""

import argparse
import base64
import json
import re
import sys
import unicodedata
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = Path(__file__).resolve().parent
CHALLENGE = ROOT / ".context/500-sombras-de-alberto"
GOLDEN = ROOT / "backend/tests/golden/batch1_expected.jsonl"


def key_of(name: str) -> str:
    """The element id a file name gets in the page."""
    return re.sub(r"[^A-Za-z0-9]+", "_", name)


def norm(value: object) -> str:
    """Compare keys the way the rules do: no spaces, dots or hyphens, uppercase."""
    return re.sub(r"[\s.\-]", "", str(value or "")).upper()


def read_jsonl(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    rows = (json.loads(line) for line in path.read_text().splitlines() if line.strip())
    return {row["file_id"]: row for row in rows}


def collect(api: httpx.Client, process_id: int, outcomes: dict[str, dict]) -> dict:
    """Everything the page shows, straight from the API."""
    rules = {r["id"]: r for r in api.get(f"/processes/{process_id}/rules").json()}
    sources = {
        s["name"]: api.get(f"/processes/{process_id}/sources/{s['name']}").json()["data"]
        for s in api.get(f"/processes/{process_id}/sources").json()
    }
    by_nif: dict[str, list[dict]] = {}
    for row in sources.get("suppliers", []):
        by_nif.setdefault(norm(row.get("nif")), []).append(row)
    orders = {norm(r.get("purchase_order")): r for r in sources.get("orders", [])}
    erp = {norm(r.get("purchase_order")): r for r in sources.get("erp", [])}
    golden = read_jsonl(GOLDEN)

    records = []
    listing = api.get(f"/processes/{process_id}/instances").json()
    for n, row in enumerate(listing, 1):
        instance = api.get(f"/instances/{row['id']}").json()
        decision = (instance.get("decisions") or [{}])[-1]
        symbols = {k: (v or {}).get("value") for k, v in (instance.get("symbols") or {}).items()}
        expected = golden.get(row["name"], {})
        records.append(
            {
                "file_id": row["name"],
                # The delivered result, when a delivery file was given: shown beside ours.
                "delivered": (outcomes.get(row["name"], {}) or {}).get("result", row["decision"]),
                "local": row["decision"],
                "reason": row["reason"] or "NO_FINDING",
                "rules": [
                    {
                        "rule_id": r["rule_id"],
                        "fires": r.get("fires"),
                        "reason": r.get("reason") or "",
                        "text": rules.get(r["rule_id"], {}).get("text", ""),
                        "decision": rules.get(r["rule_id"], {}).get("decision", ""),
                        "type": rules.get(r["rule_id"], {}).get("type", ""),
                    }
                    for r in decision.get("results", [])
                ],
                "expected": expected.get("expected"),
                "confidence": expected.get("confidence"),
                "why": expected.get("why"),
                "symbols": {k: v for k, v in symbols.items() if k != "free_text"},
                "text": symbols.get("free_text") or "",
                # No reference outcome means an image-only scan: nothing cross-checks it.
                "is_scan": row["name"] in golden and expected.get("expected") is None,
                "sources": {
                    "suppliers": by_nif.get(norm(symbols.get("issuer_nif")), []),
                    "order": orders.get(norm(symbols.get("purchase_order"))),
                    "erp": erp.get(norm(symbols.get("purchase_order"))),
                    "parameters": sources.get("parameters", []),
                },
            }
        )
        if n % 100 == 0:
            print(f"  read {n}/{len(listing)}", flush=True)

    records.sort(key=lambda r: r["file_id"])
    return {"records": records, "rules": list(rules.values())}


def pdf_blocks(records: list[dict], invoices: Path) -> str:
    """Each original PDF as its own base64 block, decoded only when it is opened."""
    blocks, missing = [], []
    names = {unicodedata.normalize("NFC", p.name): p for p in invoices.glob("*.pdf")}
    for record in records:
        path = names.get(unicodedata.normalize("NFC", record["file_id"]))
        if path is None:
            missing.append(record["file_id"])
            continue
        data = base64.b64encode(path.read_bytes()).decode()
        tag = f'<script id="pdf-{key_of(record["file_id"])}" type="text/plain-base64">'
        blocks.append(f"{tag}{data}</script>")
    if missing:
        print(f"WARNING: no PDF for {len(missing)} instances, e.g. {missing[:3]}", file=sys.stderr)
    return "\n".join(blocks)


def build(payload: dict, invoices: Path, output: Path) -> None:
    template = (HERE / "template.html").read_text()
    # A JSON payload in a <script> may not carry "</"; only strings can contain it.
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    pdfs = pdf_blocks(payload["records"], invoices)
    page = template.replace("__DATA__", data).replace("__PDFS__", pdfs)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page)
    size = output.stat().st_size / 1e6
    print(f"{output}: {len(payload['records'])} instances, {size:.1f} MB")
    if size > 16:
        print("WARNING: over the 16 MB an Artifact accepts", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--process", type=int, default=1)
    parser.add_argument("--user", default="1", help="X-User-Id of a manager")
    parser.add_argument("--invoices", type=Path, default=CHALLENGE / "facturas")
    parser.add_argument("--outcomes", type=Path, help="a delivered outcomes.jsonl to compare")
    parser.add_argument("--output", type=Path, default=ROOT / "output/audit.html")
    args = parser.parse_args()

    if not args.invoices.is_dir():
        parser.error(f"No such folder of PDFs: {args.invoices}")
    outcomes = read_jsonl(args.outcomes) if args.outcomes else {}
    with httpx.Client(base_url=args.api, headers={"X-User-Id": args.user}, timeout=120) as api:
        payload = collect(api, args.process, outcomes)
    build(payload, args.invoices, args.output)


if __name__ == "__main__":
    main()
