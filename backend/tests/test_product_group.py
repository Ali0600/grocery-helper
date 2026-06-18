"""Tests for the in-category product grouping (app/product_group.py)."""
import pytest

from app.product_group import product_group


@pytest.mark.parametrize(
    "name,expected",
    [
        # Real fruit names sampled from the live DB.
        ("Avocado", "avocado"),
        ("Aprikosen", "aprikose"),
        ("Aprikosen, lose", "aprikose"),
        ("Gelb- oder weißfleischige Nektarinen", "nektarine"),
        ("Gelb- oder weißfleischige Pfirsiche", "pfirsich"),
        ("Bellini Pfirsich", "pfirsich"),
        ("Mix Tafeltrauben", "traube"),
        ("Dunkle,  kernlose Trauben", "traube"),
        ("Erdbeeren", "erdbeere"),
        ("Kirschen", "kirsche"),
        ("Ananas, lose", "ananas"),
        ("Wassermelone", "melone"),
    ],
)
def test_fruit_names_group_by_product(name, expected):
    key, _label = product_group(name, None, "fruits")
    assert key == expected


def test_specific_berry_beats_generic_beere():
    # "Erdbeere"/"Himbeere" contain "beere"; the specific rule must win.
    assert product_group("Erdbeeren", None, "fruits")[0] == "erdbeere"
    assert product_group("Himbeeren", None, "fruits")[0] == "himbeere"
    assert product_group("Schwarze Johannisbeeren", None, "fruits")[0] == "johannisbeere"
    # A berry with no specific rule falls back to the generic "Beere".
    assert product_group("Gemischte Beeren", None, "fruits") == ("beere", "Beere")


def test_label_is_returned_with_key():
    assert product_group("Avocado", None, "fruits") == ("avocado", "Avocado")


def test_substring_traps_resolve_to_the_specific_product():
    # "lauch" ⊂ "knoblauch", "lachs" ⊂ "seelachs", "milch" ⊂ "buttermilch".
    assert product_group("Knoblauch", None, "vegetables")[1] == "Knoblauch"
    assert product_group("Seelachsfilet", None, "fish")[1] == "Seelachs"
    assert product_group("Buttermilch", None, "dairy")[1] == "Buttermilch"
    assert product_group("Frische Vollmilch", None, "dairy")[1] == "Milch"


def test_beef_cuts_group_for_the_eur_per_kg_comparison():
    assert product_group("Rinder-Hackfleisch", None, "beef")[1] == "Hackfleisch"
    assert product_group("Rinderfilet", None, "beef")[1] == "Filet"
    assert product_group("Rumpsteak", None, "beef")[1] == "Steak"


def test_unmapped_category_and_no_match_return_none():
    # Sweets isn't a grouping category -> never groups.
    assert product_group("Milka Schokolade", None, "sweets") == (None, None)
    # A fruits offer with no known noun stays ungrouped.
    assert product_group("Obstsalat to go", None, "fruits") == (None, None)
    # Missing/empty category or name is safe.
    assert product_group("Avocado", None, None) == (None, None)
    assert product_group("", None, "fruits") == (None, None)
