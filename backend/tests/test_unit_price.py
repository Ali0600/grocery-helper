"""Tests for normalizing a per-unit price string to comparable cents/kg|l."""
import pytest

from app.unit_price import unit_price_cents


@pytest.mark.parametrize(
    "ppu, expected",
    [
        ("1 kg = 13.33", 1333),      # weight -> cents/kg
        ("1 kg = 1.93", 193),
        ("1 l = 2.47", 247),         # volume -> cents/l, same axis
        ("1 kg = 39.96", 3996),      # cheap..expensive beef both parse
        ("1 kg = 59.95", 5995),
        ("22.79 €/kg", 2279),        # bare Lidl shape (no "1 kg =")
        ("1 kg = 9.97/10.83/11.07", 997),  # range -> first value
        ("1 kg = 1,93", 193),        # comma decimal, just in case
        # not comparable -> None (these sink under the €/kg sort)
        ("0.46 €/Stk.", None),
        ("1 wl = 0.30", None),       # wash load
        ("1 m = 2.00", None),        # per metre
        ("Kg-Preis", None),
        ("kg-Preis 4.44", None),
        ("", None),
        (None, None),
        ("1 kg = 0", None),          # non-positive -> None
    ],
)
def test_unit_price_cents(ppu, expected):
    assert unit_price_cents(ppu) == expected
