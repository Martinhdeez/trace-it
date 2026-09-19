"""The delivery check refuses everything the organisers' verifier would refuse."""

from check_delivery import check

VALID = (
    '{"file_id": "a.pdf", "result": "PAGAR"}\n'
    '{"file_id": "b.pdf", "result": "NO_PAGAR", "reason": "no order"}\n'
    '{"file_id": "c.pdf", "result": "ESCALAR"}\n'
)


def test_a_valid_file_passes_and_counts_results():
    problems, warnings, results = check(VALID, {"a.pdf", "b.pdf", "c.pdf"})
    assert problems == []
    assert results == {"PAGAR": 1, "NO_PAGAR": 1, "ESCALAR": 1}
    assert warnings == ["extra top-level fields (optional trace fields): reason"]


def test_an_unknown_result_fails():
    problems, _, _ = check('{"file_id": "a.pdf", "result": "PAY"}\n', None)
    assert problems == ["line 1: result 'PAY' is not one of ('PAGAR', 'NO_PAGAR', 'ESCALAR')"]


def test_a_missing_file_id_fails():
    problems, _, _ = check('{"result": "PAGAR"}\n', None)
    assert problems == ["line 1: no file_id"]


def test_a_duplicate_file_id_fails():
    line = '{"file_id": "a.pdf", "result": "PAGAR"}\n'
    problems, _, _ = check(line * 2, {"a.pdf"})
    assert problems == ["a.pdf: 2 lines"]


def test_a_line_that_is_not_json_fails():
    problems, _, _ = check(VALID + "not json\n", {"a.pdf", "b.pdf", "c.pdf"})
    assert problems and problems[0].startswith("line 4: not JSON")


def test_a_pdf_without_a_line_and_a_line_without_a_pdf_fail():
    problems, _, _ = check(VALID, {"a.pdf", "b.pdf", "d.pdf"})
    assert problems == ["c.pdf: not a PDF of the batch", "d.pdf: missing"]
