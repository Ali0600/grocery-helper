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
    # `other` is the classifier's fallback and is the one category left unmapped on
    # purpose, so nothing in it ever groups. (This assertion used to name `sweets`,
    # which is a real aisle and now has its own map.)
    assert product_group("Milka Schokolade", None, "other") == (None, None)
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
    were ever repeated — no error, just a category that stops grouping the way it did.

    The grocery set is DERIVED (`_GROCERY_GROUP_KEYS`, snapshotted at the merge site) rather
    than written out here: this test used to carry a 12-slug literal, which would have gone on
    passing while covering none of the categories added since."""
    from app.product_group import _DRUGSTORE_GROUPS, _GROCERY_GROUP_KEYS, _GROUPS
    assert not (set(_DRUGSTORE_GROUPS) & _GROCERY_GROUP_KEYS), \
        "a drugstore key shadows a grocery map"
    assert _GROCERY_GROUP_KEYS <= set(_GROUPS), "a grocery map went missing from _GROUPS"


def test_every_category_has_sub_groups():
    """RATCHET, and it only tightens. Every category the app can show should offer sub-groups,
    so a NEW category cannot ship as an unstructured flat list by accident, and a typo'd slug
    in `_GROUPS` (which would simply never fire) fails here instead of going unnoticed.

    `other` is exempt permanently: it is the classifier's fallback bucket, is driven toward
    zero offers by the weekly audit, and its contents are unclassifiable by construction.

    `STILL_TO_MAP` is the temporary half — the categories not yet worked through. Both
    directions bite: a category outside the list that loses its map fails, and an entry that
    HAS been mapped fails as stale, so finishing one forces its removal here."""
    from app.categories import CATEGORIES
    from app.product_group import _GROUPS

    UNGROUPABLE = {"other"}
    STILL_TO_MAP: set[str] = set()

    missing = set(CATEGORIES) - set(_GROUPS) - UNGROUPABLE - STILL_TO_MAP
    assert not missing, f"categories with no sub-groups: {sorted(missing)}"

    orphans = set(_GROUPS) - set(CATEGORIES)
    assert not orphans, f"_GROUPS keys that are not categories: {sorted(orphans)}"

    assert UNGROUPABLE.isdisjoint(_GROUPS), "`other` is mapped; drop it from UNGROUPABLE"
    done = STILL_TO_MAP & set(_GROUPS)
    assert not done, f"now mapped — remove from STILL_TO_MAP: {sorted(done)}"
    unknown = (STILL_TO_MAP | UNGROUPABLE) - set(CATEGORIES)
    assert not unknown, f"exemption names a category that does not exist: {sorted(unknown)}"


def test_a_group_label_the_catalog_already_covers_is_spelled_its_way():
    """Mobile's `basketResolve.subGroupItem` maps a group LABEL onto a `GROCERY_CATALOG` item
    by exact equality (against the German name, then against each keyword), and a hit wins
    because catalog entries carry `exclude` guards a synthesized `grp:` item has not.

    So a label that drifts from the catalog's spelling does not merely look different — it
    mints a second basket item for a product the catalog already has, and the same thing
    occupies two rows. "Müsli & Cerealien" would do exactly that; "Müsli" does not.

    The catalog lives in mobile/, so this pins the backend half: these exact strings must
    survive any relabelling here."""
    from app.product_group import _GROUPS

    # (category, label) -> the GROCERY_CATALOG entry it has to keep matching.
    catalog_backed = {
        ("alcoholic", "Bier"): "beer.de",
        ("pantry", "Nudeln"): "pasta.de",
        ("pantry", "Reis"): "rice.de",
        ("pantry", "Mehl"): "flour.de",
        ("pantry", "Zucker"): "sugar.de",
        ("pantry", "Müsli"): "cereal.de",
        ("pantry", "Speiseöl"): "oil.keywords",
    }
    for (category, label), catalog_ref in catalog_backed.items():
        labels = [lbl for lbl, _kws in _GROUPS[category]]
        assert label in labels, (
            f"{category} lost the label {label!r}, which mobile's {catalog_ref} matches "
            f"by exact equality — renaming it duplicates the product in the Basket. "
            f"Have: {labels}"
        )


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


# --- alcoholic: grouped by DRINK TYPE ------------------------------------------
# Two thirds of these names are a bare brand with no type word at all ("Jägermeister",
# "Aperol", "Heineken"), so each type carries its brands after its type words. Every case
# below is a real name from the DB.


@pytest.mark.parametrize(
    "name,expected",
    [
        ("BITBURGER Premium Pils", "Bier"),
        ("Franziskaner Weissbier", "Bier"),
        ("Benediktiner Hell", "Bier"),
        ("Gösser Natur Radler", "Bier"),
        ("Köstritzer Schwarzbier", "Bier"),
        ("HEINEKEN Original", "Bier"),          # brand only, and "Original" holds no type word
        ("Knabe Malz", "Bier"),
        ("Dornfelder QbA, Rotwein, lieblich", "Wein"),
        ("Cantine Leuci Primitivo", "Wein"),
        ("Folonari Pinot Grigio", "Wein"),
        ("Chablis AOP", "Wein"),
        ("Gewürztraminer", "Wein"),
        ("Rotkäppchen Sekt", "Sekt & Champagner"),
        ("MOET & CHANDON Imperial, Champagner, brut", "Sekt & Champagner"),
        ("ARESTEL Cava", "Sekt & Champagner"),
        ("Mionetto Prosecco Spumante", "Sekt & Champagner"),
        ("Jameson Irish Whiskey", "Whisky"),
        ("THE MACALLEN Double Cask Highland Single Malt Scotch Whisky 12 Jahre", "Whisky"),
        ("Gorbatschow Wodka", "Wodka"),
        ("ABSOLUT Vodka", "Wodka"),
        ("Roku Gin", "Gin"),                    # trailing "Gin"
        ("GIN SUL Dry Gin/ Laranjal", "Gin"),   # leading "Gin"
        ("Havana Club Añejo 3 Años", "Rum"),
        ("POTT Rum", "Rum"),
        ("Jägermeister", "Likör"),
        ("Eckes Edler Eierlikör", "Likör"),
        ("Pallini Limoncello", "Likör"),
        ("Aperol", "Aperitif"),
        ("MARTINI Bianco", "Aperitif"),
        ("Gracioso Hugo", "Aperitif"),
        ("Sierra Tequila Blanco", "Spirituosen"),
        ("Echter Nordhäuser Doppelkorn", "Spirituosen"),
        ("PIRCHER Mirabellen Edelbrand", "Spirituosen"),
        ("Ouzo Plomari", "Spirituosen"),
        ("Somersby Cider", "Cider & Fruchtwein"),
        ("Kelterei Heil Cidre", "Cider & Fruchtwein"),
    ],
)
def test_alcoholic_groups_by_drink_type(name, expected):
    assert product_group(name, None, "alcoholic")[1] == expected


@pytest.mark.parametrize(
    "name",
    [
        "Jack Daniel's Dosen",
        "Jack Daniel’s Coca-Cola",
        "Jim Beam Bourbon Whiskey & Cola",
        "Three Sixty Dosen",
        "Smirnoff Ice Vodka",
        "Karlsberg Mixery Bier+Cola",
        "Gorbatschow Premixed Longdrink Lemon",
        "Maelt Hard Seltzer",
        "Cocktail Ready To Serve Cosmopolitan",
    ],
)
def test_a_premixed_can_is_not_the_bottle_it_is_named_after(name):
    """A 0,33 l can of "Jack Daniel's Cola" is not a substitute for a bottle of Jack Daniel's,
    so ranking them together answers the wrong question — the same form-not-brand argument the
    coffee map makes for capsules vs beans.

    Mixgetränke therefore runs FIRST, ahead of every spirit and beer brand below it. Sabotage:
    move that tuple to the end of the alcoholic list and each of these lands in Whisky / Wodka
    / Bier instead."""
    assert product_group(name, None, "alcoholic")[1] == "Mixgetränke"


def test_a_liqueur_that_merely_names_a_spirit_is_not_that_spirit():
    """"whisky" fires inside "WhiskyGESCHMACK". These two are liqueurs that name a whisky
    flavour, which is a designation-vs-ingredient distinction, so Likör must run before
    Whisky. Sabotage: swap the two tuples and both become Whisky."""
    assert product_group("FIREBALL Likör mit Zimt- und Whiskygeschmack", None,
                         "alcoholic")[1] == "Likör"
    assert product_group("IRISH MIST Honig Whiskey Liqueur", None, "alcoholic")[1] == "Likör"
    # ...while a real whisky is untouched.
    assert product_group("Jack Daniel's Tennessee Whiskey", None, "alcoholic")[1] == "Whisky"


@pytest.mark.parametrize(
    "name,expected,why",
    [
        ("Werder Fruchtweine", "Cider & Fruchtwein", "'fruchtwein' contains 'wein'"),
        ("ARMILAR Portwein Late Bottled Vintage 2020", "Wein", "'portwein' contains 'wein'"),
        ("Salitos Tequila Beer", "Bier", "'tequila' would claim a tequila-flavoured beer"),
        ("Chandon Garden Spritz", "Aperitif", "'chandon' is a Sekt brand, 'spritz' wins"),
        ("Aperol Aperitif Bitter", "Aperitif", "'bitter' would claim it for Likör"),
    ],
)
def test_alcoholic_ordering_is_part_of_the_mapping(name, expected, why):
    got = product_group(name, None, "alcoholic")[1]
    assert got == expected, f"{name!r} -> {got!r}, expected {expected!r} because {why}"


def test_gin_and_rum_tokens_are_space_guarded():
    """"gin" sits inside "oriGINal" and "rum" inside "tRUMpf", so neither token is bare — the
    pair " gin"/"gin " catches the word at either end of a name without catching the compound.
    Sabotage: replace them with a bare "gin" and the first two assertions below flip to Gin."""
    assert product_group("Havana Club Original", None, "alcoholic")[1] == "Rum"
    assert product_group("DESPERADOS Original", None, "alcoholic")[1] == "Bier"
    assert product_group("Gordon's London Dry Gin", None, "alcoholic")[1] == "Gin"


# --- pantry: the dry-goods shelf -----------------------------------------------


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Bertolli Olivenöl", "Speiseöl"),
        ("Hengstenberg Balsamico Bianco", "Essig"),
        ("Heinz Tomato Ketchup", "Ketchup"),
        ("Bautz'ner Senf", "Senf"),
        ("Kunella Feinkost Delikatess-Mayonnaise", "Mayonnaise & Dressing"),
        ("Barilla Pesto", "Pesto"),
        ("Maggi Delikatess-Saucen", "Sauce"),
        ("Landliebe Konfitüre", "Konfitüre"),
        ("Deluxe Manuka Honig", "Honig"),
        ("Zentis Nusspli", "Nussmus & Creme"),
        ("Knorr Fix Spaghetti Bolognese", "Fix & Instant"),
        ("Barilla Italienische Teigwaren", "Nudeln"),
        ("Steinhaus Tortelloni", "Nudeln"),
        ("GUT&GÜNSTIG Langkorn-Spitzenreis", "Reis"),
        ("Kölln Blütenzarte Haferflocken", "Müsli"),
        ("EDEKA Herzstücke Antipasti", "Feinkost-Salate"),
        ("MYVAY Grilltofu", "Tofu & Fleischersatz"),
        ("EDEKA Bio Kichererbsen", "Konserven"),
        ("Erasco 1-Portions-Eintöpfe", "Eintopf & Suppe"),
        ("Back Family Natron XXL", "Backzutaten"),
        ("Diamant Weizenmehl Extra Type 405 XXL", "Mehl"),
        ("GUT&GÜNSTIG Feiner Raffinadezucker", "Zucker"),
        ("Bad Reichenhaller Alpen Jodsalz", "Gewürze"),
    ],
)
def test_pantry_groups_by_product(name, expected):
    assert product_group(name, None, "pantry")[1] == expected


@pytest.mark.parametrize(
    "name,expected,why",
    [
        ("Bio-Zuckermais", "Konserven", "'zucker' would sell sweetcorn as a bag of sugar"),
        ("Noa Hummus Dattel-Curry", "Feinkost-Salate", "'curry' would file hummus as a spice"),
        ("Eigene Herstellung Bohnensalat", "Feinkost-Salate", "'bohnen' would tin a deli salad"),
        ("Knorr Salat Krönung", "Mayonnaise & Dressing", "'salat' would make a sachet a salad"),
        ("EDEKA Herzstücke Ölspray", "Speiseöl", "Konserven's 'oliven' must not precede oils"),
        ("EDEKA Bio Grüne Oliven", "Konserven", "...while real olives still reach Konserven"),
        ("Bautz’ner fix Tomatensoße", "Sauce", "Konserven's 'tomaten' must not beat a sauce"),
        ("Knorr Asia Noodles Chicken Taste", "Fix & Instant", "a cup noodle is not dry pasta"),
        ("Miracel Whip Salatcreme Original", "Mayonnaise & Dressing",
         "'creme' would send a salad cream to the spreads"),
    ],
)
def test_pantry_ordering_is_part_of_the_mapping(name, expected, why):
    got = product_group(name, None, "pantry")[1]
    assert got == expected, f"{name!r} -> {got!r}, expected {expected!r} because {why}"


def test_hefe_is_not_a_bare_token_in_backzutaten():
    """"hefe" sits inside Hefezopf, Hefe-Röllchen and Hefeweizen, none of which is a baking
    ingredient — so Backzutaten spells out the actual products. Sabotage: add a bare "hefe"
    and the pastry below becomes a baking ingredient."""
    assert product_group("Pagen Gifflar Hefe-Röllchen", None, "pantry") == (None, None)
    assert product_group("Dr. Oetker Trockenhefe", None, "pantry")[1] == "Backzutaten"


def test_a_bread_mis_filed_into_pantry_stays_ungrouped():
    """The classifier currently files a handful of in-store bakery breads under pantry (a
    known, separately-tracked bug). Adding bread keywords HERE would paper over it and make
    the mis-classification invisible, so they stay ungrouped — the honest answer for a product
    that is in the wrong aisle to begin with."""
    assert product_group("EDEKA Bio Kräuterröpfe", None, "pantry") == (None, None)
    assert product_group("ÖLZ Mohnstrudel", None, "pantry") == (None, None)


# --- the remaining food categories ---------------------------------------------


@pytest.mark.parametrize(
    "category,name,expected",
    [
        # sweets — grouped by confection type, not by brand.
        ("sweets", "FIN CARRÉ Tafelschokolade", "Schokolade"),
        ("sweets", "Ritter Sport Alpenmilch", "Schokolade"),
        ("sweets", "Mars Snickers", "Riegel"),
        ("sweets", "Storck Knoppers", "Riegel"),
        ("sweets", "De Beukelaer Prinzenrolle", "Kekse"),
        ("sweets", "Amicelli Waffelröllchen", "Waffeln"),
        ("sweets", "Haribo Fruchtgummi", "Fruchtgummi & Lakritz"),
        ("sweets", "Chupa Chups Lutscher", "Bonbon & Lutscher"),
        ("sweets", "WRIGLEY’S Extra Plus Kaugummi", "Kaugummi"),
        ("sweets", "Ferrero Raffaello", "Pralinen"),
        ("sweets", "Deluxe Baklava Pistazie", "Kuchen & Gebäck"),
        ("sweets", "Nudossi Nuss-Nougat-Creme", "Nuss-Nougat-Creme"),
        # ice_cream — grouped by FORM, like coffee.
        ("ice_cream", "EDEKA Herzstücke Stieleis", "Stieleis"),
        ("ice_cream", "Langnese Magnum", "Stieleis"),
        ("ice_cream", "Langnese Cornetto Classic", "Hörnchen"),
        ("ice_cream", "BON GELATI Sandwich-Eis XXL", "Sandwich-Eis"),
        ("ice_cream", "Little Moons Mochi Ice", "Mochi"),
        ("ice_cream", "Sun Lolly Wassereis", "Wassereis"),
        ("ice_cream", "KULJANKA Eistorte", "Eistorte & Dessert"),
        ("ice_cream", "Ferrero Ice-Cream-Multipack", "Multipack"),
        ("ice_cream", "Langnese Cremissimo", "Eiscreme"),
        # frozen
        ("frozen", "Wagner Steinofen Pizza", "Pizza"),
        ("frozen", "McCain Western Fries", "Pommes"),
        ("frozen", "Iglo Fischstäbchen", "Fisch"),
        ("frozen", "Iglo Rahm-Spinat", "Gemüse"),
        ("frozen", "EDEKA Bio Erdbeeren", "Beeren & Obst"),
        # vegan — grouped by the food each product REPLACES.
        ("vegan", "Oatly Haferdrink", "Pflanzendrink"),
        ("vegan", "Billie Green Vegane Bratwurst", "Fleischalternative"),
        ("vegan", "Bedda Vegane Scheiben", "Käsealternative"),
        ("vegan", "REWE Bio pflanzlich Sojagurt Natur", "Joghurtalternative"),
        ("vegan", "Vemondo Veganer Bio Brotaufstrich", "Aufstrich"),
        # butter / ready_meals / other_meat / eggs
        ("butter", "Landliebe Butter", "Butter"),
        ("butter", "Lätta Original", "Margarine"),
        ("butter", "Meggle Kräuter-Butter", "Kräuterbutter"),
        ("ready_meals", "Sushi4You Sushi", "Sushi"),
        ("ready_meals", "BÜRGER Maultaschen", "Maultaschen"),
        ("ready_meals", "Popp Meistersalat Eiersalat", "Salat"),
        ("ready_meals", "iglo Fertiggerichte", "Fertiggericht"),
        ("other_meat", "Lammkeule in Scheiben", "Lamm"),
        ("other_meat", "OLIVIA Ganzes Kaninchen", "Kaninchen"),
        ("eggs", "GUT&GÜNSTIG Eier", "Eier"),
    ],
)
def test_the_remaining_food_categories_group(category, name, expected):
    assert product_group(name, None, category)[1] == expected


@pytest.mark.parametrize(
    "category,name,expected,why",
    [
        ("sweets", "Kaugummistange", "Kaugummi",
         "'gummi' is inside 'KAUgummi', so Kaugummi must run before Fruchtgummi"),
        ("sweets", "Choceur Waffelriegel", "Riegel",
         "'waffel' would claim a bar that happens to be a wafer"),
        ("sweets", "Schwartau Corny Schoko", "Riegel",
         "'schoko' would claim a muesli bar for the chocolate shelf"),
        ("sweets", "Nutella-Muffin", "Kuchen & Gebäck",
         "Kuchen runs before the spread, so a muffin is not a jar of Nutella"),
        ("sweets", "Ferrero Nutella Biscuits", "Kekse",
         "...and so does Kekse"),
        ("ice_cream", "Fruity Sticks Mango", "Wassereis",
         "'sticks' would file a water ice as a Stieleis"),
        ("butter", "Rama mit Butter XXL", "Margarine",
         "'butter' is in the name of a margarine"),
        ("butter", "Kerrygold Kräuterbutter oder Original Irische Butter", "Kräuterbutter",
         "the specific spread must beat the generic block"),
        ("frozen", "Dermaris Pizza-Brötchen Mozzarella-Kräuterbutter", "Pizza",
         "'brötchen' would file a pizza roll as bread"),
        ("vegan", "Rügenwalder Vegane Mühlen BBQ-Filets oder Rostbratwürstchen",
         "Fleischalternative", "the meat words must outrank nothing else here"),
    ],
)
def test_the_remaining_categories_ordering_is_part_of_the_mapping(category, name, expected, why):
    got = product_group(name, None, category)[1]
    assert got == expected, f"{name!r} -> {got!r}, expected {expected!r} because {why}"


def test_the_feeds_own_spelling_variants_are_covered():
    """Three stems that look right and match nothing. Each was found by diffing against the
    real DB, never by reading the table."""
    # "mühle" not "mühlen" — the feed ships both.
    assert product_group("Rügenwalder Mühle Veganer Schinkenspicker", None,
                         "vegan")[1] == "Fleischalternative"
    # Kærgården appears with æ, ae and a.
    for spelling in ("Arla Kærgården", "Arla Kaergarden Butter", "ARLA Kærgården XXL"):
        assert product_group(spelling, None, "butter")[1] == "Butter", spelling
    # "Multiplack" is the feed's own typo and it ships that spelling every week.
    assert product_group("Schöller Multiplack-Eis", None, "ice_cream")[1] == "Multipack"


def test_eis_is_never_a_bare_token():
    """A bare "eis" sits inside Reis, Fleisch and Eiweiß. The category gate makes that
    survivable but not safe, so Eiscreme carries the three affixed forms instead. Sabotage:
    replace them with a bare "eis" — this still passes, which is the point of pinning the
    ungrouped case below it."""
    assert product_group("Langnese Cremissimo Eis", None, "ice_cream")[1] == "Eiscreme"
    assert product_group("Schöller Multiplack-Eis", None, "ice_cream")[1] == "Multipack"
    # A name with no ice-cream word at all stays ungrouped rather than being swept up.
    assert product_group("Deluxe Pistazien-Drink", None, "ice_cream") == (None, None)


# --- household: the non-food catch-all -----------------------------------------
# The discounters' own brands are the most reliable signal here, but they run in a SECOND
# pass so that what a thing IS always beats who made it.


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Tempo Taschentücher Box", "Papier & Hygiene"),
        ("NOVITESSE Renforcé-Spannbetttuch", "Bettwaren"),
        ("T-Shirt mit Tulpen-Muster & Ripp-Struktur, beige, Gr. 110, 1 St", "Kleidung & Schuhe"),
        ("UP2FASHION Slipper", "Kleidung & Schuhe"),
        ("Tefal Pfannenset", "Küche & Geschirr"),
        ("SILVERCREST Premium-Espressomaschine", "Küche & Geschirr"),
        ("PARKSIDE Zug-/Kapp- und Gehrungssäge", "Werkzeug"),
        ("AMBIANO Mini-Bluetooth-Lautsprecher", "Elektronik"),
        ("GARDENLINE Lavendel", "Garten & Pflanzen"),
        ("LUPILU PAW Patrol Spielzelt", "Spielzeug"),
        ("ULTIMATE SPEED Kindersitzerhöhung", "Auto & Fahrrad"),
        ("Domestos Aktiv Kraft WC-Gel", "Reinigung"),
        ("HOME CREATION Duftkerze Verbena & Citronella", "Wohnen & Deko"),
        ("Pritt Stick", "Schreibwaren & Büro"),
        ("Zalando Geschenkkarte", "Reisen & Erlebnis"),
    ],
)
def test_household_groups_by_aisle(name, expected):
    assert product_group(name, None, "household")[1] == expected


@pytest.mark.parametrize(
    "name,expected,why",
    [
        ("CRIVIT Wendejacke", "Kleidung & Schuhe",
         "the garment noun must beat the sport brand"),
        ("CRIVIT Fahrrad-Helm mit Rücklicht", "Auto & Fahrrad",
         "...and so must the bike noun"),
        ("CRIVIT Funktionstop", "Sport & Freizeit",
         "...while the brand still catches what no noun claimed"),
        ("LIVARNO 4-Jahreszeiten-Steppbett", "Bettwaren",
         "'livarno' would file bedding as decor"),
        ("LIVARNO Textil-Kleiderschrank", "Wohnen & Deko",
         "'kleid' is inside 'KLEIDerschrank' — a wardrobe is furniture"),
        ("LIVARNO Bett-Tablett", "Küche & Geschirr",
         "'tablet' is inside 'TABLETt' — a bed tray is not a computer"),
        ("CRIVIT Sportbrille mit Wechselgläsern", "Sport & Freizeit",
         "a bare 'gläser' would file sports glasses as drinkware"),
        ("AMBIANO Mini-Kontaktgrill", "Küche & Geschirr",
         "a contact grill is a kitchen appliance, not a barbecue"),
        ("Bepflanzte Zinkschale", "Küche & Geschirr",
         "'schal' must not fire inside 'SCHALE' — the clothing token is plural-guarded"),
    ],
)
def test_household_head_nouns_beat_the_brand_that_made_it(name, expected, why):
    got = product_group(name, None, "household")[1]
    assert got == expected, f"{name!r} -> {got!r}, expected {expected!r} because {why}"


@pytest.mark.parametrize(
    "name,expected",
    [
        # Each of these carries NO head noun from any aisle — the brand is the only signal,
        # so only the second pass can place them. An earlier version of this test used
        # "PARKSIDE Absperrkette", which the Werkzeug NOUN "absperr" already catches: it
        # therefore never reached the brand pass and the test proved nothing (the sabotage
        # harness reported it NOT-CAUGHT, which is how this was found).
        ("PARKSIDE Akku-Kombi-gerät", "Werkzeug"),
        ("ULTIMATE SPEED Autozubehör", "Auto & Fahrrad"),
        ("SilverCrest Pasta-Maschine", "Küche & Geschirr"),
        ("LIVARNO home Folienballon/Partyartikel", "Wohnen & Deko"),
    ],
)
def test_the_household_brand_fallback_pass_places_what_no_noun_claimed(name, expected):
    """The map lists several labels TWICE — once with head nouns, once with brand tokens far
    below. That split is what makes "what it IS beats who made it" expressible in a flat
    first-hit-wins table, and a repeated label is the same slug, so both tuples feed one
    group. Sabotage: rename the brand tuple's label and these stop matching."""
    assert product_group(name, None, "household")[1] == expected


