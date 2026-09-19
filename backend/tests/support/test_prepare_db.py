from tests.support.prepare_db import is_test_db


def test_only_test_databases_are_recreated():
    assert all(map(is_test_db, ["trace_test", "trace_test_scale", "trace_ingestion_test"]))
    assert not any(map(is_test_db, ["trace", "postgres", "trace_demo", "test_trace", None]))
