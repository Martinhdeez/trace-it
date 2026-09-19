"""Content-addressed provider calls with no automatic retry after uncertain delivery."""

import hashlib
import json
import os
import time

from filelock import FileLock


def recorded_call(directory, identity, call):
    directory.mkdir(parents=True, exist_ok=True)
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    path = directory / f"{fingerprint}.json"
    with FileLock(str(path) + ".lock", timeout=60):
        if path.exists():
            record = json.loads(path.read_text(encoding="utf-8"))
            if record["state"] != "complete":
                raise RuntimeError("Provider delivery uncertain; inspect the request journal")
            return record["response"]
        record = {"identity": identity, "state": "started", "started_at": time.time()}
        path.write_text(json.dumps(record), encoding="utf-8")
        started = time.perf_counter()
        try:
            record["response"] = call()
            record["state"] = "complete"
        except Exception as exc:
            record.update(state="uncertain_or_failed", error_type=type(exc).__name__)
            raise
        finally:
            record["seconds"] = round(time.perf_counter() - started, 3)
            temporary = path.with_suffix(".part")
            temporary.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
            os.replace(temporary, path)
        return record["response"]
