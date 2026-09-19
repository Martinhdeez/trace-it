"""The demo driver must use the same HTTP ingestion path as production."""

import hashlib
import json
import runpy
from pathlib import Path

import httpx
import pytest

DEMO = runpy.run_path(str(Path(__file__).resolve().parents[5] / "tools/demo_run.py"))


async def test_authenticate_discovers_invoice_process_and_sends_user_header():
    paths = []

    def respond(request):
        paths.append(request.url.path)
        if request.url.path == "/login":
            assert request.read() == b'{"email":"operator@test.invalid"}'
            return httpx.Response(200, json={"id": 42})
        assert request.url.path == "/processes"
        assert request.headers["X-User-Id"] == "42"
        return httpx.Response(
            200,
            json=[
                {"id": 1, "name": "Other process"},
                {"id": 73, "name": "Invoice payment"},
            ],
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(respond), base_url="http://demo"
    ) as api:
        process_id = await DEMO["authenticate"](api, "operator@test.invalid", None)
        assert api.headers["X-User-Id"] == "42"
    assert process_id == 73
    assert paths == ["/login", "/processes"]


@pytest.mark.parametrize("local_only", [False, True])
@pytest.mark.parametrize("reviewed", [False, True])
async def test_demo_loads_sources_then_ocr_uploads_and_exports_result(
    tmp_path, local_only, reviewed
):
    book = tmp_path / "master.xlsx"
    invoice = tmp_path / "scan.pdf"
    book.write_bytes(b"xlsx content")
    invoice.write_bytes(b"%PDF-scan content")
    calls = []

    def respond(request):
        calls.append((request.method, request.url.path, request))
        if request.url.path == "/processes/7/sources/workbook":
            assert b"xlsx content" in request.read()
            assert b"cut_off_date" in request.content
            assert b"2026-09-19" in request.content
            return httpx.Response(201, json={"sources": []})
        if request.url.path == "/processes/7/sources/erp/sync":
            return httpx.Response(200, json={"rows": 1})
        if request.url.path == "/processes/7/instances":
            if not any(path == "/processes/7/files" for _, path, _ in calls):
                return httpx.Response(200, json=[])
            return httpx.Response(200, json=[{"id": 11, "name": invoice.name}])
        if request.url.path == "/processes/7/files":
            content = request.read()
            assert b"%PDF-scan content" in content
            assert b'name="ocr"' in content and b"true" in content
            assert (b'name="vlm"' in content) is local_only
            assert (b'name="jev"' in content) is local_only
            return httpx.Response(
                201,
                json={
                    "instance_id": 11,
                    "name": invoice.name,
                    "created": True,
                    "status": "PENDING",
                    "extraction": {"metrics": {"ocr_calls": 2}},
                    "symbols": {"total": {"value": "1802.90"}},
                },
            )
        if request.url.path == "/processes/7/run":
            return httpx.Response(200, json={"decided": 1})
        if request.url.path == "/processes/7/export":
            decision = "ESCALAR" if reviewed else "PAGAR"
            return httpx.Response(200, text=json.dumps({"file_id": "scan.pdf", "result": decision}))
        if request.url.path == "/instances/11":
            return httpx.Response(
                200,
                json={
                    "symbols": {"total": {"value": "1802.90"}},
                    "decisions": [
                        {
                            "id": 1,
                            "decision": "PAGAR",
                            "author": "engine",
                            "results": [{"fires": True, "reason": "Matched order"}],
                        },
                        {
                            "id": 2,
                            "decision": "ESCALAR",
                            "author": "human",
                            "results": [],
                        },
                    ],
                    "reviews": [{"decision_id": 1}] if reviewed else [],
                },
            )
        raise AssertionError(request.url.path)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(respond), base_url="http://demo"
    ) as api:
        await DEMO["run"](
            api, 7, [invoice], book, "2026-09-19", tmp_path / "out", local_only=local_only
        )

    assert [(method, path) for method, path, _ in calls] == [
        ("POST", "/processes/7/sources/workbook"),
        ("POST", "/processes/7/sources/erp/sync"),
        ("GET", "/processes/7/instances"),
        ("POST", "/processes/7/files"),
        ("POST", "/processes/7/run"),
        ("GET", "/processes/7/export"),
        ("GET", "/processes/7/instances"),
        ("GET", "/instances/11"),
    ]
    output = tmp_path / "out"
    assert (
        json.loads((output / "extractions.jsonl").read_text())["extraction"]["metrics"]["ocr_calls"]
        == 2
    )
    assert json.loads((output / "outcomes.jsonl").read_text()) == {
        "file_id": invoice.name,
        "result": "ESCALAR" if reviewed else "PAGAR",
    }
    detail = json.loads((output / "detail.json").read_text())[0]
    assert detail["rules_that_fired"] == ([] if reviewed else ["Matched order"])
    assert detail["decision_author"] == ("human" if reviewed else "engine")
    assert detail["engine_rules_that_fired"] == ["Matched order"]