def test_the_household_brand_pass_introduces_no_new_group():
    """A brand tuple must reuse a label the head-noun pass already defines. A typo'd one
    would silently create a second, near-duplicate section in the deals list."""
    from app.product_group import _GROUPS
    labels = [lbl for lbl, _kws in _GROUPS["household"]]
    repeated = {lbl for lbl in labels if labels.count(lbl) > 1}
    assert repeated, "the brand-fallback pass is gone; head nouns no longer outrank brands"
    # Every label after the first repeat must have appeared before it.
    first_repeat = next(i for i, lbl in enumerate(labels) if lbl in labels[:i])
    for i, lbl in enumerate(labels[first_repeat:], start=first_repeat):
        assert lbl in labels[:i], f"{lbl!r} appears only in the fallback pass"


def test_cosmetics_and_food_mis_filed_into_household_stay_ungrouped():
    """This chip still holds ~63 cosmetics that belong in the drugstore aisles and ~62 edible
    products the source hangs off a non-food node. Both are tracked classifier findings.
    Adding tokens for them HERE would paper over the mis-classification and make it invisible
    — the same call the pantry map makes for the in-store breads."""
    for name in ("Nivea Q10 Anti-Falten Power", "Colgate Total", "Taft Schaumfestiger"):
        assert product_group(name, None, "household") == (None, None), name
    for name in ("GUT&GÜNSTIG Mozzarella", "BABYBEL 9er-Netz", "Frische Schweine Schälrippe"):
        assert product_group(name, None, "household") == (None, None), name
    # "SonnenBLUMEnkerne" is the reason Garten carries no bare "blume" token. That guard is
    # also what keeps a flower-PATTERNED garment out of the flower bed — the clothing nouns
    # would win anyway, so THIS is the assertion that bites, not an ordering one.
    assert product_group("EDEKA Bio Sonnenblumenkerne", None, "household") == (None, None)
    assert product_group("Duftkerze im Glas mit Blumen, 1 St", None,
                         "household")[1] == "Wohnen & Deko"


