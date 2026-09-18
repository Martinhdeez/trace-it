"""Run explicit text-only Jev probes; never modify extraction results."""

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

from app.features.ingesta.config import REPOSITORY_ROOT
from app.features.ingesta.tools.jev_cases import (
    CASES,
    INPUT_USD_PER_MILLION,
    MODEL,
    request_body,
)

URL = "https://api.typesafe.ai/v1/systemone"


def cached_probe(client, payload, key, output, offline=False):
    identity = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    path = output / f"{identity}.json"
    if path.exists():
        record = json.loads(path.read_text(encoding="utf-8"))
        if record["state"] != "complete":
            raise RuntimeError("Incomplete attempt; inspect its journal before resubmitting")
        return record
    if offline:
        raise FileNotFoundError("No cached response for this request")
    if not key:
        raise ValueError("Set TYPESAFE_API_KEY in the repository .env")
    record = {"request": payload, "state": "started", "started_at": time.time()}
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    started = time.perf_counter()
    try:
        response = client.post(URL, headers={"Authorization": f"Bearer {key}"}, json=payload)
        record["http_status"] = response.status_code
        if response.status_code != 200:
            # Do not persist response bodies which may echo authentication details.
            raise RuntimeError(f"TypeSafe returned HTTP {response.status_code}")
        data = response.json()
        choice = data["answers"]["selection"]
        support = data["answers"]["support"]
        options = payload["questions"]["selection"]["criteria"]
        if (
            choice["type"] != "choice"
            or choice["choice"] not in options
            or set(choice["probabilities"]) != set(options)
            or not all(0 <= p <= 1 for p in choice["probabilities"].values())
            or abs(sum(choice["probabilities"].values()) - 1) > 0.01
            or not 0 <= choice["confidence"] <= 1
            or support["type"] != "noul"
            or not 0 <= support["noul"] <= 1
        ):
            raise ValueError("Invalid typed answers")
        record.update(state="complete", response=data)
    except Exception as error:
        record.update(state="uncertain_or_failed", error_type=type(error).__name__)
        raise
    finally:
        record["seconds"] = round(time.perf_counter() - started, 3)
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    load_dotenv(REPOSITORY_ROOT / ".env")
    results = []
    with httpx.Client(timeout=60, follow_redirects=False) as client:
        for case in CASES:
            record = cached_probe(
                client,
                request_body(case, args.model),
                os.getenv("TYPESAFE_API_KEY"),
                args.output,
                args.offline,
            )
            answer = record["response"]
            choice = answer["answers"]["selection"]["choice"]
            results.append(
                {
                    **case,
                    "answers": answer["answers"],
                    "model": answer["model"],
                    "usage": answer["usage"],
                    "seconds": record["seconds"],
                    "selection_matches": choice == (case["expected_choice"] or "none"),
                }
            )
    summary = {
        "scope": "Six development probes; textual support, not visual correctness",
        "results": results,
        "selection_matches": sum(r["selection_matches"] for r in results),
        "estimated_usd": sum(r["usage"]["input_tokens"] for r in results)
        * INPUT_USD_PER_MILLION
        / 1_000_000,
        "price_basis": f"USD {INPUT_USD_PER_MILLION}/million input tokens; billing unverified",
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
