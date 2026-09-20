"""A complete cache cannot mix batches, lose PDFs, or outlive its OCR identity."""

import base64
import hashlib
import importlib.util
from copy import deepcopy
from pathlib import Path

import pytest


def module(name, filename):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).with_name(filename)
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


reset = module("reset_full_seed", "reset-demo.py")
cache = module("seed_cache_check", "seed_cache.py")


@pytest.fixture
def seed():
    result = {
        "version": 4,
        "challenge_commit": "a" * 40,
        "examples": [],
        "batches": [],
        "reference_files": [],
        "rule_baselines": [],
    }
    for batch_number, count, erp_count in [(1, 500, 516), (2, 40, 556)]:
        pid = 1
        documents = {}
        if batch_number == 1:
            result["rule_baselines"].append(
                {"process_id": pid, "rules": [{"code": None}], "norm_rules": []}
            )
        for n in range(count):
            content = f"%PDF-1.4 {batch_number} {n}".encode()
            digest = hashlib.sha256(content).hexdigest()
            name = f"{batch_number}_{n}.pdf"
            documents[name] = digest
            result["examples"].append(
                {
                    "process_id": pid,
                    "name": name,
                    "hash": digest,
                    "content": base64.b64encode(content).decode(),
                    "symbols": {"invoice": {"value": n}},
                    "evidence": {"extraction": {}},
                }
            )
        result["batches"].append(
            {
                "number": batch_number,
                "process_id": pid,
                "count": count,
                "erp_count": erp_count,
                "documents": documents,
                "sources": {
                    "erp": [{}] * erp_count,
                    "suppliers": [],
                    "orders": [],
                    "parameters": [],
                },
            }
        )
    return result


def test_complete_challenge(seed):
    reset.validate_seed(seed)


@pytest.mark.parametrize(
    "corruption", ["missing", "duplicate", "erp", "pdf", "name", "process"]
)
def test_reject_corrupt_challenge(seed, corruption):
    if corruption == "missing":
        seed["examples"].pop()
    elif corruption == "duplicate":
        seed["examples"][-1] = deepcopy(seed["examples"][-2])
    elif corruption == "erp":
        seed["batches"][0]["sources"]["erp"] = seed["batches"][1]["sources"]["erp"]
    elif corruption == "pdf":
        seed["examples"][0]["hash"] = "0" * 64
    elif corruption == "name":
        seed["examples"][0]["name"] = "unexpected.pdf"
    else:
        seed["batches"][1]["process_id"] = 2
    with pytest.raises(ValueError):
        reset.validate_seed(seed)


def test_cache_invalidates_code_dependencies_and_settings(tmp_path):
    app = tmp_path / "app"
    for name in [
        "features/ingestion/reader.py",
        "common/prompts.py",
        "features/processes/execution.py",
    ]:
        p = app / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("initial")
    (tmp_path / "uv.lock").write_text("dependencies")
    settings = {"mode": "api", "vision_model": "reader-a"}
    seed = {
        "ocr_cache": {
            "code_hash": cache.fingerprint(app),
            "extraction_settings": {"invoice": settings},
        }
    }
    snapshots = {"invoice": {"execution": {"extraction": settings}}}
    cache.verify(seed, app, snapshots)
    snapshots["invoice"]["execution"]["extraction"] = {
        **settings,
        "vision_model": "reader-b",
    }
    with pytest.raises(ValueError, match="settings changed"):
        cache.verify(seed, app, snapshots)
    snapshots["invoice"]["execution"]["extraction"] = settings
    (app / "features/ingestion/reader.py").write_text("new OCR implementation")
    with pytest.raises(ValueError, match="code/dependencies changed"):
        cache.verify(seed, app, snapshots)
