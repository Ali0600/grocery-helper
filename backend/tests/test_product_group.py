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


@pytest.mark.parametrize(
    "name,expected",
    [
        # Real vegetable names sampled from the live DB. Everything below the divider was
        # UNGROUPED before 2026-07-29 — 107 rows / 46 distinct produce products had no
        # sub-group at all, so a lone fruit/veg had no sub-category to head a section with
        # or to hand to the Basket.
        ("Rispentomaten", "tomate"),
        ("Salatgurke", "gurke"),
        ("Speisefrühkartoffeln", "kartoffel"),
        ("Zwiebeln", "zwiebel"),
        ("Spitzpaprika", "paprika"),
        ("Bio Möhren", "mohre"),
        ("Brokkoli", "brokkoli"),
        # ---- newly covered ----
        ("Kohlrabi", "kohlrabi"),
        ("EDEKA Regional Kohlrabi", "kohlrabi"),
        ("Radieschen", "radieschen"),
        ("Radieschentopf", "radieschen"),
        ("Deutscher Frischer Zuckermais", "mais"),
        ("Bonduelle Goldmais", "mais"),
        ("Buschbohnen", "bohne"),
        ("REWE Beste Wahl Prinzessbohnen", "bohne"),
        ("REWE Bio Edamame", "edamame"),
        ("Pfifferlinge", "pilz"),
        ("Portobello", "pilz"),
        ("Mini-Pak-Choi", "pak-choi"),
        ("Spitzkohl", "kohl"),
        ("Kresse", "kresse"),
        ("Bio Ingwer", "ingwer"),
        ("Chicorée", "chicoree"),
        ("Peperoni-Mix", "peperoni"),
        ("Lollo Bionda", "salat"),
        ("EDEKA Bio Gemüse", "gemuse"),
        # The feed ships a typo'd "Romatomen"; it is still a tomato.
        ("Romatomen", "tomate"),
    ],
)
def test_vegetable_names_group_by_product(name, expected):
    key, _label = product_group(name, None, "vegetables")
    assert key == expected


def test_generic_kohl_stays_behind_the_specific_cabbages():
    # "kohl" ⊂ "Blumenkohl" and ⊂ "Kohlrabi", so the generic MUST sit last in the list.
    # Sabotage: move ("Kohl", ["kohl"]) above them -> the first two assertions fail.
    assert product_group("Blumenkohl", None, "vegetables")[1] == "Blumenkohl"
    assert product_group("Kohlrabi", None, "vegetables")[1] == "Kohlrabi"
    # A cabbage with no specific rule falls back to the generic.
    assert product_group("Spitzkohl", None, "vegetables") == ("kohl", "Kohl")


def test_generic_gemuese_never_beats_a_named_vegetable():
    # "gemüse" ⊂ "Gemüsezwiebel"/"Gemüsemais"; the named product must win, so the generic
    # veg-mix bucket sits last of all. Sabotage: move ("Gemüse", …) up -> these fail.
    assert product_group("Gemüsezwiebeln", None, "vegetables")[1] == "Zwiebel"
    assert product_group("Gemüsemais", None, "vegetables")[1] == "Mais"
    assert product_group("Frosta Gemüse Mix", None, "vegetables")[1] == "Gemüse"


def test_pak_choi_matches_the_hyphenated_spelling():
    # The flyer writes "Mini-Pak-Choi"; a spaced-only keyword misses it entirely (this was
    # caught by diffing against the real DB, not by reading the code). Sabotage: drop
    # "pak-choi" from the keywords -> the first assertion fails.
    assert product_group("Mini-Pak-Choi", None, "vegetables")[1] == "Pak Choi"
    assert product_group("Pak Choi", None, "vegetables")[1] == "Pak Choi"


def test_grapefruit_and_melon_cultivars_group():
    # Grapefruit had no rule at all; "Piel de Sapo" is a melon the flyer names without
    # the word "Melone".
    assert product_group("Grapefruit", None, "fruits") == ("grapefruit", "Grapefruit")
    assert product_group("Piel de Sapo", None, "fruits")[1] == "Melone"
    assert product_group("Piel de Sapo Melone", None, "fruits")[1] == "Melone"
    # The category gate keeps grapefruit-FLAVOURED drinks out of the fruit bowl.
    assert product_group("Rio d'Oro Pink Grapefruit", None, "soft_drinks")[1] != "Grapefruit"


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


# --- Drugstore aisles (2026-08-04) -----------------------------------------------------------
# Every name below is a real product from the corpus, not an invented one.

