"""Categorization guards against real-world miscategorizations.

Cases drawn from a live Lidl Berlin snapshot where the old name-only classifier
misfired (a flavour/brand word won over the real category).
"""
import pytest

from app.categories import CATEGORIES, classify


@pytest.mark.parametrize(
    "name, brand, expected",
    [
        # --- regressions fixed by the brand map / overrides ---
        ("Allini Hugo Frizzante Mango", "ALLINI", "beverages"),  # sekt, not fruit
        ("Allini Rhabarber-Erdbeer Secco", "ALLINI", "beverages"),
        ("Mister Choc Milch Freunde", "MISTER CHOC", "sweets"),  # chocolate, not dairy
        ("Iglo Rahm-Spinat", "IGLO", "frozen"),  # frozen brand, not veg
        # --- things that must keep working ---
        ("Milbona Käse am Stück", "MILBONA", "cheese"),
        ("Metzgerfrisch Puten-Hacksteaks", "METZGERFRISCH", "poultry"),
        ("Frisches Rinderhackfleisch", None, "beef"),
        ("Deutsche Markenbutter", "Milbona", "butter"),
        ("Ehrmann Almighurt", "EHRMANN", "dairy"),
        ("Valensina Saft/Nektar", "VALENSINA", "beverages"),
        ("PARKSIDE Akku-Bohrschrauber", "PARKSIDE", "household"),
        # --- flyer-catalog keyword expansion ---
        ("DELUXE Irisches Angus Rumpsteak", "DELUXE", "beef"),
        ("Sol & Mar Chorizo Klassik", "Sol & Mar", "pork"),
        ("Dulano Delikatess Bacon", "Dulano", "pork"),
        ("Gelatelli Premium Stieleis", "Gelatelli", "frozen"),
        ("Ferrero Hanuta", "Ferrero", "sweets"),
        ("Moët & Chandon Impérial Champagner", "Moët & Chandon", "beverages"),
        ("Milbona Edamer", "Milbona", "cheese"),
        ("TRONIC Standventilator", "TRONIC", "household"),
        # --- substring / flavour-word regressions caught in review ---
        ("Frisches Schweinegulasch", None, "pork"),  # not beef ("gulasch")
        ("Metzgerfrisch Schweine-Nackensteak", None, "pork"),  # not beef ("steak")
        ("Volvic Touch Zitrone Limette", "Volvic", "beverages"),  # "limette" != Mett
        ("Lipton Ice Tea Pfirsich", "Lipton", "beverages"),  # not fruit ("pfirsich")
        ("Trumpf Schogetten Freeze Mango", "Trumpf", "sweets"),  # not fruit ("mango")
        ("Häagen-Dazs Belgian Chocolate", "Häagen-Dazs", "frozen"),  # ice cream, not sweets
    ],
)
def test_classify(name, brand, expected):
    assert classify(name, brand) == expected


# Bonial taxonomy paths (level-1 + product/brand nodes).
_NONFOOD = ["Elektronik und Technik", "Marken", "Marken Möbel und Wohnen"]
_FOOD = "Lebensmittel und Getränke"


@pytest.mark.parametrize(
    "name, brand, path, expected",
    [
        # non-food path wins even when the name has a food word ("Käse")
        ("Käse-Reibe Edelstahl", None, _NONFOOD, "household"),
        # product taxonomy nodes map directly
        ("x", None, [_FOOD, "Produkte", "Lebensmittel", "Milchprodukte", "Käse", "Weichkäse"], "cheese"),
        ("x", None, [_FOOD, "Produkte", "Lebensmittel", "Fleisch", "Wurstwaren"], "pork"),
        ("x", None, [_FOOD, "Produkte", "Getränke", "Alkoholische Getränke"], "beverages"),
        ("x", None, [_FOOD, "Produkte", "Lebensmittel", "Obst", "Kernobst"], "fruits"),
        # brand-only food path -> falls back to keyword classifier on the name
        ("Eberswalder Rostbratwurst", "Eberswalder", [_FOOD, "Marken", "Marken Lebensmittel"], "pork"),
    ],
)
def test_classify_with_path(name, brand, path, expected):
    assert classify(name, brand, path) == expected


def test_classify_name_only_still_works():
    # brand is optional
    assert classify("Tiefkühl Pizza Salami") == "frozen"


def test_unknown_is_other():
    assert classify("Zzz Quux Widget", None) == "other"


def test_every_result_is_a_known_category():
    for name in ["Bananen", "Gouda", "Cola", "Mystery item 123"]:
        assert classify(name) in CATEGORIES
