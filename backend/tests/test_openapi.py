from app.main import app


def test_contract_is_clean_for_codegen():
    spec = app.openapi()
    ids = [op["operationId"] for path in spec["paths"].values() for op in path.values()]
    assert len(ids) == len(set(ids))
    assert not [i for i in ids if "__" in i], "add an explicit operation_id"
    assert not [s for s in spec["components"]["schemas"] if "__" in s], "rename the schema"
