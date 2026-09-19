"""Compare a corpus against a frozen extraction and a separate visual review.

python -m evals.ocr_regression --baseline reports/ocr-advanced-20260919 \
    --candidate reports/ocr-improved-20260919

The candidate directory must contain extractions.jsonl. The baseline contains
extractions.jsonl, decisions.jsonl, sources.json and evaluation.jsonl. No reader
receives the review, and the evaluation never repairs the extracted symbols.
"""

import argparse
import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

from app.features.agents.sandbox import run_dataset
from app.features.decisions.engine import Outcomes, decide
from app.features.rules.model import Rule
from tests.golden import build_golden as reference

MAPPING = {
    "issuer_nif": "supplier_tax_id",
    "iban": "payment_iban",
    "invoice_number": "invoice_number",
    "date": "issued_on",
    "purchase_order": "purchase_order_ref",
    "base": "net_amount",
    "vat_rate": "vat_rate",
    "vat_amount": "vat_amount",
    "total": "gross_amount",
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def jsonl(path, values):
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in values), encoding="utf-8"
    )


def equal(name, a, b):
    if a is None or b is None:
        return a == b
    if name in {"base", "vat_rate", "vat_amount", "total"}:
        return Decimal(str(a)) == Decimal(str(b))
    return str(a).replace(" ", "") == str(b).replace(" ", "")


def symbols(result):
    fields = result["fields"]
    row = {k: fields[v]["value"] for k, v in MAPPING.items()}
    row.update(file_id=result["file_id"], _instance=result["file_id"])
    if row["date"] is None:
        # Retain impossible printed dates for the invalid-date business rule.
        match = re.fullmatch(
            r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})",
            (fields["issued_on"].get("text") or "").strip(),
        )
        if match:
            d, m, y = map(int, match.groups())
            row["date"] = f"{y:04d}-{m:02d}-{d:02d}"
    return row


def evaluate(dataset, sources):
    root = Path(__file__).resolve().parents[2] / "processes"
    definition = read(root / "invoice-payment.json")
    rules = []
    for i, spec in enumerate(definition["rules"], 1):
        code = (root / spec["code"]).read_text(encoding="utf-8")
        rules.append(
            Rule(
                id=i,
                text=spec["text"],
                decision=spec["decision"],
                type=spec["type"],
                code=code,
                hash=hashlib.sha256(code.encode()).hexdigest(),
            )
        )
    priorities = {r["name"]: r["priority"] for r in definition["decision_types"]}
    default = next(r["name"] for r in definition["decision_types"] if r.get("is_default"))
    numbered = list(enumerate(dataset, 1))
    escalate = max(
        (r for r in definition["decision_types"] if r.get("requires_human")),
        key=lambda r: r["priority"],
    )["name"]
    return decide(
        rules, Outcomes(priorities, default, escalate), numbered, sources, numbered, run_dataset
    )


