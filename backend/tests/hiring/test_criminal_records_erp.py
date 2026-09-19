import importlib.util
import threading
from pathlib import Path
from urllib.request import urlopen

SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "processes"
    / "hiring-screening"
    / "criminal_records_erp.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("criminal_records_erp", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fixture_has_unique_ids_and_one_known_hiring_candidate():
    module = load_module()
    assert len(module.RECORDS) == 23
    assert len({row["record_id"] for row in module.RECORDS}) == len(module.RECORDS)
    assert [row for row in module.RECORDS if row["full_name"] == "Ana Molina"] == [
        {
            "record_id": "CR-00001",
            "full_name": "Ana Molina",
            "conviction_date": "2024-05-12",
            "offense": "Fraud",
            "status": "ACTIVE",
        }
    ]


def test_registry_does_not_define_credentials():
    module = load_module()
    assert not hasattr(module, "USER")
    assert not hasattr(module, "PASSWORD")


def test_public_prefix_exposes_status_and_records():
    module = load_module()
    server = module.ThreadingHTTPServer(("127.0.0.1", 0), module.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urlopen(base + module.PUBLIC_PREFIX + "/", timeout=2) as response:
            assert b"<system>ONLINE</system>" in response.read()
        with urlopen(
            base + module.PUBLIC_PREFIX + "/criminal/records?page=1", timeout=2
        ) as response:
            assert b"<name>Ana Molina</name>" in response.read()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
