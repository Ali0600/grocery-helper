"""Tests for normalizing a per-unit price string to comparable cents/kg|l."""
import pytest

from app.unit_price import derive_price_per_unit, unit_price_cents


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


@pytest.mark.parametrize(
    "unit, price_cents, expected",
    [
        # Sold as a single 1 kg / 1 l quantity -> the price IS the per-unit price.
        ("Spanien/Italien/Portugal Klasse I 1 kg", 249, "1 kg = 2.49"),
        ("Spanien/Italien/Griechenland Kl. I je 1-kg-Schale", 199, "1 kg = 1.99"),
        ("Spanien Kl. I je 1-kg-Btl.", 222, "1 kg = 2.22"),
        ("Italien Kl. I, kernarm je 1 kg", 111, "1 kg = 1.11"),
        ("100 % Saft 1 l zzgl. 0.25 Pfand", 149, "1 l = 1.49"),
        ("aus Konzentrat, versch. Sorten 1-l-Pckg.", 199, "1 l = 1.99"),
        ("Verschiedene Sorten 1 Liter", 599, "1 l = 5.99"),
        # The Grundpreis is embedded in the description but was never extracted.
        ("48/50/45 % Fett i. Tr. Gekühlt, 1 kg = 5.67 150 g", 85, "1 kg = 5.67"),
        ("Versch. Sorten. 1 kg = 17.00 100 ml 3 x 100 g", 510, "1 kg = 17.00"),
        # Ambiguous -> None (a wrong €/kg is worse than none).
        ("3,5 % Fett, Gekühlt. Standardpackung: 500 g 1 kg", 149, None),  # 1 kg = base ref
        ("Gekühlt 1 kg 20 Stück", 679, None),                            # second quantity
        ("Ohne Brustbein Ca. 1,1 kg", 444, None),                        # approximate, not 1
        ("Verschiedene Sorten, Standardpackung: 1 l 2 l", 299, None),    # multi-variant
        ("Je 1,2/1,1 kg/800/650 g", 549, None),                          # ranges
        ("Frische Erdbeeren 500-g-Schale", 299, None),                   # 500 g, not 1 kg
        ("6 Stück", 199, None),                                          # per-piece
        ("", 199, None),
        (None, 199, None),
        ("Klasse I 1 kg", 0, None),                                      # no price
    ],
)
def test_derive_price_per_unit(unit, price_cents, expected):
    assert derive_price_per_unit(unit, price_cents) == expected


def test_derived_value_feeds_the_eur_per_kg_sort():
    # End to end: a 1-kg tray with no Grundpreis still gets a comparable €/kg.
    ppu = derive_price_per_unit("Spanien/Italien/Portugal Klasse I 1 kg", 249)
    assert unit_price_cents(ppu) == 249