@pytest.mark.parametrize(
    "category,name,expected",
    [
        ("body", "Dove Deospray", "Deo"),
        ("body", "Fa Deo", "Deo"),
        ("body", "Axe Duschgel", "Duschgel"),
        ("body", "Gillette Fusion5 Rasierklingen", "Rasur"),
        ("body", "Cerruti 1881 Homme After Shave", "Rasur"),
        ("body", "Cien Sun kids Sonnenspray", "Sonnenschutz"),
        ("body", "Isana Bodylotion", "Bodylotion"),
        ("body", "Always Slipeinlagen", "Damenhygiene"),
        ("body", "Jean&Len Handseife", "Seife"),
        ("hair", "Garnier Fructis Shampoo", "Shampoo"),
        ("hair", "Batiste Trockenshampoo", "Trockenshampoo"),
        ("hair", "Garnier Nutrisse Ultra Crème Coloration", "Coloration"),
        ("dental", "Oral-B Zahncreme", "Zahncreme"),
        ("dental", "Curaprox Zahnbürste Ultra Soft", "Zahnbürste"),
        ("dental", "Oral-B Aufsteckzahnbürste iO", "Aufsteckbürsten"),
        ("dental", "Philips Elektrische Zahnbürste Sonicare 5500", "Elektrische Zahnbürste"),
        ("dental", "CB12 Mundspülung", "Mundspülung"),
        ("makeup", "Blush Stick Blushin' Charm 020 Coral Cutie, 5,5 g", "Blush"),
        ("makeup", "Concealer Cream Ultimate 010 N Ivory, 3 g", "Concealer"),
        ("makeup", "Eyeliner Calligraph Art Matte 070 Snow White, 1,1 ml", "Eyeliner"),
        ("fragrance", "AIGNER Pour Homme Eau de Toilette", "Eau de Toilette"),
        ("fragrance", "Burberry Woman Eau de Parfum", "Eau de Parfum"),
        ("laundry", "Lenor Weichspüler", "Weichspüler"),
        ("laundry", "Burti Feinwaschmittel Flüssig", "Feinwaschmittel"),
        ("cleaning", "Fairy Spülmittel", "Spülmittel"),
        ("cleaning", "Frosch Spülmaschinentabs", "Spülmaschine"),
        ("cleaning", "Frosch WC Reiniger", "Reiniger"),
        ("baby", "Pampers Big Pack", "Windeln"),
        ("baby", "Bübchen Baby Wundschutzcreme sensitiv", "Babypflege"),
        ("health", "Doppelherz Magnesium", "Vitamine"),
        ("health", "ALDI SPORTS High-Protein-Pulver Iced Matcha Latte", "Sportnahrung"),
        ("health", "Dr. Scholl's Hühneraugenpflaster", "Pflaster"),
        ("pet", "Sheba Katze Filet", "Katzenfutter"),
        ("pet", "Vitakraft Hundesnacks", "Tiersnacks"),
        ("pet", "Beneful Hund Trockennahrung", "Hundefutter"),
    ],
)
def test_drugstore_products_get_a_sub_group(category, name, expected):
    assert product_group(name, None, category)[1] == expected


@pytest.mark.parametrize(
    "category,name,expected,beats",
    [
        # Each of these ALSO contains a keyword of the group named in `beats`, so it only lands
        # correctly because the specific entry is scanned first. Reorder and the test fails.
        ("pet", "CACHET Katzentoilette", "Tierzubehör", "Katzenfutter"),
        ("pet", "CACHET Katzenkratzspielzeug", "Tierzubehör", "Katzenfutter"),
        ("pet", "ZOOROYAL Katzenstreu", "Katzenstreu", "Katzenfutter"),
        ("pet", "GUT&GÜNSTIG Lieblings-Kaurollchen", "Tiersnacks", "Hundefutter"),
        ("dental", "Oral-B Aufsteckzahnbürste iO", "Aufsteckbürsten", "Zahnbürste"),
        ("dental", "Oral-B Elektrische Zahnbürste iO Series 5", "Elektrische Zahnbürste",
         "Zahnbürste"),
        ("hair", "Batiste Trockenshampoo", "Trockenshampoo", "Shampoo"),
        ("laundry", "Domol Feinwaschmittel Black", "Feinwaschmittel", "Waschmittel"),
        ("laundry", "Colorwaschmittel Pulver Glamorous Touch, 20 Wl", "Colorwaschmittel",
         "Waschmittel"),
        ("laundry", "Perwoll Wollwaschmittel", "Feinwaschmittel", "Waschmittel"),
        ("cleaning", "Domol Geschirr-Reiniger Tabs 12-fach Power", "Spülmaschine", "Reiniger"),
        ("body", "LACURA SUN After Sun Lotion", "Sonnenschutz", "Bodylotion"),
        ("health", "Max Balance Whey Proteinpulver", "Sportnahrung", "Nahrungsergänzung"),
    ],
)
def test_a_specific_drugstore_group_beats_the_generic_one(category, name, expected, beats):
    got = product_group(name, None, category)[1]
    assert got == expected, f"{name!r} -> {got!r}, expected {expected!r} (not {beats!r})"


def test_the_drugstore_maps_do_not_overwrite_a_grocery_one():
    """`_GROUPS.update(_DRUGSTORE_GROUPS)` would SILENTLY replace a grocery mapping if a slug
    were ever repeated — no error, just a category that stops grouping the way it did."""
    from app.product_group import _DRUGSTORE_GROUPS, _GROUPS
    grocery = {"fruits", "vegetables", "beef", "poultry", "pork", "fish", "cheese", "dairy",
               "bakery", "coffee", "soft_drinks", "snacks"}
    assert not (set(_DRUGSTORE_GROUPS) & grocery), "a drugstore key shadows a grocery map"
    assert grocery <= set(_GROUPS), "a grocery map went missing from _GROUPS"


def test_an_either_variant_name_picks_one_group_and_that_is_fine():
    """The source sells one offer covering two variants ("Color- oder Vollwaschmittel"). Only
    the second compound is spelled out, so it lands in Vollwaschmittel. Pinned deliberately:
    either label is defensible for a combined offer, and the point is that it lands SOMEWHERE
    rather than falling out of the aisle entirely."""
    assert product_group("Domol Color- oder Vollwaschmittel Flüssig", None,
                         "laundry")[1] == "Vollwaschmittel"


def test_food_mis_filed_into_a_drugstore_aisle_stays_ungrouped():
    """`body` still holds a few mis-filed FOODS whose names end in "Creme". A bare `creme`
    keyword would file a cooking cream and a chocolate as body care; leaving them ungrouped is
    the honest answer for a product that is in the wrong aisle to begin with."""
    assert product_group("Bioland Feine Creme zum Kochen", None, "body") == (None, None)
    assert product_group("Choceur Milchmäuse-Duo-Creme", None, "body") == (None, None)
    # ...while a genuine body cream still groups.
    assert product_group("ISANA Softcreme", None, "body")[1] == "Hautcreme"