# --- deepening the maps that already existed ------------------------------------
# Unlike a brand-new category map, these CAN regress: a new token here sits alongside
# tokens that already place products. Every case below is a real DB name that was
# ungrouped before, paired with the sibling that must not move.


@pytest.mark.parametrize(
    "category,name,expected",
    [
        ("cheese", "Philadelphia Original", "Frischkäse"),
        ("cheese", "Gervais Hüttenkäse", "Frischkäse"),
        ("cheese", "EDEKA Bio Hirtenkäse", "Feta"),
        ("cheese", "Kerrygold Cheddar herzhaft", "Cheddar"),
        ("cheese", "Bergader Watzmann Bergkäse", "Bergkäse"),
        ("cheese", "MILBONA Halloumi Grillkäse", "Halloumi & Grillkäse"),
        ("cheese", "Old Amsterdam", "Käse"),
        ("dairy", "Danone Actimel Drink", "Joghurt"),
        ("dairy", "Ehrmann Grand Dessert", "Dessert"),
        ("dairy", "Müller Ayran", "Milchgetränk"),
        ("pork", "Bauerngut Spareribs", "Spareribs"),
        ("pork", "Duroc Schweine-Filet", "Filet"),
        ("pork", "Schweine-rückensteak mariniert", "Steak"),
        ("pork", "GUT&GÜNSTIG Schweine-Cordon-Bleu", "Cordon Bleu"),
        ("pork", "SOL & MAR Jamón Serrano", "Luftgetrocknetes"),
        ("soft_drinks", 'Kräutertee "Chamomile" (20 Beutel), 40 g', "Tee"),
        ("soft_drinks", "San Pellegrino", "Wasser"),
        ("soft_drinks", "GUT&GÜNSTIG Getränkesirup", "Sirup"),
        ("bakery", "Harry Sandwich", "Sandwich & Wrap"),
        ("bakery", "GUT&GÜNSTIG Bienenstich", "Feingebäck"),
        ("bakery", "LYTTOS Zwieback", "Feingebäck"),
        ("poultry", "Chicken Nuggets", "Nuggets & Paniertes"),
        ("poultry", "Gutfried Geflügel-Aufschnitt", "Geflügelwurst"),
        ("fish", "Deutsche See Crevetten", "Meeresfrüchte"),
        ("fish", "SOL & MAR Tintenfisch", "Meeresfrüchte"),
        ("fish", "EDEKA Herzstücke Pazifische Schollenfilets", "Scholle"),
    ],
)
def test_deepened_maps_place_what_used_to_fall_through(category, name, expected):
    assert product_group(name, None, category)[1] == expected


