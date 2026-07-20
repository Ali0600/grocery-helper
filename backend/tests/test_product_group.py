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


@pytest.mark.parametrize(
    "name,expected",
    [
        # Real soft-drink names sampled from the live DB, one per group.
        ("Lipton Ice Tea", "Tee"),
        ("FUZE TEA", "Tee"),  # English "tea" (not the German "tee")
        ("Rauch Eistee", "Tee"),
        ("Red Bull Energy Drink", "Energy"),
        ("Rockstar Energydrink", "Energy"),
        ("Gerolsteiner Schorle", "Schorle"),
        ("Innocent Creamy Smoothie", "Smoothie"),
        ("COCA-COLA", "Cola"),
        ("Pepsi Cola", "Cola"),
        ("Vita Cola", "Cola"),
        ("FANTA", "Limonade"),
        ("Almdudler Original", "Limonade"),
        ("Rixdorfer Fassbrause", "Limonade"),
        ("Valensina 100 % Saft", "Saft"),
        ("becker's bester Fruchtsäfte", "Saft"),
        ("Evian Mineralwasser", "Wasser"),
        ("Spreequell Naturell", "Wasser"),
    ],
)
def test_soft_drinks_group_by_type(name, expected):
    assert product_group(name, None, "soft_drinks")[1] == expected


def test_soft_drinks_ordering_and_brand_disambiguation():
    g = lambda n: product_group(n, None, "soft_drinks")[1]  # noqa: E731
    # Cola before Limonade: a cola that also says "Erfrischungsgetränk" stays Cola.
    assert g("Coca-Cola Erfrischungsgetränk") == "Cola"
    # Limonade before Saft: Granini makes both — "Die Limo" is a Limonade, not a juice.
    assert g("Granini Die Limo") == "Limonade"
    assert g("Granini Trinkgenuss") == "Saft"
    # A brand that spans three types resolves by the type word before the brand word.
    assert g("VOLVIC Tee") == "Tee"
    assert g("Volvic Juicy") == "Saft"
    assert g("Volvic naturelle") == "Wasser"
    # The " spezi" leading-space guard must NOT match "…-Spezialsalz" (a mis-filed non-drink).
    assert product_group("GUT&GÜNSTIG Spülmaschinen-Spezialsalz", None, "soft_drinks") == (None, None)
    # …but a real Spezi (cola-mix) still groups as Cola.
    assert g("Krombacher Spezi") == "Cola"


@pytest.mark.parametrize(
    "name,expected",
    [
        # Real snack names sampled from the live DB, one+ per group.
        ("Pringles Chips", "Chips"),
        ("funny-frisch Ofen Chips", "Chips"),
        ("Lorenz Crunchips oder Nic Nac's", "Chips"),
        ("REWE Bio Tortilla Chips", "Chips"),
        ("Wurzener Erdnussflips", "Chips"),  # "flips" → a puffed snack, not raw nuts
        ("ALESTO Cashewkerne", "Nüsse"),
        ("ALESTO Mandeln XXL", "Nüsse"),
        ("ja! Pikante Erdnüsse", "Nüsse"),
        ("Alesto Nussmix", "Nüsse"),
        ("Alesto Studentenfutter Classic", "Studentenfutter"),
        ("GUT&GÜNSTIG Studentenfutter", "Studentenfutter"),
        ("Alesto Feigen/Datteln", "Studentenfutter"),
        ("ALESTO Bio Samen", "Studentenfutter"),
        ("TUC Cracker", "Cracker"),
        ("Lorenz Saltletts", "Cracker"),
        ("funny frisch Brezli", "Cracker"),
        ("Wasa Crunchy Bites", "Cracker"),
    ],
)
def test_snacks_group_by_type(name, expected):
    assert product_group(name, None, "snacks")[1] == expected


def test_snacks_studentenfutter_beats_the_alesto_nut_brand():
    g = lambda n: product_group(n, None, "snacks")[1]  # noqa: E731
    # Alesto is Lidl's nut brand, but its trail-mix lines must group by the specific word,
    # not fall into Nüsse via "alesto".
    assert g("Alesto Studentenfutter Classic") == "Studentenfutter"
    assert g("Alesto Trail Mix") == "Studentenfutter"
    assert g("ALESTO Soft-Früchte") == "Studentenfutter"
    # …while a plain Alesto nut product still groups as Nüsse.
    assert g("ALESTO Walnusskerne") == "Nüsse"


def test_unmapped_category_and_no_match_return_none():
    # Sweets isn't a grouping category -> never groups.
    assert product_group("Milka Schokolade", None, "sweets") == (None, None)
    # A fruits offer with no known noun stays ungrouped.
    assert product_group("Obstsalat to go", None, "fruits") == (None, None)
    # Missing/empty category or name is safe.
    assert product_group("Avocado", None, None) == (None, None)
    assert product_group("", None, "fruits") == (None, None)


# --- coffee: grouped by FORM ---------------------------------------------------
# Capsules, pads, beans and a chilled iced coffee are not substitutes, so "which is cheapest"
# is only a fair question within a form. Ordering matters: the specific forms must beat the
# catch-all "Gemahlen", whose keywords ("kaffee", "espresso") appear in almost every name.


def test_coffee_groups_by_form_not_by_brand():
    # Brand-only names (the word "Kaffee" absent) still land, via the brand keywords in Gemahlen.
    assert product_group("Jacobs Gold", None, "coffee")[1] == "Gemahlen"
    assert product_group("Lavazza Caffè Crema", None, "coffee")[1] == "Gemahlen"
    assert product_group("Jacobs Lungo Kaffeekapseln Intenso", "Jacobs", "coffee")[1] == "Kapseln"
    assert product_group("Senseo Kaffeepads Classic", "Senseo", "coffee")[1] == "Pads"
    assert product_group("Tchibo Feine Milde Ganze Bohne", "Tchibo", "coffee")[1] == "Ganze Bohnen"
    assert product_group("Mövenpick Iced Coffee", "Mövenpick", "coffee")[1] == "Eiskaffee"
    assert product_group("ja! Röstkaffee kräftig", "ja!", "coffee")[1] == "Gemahlen"
    assert product_group("Dallmayr Prodomo", "Dallmayr", "coffee")[1] == "Gemahlen"


def test_a_specific_coffee_form_beats_the_generic_ground_bucket():
    """Every one of these also contains a "Gemahlen" keyword ("kaffee"/"espresso"/a brand), so
    they only land right because the specific forms are scanned first."""
    assert product_group("Jacobs Kaffeekapseln Espresso", "Jacobs", "coffee")[1] == "Kapseln"
    assert product_group("Melitta Kaffeepads Espresso", "Melitta", "coffee")[1] == "Pads"
    assert product_group("Lavazza Espresso Ganze Bohnen", "Lavazza", "coffee")[1] == "Ganze Bohnen"
    assert product_group("Nescafé 3in1 Instant Kaffee", "Nescafé", "coffee")[1] == "Instant"


def test_coffee_grouping_does_not_leak_into_other_categories():
    # The map is keyed by category, so a cheese named "Bohne" can't become Ganze Bohnen.
    assert product_group("Bohnen-Käse", None, "cheese")[1] != "Ganze Bohnen"
