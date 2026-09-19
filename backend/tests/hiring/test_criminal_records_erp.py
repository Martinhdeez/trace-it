import importlib.util
from pathlib import Path

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
