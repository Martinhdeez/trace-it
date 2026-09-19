"""Publish an extraction-only migration without replacing historical versions or drafts."""

from copy import deepcopy

MODEL = "helmcode:qwen3.6"


def switch_reader(request, process_id):
    prefix = f"/processes/{process_id}"
    current = request(prefix + "/execution")
    settings = current["settings"]
    if settings["extraction"]["vision_model"] == MODEL and current["revision"] is None:
        print(f"Published reader already {MODEL}")
        return
    if current["revision"] is not None:
        raise SystemExit(
            "An unpublished draft exists; preserve it and migrate the reader in the UI"
        )
    if current["version_id"] is None:
        raise SystemExit(
            "Publish the initial process explicitly before migrating its reader"
        )
    if not (settings["extraction"]["vision_model"] or "").startswith("gemini:"):
        raise SystemExit("The current reader is not Gemini; inspect before changing it")
    original = request(f"/process-versions/{current['version_id']}")["snapshot"]
    settings = deepcopy(settings)
    settings["preset"] = "custom"
    settings["extraction"]["vision_model"] = MODEL
    draft = request(prefix + "/draft", ["--request", "PUT"], {"execution": settings})
    # Check the server's resulting snapshot, including rules, sources, and agents,
    # before approving a publication. A concurrent edit cannot pass the revision check.
    before, after = deepcopy(original), deepcopy(draft["snapshot"])
    before.pop("execution", None)
    after.pop("execution", None)
    for snapshot in (before, after):
        snapshot["process"].pop("active_version_id", None)
    if before != after or draft["base_version_id"] != current["version_id"]:
        raise SystemExit("Unexpected non-extraction changes; draft retained for review")
    validated = request(prefix + "/draft/validate", ["--request", "POST"])
    if (
        validated["revision"] != draft["revision"]
        or not validated["validation"]["valid"]
    ):
        raise SystemExit("Reader draft changed or failed validation; nothing published")
    published = request(
        prefix + "/draft/publish",
        ["--request", "POST"],
        {
            "revision": validated["revision"],
            "validation_hash": validated["validation"]["hash"],
            "reason": "Retire exhausted Gemini quota; use Helmcode Qwen 3.6 for visual reading",
        },
    )
    if published["snapshot"]["execution"]["extraction"]["vision_model"] != MODEL:
        raise SystemExit("Published reader verification failed")
    print(f"Published process version {published['number']} with {MODEL}")
