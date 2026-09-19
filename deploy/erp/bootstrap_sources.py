"""Load missing batch-one references through the production API; never run decisions."""

import argparse
import json
import subprocess
from datetime import date
from pathlib import Path

from switch_reader import switch_reader

BASE = "https://gex-dashboard.hopto.org/nexia/trace-it/api"


def bootstrap(request, process_id, workbook, cutoff):
    prefix = f"/processes/{process_id}/sources"
    current = {row["name"]: row for row in request(prefix)}
    reference = {"suppliers", "orders", "parameters"}
    present = reference & current.keys()
    if present and present != reference:
        raise SystemExit(
            "Partial reference sources exist; review them before importing a workbook"
        )
    if not present:
        result = request(
            prefix + "/workbook",
            [
                "--form",
                f"file=@{workbook};type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "--form",
                f"cut_off_date={cutoff}",
            ],
        )
        print("Reference sources:", result["sources"])
    else:
        print("Existing reference sources preserved")
    result = request(prefix + "/erp/sync", ["--request", "POST"])
    print(f"ERP: {result['rows']} rows; {result['stats']['retries']} retries")
    loaded = {row["name"]: row for row in request(prefix)}
    if not reference.union({"erp"}) <= loaded.keys() or any(
        loaded[name]["rows"] == 0 or loaded[name].get("status") == "down"
        for name in reference.union({"erp"})
    ):
        raise SystemExit("Source verification failed")
    print("All four sources ready. Existing decisions are unchanged.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--process-id", type=int, required=True)
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--cut-off-date", type=date.fromisoformat, required=True)
    parser.add_argument("--workbook", type=Path, required=True)
    args = parser.parse_args()
    if not args.workbook.is_file() or min(args.user_id, args.process_id) < 1:
        parser.error("An existing workbook and positive IDs are required")

    def request(path, extra=(), body=None):
        payload = (
            ["--header", "Content-Type: application/json", "--data-binary", "@-"]
            if body is not None
            else []
        )
        response = subprocess.run(
            [
                "curl",
                "--config",
                "/opt/trace-it/secrets/curl.conf",
                "--fail-with-body",
                "--silent",
                "--show-error",
                "--max-time",
                "180",
                "--header",
                f"X-User-Id: {args.user_id}",
                *extra,
                *payload,
                BASE + path,
            ],
            input=json.dumps(body) if body is not None else None,
            capture_output=True,
            text=True,
            check=False,
        )
        if response.returncode:
            raise SystemExit(f"API request failed: {path}: {response.stdout[:1000]}")
        return json.loads(response.stdout)

    bootstrap(request, args.process_id, args.workbook.resolve(), args.cut_off_date)
    switch_reader(request, args.process_id)


if __name__ == "__main__":
    main()