def compare(baseline, candidate):
    old = {r["file_id"]: r for r in rows(baseline / "extractions.jsonl")}
    new = {r["file_id"]: r for r in rows(candidate / "extractions.jsonl")}
    assert old.keys() == new.keys(), "Corpus membership changed"
    assert all(old[k]["sha256"] == new[k]["sha256"] for k in old), "Source hash changed"
    reviews = {r["file_id"]: r for r in rows(baseline / "evaluation.jsonl")}
    previous = {r["file_id"]: r for r in rows(baseline / "decisions.jsonl")}
    sources = read(baseline / "sources.json")
    dataset = [symbols(r) for r in new.values() if r["kind"] == "invoice"]
    verdicts = evaluate(dataset, sources)
    replay = evaluate(dataset, sources)
    assert [asdict(v) for v in verdicts] == [asdict(v) for v in replay]
    orders = Counter(reference.key(r["purchase_order"]) for r in dataset if r["purchase_order"])
    comparisons, decisions = [], []
    for row, verdict in zip(dataset, verdicts, strict=True):
        name = row["file_id"]
        found = reference.findings(row, sources)
        if row["purchase_order"] and orders[reference.key(row["purchase_order"])] > 1:
            found.append("DUPLICATE_PO: " + row["purchase_order"])
        independent = max(
            (reference.OUTCOME[f.split(":")[0]] for f in found),
            key=reference.RANK.__getitem__,
            default="PAGAR",
        )
        assert verdict.decision == independent, (name, verdict.decision, independent)
        before = previous[name]
        reviewed = reviews[name]
        differences = {
            k: {
                "before": before["symbols"][k],
                "after": row[k],
                "visual_reference": reviewed["reviewed_symbols"][k],
            }
            for k in MAPPING
            if not equal(k, before["symbols"][k], row[k])
        }
        comparisons.append(
            {
                "file_id": name,
                "before": before["result"],
                "after": verdict.decision,
                "assessment_before": reviewed["assessment"],
                "visual_recommendation": reviewed["recommended_result"],
                "field_changes": differences,
                "findings": found,
                "visual_evidence": reviewed["visual_evidence"],
                "sha256": new[name]["sha256"],
            }
        )
        decisions.append(
            {
                "file_id": name,
                "result": verdict.decision,
                "symbols": row,
                "rules_hash": verdict.rules_hash,
                "all_rules": [asdict(v) for v in verdict.results],
            }
        )
    native = [c for c in comparisons if not new[c["file_id"]]["metrics"]["ocr_calls"]]
    workbooks = [name for name in new if new[name]["kind"] == "workbook"]
    workbook_equal = all(
        {k: v for k, v in old[name]["data"].items() if k != "provenance"}
        == {k: v for k, v in new[name]["data"].items() if k != "provenance"}
        for name in workbooks
    )
    regressions = [
        c
        for c in comparisons
        if c["assessment_before"] in {"CORRECTO", "ESCALADO_CORRECTO"} and c["before"] != c["after"]
    ]
    coverage_losses, wrong_before, wrong_after = [], [], []
    for row in dataset:
        name = row["file_id"]
        for field in MAPPING:
            truth = reviews[name]["reviewed_symbols"][field]
            if truth is None:
                continue  # Uncertain visual references cannot score OCR accuracy.
            before, after = previous[name]["symbols"][field], row[field]
            detail = {
                "file_id": name,
                "field": field,
                "before": before,
                "after": after,
                "visual_reference": truth,
            }
            if before is not None and not equal(field, before, truth):
                wrong_before.append(detail)
            if after is not None and not equal(field, after, truth):
                wrong_after.append(detail)
            if before is not None and equal(field, before, truth) and after is None:
                coverage_losses.append(detail)
    summary = {
        "files": len(dataset),
        "source_hashes_match": len(new),
        "before": dict(Counter(c["before"] for c in comparisons)),
        "after": dict(Counter(c["after"] for c in comparisons)),
        "decision_changes": [c for c in comparisons if c["before"] != c["after"]],
        "previously_validated_decision_regressions": regressions,
        "field_coverage_losses": coverage_losses,
        "accepted_field_errors_before": wrong_before,
        "accepted_field_errors_after": wrong_after,
        "no_regression_on_all_metrics": not (regressions or wrong_after or coverage_losses),
        "native_documents": len(native),
        "native_field_checks": len(native) * len(MAPPING),
        "native_field_changes": sum(len(c["field_changes"]) for c in native),
        "workbook_data_unchanged": workbook_equal,
        "deterministic_replay_identical": True,
        "independent_rule_matches": len(dataset),
        "remaining_visual_disagreements": [
            c for c in comparisons if c["after"] != c["visual_recommendation"]
        ],
        "baseline_reader_calls": {
            k: sum(r["metrics"].get(k, 0) for r in old.values())
            for k in ("ocr_calls", "vlm_calls", "jev_calls")
        },
        "candidate_reader_calls": {
            k: sum(r["metrics"].get(k, 0) for r in new.values())
            for k in ("ocr_calls", "vlm_calls", "jev_calls")
        },
        "limitations": "Development corpus; assistant visual reference, not official ground truth. "
        "Provider journal freezes previously recorded calls. Counts include replayed calls; "
        "elapsed time cannot establish a speed improvement. "
        "Rules execute through the current dev engine; "
        "independent comparison uses the separate golden evaluator.",
    }
    jsonl(candidate / "symbols.jsonl", dataset)
    jsonl(candidate / "decisions.jsonl", decisions)
    jsonl(
        candidate / "outcomes.jsonl",
        ({"file_id": r["file_id"], "result": r["result"]} for r in decisions),
    )
    jsonl(candidate / "comparison.jsonl", comparisons)
    dump(candidate / "comparison-summary.json", summary)
    print(
        json.dumps(
            {
                k: v
                for k, v in summary.items()
                if k
                not in {
                    "decision_changes",
                    "remaining_visual_disagreements",
                    "previously_validated_decision_regressions",
                }
            },
            ensure_ascii=False,
        )
    )
    print(
        "Changed decisions:",
        [(c["file_id"], c["before"], c["after"]) for c in summary["decision_changes"]],
    )
    print("Regressions:", [(c["file_id"], c["field_changes"]) for c in regressions])
    assert not regressions and not wrong_after and workbook_equal, (
        "Decision/accepted-value regression; inspect comparison-summary.json"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    compare(args.baseline, args.candidate)
