"""Tests for normalizing a per-unit price string to comparable cents/kg|l."""
import pytest

from app.unit_price import derive_price_per_unit, normalize_price_per_unit, unit_price_cents


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
        # Single net weight/volume -> divide price by the amount (in kg / l).
        ("Frische Erdbeeren 500-g-Schale", 299, "1 kg = 5.98"),  # 2.99 / 0.5 kg
        ("250 g", 199, "1 kg = 7.96"),                           # 1.99 / 0.25 kg
        ("Versch. Sorten 800 g", 199, "1 kg = 2.49"),            # 1.99 / 0.8 kg (rounded)
        ("Gekühlt 40 g", 59, "1 kg = 14.75"),                    # 0.59 / 0.04 kg
        ("Je 2,5 l", 1499, "1 l = 6.00"),                        # 14.99 / 2.5 l (rounded)
        ("330-ml-Dose", 99, "1 l = 3.00"),                       # 0.99 / 0.33 l
        ("50 cl", 99, "1 l = 1.98"),                             # 0.99 / 0.5 l
        # Ambiguous -> None (a wrong €/kg is worse than none).
        ("3,5 % Fett, Gekühlt. Standardpackung: 500 g 1 kg", 149, None),  # 1 kg = base ref
        ("Gekühlt 1 kg 20 Stück", 679, None),                            # second quantity
        ("Aus Alaska-Seelachsfilet. 900 g 30 Stück", 399, None),         # weight + count
        ("Ohne Brustbein Ca. 1,1 kg", 444, None),                        # approximate
        ("beim Kauf von 3 Stk. 3x 400 ml", 199, None),                   # multipack
        ("Versch. Sorten 20 × 10 g", 199, None),                         # multipack ×
        ("Frische Beeren 250-300 g", 299, None),                         # range
        ("Verschiedene Sorten, Standardpackung: 1 l 2 l", 299, None),    # multi-variant
        ("Je 1,2/1,1 kg/800/650 g", 549, None),                          # ranges
        ("6 Stück", 199, None),                                          # per-piece
        ("Inhalt: 6 Beutel", 199, None),                                 # no weight unit
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


@pytest.mark.parametrize(
    "ppu, price_cents, expected",
    [
        # parenthesized Grundpreis — the feed's most common variant (~19% of served offers);
        # the anchored _EQ_RE can't read it and the card renders "8,05) €/(1 kg".
        ("(1 kg = 8.05)", 399, "1 kg = 8.05"),
        ("(1 L = 1.05)", 79, "1 L = 1.05"),
        # non-kg/l units are unwrapped too (fixes the card); they stay unsortable below.
        ("(1 WL = 0.19)", 499, "1 WL = 0.19"),
        # German shorthand: the dash stands in for the euros.
        ("1 kg = -.90", 179, "1 kg = 0.90"),
        ("1 l = -,75", 99, "1 l = 0,75"),
        # bare label: the advertised price IS the per-unit price
        ("kg-Preis", 149, "1 kg = 1.49"),
        ("100-g-Preis", 33, "1 kg = 3.30"),  # per-100g normalized to kg (the feed's own convention)
        # label with the value attached
        ("kg-Preis = 4.98", 259, "1 kg = 4.98"),
        # a label with no usable price -> None, so derive_price_per_unit can run instead
        ("kg-Preis", 0, None),
        ("100-g-Preis", None, None),
        # already-clean strings are untouched (idempotent), unknown shapes pass through
        ("1 kg = 8.05", 399, "1 kg = 8.05"),
        ("22.79 €/kg", 799, "22.79 €/kg"),
        ("1 Topf", 149, "1 Topf"),
        (None, 199, None),
        ("", 199, None),
    ],
)
def test_normalize_price_per_unit(ppu, price_cents, expected):
    assert normalize_price_per_unit(ppu, price_cents) == expected


@pytest.mark.parametrize(
    "ppu, price_cents, expected_cents",
    [
        ("(1 kg = 8.05)", 399, 805),      # was None -> now sortable
        ("(1 L = 1.05)", 79, 105),
        ("1 kg = -.90", 179, 90),
        ("100-g-Preis", 33, 330),         # the reported Lidl "Kirschen" (0,33 €/100 g)
        ("kg-Preis", 149, 149),
        ("kg-Preis = 4.98", 259, 498),
        ("(1 WL = 0.19)", 499, None),     # cleaned for display, still not a €/kg|€/l axis
        ("(1 m² = 11.90)", 2499, None),
    ],
)
def test_normalized_value_feeds_the_eur_per_kg_sort(ppu, price_cents, expected_cents):
    assert unit_price_cents(normalize_price_per_unit(ppu, price_cents)) == expected_cents