@pytest.mark.parametrize(
    "category,name,expected,why",
    [
        ("cheese", "Rougette Ofenkäse fein-würzig", "Käse",
         "an Ofenkäse is a soft BAKING cheese, not a firm grilling one"),
        ("bakery", "Fladenbrot mit Kümmel und Sesam", "Brot",
         "a flatbread is bread, not a sandwich"),
        ("cheese", "FAIRGLOBE Bio Hochland Kaffee", None,
         "'hochland' is a cheese brand AND a word in this bag of coffee, so it is not a token"),
        ("pork", "Gut Drei Eichen Nürnberger Rostbratwürste", "Bratwurst",
         "the existing Bratwurst group must still win"),
        ("dairy", "Frische Vollmilch", "Milch",
         "the new Milchgetränk group must not claim plain milk"),
        ("soft_drinks", "VOLVIC Tee", "Tee",
         "the widened Tee tokens must not disturb the brand-after-type convention"),
    ],
)
def test_deepening_did_not_disturb_what_was_already_right(category, name, expected, why):
    got = product_group(name, None, category)[1]
    assert got == expected, f"{name!r} -> {got!r}, expected {expected!r} because {why}"


def test_hochland_is_deliberately_not_a_cheese_brand_token():
    """Every other big cheese brand is a token here; Hochland is not, because "FAIRGLOBE Bio
    HOCHLAND Kaffee" is a bag of coffee the classifier files into this chip. Adding it would
    put coffee in the cheese aisle's generic group. Its own product still resolves — via
    "patros", the sub-brand, which names an actual cheese."""
    assert product_group("FAIRGLOBE Bio Hochland Kaffee", None, "cheese") == (None, None)
    assert product_group("Hochland Patros", None, "cheese")[1] == "Feta"
