import pytest

from app.common.normalization import invoice_date, money


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1.802,90", "1802.90"),
        ("EUR 1802.90", "1802.90"),
        ("1,802.90", "1802.90"),
        ("0,01", "0.01"),
        ("(1.802,90)", "-1802.90"),
        ("1\u200b.802,90", "1802.90"),
    ],
)
def test_money(raw, expected):
    assert money(raw) == expected


@pytest.mark.parametrize("raw", ["1.802", "1,802", "1.80,20", "NaN", "", "1,2,3"])
def test_ambiguous_money(raw):
    with pytest.raises(ValueError):
        money(raw)


def test_dates():
    assert invoice_date("6 de abril de 2026") == "2026-04-06"
    assert invoice_date("2026-04-06") == "2026-04-06"
    with pytest.raises(ValueError):
        invoice_date("30/02/2026")