async def test_demo_reextracts_pending_reupload_but_preserves_decided_instance(tmp_path):
    book = tmp_path / "master.xlsx"
    pending = tmp_path / "pending.pdf"
    decided = tmp_path / "decided.pdf"
    for path in (book, pending, decided):
        path.write_bytes(b"content")
    paths = []

    def respond(request):
        paths.append(request.url.path)
        path = request.url.path
        if path.endswith("/sources/workbook"):
            return httpx.Response(201, json={})
        if path.endswith("/sources/erp/sync"):
            return httpx.Response(200, json={"rows": 1})
        if path.endswith("/instances"):
            return httpx.Response(
                200,
                json=[{"id": 11, "name": "pending.pdf"}, {"id": 12, "name": "decided.pdf"}],
            )
        if path.endswith("/files"):
            raise AssertionError("Matching instances must not be uploaded again")
        if path == "/instances/11/extract":
            assert request.read() == b'{"ocr":true,"vlm":false,"jev":false}'
            return httpx.Response(
                200,
                json={
                    "instance_id": 11,
                    "name": "pending.pdf",
                    "created": False,
                    "status": "PENDING",
                    "extraction": {"id": "new", "metrics": {"ocr_calls": 2}},
                },
            )
        if path.endswith("/run"):
            return httpx.Response(200, json={"decided": 1})
        if path.endswith("/export"):
            return httpx.Response(
                200,
                text='{"file_id":"pending.pdf","result":"PAGAR"}\n'
                '{"file_id":"decided.pdf","result":"ESCALAR"}\n',
            )
        if path.startswith("/instances/"):
            return httpx.Response(
                200,
                json={
                    "id": int(path.rsplit("/", 1)[1]),
                    "file_hash": hashlib.sha256(b"content").hexdigest(),
                    "status": "PENDING" if path.endswith("/11") else "DECIDED",
                    "symbols": {},
                    "decisions": [
                        {
                            "id": 1,
                            "decision": "PAGAR" if path.endswith("/11") else "ESCALAR",
                            "author": "engine",
                            "results": [],
                        }
                    ],
                },
            )
        raise AssertionError(path)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(respond), base_url="http://demo"
    ) as api:
        await DEMO["run"](
            api, 7, [pending, decided], book, "2026-09-19", tmp_path / "out", local_only=True
        )
    assert paths.count("/instances/11/extract") == 1
    assert "/instances/12/extract" not in paths
    assert "/processes/7/files" not in paths
    evidence = [
        json.loads(line) for line in (tmp_path / "out/extractions.jsonl").read_text().splitlines()
    ]
    assert evidence[0]["extraction"]["id"] == "new"
    assert evidence[1]["reused"] is True
    assert "extraction" not in evidence[1]


async def test_failed_upload_stops_before_rules_or_export(tmp_path):
    book = tmp_path / "master.xlsx"
    invoice = tmp_path / "scan.pdf"
    book.write_bytes(b"content")
    invoice.write_bytes(b"content")
    output = tmp_path / "out"
    output.mkdir()
    prior = {
        "extractions.jsonl": b"old extraction evidence\n",
        "outcomes.jsonl": b"old outcomes\n",
        "detail.json": b"old detail\n",
    }
    for name, content in prior.items():
        (output / name).write_bytes(content)
    paths = []

    def respond(request):
        paths.append(request.url.path)
        if request.url.path.endswith("/sources/workbook"):
            return httpx.Response(201, json={})
        if request.url.path.endswith("/sources/erp/sync"):
            return httpx.Response(200, json={"rows": 1})
        if request.url.path.endswith("/instances"):
            return httpx.Response(200, json=[])
        return httpx.Response(422, json={"detail": "invalid PDF"})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(respond), base_url="http://demo"
    ) as api:
        with pytest.raises(httpx.HTTPStatusError):
            await DEMO["run"](api, 7, [invoice], book, "2026-09-19", output)
    assert paths == [
        "/processes/7/sources/workbook",
        "/processes/7/sources/erp/sync",
        "/processes/7/instances",
        "/processes/7/files",
    ]
    assert {name: (output / name).read_bytes() for name in prior} == prior


