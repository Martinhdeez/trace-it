import json
from pathlib import Path

from app.main import app

COMMITTED = Path(__file__).parents[2] / "frontend" / "openapi.json"


def test_contract_is_clean_for_codegen():
    spec = app.openapi()
    ids = [op["operationId"] for path in spec["paths"].values() for op in path.values()]
    assert len(ids) == len(set(ids))
    assert not [i for i in ids if "__" in i], "add an explicit operation_id"
    assert not [s for s in spec["components"]["schemas"] if "__" in s], "rename the schema"


def test_committed_contract_is_current():
    assert json.loads(COMMITTED.read_text()) == json.loads(json.dumps(app.openapi())), (
        "run `make openapi`"
    )
