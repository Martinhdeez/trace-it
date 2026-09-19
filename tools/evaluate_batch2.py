"""Compare captured readers and real sandbox decisions with fixed reference snapshots."""

import argparse
import dataclasses
import json
import sys
from collections import Counter
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "backend"))
    from app.features.agents import sandbox
    from app.features.decisions.engine import decide
    from app.features.ingestion.symbols import flatten_symbols, scan, unverified
    from app.features.rules.model import Rule
    from app.features.rules.service import rule_hash
    from tests.support import pack

    args.output.mkdir(parents=True, exist_ok=True)
    captures = {
        stage: {
            str(p.relative_to(folder)): read(p)
            for batch in ("facturas", "facturas_primin")
            for p in (folder / batch).glob("*.json")
        }
        for stage, folder in (("before", args.before), ("after", args.after))
    }
    assert len(captures["before"]) == len(captures["after"]) == 540
    assert captures["before"].keys() == captures["after"].keys()
    assert (
        read(args.before / "summary.json")["manifest"]
        == read(args.after / "summary.json")["manifest"]
    )
    summary = {"counts": {}, "changes": {}, "fields": {}}
    outputs = {}

    def patient(code, dataset, sources, population):
        return sandbox.run_dataset(code, dataset, sources, population, timeout_s=120)

    for stage, repo in (("before", args.baseline_root), ("after", root)):
        definition = read(repo / "processes/invoice-payment.json")
        rules = [
            Rule(
                id=i,
                text=r["text"],
                type=r["type"],
                decision=r["decision"],
                code=(code := (repo / "processes" / r["code"]).read_text(encoding="utf-8")),
                hash=rule_hash(r["text"], code),
            )
            for i, r in enumerate(definition["rules"], 1)
        ]
        for scenario in ("original", "source_update", "updated"):
            records = {
                k: v
                for k, v in captures[stage].items()
                if scenario == "updated" or k.startswith("facturas\\") or k.startswith("facturas/")
            }
            dataset = [(k, flatten_symbols(v["symbols"])) for k, v in sorted(records.items())]
            population = [(k, {**s, "_instance": records[k]["file_id"]}) for k, s in dataset]
            source_name = "original" if scenario == "original" else "updated"
            sources = read(args.sources / f"sources-{source_name}.json")
            verdicts = decide(
                rules,
                pack.outcomes(definition),
                dataset,
                sources,
                population,
                patient,
                scans={k: u for k, v in records.items() if (u := scan(v["symbols"])) is not None},
                unverified={k: unverified(v["symbols"]) for k, v in records.items()},
            )
            result = {
                key: dataclasses.asdict(v) for (key, _), v in zip(dataset, verdicts, strict=True)
            }
            outputs[stage, scenario] = result
            summary["counts"][f"{stage}_{scenario}"] = dict(
                Counter(v["decision"] for v in result.values())
            )
            (args.output / f"{stage}-{scenario}.json").write_text(
                json.dumps(result, indent=2), encoding="utf-8"
            )
    for scenario in ("original", "source_update", "updated"):
        before, after = outputs["before", scenario], outputs["after", scenario]
        summary["changes"][scenario] = [
            {
                "file": k,
                "before": v["decision"],
                "after": after[k]["decision"],
                "reason": after[k]["reason"],
            }
            for k, v in before.items()
            if v["decision"] != after[k]["decision"]
        ]
    for fixture, batch in (
        ("scans-reviewed.json", "facturas"),
        ("batch2-reviewed-fields.json", "facturas_primin"),
    ):
        reference = read(root / "backend/app/features/ingestion/tests/fixtures" / fixture)
        for stage in captures:
            count = Counter()
            wrong = []
            for case in reference:
                actual = captures[stage][str(Path(batch) / (case["file_id"] + ".json"))]
                for field, expected in case["fields"].items():
                    reading = actual["fields"][field]
                    value = reading["value"]
                    count["total"] += 1
                    count["correct"] += value == expected
                    count["verified_correct"] += (
                        value == expected and reading["verification"] == "verified"
                    )
                    count["missing"] += value is None
                    if value is not None and value != expected:
                        count["wrong"] += 1
                        wrong.append(
                            {
                                "file": case["file_id"],
                                "field": field,
                                "expected": expected,
                                "value": value,
                                "verification": reading["verification"],
                            }
                        )
            summary["fields"][f"{stage}_{batch}"] = {**count, "errors": wrong}
    golden = {
        r["file_id"]: r["expected"]
        for r in (
            json.loads(line)
            for line in (root / "backend/tests/golden/batch1_expected.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        )
        if r["expected"] is not None
    }
    summary["golden_mismatches"] = [
        {
            "file": name,
            "expected": expected,
            "actual": outputs["after", "original"][str(Path("facturas") / (name + ".json"))][
                "decision"
            ],
        }
        for name, expected in golden.items()
        if outputs["after", "original"][str(Path("facturas") / (name + ".json"))]["decision"]
        != expected
    ]
    summary["source_only_changes"] = [
        {
            "file": k,
            "before": v["decision"],
            "after": outputs["after", "source_update"][k]["decision"],
            "reason": outputs["after", "source_update"][k]["reason"],
        }
        for k, v in outputs["after", "original"].items()
        if v["decision"] != outputs["after", "source_update"][k]["decision"]
    ]
    summary["gates"] = {
        "original_labels_unchanged": not summary["changes"]["original"],
        "original_reasons_unchanged": all(
            v["reason"] == outputs["before", "original"][k]["reason"]
            for k, v in outputs["after", "original"].items()
        ),
        "original_golden_matches": not summary["golden_mismatches"],
        "international_fields_all_correct": summary["fields"]["after_facturas_primin"][
            "verified_correct"
        ]
        == 135,
        "no_verified_field_errors": not any(
            e["verification"] == "verified"
            for batch in ("facturas", "facturas_primin")
            for e in summary["fields"][f"after_{batch}"]["errors"]
        ),
        "scan_correct_fields_preserved": summary["fields"]["after_facturas"]["correct"]
        >= summary["fields"]["before_facturas"]["correct"],
        "scan_verified_fields_preserved": summary["fields"]["after_facturas"]["verified_correct"]
        >= summary["fields"]["before_facturas"]["verified_correct"],
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if not all(summary["gates"].values()):
        raise SystemExit("One or more comparison gates failed; inspect summary.json")


if __name__ == "__main__":
    main()