async def test_historical_same_name_hash_cannot_override_newest_instance(tmp_path):
    book = tmp_path / "master.xlsx"
    invoice = tmp_path / "invoice.pdf"
    book.write_bytes(b"content")
    invoice.write_bytes(b"%PDF-old version")
    old_hash = hashlib.sha256(invoice.read_bytes()).hexdigest()
    paths = []

    def respond(request):
        path = request.url.path
        paths.append(path)
        if path.endswith("/sources/workbook"):
            return httpx.Response(201, json={})
        if path.endswith("/sources/erp/sync"):
            return httpx.Response(200, json={"rows": 1})
        if path.endswith("/instances"):
            return httpx.Response(
                200,
                json=[{"id": 10, "name": invoice.name}, {"id": 20, "name": invoice.name}],
            )
        if path in {"/instances/10", "/instances/20"}:
            instance_id = int(path.rsplit("/", 1)[1])
            return httpx.Response(
                200,
                json={
                    "id": instance_id,
                    "file_hash": old_hash if instance_id == 10 else "newer-file-hash",
                    "status": "DECIDED",
                    "symbols": {},
                },
            )
        raise AssertionError(f"Unexpected mutation after historical match: {path}")

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(respond), base_url="http://demo"
    ) as api:
        with pytest.raises(ValueError, match=r"(?i)historical|newer"):
            await DEMO["run"](api, 7, [invoice], book, "2026-09-19", tmp_path / "out")
    assert "/processes/7/run" not in paths
    assert "/processes/7/export" not in paths
    assert "/processes/7/files" not in paths


async def test_reviewed_human_resolution_supplies_detail_for_exported_outcome(tmp_path):
    book = tmp_path / "master.xlsx"
    invoice = tmp_path / "invoice.pdf"
    book.write_bytes(b"content")
    invoice.write_bytes(b"%PDF-existing")
    file_hash = hashlib.sha256(invoice.read_bytes()).hexdigest()

    def respond(request):
        path = request.url.path
        if path.endswith("/sources/workbook"):
            return httpx.Response(201, json={})
        if path.endswith("/sources/erp/sync"):
            return httpx.Response(200, json={"rows": 1})
        if path.endswith("/instances"):
            return httpx.Response(200, json=[{"id": 15, "name": invoice.name}])
        if path == "/instances/15":
            return httpx.Response(
                200,
                json={
                    "id": 15,
                    "file_hash": file_hash,
                    "status": "DECIDED",
                    "symbols": {},
                    "decisions": [
                        {
                            "id": 100,
                            "decision": "PAGAR",
                            "author": "engine",
                            "results": [{"fires": True, "reason": "Order matched"}],
                        },
                        {
                            "id": 101,
                            "decision": "NO_PAGAR",
                            "author": "operator",
                            "results": [],
                        },
                    ],
                    "reviews": [{"decision_id": 100, "requires_human": True}],
                },
            )
        if path.endswith("/run"):
            return httpx.Response(200, json={"decided": 0})
        if path.endswith("/export"):
            return httpx.Response(200, text='{"file_id":"invoice.pdf","result":"NO_PAGAR"}\n')
        raise AssertionError(f"Unexpected request: {path}")

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(respond), base_url="http://demo"
    ) as api:
        await DEMO["run"](api, 7, [invoice], book, "2026-09-19", tmp_path / "out")

    assert json.loads((tmp_path / "out/outcomes.jsonl").read_text()) == {
        "file_id": "invoice.pdf",
        "result": "NO_PAGAR",
    }
    detail = json.loads((tmp_path / "out/detail.json").read_text())
    assert detail[0]["result"] == "NO_PAGAR"
    assert detail[0]["decision_author"] == "operator"
    assert detail[0]["rules_that_fired"] == []
    assert detail[0]["engine_rules_that_fired"] == ["Order matched"]
