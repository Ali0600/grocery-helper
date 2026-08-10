"""Categorization guards against real-world miscategorizations.

Cases drawn from a live Lidl Berlin snapshot where the old name-only classifier
misfired (a flavour/brand word won over the real category).
"""
import pytest

from app.categories import (
    _DRUGSTORE_PATH_MAP,
    _DRUGSTORE_RULES,
    BRAND_CATEGORY,
    CATEGORIES,
    DRUGSTORE_CATEGORIES,
    classify,
)


@pytest.mark.parametrize(
    "name, brand, expected",
    [
        # --- regressions fixed by the brand map / overrides ---
        ("Allini Hugo Frizzante Mango", "ALLINI", "alcoholic"),  # sekt, not fruit
        ("Allini Rhabarber-Erdbeer Secco", "ALLINI", "alcoholic"),
        ("Mister Choc Milch Freunde", "MISTER CHOC", "sweets"),  # chocolate, not dairy
        ("Iglo Rahm-Spinat", "IGLO", "frozen"),  # frozen brand, not veg
        # --- things that must keep working ---
        ("Milbona Käse am Stück", "MILBONA", "cheese"),
        ("Metzgerfrisch Puten-Hacksteaks", "METZGERFRISCH", "poultry"),
        ("Frisches Rinderhackfleisch", None, "beef"),
        ("Deutsche Markenbutter", "Milbona", "butter"),
        ("Ehrmann Almighurt", "EHRMANN", "dairy"),
        ("Valensina Saft/Nektar", "VALENSINA", "soft_drinks"),
        ("PARKSIDE Akku-Bohrschrauber", "PARKSIDE", "household"),
        # --- flyer-catalog keyword expansion ---
        ("DELUXE Irisches Angus Rumpsteak", "DELUXE", "beef"),
        ("Sol & Mar Chorizo Klassik", "Sol & Mar", "pork"),
        ("Dulano Delikatess Bacon", "Dulano", "pork"),
        ("Gelatelli Premium Stieleis", "Gelatelli", "ice_cream"),
        ("Ferrero Hanuta", "Ferrero", "sweets"),
        ("Moët & Chandon Impérial Champagner", "Moët & Chandon", "alcoholic"),
        ("Milbona Edamer", "Milbona", "cheese"),
        ("TRONIC Standventilator", "TRONIC", "household"),
        # --- substring / flavour-word regressions caught in review ---
        ("Frisches Schweinegulasch", None, "pork"),  # not beef ("gulasch")
        ("Metzgerfrisch Schweine-Nackensteak", None, "pork"),  # not beef ("steak")
        ("Volvic Touch Zitrone Limette", "Volvic", "soft_drinks"),  # "limette" != Mett
        ("Lipton Ice Tea Pfirsich", "Lipton", "soft_drinks"),  # not fruit ("pfirsich")
        ("Trumpf Schogetten Freeze Mango", "Trumpf", "sweets"),  # not fruit ("mango")
        ("Häagen-Dazs Belgian Chocolate", "Häagen-Dazs", "ice_cream"),  # ice cream, not sweets
        # --- ice cream split out of frozen ---
        ("Langnese Cremissimo Vanille", "Langnese", "ice_cream"),
        ("Bon Gelati Wassereis", "Bon Gelati", "ice_cream"),  # "wassereis" (contains "reis"!) is ice cream
        ("Snickers Ice Cream", None, "ice_cream"),  # beats the snickers->sweets rule
        ("Mövenpick Zitronensorbet", "Mövenpick", "ice_cream"),
        # --- savoury frozen stays frozen; "eis" substring traps must NOT be ice cream ---
        ("Wagner Steinofen-Pizza Salame", "Wagner", "frozen"),
        ("McCain 1-2-3 Original Fries", "McCain", "frozen"),
        ("Frisches Rindfleisch-Gulasch", None, "beef"),  # "Fleisch" contains "eis"
        ("Müller Milchreis", "Müller", "dairy"),  # "Reis" contains "eis"
        ("Pfanner Eistee Pfirsich", "Pfanner", "soft_drinks"),  # Eistee is a drink, not ice cream
        # --- vegan is its own category (cross-cutting; wins over the natural category) ---
        ("Vemondo veganes Gyros mit Zwiebeln", "VEMONDO", "vegan"),
        ("VEMONDO Pesto Basilico", "VEMONDO", "vegan"),  # Vemondo (vegan-only brand) even without "vegan"
        ("Like Meat Vegane Fleischalternative", "Like Meat", "vegan"),
        ("REWE Beste Wahl pflanzliche Bratwurst", "REWE Beste Wahl", "vegan"),  # "pflanzlich"
        ("Rama Cremefine 100% Pflanzlich", "Rama", "vegan"),
        # guards: vegetarian != vegan, and a mixed meat/vegan brand keeps its meat
        ("Vegetarische Mortadella", None, "pork"),  # "vegetarisch" must NOT trigger vegan
        ("Rügenwalder Mühle Teewurst", "Rügenwalder Mühle", "pork"),  # mixed brand, this is meat
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
        ("x", None, [_FOOD, "Produkte", "Getränke", "Alkoholische Getränke"], "alcoholic"),
        ("x", None, [_FOOD, "Produkte", "Lebensmittel", "Obst", "Kernobst"], "fruits"),
        # brand-only food path -> falls back to keyword classifier on the name
        ("Eberswalder Rostbratwurst", "Eberswalder", [_FOOD, "Marken", "Marken Lebensmittel"], "pork"),
        # a form/brand override (Vilsa water) beats a mis-filed Obst path (the source files
        # the flavoured water "Vilsa H2 Obst …" under Obst, which would otherwise -> fruits)
        ("Vilsa H2 Obst Apfel-Limette-Zitrone", "Vilsa", [_FOOD, "Produkte", "Obst"], "soft_drinks"),
        # a freeze-dried fruit snack the source files under Obst/Beeren -> snacks, not fruits
        ("TRÜFRÜ Nature’s Strawberries", "TRÜFRÜ", [_FOOD, "Produkte", "Lebensmittel", "Obst", "Beeren"], "snacks"),
    ],
)
def test_classify_with_path(name, brand, path, expected):
    assert classify(name, brand, path) == expected


# Real REWE "Dein Markt" flyer products that landed in "Other" before tuning.
_BRAND_ONLY = [_FOOD, "Marken", "Marken Lebensmittel"]  # brand-organized, no product node


@pytest.mark.parametrize(
    "name, brand, path, expected",
    [
        # path wins over a misleading brand: Kerrygold maps to butter, but the
        # taxonomy says Hartkäse -> cheese (it's sliced cheddar, not butter)
        ("Kerrygold Cheddar Käse Scheiben", "Kerrygold",
         [_FOOD, "Produkte", "Lebensmittel", "Milchprodukte", "Käse", "Hartkäse", "Cheddar"], "cheese"),
        # brand-only food paths -> brand map
        ("Mirée Französische Kräuter", "Mirée", _BRAND_ONLY, "cheese"),
        ("Leerdammer Original", "Leerdammer", _BRAND_ONLY, "cheese"),
        ("Rotkäppchen Rosé Trocken", "Rotkäppchen", _BRAND_ONLY, "alcoholic"),
        ("Deutsche See Pulpo-Arme", "Deutsche See", _BRAND_ONLY, "fish"),
        ("Katjes Fruchtgummi", "Katjes", _BRAND_ONLY, "sweets"),
        ("Lay's Gesalzen", "Lay's", _BRAND_ONLY, "snacks"),
        ("Nuii Ice Cream Salted Caramel", "Nuii", _BRAND_ONLY, "ice_cream"),
        ("Danone Frucht Zwerge", "Danone", _BRAND_ONLY, "dairy"),
        # taxonomy nodes added for the REWE catalog
        ("Choi's Bibimmyoen Carbonara", "Choi's",
         [_FOOD, "Produkte", "Lebensmittel", "Beilagen", "Teigwaren", "Nudeln"], "pantry"),
        ("Kölln Hafer-Porridge", "Kölln",
         [_FOOD, "Produkte", "Lebensmittel", "Cerealien", "Haferbrei", "Porridge"], "pantry"),
        ("Salzgebäck", None, [_FOOD, "Produkte", "Lebensmittel", "Knabberzeug", "Salzgebäck"], "snacks"),
        ("Barebells Soft Protein Bar", "Barebells",
         [_FOOD, "Produkte", "Lebensmittel", "Proteinprodukte", "Proteinriegel"], "snacks"),
        # keyword-only (no usable path): German/English beer + product words
        ("Estrella Damm Spanisches Lagerbier", "Estrella Damm", None, "alcoholic"),
        ("Radeberger Pilsner", "Radeberger", None, "alcoholic"),
        ("REWE Beste Wahl Limetten", "REWE Beste Wahl", None, "fruits"),
        ("Followfood Bio Carbonara Style Noodles", "followfood", _BRAND_ONLY, "pantry"),
        ("Butcher's Burger Buns Lauge", "Butcher's Burger", _BRAND_ONLY, "bakery"),
        ("Butcher's Burger Smash Burger Patties", "Butcher's Burger", _BRAND_ONLY, "beef"),
    ],
)
def test_classify_rewe_flyer(name, brand, path, expected):
    assert classify(name, brand, path) == expected


@pytest.mark.parametrize(
    "name, brand, expected",
    [
        # --- EDEKA flyer products that landed in "Other" before tuning ---
        ("Wiesenhof Bruzzzler", "Wiesenhof", "poultry"),          # brand
        ("Steinhaus Original Krustenbraten", "Steinhaus", "pork"),
        ("Citterio Italienische Mortadella", "Citterio", "pork"),
        ("Hein Original Pastrami New York", "Hein", "pork"),      # keyword "pastrami"
        ("Houdek Kabanos", "Houdek", "pork"),
        ("Bauern Gut Spareribs", "Bauern Gut", "pork"),
        ("Schäfer's Delikatess Plunder", "Schäfer's", "bakery"),  # brand
        ("EDEKA Herzstücke 8 Protein-Wraps", "EDEKA", "bakery"),  # keyword "wrap"
        ("Gut&Günstig Blätterteig-Vanillestange", "Gut&Günstig", "bakery"),
        ("Alnatura Bio Penne, Fusilli oder Spaghetti", "Alnatura", "pantry"),
        ("EDEKA Bio My Veggie Falafel", "EDEKA Bio", "pantry"),
        ("Mövenpick Edle Komposition", "Mövenpick", "ice_cream"),  # ice cream brand
        ("Frosta Pollack Filets", "Frosta", "frozen"),  # a plain frozen item (Fertiggerichte moved to ready_meals)
        ("McCain Pickers", "McCain", "frozen"),
        ("Hochland Sandwich Scheiben", "Hochland", "cheese"),
        ("Trolli Fruchtgummi", "Trolli", "sweets"),
        ("Nescafé frappé", "Nescafé", "coffee"),
        ("Chio Dip!", None, "snacks"),                            # brand in name
        ("EDEKA zuhause Holzkohle", "EDEKA zuhause", "household"),
        ("Gut & Günstig Grillbriketts", "Gut & Günstig", "household"),
        # --- non-regression guards for the new keywords ---
        ("Original Elsässer Flammkuchen", None, "bakery"),  # " lamm" must NOT catch Fla(mm)kuchen
        ("Müllermilch Erdbeere", "Müller", "dairy"),        # "müll*" must NOT catch Müller
    ],
)
def test_classify_edeka_flyer(name, brand, expected):
    assert classify(name, brand) == expected


@pytest.mark.parametrize(
    "path, expected",
    [
        # real taxonomy nodes added from the live survey (the leaf is often a brand, so
        # the *intermediate* node carries the category)
        ([_FOOD, "Produkte", "Lebensmittel", "Würzmittel"], "pantry"),
        ([_FOOD, "Produkte", "Lebensmittel", "Salatdressing"], "pantry"),
        ([_FOOD, "Produkte", "Getränke", "Wasser"], "soft_drinks"),
        ([_FOOD, "Produkte", "Getränke", "Schaumwein"], "alcoholic"),
        ([_FOOD, "Marken", "Marken Getränke", "Softdrinkmarken"], "soft_drinks"),
        ([_FOOD, "Produkte", "Lebensmittel", "Melone"], "fruits"),
        ([_FOOD, "Produkte", "Lebensmittel", "Zwiebeln"], "vegetables"),
        ([_FOOD, "Produkte", "Lebensmittel", "Weißbrot"], "bakery"),
        ([_FOOD, "Produkte", "Lebensmittel", "Ciabatta"], "bakery"),
        ([_FOOD, "Produkte", "Lebensmittel", "Fleisch", "Leberwurst"], "pork"),
        ([_FOOD, "Produkte", "Lebensmittel", "Fisch", "Räucherlachs"], "fish"),
        ([_FOOD, "Produkte", "Lebensmittel", "Vegane Lebensmittel", "Veganes Schnitzel"], "pantry"),
        ([_FOOD, "Produkte", "Lebensmittel", "Baked Beans"], "pantry"),
    ],
)
def test_classify_expanded_paths(path, expected):
    assert classify("x", None, path) == expected


@pytest.mark.parametrize(
    "name, brand, expected",
    [
        # new single-category brands
        ("Knorr Fix für Spaghetti Bolognese", "Knorr", "pantry"),
        ("Harry Grillkruste", "Harry", "bakery"),
        ("Wasa Original Sesam", "Wasa", "snacks"),
        ("Saint Agur Blauschimmel", "Saint Agur", "cheese"),
        ("Becel Original", "Becel", "butter"),
        ("Rapso Reines Rapsöl", "Rapso", "pantry"),
        ("Nestlé PURINA ONE Adult", None, "household"),
        # new keywords (no usable path -> name only)
        ("Grapefruit rosa", None, "fruits"),
        ("Kohlrabi", None, "vegetables"),
        ("Burrata di Bufala", None, "cheese"),
        ("Bürger Schupfnudeln", "Bürger", "pantry"),  # Maultaschen moved to ready_meals; plain noodles stay pantry
        ("EDEKA Bio Smoothie", "EDEKA Bio", "soft_drinks"),
        ("Costa Pacific Prawns", "Costa", "fish"),
        ("Kalbs-Hals", None, "beef"),
        ("ja! Delikatess Mayonnaise", "ja!", "pantry"),
        ("Floristenstrauß der Saison", None, "household"),
        # non-regression guards: the new short tokens must not steal real categories
        ("Steinhaus Original Krustenbraten", "Steinhaus", "pork"),  # not bakery (grill/tigerkruste)
        ("Champagner Brut", None, "alcoholic"),  # "pane " must not catch it
        # fruit-flavoured items that are NOT fruit (confirmed against the product images)
        ("Bellini Pfirsich 0,0%", None, "alcoholic"),  # peach sparkling aperitif, not "pfirsich"
        ("EDEKA Herzstücke Bananenchips", "EDEKA Herzstücke", "snacks"),  # chips, not "banane"
        ("Gut&Günstig Zitronenlimonade", "Gut&Günstig", "soft_drinks"),  # lemonade, not "zitrone"
        ("Müller Froop Pfirsich-Maracuja", "Müller", "dairy"),  # yogurt, not "pfirsich"
        ("Apfelsaft naturtrüb", None, "soft_drinks"),  # juice, not "apfel"
        ("Erdbeer Joghurt", None, "dairy"),  # yogurt, not "erdbeere"
        # week-of-2026-06-23 fruit-trap fixes (confirmed against the product images)
        ("REWE Bio Mango Sorbet", "REWE Bio", "ice_cream"),  # sorbet is ice cream, not "mango"
        ("Vilsa H2 Obst Apfel-Limette-Zitrone", "Vilsa", "soft_drinks"),  # water brand, not "apfel"
        ("Bioland Bio Mini Pflaumentomaten", "Bioland", "vegetables"),  # tomato, not "pflaume"
        ("Unsere Heimat Apfelessig", "Unsere Heimat", "pantry"),  # vinegar, not "apfel"
        # guards: the new overrides must stay specific
        # CONVENTION CHANGE 2026-07-29 (user's call): preserved produce leaves the FRESH chip,
        # so a pickled gherkin is pantry now. This line previously asserted "vegetables"; it is
        # updated deliberately, not relaxed — `test_fresh_produce_is_untouched_by_the_preserved_rule`
        # pins that a loose Salatgurke still classifies as vegetables.
        ("Essiggurken", None, "pantry"),
        ("Plattpfirsiche, lose", None, "fruits"),  # real peaches unaffected by the tomato/vinegar rules
        # prepared-deli + flavour traps that aren't raw produce
        ("Popp Fleischsalat", "Popp", "ready_meals"),  # sausage-based deli salad, not "salat"
        ("HEINZ Tomatenketchup", "HEINZ", "pantry"),  # ketchup, not "tomate"
        ("Golßener Kartoffelsalat", "Golßener", "ready_meals"),  # prepared salad, not "kartoffel"
        ("Popp Kartoffel-Salat", "Popp", "pantry"),
        ("BLOCK HOUSE Brot XXL Knoblauch", "BLOCK HOUSE", "bakery"),  # garlic bread, not "knoblauch"
        ("Kühne Knoblauch", "Kühne", "pantry"),  # condiment brand, not raw garlic
        ("Zwiebelkuchen", None, "bakery"),  # onion tart -> bakery (bakery beats vegetables)
        # guards: real produce must still be produce
        ("Knoblauch", None, "vegetables"),
        ("Knoblauchzehen lose", None, "vegetables"),
        ("Kopfsalat", None, "vegetables"),
        ("Gurkensalat", None, "vegetables"),  # cucumber salad stays veg (only fleisch/kartoffel diverge)
        # real fruit must still classify as fruit
        ("Aprikosen, lose", None, "fruits"),
        ("Zespri SunGold Kiwi", "Zespri", "fruits"),
        ("Rote Äpfel", None, "fruits"),
    ],
)
def test_classify_expanded_names(name, brand, expected):
    assert classify(name, brand) == expected


# Mis-classified items surfaced by the sub-grouping work — the source path/keywords put
# them in the wrong bucket; these are the 2026-07-15 categories.py cleanup fixes. Paths are
# the real ones observed in the live feed.
_KNAB_STICKS = [_FOOD, "Produkte", "Lebensmittel", "Knabberzeug", "Sticks"]  # → "snacks" node
_GUG = [_FOOD, "Marken", "Marken Lebensmittel", "Gut & Günstig"]  # brand-only, no product node


@pytest.mark.parametrize(
    "name, brand, path, expected",
    [
        # spirits/premixed the source files under soft-drink nodes (L2 form override beats path)
        ("Havana Club Dosen", "Havana Club",
         [_FOOD, "Produkte", "Getränke", "Softdrinks", "Limonade", "Cola"], "alcoholic"),
        ("Maelt Hard Seltzer", "Maelt",
         [_FOOD, "Produkte", "Getränke", "Softdrinks", "Energydrink"], "alcoholic"),
        ("Nordhäuser Reiche Ernte Williamsbirne", "Nordhäuser",
         [_FOOD, "Marken", "Marken Getränke", "Echter Nordhäuser"], "alcoholic"),
        # a real Nordhäuser Korn stays alcoholic (regression guard for the new form word)
        ("Echter Nordhäuser Doppelkorn", "Echter Nordhäuser",
         [_FOOD, "Produkte", "Getränke", "Alkoholische Getränke", "Spirituosen", "Korn"], "alcoholic"),
        # non-snack "X Sticks" the source dumps into Knabberzeug>Sticks (L2 beats the path)
        ("GUT&GÜNSTIG Dental-Sticks", "GUT&GÜNSTIG", _KNAB_STICKS, "pet"),
        ("GUT&GÜNSTIG Chicken-Drumsticks", "GUT&GÜNSTIG", _KNAB_STICKS, "poultry"),
        # a real snack stick still classifies as snacks (the path node itself is unchanged)
        ("funny frisch Brezli", "funny frisch", _KNAB_STICKS, "snacks"),
        # Gut&Günstig house-brand lines: opaque names, no product node → pinned by keyword
        ("GUT&GÜNSTIG Hello my cat Knuspermenü", "GUT&GÜNSTIG", _GUG, "pet"),
        ("GUT&GÜNSTIG Knusperdinos", "GUT&GÜNSTIG", _GUG, "poultry"),   # Hähnchen nuggets
        ("GUT&GÜNSTIG Knusperjungs", "GUT&GÜNSTIG", _GUG, "bakery"),    # Weizenbrötchen
        # "lorenz" brand key no longer swallows "Lorenzo" (trailing-space fix) → real category
        ("Lorenzo Pizza", "Lorenzo",
         [_FOOD, "Produkte", "Lebensmittel", "Fertiggerichte", "Fast Food", "Flammkuchen"], "frozen"),
        ("Lorenz Saltletts", "Lorenz", _KNAB_STICKS, "snacks"),  # real Lorenz still snacks
        # jam brand-only path fell through to the "erdnuss" snacks keyword before the brand entry
        ("Bonne Maman Konfitüre, Gelee, Haselnuss-Kakao- oder Erdnuss-Creme", "Bonne Maman",
         [_FOOD, "Marken", "Marken Lebensmittel", "Bonne Maman"], "pantry"),
    ],
)
def test_classify_misfile_cleanup(name, brand, path, expected):
    assert classify(name, brand, path) == expected


def test_classify_name_only_still_works():
    # brand is optional
    assert classify("Tiefkühl Pizza Salami") == "frozen"


def test_unknown_is_other():
    assert classify("Zzz Quux Widget", None) == "other"


def test_every_result_is_a_known_category():
    for name in ["Bananen", "Gouda", "Cola", "Mystery item 123"]:
        assert classify(name) in CATEGORIES


# --- ALDI's items land on the brand/keyword layers ------------------------------------
# ALDI's category paths dead-end at generic nodes ("… > Marken > Marken Lebensmittel"),
# which carry no category signal — so unlike a mis-filed path this needs no _FORM_OVERRIDES
# guard, just brand/keyword coverage. This pass took ALDI from 9.4% "other" to 0.8%.
@pytest.mark.parametrize(
    "name, expected",
    [
        ("Halloren Classic", "sweets"),
        ("Storck Knoppers minis", "sweets"),
        ("Ahoj-Brause", "sweets"),                       # candy powder, not a soft drink
        ("Philadelphia", "cheese"),
        ("Eberswalder Bockwürste", "pork"),              # umlaut plural the bare "wurst" missed
        ("ALPENSCHMAUS Mini-Haxen", "pork"),
        ("GOURMET FINEST CUISINE Ganze Wachteln", "poultry"),
        ("Kresse", "vegetables"),
        ("Focaccia", "bakery"),
        ("MILSANI Kasländer Würzig", "cheese"),
        ("Trader Joe's Walnusskerne", "snacks"),
        ("Tuc Original", "snacks"),
        ("Pottkieker Beste Eintöpfe", "ready_meals"),
        ("SPEISEZEIT Leichte Suppe Gulasch-Suppe", "pantry"),
        ("Lasagne-blätter", "pantry"),
        ("Gigli", "pantry"),
        ("WORKZONE Federzwingen-Set", "household"),
        ("joie Trinkhalm-abdeckung", "household"),
        ("Profiteroles", "sweets"),
        ("Milsani Japanese Cheesecake Style", "sweets"),
    ],
)
def test_classifies_aldi_items(name, expected):
    assert classify(name, None, None) == expected


@pytest.mark.parametrize(
    "name, expected",
    [
        # "suppe " keeps its trailing space: pantry sits second-to-last, so an unguarded
        # "suppe" would swallow anything Suppen-prefixed that no earlier rule claims.
        ("GUT&GÜNSTIG Suppenhuhn", "poultry"),
        ("Rinderwurst", "beef"),          # "würst"/"wurst" must not outrank beef
        ("Geflügelwurst", "poultry"),
        ("Kalbshaxe", "beef"),            # "haxe" must not outrank beef
        ("Putenhaxe", "poultry"),
        ("Brunnenkresse", "vegetables"),
        ("Lorenzo Pizza", "frozen"),      # the "lorenz " guard still holds
    ],
)
def test_aldi_keywords_do_not_steal_from_earlier_rules(name, expected):
    assert classify(name, None, None) == expected


def test_suppe_guard_does_not_drag_suppengruen_into_pantry():
    """Suppengrün is a vegetable bundle; the space-guarded "suppe " must not claim it."""
    assert classify("Suppengrün", None, None) != "pantry"


def test_multi_category_aldi_house_brands_stay_off_the_brand_map():
    """MILSANI/Trader Joe's span categories (milk, cheese, nuts, candy), so pinning them to
    one slug would mis-file the rest — same rule as Gut&Günstig / Deluxe / Dr.Oetker."""
    for brand in ("milsani", "trader joe", "meine metzgerei", "gourmet finest cuisine"):
        assert brand not in BRAND_CATEGORY


# --- The flyer caption (Offer.unit) as a classification signal -------------------------------
# Found by auditing every category against its product IMAGES (2698 products): the name is a
# marketing string that lies — a flavour word in it steals the product — while the caption states
# the product's own designation. It was stored all along and never read.


def test_caption_beats_a_flavour_word_in_the_name():
    # "Bauer Diplomat Paprika" is a CHEESE. Its path is a brand leaf (no signal), so the bare
    # "paprika" keyword used to drag it into vegetables.
    assert classify("Bauer Diplomat Paprika", "Bauer", ["Lebensmittel und Getränke", "Marken", "Marken Lebensmittel", "Bauer"]) == "vegetables"
    assert (
        classify("Bauer Diplomat Paprika", "Bauer", ["Lebensmittel und Getränke", "Marken", "Marken Lebensmittel", "Bauer"],
                 "55% Fett i. Tr. 150g Packung")
        == "cheese"
    )


def test_caption_beats_a_MIS_FILED_source_path():
    # The source filed a turkey cold-cut under a vegetable-ish brand node and the name carries
    # "Paprikarand" — only the caption says "Geflügel-Aufschnitt".
    unit = "der leckere Geflügel-Aufschnitt mit einer feinen Paprikanote, 100 g"
    assert classify("Müller & Müller Truthahnbrust mit Paprikarand", "Müller & Müller",
                    ["Lebensmittel und Getränke", "Marken", "Marken Lebensmittel", "Müller"], unit) == "poultry"


def test_caption_resolves_the_Lachs_loin_trap():
    # "Lachs" is a German LOIN cut as well as salmon: this is cured PORK, not fish.
    assert classify("Berschneider Graved Lachsfleisch", None, None,
                    "vom Schweinerücken, in Scheiben geschnitten, gebeizt") == "pork"
    # ...and a real salmon is still fish.
    assert classify("Lachsfilet", None, None, "Norwegen, 125 g") == "fish"


def test_caption_moves_pastry_out_of_fruits():
    assert classify("GUT&GÜNSTIG Apfeldreieck", "GUT&GÜNSTIG", None,
                    "Blätterteig mit einer Füllung aus Apfelstückchen") == "bakery"


def test_poultry_sausage_beats_the_Wurstwaren_path():
    # THE biggest cluster (~20 products): "Wurstwaren > Wurst > Brühwurst" maps to pork and a path
    # beats a keyword, so poultry sausage landed in pork. Layer 2 is the only thing that can win.
    path = ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Wurstwaren", "Wurst", "Brühwurst"]
    assert classify("Gutfried Hähnchen-Fleischwurst", "Gutfried", path) == "poultry"
    assert classify("Langewiesche Putenbrust", "Langewiesche", path) == "poultry"
    # A real pork sausage under the same path is untouched.
    assert classify("Bratwurst vom Schwein", None, path) == "pork"


def test_caption_signals_are_designations_not_ingredients():
    # Deliberately rejected during the audit: a cheesecake whose caption merely mentions
    # Frischkäse, and a snack box that merely CONTAINS Schmelzkäse, must NOT become cheese.
    assert classify("Coppenrath & Wiese Lust auf Torte", "Coppenrath & Wiese", None,
                    "versch. Sorten, mit Frischkäse") != "cheese"
    assert classify("Gutfried Junior Lieblings-Snack-Box", "Gutfried", None,
                    "mit Cracker, Geflügel-Fleischwurst und Schmelzkäse") != "cheese"


def test_classify_without_a_caption_is_unchanged():
    # `unit` is optional — old callers and coupon rows with no caption keep working.
    assert classify("Bananen", None, None) == "fruits"
    assert classify("Bananen", None, None, None) == "fruits"


# --- Substring guards, multi-category brands, mis-filed drink paths -------------------------
# From the same image audit, adjudicated against every stored offer: 74 rows moved, 0 regressions.
# German compounds mean a keyword SHOULD usually fire mid-word ("Bratwurst" is pork), so a guard is
# only justified where the match is a coincidence. Each is pinned to the real product that proved
# it — and to the sibling that must survive the guard.


@pytest.mark.parametrize(
    "name, brand, expected, why",
    [
        # A "-dicksaft"/"Goldsaft" is a syrup, not a juice. The "saft " form word only pins its
        # trailing side, so "Agavendicksaft " matched it.
        ("EDEKA Bio Agavendicksaft", "EDEKA Bio", "pantry", "syrup, not juice"),
        ("Grafschafter Goldsaft", "Grafschafter", "pantry", "sugar-beet syrup"),
        ("GUT&GÜNSTIG Apfelsaft", "GUT&GÜNSTIG", "soft_drinks", "a real juice still wins"),
        ("Rauch Happy Day Saft", "Rauch", "soft_drinks", "a real juice still wins"),
        # "spezi" fires inside Spezialsalz / Spezialmehl / Käsespezialitäten.
        # Was `household` until the drugstore aisles were spliced into `_RULES` (2026-08-09);
        # dishwasher salt is a cleaning product, so this is the better answer. The guard's own
        # intent is unchanged and is what the `why` still names: `spezi` must not claim it.
        ("GUT&GÜNSTIG Spülmaschinen-Spezialsalz", "GUT&GÜNSTIG", "cleaning", "not a Spezi"),
        ("Italiamo Spezialmehl", "ITALIAMO", "pantry", "special flour"),
        ("Krombacher Spezi", "Krombacher", "soft_drinks", "the real Spezi still wins"),
        ("Milbona Hartkäse Spezialitäten", "Milbona", "cheese", "Spezialitäten is not Spezi"),
        # "limo" fires inside Limonaie (an Italian lemon biscuit).
        ("Granini Die Limo", "Granini", "soft_drinks", "the standalone word still wins"),
        ("Vita Cola oder Limo", None, "soft_drinks", "the standalone word still wins"),
        ("Sinalco Limonade", "Sinalco", "soft_drinks", "caught a layer earlier"),
        # "milka" fires inside Milkana (a cheese); "trolli" inside Trollinger (a wine).
        ("Milkana Schmelzkäse", "Milkana", "cheese", "not Milka"),
        ("Milka Alpenmilch", "Milka", "sweets", "the real Milka still wins"),
        ("Trollinger mit Lemberger QbA, Rotwein, feinherb", None, "alcoholic", "not Trolli"),
        ("Trolli Saure Glühwürmchen", "Trolli", "sweets", "the real Trolli still wins"),
        # "gefrier" reads freeze-DRIED fruit as tiefkühl; it is shelf-stable.
        ("Seeberger Gefriergetrocknete Himbeeren", "Seeberger", "snacks", "freeze-dried"),
        ("KoRo Gefriergetrocknete Erdbeerscheiben", "KoRo", "snacks", "freeze-dried"),
        ("Iglo Rahm-Spinat", "IGLO", "frozen", "actually frozen"),
        # Green beans had no rule at all; the pulse and the coffee must not follow them in.
        ("Buschbohnen", None, "vegetables", "green beans"),
        ("Freshona Brechbohnen", "Freshona", "vegetables", "green beans"),
        ("GUT & GÜNSTIG Kidneybohnen", "GUT & GÜNSTIG", "pantry", "a pulse, cf. kichererbsen"),
        ("Sommer Bio-Cracker mit Ackerbohnen", "Sommer", "snacks", "a cracker, not a bean"),
        # Ciabatta was a taxonomy node with no keyword, so a path-less row fell to "other".
        ("Ciabatta", None, "bakery", "keyword layer had no entry"),
        # The keyword was plural-only, so the singular fell to "other".
        ("EDEKA Regional Chrysantheme „Swifty“", "EDEKA Regional", "household", "a flower"),
    ],
)
def test_substring_guards(name, brand, expected, why):
    assert classify(name, brand, None) == expected, why


def test_angus_stays_unguarded_on_purpose():
    """A leading-space guard would fix "Lavendel angustifolia" but break the real beef, which
    HYPHENATES ("Black-Angus-"). The plant is already caught by its non-food path, so the guard
    costs a row and saves none — pinned so nobody "fixes" it and drops the Chipolata."""
    assert classify("MEINE METZGEREI Black-Angus-Chipolata", "MEINE METZGEREI", None) == "beef"
    assert classify("Lavendel angustifolia", None, ["Heimwerken und Garten", "Marken"]) == "household"


def test_rondo_is_off_the_brand_map():
    """A brand entry beats every keyword, so a brand spanning categories mis-files every product
    whose path is a brand leaf. "rondo" is Bahlsen biscuits AND Röstfein coffee — and all three
    live rows are coffee, which the map was filing as sweets."""
    assert "rondo" not in BRAND_CATEGORY


def test_coffee_is_no_longer_ice_cream_or_sweets():
    assert classify("Röstfein Rondo Original Ganze Bohnen", "Röstfein", None) == "coffee"
    assert classify("Rondo Original", "Rondo", None, "gemahlen, versch. Sorten 500g Packung") == "coffee"
    assert classify("Mövenpick Ganze Bohnen", "MÖVENPICK", None) == "coffee"
    # A chilled RTD coffee that the source files under its own "Eis" node is a drink, not an ice
    # cream — layer 2 has to beat both that path and the "mövenpick" -> ice_cream brand entry.
    eis_path = ["Lebensmittel und Getränke", "Produkte", "Dessert", "Eis"]
    assert classify("Mövenpick Iced Coffee", "Mövenpick", eis_path, "koffeinhaltig, 220-ml-Becher") == "coffee"


def test_multi_category_brands_that_deliberately_stay_on_the_brand_map():
    """The counter-examples to the rule above. Dropping either costs a row and saves none, so the
    fix goes a layer EARLIER instead (form words beat the brand map). Pinned so that "cleanup"
    can't land silently. mövenpick = ice cream AND coffee; kerrygold = butter AND cheese."""
    assert BRAND_CATEGORY["mövenpick"] == "ice_cream"
    # Its ice creams carry no other signal at all — that is why the entry has to stay.
    assert classify("Mövenpick Edle Komposition", "Mövenpick", None) == "ice_cream"

    # kerrygold -> butter files "Kerrygold extra XXL" correctly (its name/caption never say butter,
    # so the brand entry is the ONLY signal). Its cheeses are saved a layer EARLIER — by a Käse
    # PATH NODE (layer 3) or a "reibekäse" CAPTION (layer 2b), both before the brand map — NOT by
    # "Käse" in the name, which sits at layer 6, after the brand. So this only holds while the feed
    # keeps giving Kerrygold cheeses a Käse path or caption; both are pinned below.
    assert BRAND_CATEGORY["kerrygold"] == "butter"
    assert classify("Kerrygold extra XXL", "Kerrygold", None, "Versch. Sorten Gekühlt. 250 g") == "butter"
    kaese_path = ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Milchprodukte", "Käse", "Hartkäse"]
    assert classify("Kerrygold Irische Käsescheiben", "Kerrygold", kaese_path) == "cheese"  # via path
    brand_leaf = ["Lebensmittel und Getränke", "Marken", "Marken Lebensmittel", "Kerrygold"]
    assert classify("Kerrygold Käsespezialitäten", "Kerrygold", brand_leaf,
                    "irischer Schnitt- oder Reibekäse") == "cheese"  # via caption when the path is a brand leaf


@pytest.mark.parametrize(
    "name, expected, why",
    [
        # "X oder/auch alkoholfrei" is a multi-variant BEER offer, not an alcohol-free product.
        ("Benediktiner Hell, Festbier oder alkoholfrei", "alcoholic", "a beer offer"),
        ("Warsteiner Pils, auch alkoholfrei", "alcoholic", "a beer offer"),
        # ...while a product that IS alcohol-free still moves to soft_drinks (the documented rule).
        ("Maybach Alkoholfrei Weiß", "soft_drinks", "alcohol-free wine"),
        ("Deutsches Weintor Riesling, alkoholfrei", "soft_drinks", "alcohol-free wine"),
        # A Weinschorle is wine + water, and must beat the "schorle" form word.
        ("Weinschorle weiß", "alcoholic", "wine spritzer"),
        ("Gerolsteiner Schorle", "soft_drinks", "a real Schorle still wins"),
    ],
)
def test_alkoholfrei_and_schorle_forms(name, expected, why):
    assert classify(name, None, None) == expected, why


def test_a_bare_alkoholfrei_caption_signal_is_rejected():
    """Tempting and wrong: ~30 real beers carry "auch/teilw. alkoholfrei" in the CAPTION as a
    variant note. Reading it as a designation would empty the beer aisle into soft_drinks."""
    beer_path = ["Lebensmittel und Getränke", "Produkte", "Getränke", "Bier", "Biermarken", "Becks"]
    assert classify("Beck's Pilsener", "Beck's", beer_path,
                    "versch. Sorten, auch alkoholfrei 24x0,33l Flasche") == "alcoholic"


@pytest.mark.parametrize(
    "name, path_tail, expected, why",
    [
        # The source indexes some paths by BRAND under a drink node, so anything that brand touches
        # lands in alcoholic. 117 offers sit under these nodes; these are the wrong ones.
        ("Radeberger Premium-Lachsschinken", ["Bier", "Biermarken", "Radeberger"], "pork", "a ham"),
        ("GOLDEN SEAFOOD Lachsfilet-portionen", ["Bier", "Biermarken", "Golden"], "fish", "salmon"),
        ("Golden Seafood Ofenbackfisch XXL", ["Bier", "Biermarken", "Golden"], "fish", "battered fish"),
        # ...and a real beer under the same node is untouched.
        ("Radeberger Pilsner", ["Bier", "Biermarken", "Radeberger"], "alcoholic", "a real beer"),
        ("Paulaner Weißbier", ["Bier", "Biermarken", "Paulaner"], "alcoholic", "a real beer"),
        # Paulaner Spezi is a cola-orange soft drink filed under the Paulaner BEER node.
        ("Paulaner Spezi", ["Bier", "Biermarken", "Paulaner"], "soft_drinks", "cola-orange"),
    ],
)
def test_brand_indexed_drink_paths(name, path_tail, expected, why):
    path = ["Lebensmittel und Getränke", "Produkte", "Getränke", *path_tail]
    assert classify(name, None, path) == expected, why


def test_fassbrause_caption_beats_a_beer_brand_path():
    path = ["Lebensmittel und Getränke", "Produkte", "Getränke", "Bier", "Biermarken", "Veltins"]
    assert classify("Veltins Cola-Orange", "Veltins", path,
                    "Fassbrause; alkoholfrei; z. T. koffeinhaltig 0,5-L-Dose") == "soft_drinks"


@pytest.mark.parametrize(
    "name, path_tail, expected, why",
    [
        # Found by the self-disagreement detector: the same product NAME served in two categories
        # is >=1 wrong row by construction, and needs no ground truth to find.
        # A Fleischkäse is a meat loaf; "käse" claimed it whenever the source gave it no meat path.
        # Was pinned as `pork` ("a meat loaf, not cheese") until the 2026-08-09 photo sweep
        # showed it is a filled roll from the counter, i.e. the same class as `fischbrötchen`.
        # The original intent — that `käse` inside "Fleischkäse" must not make it cheese — is
        # unchanged and still asserted; only the positive answer moved.
        ("Fleischkäse im Brötchen", None, "ready_meals", "a filled roll, and never cheese"),
        # Beef mince the source files under Fleischzubereitungen (-> pork).
        ("Rinder-Hackfleisch", ["Fleisch", "Fleischzubereitungen"], "beef", "beef mince"),
        ("Hackfleisch gemischt", ["Fleisch", "Fleischzubereitungen"], "pork", "genuinely mixed"),
        # A croissant is bakery whatever it is filled with ("schinken" outranks "brot"/"gebäck").
        ("Schinken-Käse-Croissant", None, "bakery", "a croissant"),
        # "Lachs" is a loin cut as well as a salmon, and the fish rule runs first.
        ("Berschneider Lachsschinken Pariser Art", None, "pork", "cured pork loin"),
        ("Deutsche See Lachsfilet", None, "fish", "a real salmon"),
    ],
)
def test_self_disagreements_closed(name, path_tail, expected, why):
    path = ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", *path_tail] if path_tail else None
    assert classify(name, None, path) == expected, why


def test_limonaie_is_pinned_to_bakery():
    """ALDI's Cucina "Limonaie"/"Colombine" are "Feines Gebäck nach italienischer Art" — but that
    phrase is only on the flyer artwork; the payload carries neither it nor a usable path
    (`Marken > Marken Aldi Süd`), so the product name is the only handle. Pinned like knusperjung."""
    aldi_path = ["Lebensmittel und Getränke", "Marken", "Marken Aldi Süd"]
    assert classify("Limonaie", None, aldi_path, "Nach italienischer Art; 200-g-Packung") == "bakery"
    assert classify("Colombine", None, aldi_path, "Nach italienischer Art; 200-g-Packung") == "bakery"


def test_an_artificial_plant_is_not_pantry():
    """The source files it under "Würzmittel > getrocknete Kräuter", which maps to pantry."""
    path = ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Würzmittel",
            "getrocknete Kräuter", "Zitronenmelisse"]
    assert classify("HOME CREATION Künstliche Topfpflanze Lavendel", "HOME CREATION", path) == "household"


# --- Rescue real food the source dumps under a NON-food path (produce under pet/garden/promo) -----
# Found by measuring every offer with a non-food path that still carried a food signal: REWE files
# its regional produce and Deutsche See fish under generic pet-brand / promo / bare-brand nodes, so
# layer 1 turned them into "household". 63 offers moved, all household -> a food category, 0 others.

PET = ["Tierbedarf und Tierfutter", "Produkte", "Marken für Tiere"]
PROMO = ["Saison und Events", "Produkte", "Aktionen", "Payback"]
BRAND = ["Marken", "Marken Lebensmittel", "REWE Beste Wahl"]


@pytest.mark.parametrize(
    "name, brand, path, expected, why",
    [
        ("Nektarinen", None, PET, "fruits", "fruit under a pet-brand node"),
        ("Plattpfirsiche", None, PET, "fruits", "fruit under a pet-brand node"),
        ("REWE Regional Mini Roma Rispentomaten", None, PET, "vegetables", "veg under a pet node"),
        ("Große Kulturchampignons braun", None, PET, "vegetables", "mushrooms under a pet node"),
        ("Deutsche See Pangasiusfilet", "Deutsche See", PET, "fish", "a fish brand under a pet node"),
        ("Aprikosen", None, ["Heimwerken und Garten", "Marken", "Garden Feelings"], "fruits",
         "real apricots the source filed under ALDI's garden brand (image-verified)"),
        ("Bauern Gut Geflügelsalat", None, PROMO, "poultry", "poultry salad under a Payback node"),
        ("REWE Feine Welt Maishähnchen", None, BRAND, "poultry", "corn-fed chicken under a bare brand"),
        ("REWE Bio Roggenmischbrot", None, BRAND, "bakery", "bread under a bare brand"),
        ("Kania Tomatenketchup", None, PROMO, "pantry", "ketchup under a promo node"),
        ("REWE Beste Wahl Jumbo Erdnüsse", None, BRAND, "snacks", "peanuts under a bare brand"),
    ],
)
def test_food_rescued_from_a_nonfood_path(name, brand, path, expected, why):
    assert classify(name, brand, path) == expected, why


@pytest.mark.parametrize(
    "name, brand, why",
    [
        # A produce/meat word on a genuine non-food product must NOT be rescued — the veto holds it.
        ("REWE Traubenhyazinthen im Topf", None, "a flower, not grapes"),
        ("Gardenline Tomatenpflanze", "Gardenline", "a tomato plant, not a tomato"),
        ("Good Boy Bunter Hähnchen Knabbermix", None, "cat treats, not poultry"),
        ("Esmara Mango Kleid", "Esmara", "a fashion-brand dress, not a mango"),
        ("Livarno Beistelltisch Kirschholz", "Livarno", "cherry-wood furniture, not cherries"),
    ],
)
def test_nonfood_with_a_coincidental_food_word_stays_household(name, brand, why):
    garden = ["Heimwerken und Garten", "Produkte", "Garten"]
    assert classify(name, brand, garden) == "household", why


def test_rescue_only_fires_on_a_nonfood_path_not_a_food_one():
    """The gate that makes the rescue safe: a FOOD-path product carrying a rescue noun must keep its
    real category, not be dragged into produce. An Erdbeer-Joghurt is dairy, not fruits."""
    food = ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Milchprodukte", "Joghurt"]
    assert classify("Landliebe Erdbeere Joghurt", "Landliebe", food) == "dairy"
    # ...and a genuine household item with no food noun is untouched.
    assert classify("PARKSIDE Akku-Bohrschrauber", "PARKSIDE",
                    ["Heimwerken und Garten", "Produkte", "Werkzeug"]) == "household"


# --- New categories: Lamb & Other Meat, Eggs, Ready Meals, margarine -> Butter (PR3) ----------
# The audit's PR3. Full-DB diff: 72 moved, 0 regressions.


def test_new_categories_exist_with_labels():
    for slug in ("other_meat", "eggs", "ready_meals"):
        assert slug in CATEGORIES and CATEGORIES[slug]


FLEISCH = ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Fleisch"]


@pytest.mark.parametrize(
    "name, path, expected, why",
    [
        # Lamb: " lamm"/"lamm-" moved out of pork into other_meat.
        ("Neuseeländisches Lammkarree", FLEISCH, "other_meat", "lamb"),
        ("Lammkeule in Scheiben", FLEISCH, "other_meat", "lamb"),
        ("Lamm-Spieß »Despacito«", None, "other_meat", "hyphenated lamb"),
        ("Lammhüfte", None, "other_meat", "lamb, no leading space needed"),
        # Lammlachs is a lamb LOIN — was wrongly fish via "lachs"; other_meat runs before fish.
        ("Lammlachs mariniert", [*FLEISCH, "Lamm", "Lammlachse"], "other_meat", "lamb loin, not salmon"),
        # Rabbit moved out of pork.
        ("OLIVIA Ganzes Kaninchen", FLEISCH, "other_meat", "rabbit"),
        ("Meine Metzgerei Kaninchen", None, "other_meat", "rabbit"),
        # Game words (none live this week, but pinned for when they appear).
        ("Hirschgulasch", None, "other_meat", "venison"),
        ("Rehkeule", None, "other_meat", "venison"),
        # Guards: the meats that must NOT follow lamb out of their category.
        ("Elsässer Flammkuchen", None, "bakery", "Fla(mm)kuchen is not lamb"),
        ("Berschneider Graved Lachsfleisch", None, "pork", "a Schweinelachs stays pork (caption)"),
        ("Deutsche See Lachsfilet", None, "fish", "a real salmon stays fish"),
        ("Wildlachs Filet", None, "fish", "Wildlachs is fish — bare 'wild' is not a game signal"),
    ],
)
def test_other_meat(name, path, expected, why):
    unit = "vom Schweinerücken, gebeizt" if "Lachsfleisch" in name else None
    assert classify(name, None, path, unit) == expected, why


@pytest.mark.parametrize(
    "name, expected, why",
    [
        ("Hähnlein Bio Eier", "eggs", "real eggs"),
        ("EDEKA Bio Freilandeier", "eggs", "free-range eggs"),
        ("Landei Frische Eier 10 Stück", "eggs", "the ' eier ' / 'eier 10' form"),
        # Guards — the "Eier…" compounds that are a different product entirely.
        ("Eckes Edler Eierlikör", "alcoholic", "egg liqueur, not eggs"),
        ("Bauern Gut Eiersalat mit Schnittlauch", "ready_meals", "a deli salad"),
        ("Komet Eierkuchenmehl", "bakery", "pancake flour"),
    ],
)
def test_eggs(name, expected, why):
    assert classify(name, None, None) == expected, why


def test_eierkocher_appliance_is_household_not_eggs():
    path = ["Möbel und Wohnen", "Produkte", "Küche"]
    assert classify("SILVERCREST Eierkocher", "SILVERCREST", path) == "household"


@pytest.mark.parametrize(
    "name, brand, path_tail, expected, why",
    [
        # A layer-2 override: it beats the mis-filed path AND a competing brand.
        ("iglo Fertiggerichte", "iglo", ["Nudeln"], "ready_meals", "brand would say frozen"),
        ("Frosta Fertiggerichte", "Frosta", None, "ready_meals", "brand would say frozen"),
        ("YouCook Fertiggerichte", "YouCook", None, "ready_meals", "was 'other'"),
        ("YOUCOOK Indian Style Mango Chicken", "YOUCOOK", None, "ready_meals", "'chicken' would say poultry"),
        ("Sushi4You Sushi", None, ["Feinkost"], "ready_meals", "path would say pantry"),
        ("Meica Curry King", "Meica", ["Würzmittel"], "ready_meals", "brand+path would say pork/pantry"),
        ("BÜRGER Maultaschen", None, ["Nudeln"], "ready_meals", "path would say pantry"),
        ("Dönertasche Kebab", None, None, "ready_meals", "'kebab' would say pork"),
        # Guards: things that are NOT ready meals.
        ("Gustavo Gusto Pizza Margherita", "Gustavo Gusto", None, "frozen", "chilled/frozen pizza stays frozen"),
        ("GRILLMEISTER Nürnberger Rostbratwurst", None, None, "pork", "a raw sausage is not a ready meal"),
    ],
)
def test_ready_meals(name, brand, path_tail, expected, why):
    path = ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", *path_tail] if path_tail else None
    assert classify(name, brand, path) == expected, why


@pytest.mark.parametrize(
    "name, expected, why",
    [
        ("Rama Original XL", "butter", "margarine"),
        ("Rama mit Butter XXL", "butter", "margarine"),
        ("Lätta Original", "butter", "margarine"),
        ("Deli Reform Das Original", "butter", "margarine"),
        ("Arla Kærgården", "butter", "spreadable butter blend"),
    ],
)
def test_margarine_is_butter(name, expected, why):
    assert classify(name, None, None) == expected, why


def test_rama_prefix_does_not_swallow_ramazzotti():
    """'rama ' (trailing space) must not fire inside 'Ramazzotti'. With its real alcoholic path it
    stays alcoholic; even path-less it must never become butter."""
    alc = ["Lebensmittel und Getränke", "Produkte", "Getränke", "Alkoholische Getränke", "Likör"]
    assert classify("Ramazzotti Amaro", None, alc) == "alcoholic"
    assert classify("Ramazzotti Amaro", None, None) != "butter"


def test_rama_cremefine_is_rescued_to_dairy_not_swept_into_butter():
    """A cooking cream, not a spread. Its Drogerie (non-food) path catches it at layer 1, before
    the `rama ` butter override at layer 2 — so that override can never sweep it in.

    It used to stop there, at `household`. The 2026-08-09 photo sweep showed why that was only
    half an answer: the app hides `household` behind the Non-food toggle, so "honest can't tell"
    and "invisible to the user" are the same outcome. `cremefine` is now a `_FOOD_RESCUE` token,
    which runs FIRST inside layer 1 — earlier than the drugstore step that would have said Body
    & Shower, so the original reason for the veto still holds."""
    path = ["Drogerie und Haushalt", "Produkte", "Drogerie", "Körperpflege", "Creme"]
    assert classify("RAMA Cremefine", "RAMA", path) == "dairy"
    assert classify("RAMA Cremefine", "RAMA", path) != "butter", "the `rama ` override must not win"


def test_valess_is_cheese_not_meat():
    """Vegetarian (not vegan) filed by main ingredient: Valess is milk-protein. The source files it
    under 'Fleisch > Schnitzel', so a layer-2 override is required to beat the path."""
    path = ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Fleisch", "Fleischzubereitungen", "Schnitzel"]
    assert classify("Valess Crispy Sticks", "Valess", path) == "cheese"


# --- Coffee is its own category ------------------------------------------------
# Split out of soft_drinks (it was 27% of it: 117 of 441 stored offers). A bag of beans and a
# bottle of cola are not the same aisle. Tea deliberately STAYS in soft_drinks — what the feed
# carries is almost entirely ready-to-drink iced tea / kombucha, which really is a soft drink.


def test_coffee_lands_in_coffee_from_every_layer():
    kaffee_path = ["Lebensmittel und Getränke", "Produkte", "Getränke", "Kaffee"]
    assert classify("Röstkaffee gemahlen", None, kaffee_path) == "coffee"          # L3 path node
    assert classify("ja! Lungo oder Espresso", "ja!", None) == "coffee"            # L6 keyword
    assert classify("Lavazza Crema e Gusto", "Lavazza", None) == "coffee"          # L6 brand-as-keyword
    assert classify("Nescafé frappé", "Nescafé", None) == "coffee"                 # L4 brand map
    assert classify("Jacobs Krönung", "Jacobs", None) == "coffee"                  # rescued from "other"
    assert classify("Dallmayr Prodomo", "Dallmayr", None) == "coffee"


def test_the_split_does_not_drag_the_rest_of_soft_drinks_along():
    softdrink_path = ["Lebensmittel und Getränke", "Produkte", "Getränke", "Softdrinks",
                      "Softdrinkmarken"]
    assert classify("Pfanner IceTea", "Pfanner", softdrink_path) == "soft_drinks"
    # Real stored paths again: "Bubble Tea" is English, so the German " tee" keyword can't reach
    # it by name alone — its Tee path is what places it, and that path must stay soft_drinks.
    assert classify("EDEKA Herzstücke Bubble Tea", "EDEKA",
                    ["Lebensmittel und Getränke", "Produkte", "Getränke", "Heißgetränk", "Tee",
                     "Bubble Tea"]) == "soft_drinks"
    assert classify("Roy Bio-Kombucha", "Roy",
                    ["Lebensmittel und Getränke", "Produkte", "Getränke", "Teegetränk",
                     "Kombucha"]) == "soft_drinks"
    assert classify("Coca-Cola", "Coca-Cola", None) == "soft_drinks"
    assert classify("GEROLSTEINER Schorle", "Gerolsteiner",
                    ["Lebensmittel und Getränke", "Produkte", "Getränke", "Wasser",
                     "Wassermarken", "Gerolsteiner"]) == "soft_drinks"
    assert classify("Hohes C Vitamin Shots", "Hohes C",
                    ["Lebensmittel und Getränke", "Produkte", "Getränke", "Saft", "Saftsorten",
                     "Shots"]) == "soft_drinks"


def test_coffee_MACHINES_stay_household():
    """The trap that makes rescuing on a bare "kaffee" safe: an appliance is not a beverage.
    Each is a real stored offer, and each is held back ONLY by `_RESCUE_VETO` — drop that list
    and 7 of these machines move into Coffee."""
    # Real stored paths, not invented ones — these all live under an electronics/furniture root.
    for name, brand, path in (
        ("KRUPS Kaffeevollautomat Sensation", "KRUPS", ["Elektronik und Technik", "Marken", "Krups"]),
        ("SILVERCREST Espressomaschine", "SILVERCREST",
         ["Elektronik und Technik", "Marken", "SilverCrest"]),
        ("SILVERCREST Thermo-Filterkaffeemaschine", "SILVERCREST",
         ["Möbel und Wohnen", "Produkte", "Möbel", "Küche", "Geschirr", "Kannen und Karaffen"]),
        ("Bosch Kapselmaschine", "Bosch", ["Elektronik und Technik", "Marken", "Bosch"]),
        ("Melitta Barista", "Melitta", ["Elektronik und Technik", "Marken", "Melitta"]),
    ):
        assert classify(name, brand, path) == "household", name


def test_tchibo_is_not_a_coffee_brand_keyword():
    """Tchibo sells clothing and homeware (7 of its 11 stored rows are household), so it may not
    become a coffee keyword. Its clothing is already safe via the non-food path at layer 1 — the
    row that would actually break is the pathless one, which a brand keyword WOULD claim."""
    tchibo_path = ["Marken", "T", "Tchibo"]
    assert classify("Tchibo Bedruckte Palazzohose", "Tchibo", tchibo_path) == "household"
    # No path, so nothing shields it: add "tchibo" to the coffee keywords and this becomes coffee.
    assert classify("Tchibo Snack-Piekser", "Tchibo", None) != "coffee"


def test_real_coffee_under_a_nonfood_path_is_rescued():
    """Senseo pads and a REWE Bio Caffè Crema sat in household because the source filed them
    under a non-food node — the food-rescue reclaims them without touching the machines above."""
    assert classify("Senseo Kaffeepads Classic oder Crema Pads", "Senseo",
                    ["Elektronik und Technik", "Marken", "Senseo"]) == "coffee"
    assert classify("REWE Bio Caffè Crema", "REWE Bio",
                    ["Marken", "R", "REWE", "REWE Bio"]) == "coffee"


def test_coffee_is_a_registered_category():
    assert CATEGORIES["coffee"] == "Coffee"


# --- Pet food never lands in a food chip (2026-07-28, user-reported: "Orlando in Chicken is dog
# food"). The pet-food veto only ran INSIDE the non-food-path rescue, so a pathless pet product with
# a meat word ("Orlando Hundetrockennahrung Rind") sailed to the meat keyword and became beef. A
# layer-2 override now catches pet food before the meat/coffee/snacks keywords AND before a
# mis-filed food path (Sheba cat food sits under a "Fisch" node).
#
# 2026-07-31: the target became `pet` rather than `household`. Measured that the `pet` chip IS
# served in the grocery vertical, so the guard was disagreeing with itself — some pet products
# reached the chip while these sat behind the Non-food toggle. The claim below is unchanged and
# now stricter: a pet product must never be in a FOOD chip, and it must be findable. ---

@pytest.mark.parametrize(
    "name, path, was",
    [
        ("Orlando Hundetrockennahrung Rind & Gemüse", None, "beef (the reported bug)"),
        ("ROMEO Kauknochen aus Kaffeeholz", None, "coffee (kaffeeholz)"),
        ("Coshida Gefüllte Knabbersnacks", None, "snacks"),
        # A cat food the source files under a Fisch node — L2 must beat the food PATH at L3.
        ("Sheba Katzennassfutter Filets", ["Lebensmittel und Getränke", "Produkte", "Fisch"], "fish"),
        ("Orlando Pure Taste Hundetrockennahrung", None, "other"),
        ("Coshida Katzennassnahrung", None, "other"),
    ],
)
def test_pet_food_is_the_pet_chip_not_a_food_chip(name, path, was):
    assert classify(name, None, path) == "pet", f"was {was}"


def test_pet_guard_does_not_swallow_real_meat():
    """The guard is pet-term-specific, so genuine meat with the same word stays put — it fires on
    'Hundetrockennahrung', never on a bare 'Rind'."""
    assert classify("Metzgerfrisch Rinderhackfleisch", "Metzgerfrisch", None) == "beef"
    assert classify("Wiesenhof Hähnchenbrust", "Wiesenhof", None) == "poultry"
    # And a human "Filet" under a real Fisch path is still fish (only the pet token diverts it).
    assert classify("Followfish Lachsfilet", "Followfish",
                    ["Lebensmittel und Getränke", "Produkte", "Fisch"]) == "fish"


# --- Cheese the house brands leave on a bare brand-leaf path, or the source mis-files (2026-07-28
# flyer audit). The fix is keyword/brand/rescue, never a blanket brand-map for a multi-form brand. ---

@pytest.mark.parametrize(
    "name, was",
    [
        ("RÜCKER Alter Schwede", "other (brand-leaf path)"),
        ("Rücker Alter Schwede", "other"),
        ("Milbona Maasdamer", "other"),
        ("Milsani Maasdamer", "other"),
        ("Grünländer Scheiben mild & nussig", "other"),
        ("Rügener Badejunge Der Sahnige", "other"),
        ("Milkana Tolle Rolle", "other"),
    ],
)
def test_cheese_on_a_brand_leaf_path_is_cheese(name, was):
    assert classify(name, None, None) == "cheese", f"was {was}"


def test_milsani_reibekaese_rescued_from_a_pet_path():
    """Grated cheese the source filed under a pet-brand node ("Marken für Tiere") — a rescue, and
    the pet guard must not steal it (no pet token matches "reibekäse")."""
    pet = ["Tierbedarf und Tierfutter", "Marken für Tiere"]
    assert classify("Milsani Reibekäse XXL", "Milsani", pet) == "cheese"


def test_cheese_batch_does_not_overreach_multiform_brands():
    """Milkana spans cheese AND dairy, so only the specific name "Tolle Rolle" moved — its cream
    stays dairy. Pinned so a future "just brand-map Milkana" can't land silently."""
    assert classify("Milkana Frischeschale Sahne", "Milkana", None) == "dairy"
    assert classify("Milkana Schmelzkäse", "Milkana", None) == "cheese"


# --- Sausage / cured & fresh meat the house brands leave in Other, plus household-pathed pork
# (2026-07-28 flyer audit). ---

@pytest.mark.parametrize(
    "name, expected",
    [
        ("Handl Tyrolini", "pork"),
        ("Kamar Sucuk", "pork"),
        ("LANDBECK Salametti XXL", "pork"),
        ("Davitani Pancetta", "pork"),
        ("Spanferkel-Keule", "pork"),
        ("Die Thüringer Duett", "pork"),
        ("Die Thüringer Thüringer Stifte", "pork"),
        ("Stockmeyer Sonntags-Frühstück", "pork"),
        ("Black Premium Teres Major", "beef"),
    ],
)
def test_meat_on_a_brand_leaf_path_lands_right(name, expected):
    assert classify(name, None, None) == expected


def test_block_house_stays_off_the_brand_map_it_also_sells_bread():
    """Block House is a steakhouse but its flyer line includes garlic bread — so it is NOT a
    single-category beef brand; the bread stays bakery, the burgers stay Other."""
    assert classify("BLOCK HOUSE Brot XXL Knoblauch", "BLOCK HOUSE", None) == "bakery"


def test_die_thueringer_is_a_brand_phrase_not_bare_thueringer():
    """Bare 'thüringer' would grab "Mischgemüse Thüringer Art" (a vegetable); the brand phrase
    "die thüringer" catches the sausages without touching it."""
    veg = ["Lebensmittel und Getränke", "Produkte", "Gemüse", "Mischgemüse"]
    assert classify("Schneemann Mischgemüse Thüringer Art", None, veg) != "pork"
    assert classify("Die Thüringer Rostbratwurst", None, None) == "pork"


def test_household_pathed_pork_is_rescued():
    """Nackensteaks the source files under a non-food "Grillfleisch"/promo node were household;
    the rescue re-claims them (the pork keyword alone loses to the path)."""
    promo = ["Marken", "Hausmarke"]
    assert classify("Hausmarke Schweine-Nackensteaks", "Hausmarke", promo) == "pork"


# --- Drinks/coffee in Other + strays the source files under a Beer/Sekt node (2026-07-28 audit). ---

@pytest.mark.parametrize(
    "name, expected",
    [
        ("Melitta BellaCrema", "coffee"),        # no-space spelling the "bella crema" keyword misses
        ("Melitta BellaCrema SPECIALE", "coffee"),
        ("RIVER Iso Light", "soft_drinks"),
        # Activedrink moved to DAIRY on 2026-07-31 (user's call) — see
        # test_drinking_yoghurt_is_dairy. The rest of this table is unchanged.
        ("Rotbäckchen", "soft_drinks"),
        ("Von Herzen Regional Scharfe Gemüsesäfte", "soft_drinks"),
    ],
)
def test_drinks_on_a_brand_leaf_path_land_right(name, expected):
    assert classify(name, None, None) == expected


def test_drinking_yoghurt_is_dairy():
    """User's call (2026-07-31), reversing PR #105 which had put MILSANI Activedrink in
    soft_drinks. Listed with its sibling forms so the convention is consistent rather than a
    one-product patch — `kefir` moved a second product the same way. A juice or an iced tea
    must NOT come along."""
    assert classify("MILSANI Activedrink XXL", None, None) == "dairy"
    assert classify("QUARKI Kefir mild", None, None) == "dairy"
    assert classify("Müller Trinkjoghurt Erdbeer", None, None) == "dairy"
    # The counter-examples: a real soft drink stays a soft drink.
    assert classify("Rotbäckchen", None, None) == "soft_drinks"
    assert classify("RIVER Iso Light", None, None) == "soft_drinks"


def test_beer_path_traps_are_rescued_to_the_real_product():
    """The source files some non-beer products under a real "Alkoholische Getränke > Bier/Champagner
    > <brand>" node (verified stored paths); the L2 form words must beat that path. Real cases:
    tuna & trout under a beer brand, a chewing gum under "Dom Perignon", a soured-cream butter
    under "Veltins"."""
    G = ["Lebensmittel und Getränke", "Produkte", "Getränke", "Alkoholische Getränke"]
    bier = G + ["Bier", "Biermarken", "Golden"]
    assert classify("Golden Seafood Lachsforelle", "Golden Seafood", bier) == "fish"
    assert classify("GOLDEN SEAFOOD Thunfischfilets XXL", "Golden Seafood", bier) == "fish"
    assert classify("Kaugummistange", None, G + ["Schaumwein", "Champagner", "Dom Perignon"]) == "sweets"
    assert classify("Gläserne Molkerei Bio-Fassbutter Sauerrahm", "Gläserne Molkerei",
                    G + ["Bier", "Biermarken", "Veltins"]) == "butter"


# --- The Other / Household long tail (2026-07-28 flyer audit, batch F). ---

@pytest.mark.parametrize(
    "name, expected",
    [
        ("Bagel Bengel", "bakery"),
        ("Ibis Simit", "bakery"),
        ("Brandt Markenzwieback", "bakery"),
        ("Johannisbeer-Streuseltaler", "bakery"),
        ("Leimer Croutons Kräuter", "bakery"),
        ("Pfifferlinge", "vegetables"),
        ("Portobello", "vegetables"),
        ("Rotstern Chokis", "sweets"),
        ("Hitschler Hitschies", "sweets"),
        ("Nippon Häppchen", "sweets"),
        ("Little Moons Mochi Ice", "ice_cream"),
        ("EDEKA Herzstücke Ice-Bites", "ice_cream"),
        ("Blankenburg Harzer Kräuterhexe", "cheese"),
        ("Oatly Haferdrink Barista", "vegan"),
        ("Simply V Hirtengenuss", "vegan"),
        ("Like Döner", "vegan"),
    ],
)
def test_longtail_moves_out_of_other(name, expected):
    assert classify(name, None, None) == expected


def test_household_food_is_rescued_by_specific_nouns():
    """Snacks/pantry the source files under a non-food (pet/promo/brand) node."""
    pet = ["Tierbedarf und Tierfutter", "Marken für Tiere"]
    promo = ["Saison und Events", "Payback"]
    assert classify("Sun Snacks Erdnuss-flips XXL", "Sun Snacks", pet) == "snacks"
    assert classify("Trader Joe's Walnusskerne XXL", "Trader Joe's", pet) == "snacks"
    assert classify("REWE Bio Agavendicksaft", "REWE Bio", promo) == "pantry"


def test_food_rescue_stays_gated_on_a_nonfood_path():
    """A cashew BUTTER on a real food path keeps its pantry category — the rescue only fires under
    a non-food path, so the new `cashew` rescue token can't drag it into snacks."""
    real_path = ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Brotaufstrich",
                 "Fruchtaufstrich", "Fruchtmus", "Mandelmus"]
    assert classify("Maribel Bio Cashewmus", "Maribel", real_path) == "pantry"


# --- Non-food and non-produce the source files under an Obst/Gemüse node (2026-07-29). These sat
# in Fruits/Vegetables, which matters more than it looks: produce is sub-grouped for the deals
# list AND for the Basket's suggestions, so a bin bag left in Fruits becomes recommendable. ---

@pytest.mark.parametrize(
    "name, brand, path, expected, was",
    [
        # Scented bin bags. The path really is Obst > Melone — the bags are watermelon-scented,
        # so the source filed the SCENT, not the product.
        ("Power Force Duft-Müllbeutel", "Power Force",
         ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Obst", "Melone"],
         "household", "fruits"),
        # Herb cream cheese under Gemüse > Kohl > Kraut ("Kräuter" read as a cabbage node).
        ("Bresso Feine Kräuter", "Bresso",
         ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Gemüse", "Kohl", "Kraut"],
         "cheese", "vegetables"),
        # Breads the source files under produce nodes.
        ("Couronne Feigen-Walnuss", None,
         ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Obst"], "bakery", "fruits"),
        ("Mestemacher Greek Flatbread Klassisch", "Mestemacher",
         ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Gemüse"], "bakery",
         "vegetables"),
        # A cold sauce, not a vegetable.
        ("SKANDINAVIC'S Remoulade", None,
         ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Gemüse"], "pantry",
         "vegetables"),
    ],
)
def test_nonfood_and_nonproduce_leave_the_produce_chips(name, brand, path, expected, was):
    assert classify(name, brand, path) == expected, f"was {was}"


def test_the_produce_evictions_do_not_take_real_produce_with_them():
    """Each guard above is a designation, so the genuine produce sharing its path stays put."""
    obst = ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Obst", "Melone"]
    gemuese = ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Gemüse", "Kohl"]
    # A real watermelon under the SAME path the bin bags abused.
    assert classify("Wassermelone", None, obst) == "fruits"
    # A real cabbage under the same node as the Bresso cheese.
    assert classify("Spitzkohl", None, gemuese) == "vegetables"
    # "couronne"/"flatbread" are bread designations, not fruit/veg words: fresh figs stay fruit.
    assert classify("Feigen", None, obst) == "fruits"


# --- 2026-07-29 IMAGE audit: products whose NAME, PATH and BRAND all read plausibly for the
# wrong category, and only the product photo settled it. Each case is paired with the sibling
# that must NOT move — that pairing is the whole guard, since every fix here is a substring. ---

@pytest.mark.parametrize(
    "name, brand, path, expected, why",
    [
        # Fruits chip: the picture was a pastry, a jar, a yogurt pot and a chocolate bar.
        ("Apfeltasche", None, None, "bakery", "apple turnover, was fruits via 'apfel'"),
        ("Spreewaldhof Bio-Apfelmus", "Spreewaldhof", None, "pantry", "apple sauce in a jar"),
        ("CHOCEUR Orangetten", "CHOCEUR", None, "sweets", "chocolate sticks, was fruits"),
        # Vegetables chip: a sauce bottle, a jar of mayonnaise, and Hungarian salami.
        ("Heinz Knoblauch-Sauce", "Heinz", None, "pantry", "a sauce, was vegetables"),
        ("Miracel Whip Salatcreme Original", None, None, "pantry", "mayonnaise, was vegetables"),
        ("Pick Paprika Kolbasz Paare", "Pick", ["Lebensmittel und Getränke", "Gemüse", "Paprika"],
         "pork", "paprika-spiced salami the source filed under a Paprika node"),
        # Bakery chip: fried meatballs and breaded chicken.
        ("Bauerngut Berliner Buletten", "Bauerngut",
         ["Lebensmittel und Getränke", "Brot", "Feingebäck"], "pork", "meatballs under Feingebäck"),
        ("Tillman's Toasty", "Tillman's", None, "poultry", "breaded chicken, was bakery via 'toast'"),
        # Alcoholic chip: the source filed a rucksack under Schaumwein > Sekt.
        ("LIVE IN STYLE Rucksack", "LIVE IN STYLE",
         ["Lebensmittel und Getränke", "Produkte", "Getränke", "Alkoholische Getränke",
          "Schaumwein", "Sekt"], "household", "a rucksack served as Alcoholic"),
    ],
)
def test_image_audit_moves(name, brand, path, expected, why):
    assert classify(name, brand, path) == expected, why


def test_image_audit_guards_do_not_take_their_siblings():
    """Every fix above is a substring rule, so each needs the neighbour it must not touch."""
    # `apfelmus`/`apfeltasche` must not disturb a real apple, and `orangette` not an orange.
    assert classify("Apfel Pink Lady, lose", None, None) == "fruits"
    assert classify("GUT&GÜNSTIG Orangen", "GUT&GÜNSTIG", None) == "fruits"
    # `toasty` is the product; `toast` must keep meaning bread.
    assert classify("GUT&GÜNSTIG Toastbrot", "GUT&GÜNSTIG", None) == "bakery"
    # `bulette` is the meatball; a Berliner doughnut stays bakery.
    assert classify("Berliner", None, ["Lebensmittel und Getränke", "Brot", "Feingebäck"]) == "bakery"
    # `kolbasz` is the sausage; real peppers stay vegetables.
    assert classify("EDEKA Regional Paprika, rot", "EDEKA", None) == "vegetables"
    # `rucksack` is non-food; a real Sekt under the same node stays alcoholic.
    sekt = ["Lebensmittel und Getränke", "Produkte", "Getränke", "Alkoholische Getränke",
            "Schaumwein", "Sekt"]
    assert classify("Rotkäppchen Sekt", "Rotkäppchen", sekt) == "alcoholic"


def test_caption_rescues_products_a_name_rule_could_not_reach():
    """The two earlier audits DROPPED these because a name keyword clashed. The caption
    states the designation with no such collision — which is what layer 2b is for."""
    # `mars` as a name rule collides with Paulaner; the caption is unambiguous.
    assert classify("Mars", "Mars", None, "Schokoladenriegel, versch. Sorten 225 g") == "sweets"
    # Block House deliberately stayed OFF the brand map (it also sells garlic bread).
    assert classify("Block House Burger", "Block House", None,
                    "aus Rindfleisch, bratfertig tiefgefroren") == "beef"
    # A lamb cut that nothing else names.
    assert classify("DELUXE Merino-Lammlache", "DELUXE", None,
                    "Vom Merino-Lamm. Gekühlt. 250 g") == "other_meat"
    # ...but a MIXED mince keeps the house convention: "aus Schweine- und Rindfleisch" does
    # not contain "aus rindfleisch", so it must stay pork.
    assert classify("FAIR & GUT Cevapcici XXL", "FAIR & GUT", None,
                    "Hackfleischröllchen aus Schweine- und Rindfleisch; zum Braten") == "pork"


def test_brotaufstrich_is_rejected_as_a_caption_signal():
    """A spread's category comes from what it is MADE of, so "Brotaufstrich" (a USE, not an
    identity) must never be a caption signal — it moved Fleischsalat and Eiersalat out of pork
    and the Brunch spread out of cheese. Same class as the already-rejected "gebäck"."""
    # 2026-08-03: deli SALADS became ready_meals (user's convention); the point of this
    # test is unchanged — a blanket `brotaufstrich` caption signal would still drag them
    # all to pantry, which is wrong wherever they end up.
    assert classify("POPP Fleischsalat", "POPP", None,
                    "Brotaufstrich, 150-g-Becher") == "ready_meals"
    assert classify("Bauern Gut Eiersalat", "Bauern Gut", None,
                    "Brotaufstrich 150 g") == "ready_meals"


def test_vly_is_a_vegan_brand_not_dairy():
    """Its "Joghurt Alternative" was Dairy because layer 2's `joghurt` form word fired;
    layer 0 beats that. A real yogurt is unaffected."""
    assert classify("Vly Joghurt Alternative", "Vly", None, "Stracciatella 400-g-Becher") == "vegan"
    assert classify("Milbona Joghurt", "Milbona", None, "500 g") == "dairy"


# --- Preserved produce leaves the FRESH-produce chips (user's convention, 2026-07-29):
# jarred/canned -> pantry, frozen -> frozen. ---

@pytest.mark.parametrize(
    "name, brand, caption, expected",
    [
        ("Thüringer Landgarten Gewürzgurken", None, "360-g-Abtropfgew., je 670-g-Glas", "pantry"),
        ("Spreewaldhof Sauerkraut", "Spreewaldhof", "650-g-Abtropfgew., 680-g-Glas", "pantry"),
        ("REWE Bio Passata", "REWE Bio", "passierte Tomaten, vegan 700-g-Glas", "pantry"),
        ("Bonduelle Goldmais", "Bonduelle", "300g Dose", "pantry"),
        ("Oro di Parma Tomaten", "Oro di Parma", "ganz, passiert oder stückig", "pantry"),
        ("ALL SEASONS Ananas in Stücken XXL", "ALL SEASONS", "Im eigenen Saft", "pantry"),
        ("EDEKA Bio Gemüse", "EDEKA Bio", "erntefrisch tiefgefroren, versch. Sorten 300 g", "frozen"),
        ("REWE Bio Edamame", "REWE Bio", "tiefgefroren, Junge Sojabohnen aus Bio-Anbau", "frozen"),
    ],
)
def test_preserved_produce_leaves_the_fresh_chip(name, brand, caption, expected):
    assert classify(name, brand, None, caption) == expected


def test_fresh_produce_is_untouched_by_the_preserved_rule():
    """The counter-example half: loose produce must stay exactly where it is."""
    assert classify("Salatgurke", None, None, "Klasse I, je Stück") == "vegetables"
    assert classify("Rispentomaten", None, None, "500-g-Schale") == "vegetables"
    assert classify("Ananas, lose", None, None, "je Stück") == "fruits"


def test_a_bare_tiefgefroren_caption_is_rejected():
    """Simulated and rejected: a generic "tiefgefroren" caption signal moved 84 rows —
    every Eis out of ice_cream, Fischstäbchen out of fish, Chicken Nuggets out of poultry.
    The freezer is a shelf, not a category; only produce DESIGNATIONS ("erntefrisch") count."""
    assert classify("NORDSEE Fischstäbchen XXL", "NORDSEE", None,
                    "tiefgefroren, 450 g") == "fish"
    assert classify("Chef Select Chicken Nuggets XXL", "Chef Select", None,
                    "Tiefgefroren. 750 g") == "poultry"
    assert classify("BON GELATI Stieleis Mandel XXL", "BON GELATI", None,
                    "Tiefgefroren. 8 Stück") == "ice_cream"


# --- Image audit, batch 3: cheese-named sausages, savoury "waffles", and the food the
# source buried under a non-food path (layer 1 always decides there, so _FOOD_RESCUE is the
# ONLY reachable fix). ---

def test_cheese_named_sausages_are_pork():
    """A Käsewiener/Käsebeißer is a cheese-FILLED sausage. One arrived via the `käse`
    keyword and the other via a `Käse` PATH node, so the guard has to sit at layer 2."""
    assert classify("Delikat Käsewiener", "Delikat", None) == "pork"
    kaese_path = ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Käse"]
    assert classify("Richter Käsebeißer", "Richter", kaese_path) == "pork"
    # ...and a real cheese under the same node is untouched.
    assert classify("Milbona Butterkäse XXL", "Milbona", kaese_path) == "cheese"


def test_savoury_waffles_are_snacks_but_sweet_ones_are_not():
    """Reis-/Mais-/Dinkelwaffeln are pale crispbread discs ("gesalzen"); Manner Waffeln are
    confectionery. `waffel` must keep meaning sweets, so only the compounds move."""
    assert classify("EDEKA Bio Maiswaffeln", "EDEKA Bio", None, "gesalzen 130g Beutel") == "snacks"
    assert classify("EDEKA Herzstücke Reiswaffeln", "EDEKA", None) == "snacks"
    assert classify("Manner Waffeln", "Manner", None) == "sweets"
    assert classify("BISCOTTO Karamellwaffeln XXL", "BISCOTTO", None) == "sweets"


def test_roastbeef_is_beef_not_pork():
    """The source files it under `Fleischzubereitungen` (-> pork) and the brand is Metten,
    which the `mett` sausage rule also likes."""
    fz = ["Lebensmittel und Getränke", "Produkte", "Fleisch", "Fleischzubereitungen"]
    assert classify("Metten Roastbeef", "Metten", fz) == "beef"
    assert classify("Bauergut Schinkenmett", "Bauergut", fz) == "pork"  # real Mett unaffected


@pytest.mark.parametrize(
    "name, brand, path, expected",
    [
        # A path from an ENTIRELY unrelated domain — the classifier followed it faithfully.
        ("ZOTT Monte Mega", "Zott",
         ["Drogerie und Haushalt", "Produkte", "Drogerie", "Körperpflege", "Hautpflege",
          "Hautpflegeprodukte", "Creme"], "dairy"),
        ("CAPRI SUN Sirup", "CAPRI SUN",
         ["Drogerie und Haushalt", "Produkte", "Haushalt", "Reinigen", "Reinigungsmittel",
          "Spülmittel"], "soft_drinks"),
        # ...and plain "no rescue noun existed" cases under pet/promo/brand leaves.
        ("REWE Bio Sonnenkernbrot", "REWE Bio",
         ["Lebensmittel und Getränke", "Marken", "REWE Bio"], "bakery"),
        ("Golden Seafood White-Tiger-Garnelen XXL", "Golden Seafood",
         ["Tierbedarf und Tierfutter", "Marken für Tiere"], "fish"),
        ("Hamburger Heringsstipp", None,
         ["Dienstleistungen", "Gastronomie"], "fish"),
        ("REWE Beste Wahl Mix Tafeltrauben", "REWE Beste Wahl",
         ["Tierbedarf und Tierfutter", "Marken für Tiere"], "fruits"),
        ("Jack's Farm Knusperdinos XXL", "Jack's Farm",
         ["Drogerie und Haushalt", "XXL"], "poultry"),
    ],
)
def test_food_rescued_from_an_unrelated_path(name, brand, path, expected):
    assert classify(name, brand, path) == expected


def test_the_new_rescues_still_only_fire_under_a_non_food_path():
    """The rescue gate is what makes these safe. Under a real FOOD path the normal layers
    must still decide — otherwise `fruchtjoghurt` or `weine` would start hijacking rows."""
    pet = ["Tierbedarf und Tierfutter", "Marken für Tiere"]
    # A pet product that merely mentions a rescue noun must never reach a FOOD chip — that
    # was the "Orlando dog food in Chicken" bug. It now lands in the `pet` aisle rather than
    # the undifferentiated `household`, which is strictly more correct; what this pins is the
    # part that matters, that `rind` does NOT win.
    assert classify("Hundefutter mit Rind", None, pet) == "pet"
    assert classify("Hundefutter mit Rind", None, pet) != "beef"
    # THE SUBSTRING TRAP THIS ALMOST SHIPPED: "weine" is inside "Schweine-", so an unguarded
    # rescue noun turned a Schweinebraten under a pet path into ALCOHOLIC. The token carries a
    # leading space; both directions are pinned here.
    assert classify("Bauergut Schweinebraten", "Bauergut", pet) == "household"
    assert classify("Erben Weine", "Erben", ["Saison und Events", "Treuepunkte"]) == "alcoholic"


# --- The "other" bucket, adjudicated against its product photos. Nothing here was claimed by
# any layer before, so these are pure rescues — but each token still needs its guard. ---

@pytest.mark.parametrize(
    "name, expected",
    [
        ("Back Family Natron XXL", "pantry"),
        ("CROWNFIELD Cerealien XXL", "pantry"),
        ("DELUXE Ajvar", "pantry"),
        ("Landliebe Konfitüre", "pantry"),
        ("Deluxe Baklava Pistazie", "sweets"),
        ("Deluxe Cantuccini", "sweets"),
        ("DeBeukelaer Cereola", "sweets"),
        ("Milsani Götterspeise XXL", "sweets"),
        ("Kinder Delice", "sweets"),
        ("DELUXE Crème Brûlée", "dairy"),
        ("Milsani Mousse", "dairy"),
        ("Meister Filet-Räucherling", "fish"),
        ("MILRAM Hotties", "cheese"),
        ("MEIN BESTES CroFranz", "bakery"),
        ("KOPPENRATH WIESE Unsere Goldstücke", "bakery"),
        ("GUT&GÜNSTIG Hygienestreu", "pet"),
    ],
)
def test_other_bucket_rescues(name, expected):
    assert classify(name, None, None) == expected


def test_grilltaler_is_not_a_cheese_token():
    """`hotties` is Milram's grilling CHEESE, but the photo of "Grillmeister Brat- und
    Grilltaler" is a MEAT patty (Grillmeister is Lidl's grill-meat brand). A bare `grilltaler`
    token was simulated, caught here, and dropped — so the Milram rows move and the meat
    patty does not become cheese."""
    assert classify("Milram Hotties Grilltaler", "Milram", None, "Natur 180g Packung") == "cheese"
    assert classify("Grillmeister Brat- und Grilltaler", "Grillmeister", None,
                    "Versch. Sorten, Gekühlt 280 g") != "cheese"


# --- Image audit, final sweep: four brands whose layer-4 entry was beating the truth. ---

def test_moevenpick_coffees_are_not_ice_cream():
    """Mövenpick is the documented multi-category brand. Its coffees were relying on the
    `ganze bohnen`/`iced coffee` rescue, which does not fire for these three — all were
    served as ICE CREAM. The brand entry stays, because its actual ice creams need it."""
    assert classify("Mövenpick Kaffee", "Mövenpick", None,
                    "versch. Sorten, gemahlener Bohnenkaffee je 500-g-Pckg.") == "coffee"
    assert classify("Mövenpick Kaffeekapseln", "Mövenpick", None) == "coffee"
    assert classify("Mövenpick Der Himmlische", "Mövenpick", None,
                    "gemahlener Bohnenkaffee, je 500-g-Pckg.") == "coffee"
    assert classify("MÖVENPICK Eis", "Mövenpick", None, "Tiefgefroren") == "ice_cream"


def test_baileys_muffins_are_not_a_liqueur():
    """The point of this rule is that the `baileys` BRAND at layer 4 must not claim a muffin.
    The slug moved bakery -> sweets on 2026-08-03 (packaged cake is confectionery, user's call);
    what the entry guards against is unchanged."""
    assert classify("Baileys Muffins", "Baileys", None) == "sweets"
    assert classify("BAILEY'S The Original Irish Cream Likör", "Baileys", None) == "alcoholic"


def test_lachsfleisch_is_cured_pork_not_salmon():
    """German "Lachs" is a loin CUT as well as a fish — same trap as `lachsschinken`."""
    assert classify("Greußener Lachsfleisch mit Edelschimmel", None, None) == "pork"
    assert classify("GOLDEN SEAFOOD Lachsfilet", "GOLDEN SEAFOOD", None) == "fish"


def test_alcoholic_premixes_are_not_soft_drinks():
    assert classify("Jack Daniel's Cola", "Jack Daniel's", None, "10% Vol.") == "alcoholic"
    assert classify("Henderson Gin Tonic", None, None, "Mixgetränke, 10% Vol.") == "alcoholic"
    assert classify("Coca-Cola Original Taste", "Coca-Cola", None) == "soft_drinks"


def test_percent_vol_is_rejected_as_a_caption_signal():
    """"% vol" is a substring of "20% Vollmilch-Schokolade" — as a caption signal it turned a
    chocolate brioche into alcohol. Alcohol strength cannot be detected this way."""
    brioche = ("EDEKA Herzstücke Briochettes", "EDEKA", None,
               "weiche Brötchen mit 20% Vollmilch-Schokolade und 10% Butter")
    assert classify(*brioche) != "alcoholic"
    # ...and with its real path it is bakery, as it always was.
    backwaren = ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Backwaren"]
    assert classify(brioche[0], brioche[1], backwaren, brioche[3]) == "bakery"


# --- Image audit, final sweep: a water-BRAND path node serving regional food. ---

@pytest.mark.parametrize(
    "name, expected",
    [
        ("Born Thüringer Senf", "pantry"),
        ("Die Thüringer Leberwurst", "pork"),
        ("EWU Thüringer Rostbratwurst", "pork"),
        ("Schwarzwaldhof Schwarzwälder Schinken", "pork"),
        ("Mirabellen", "fruits"),
    ],
)
def test_regional_food_under_a_water_brand_node(name, expected):
    """The source files regional Thüringen FOOD under `Wasser > Wassermarken > Thüringer
    Waldquell` — a mineral-water brand. Removing the `wassermarken` node does NOT fix it: the
    scan falls through to the parent `Wasser`, which also maps to soft_drinks. Only layer 2
    beats a path, which is why these are form words and not keywords."""
    waldquell = ["Lebensmittel und Getränke", "Produkte", "Getränke", "Wasser",
                 "Wassermarken", "Thüringer Waldquell"]
    assert classify(name, None, waldquell) == expected
    # A real mineral water under the same node is untouched.
    assert classify("Thüringer Waldquell Mineralwasser", None, waldquell) == "soft_drinks"


def test_the_final_sweep_guards_hold_in_order():
    """_FORM_OVERRIDES is first-hit-wins, so these two guards must PRECEDE the tokens they
    protect against. Both were caught by the full-DB diff, not by reading the code."""
    # `mirabelle` would have made a fruit BRANDY into fruit.
    assert classify("PIRCHER Mirabellen Edelbrand", "PIRCHER", None) == "alcoholic"
    # `senf` would have made a herring in honey-mustard sauce into a condiment.
    assert classify("Matjes Honig-Senf", None, None) == "fish"


def test_other_final_sweep_moves():
    assert classify("Bauergut Holzfällerscheiben gewürzt", "Bauergut", None) == "pork"
    assert classify("Landstolz Filetpastete mit Paprika", "Landstolz",
                    ["Lebensmittel und Getränke", "Feinkostlebensmittel", "Feinkost",
                     "Pastete"]) == "pork"
    # The ALDI SPORTS powders were split across coffee and dairy by ` latte` and `sahne`.
    # 2026-08-03: sports-FORMAT nutrition (powders/bars) -> health, per the user.
    assert classify("ALDI SPORTS High-Protein-Pulver Iced Matcha Latte", "ALDI SPORTS",
                    None) == "health"
    assert classify("ALDI SPORTS High-Protein-Sahne", "ALDI SPORTS", None) == "pantry"
    # A fruit BAR the source filed under a coffee node.
    assert classify("Viba Fruchtschnitte", "Viba",
                    ["Lebensmittel und Getränke", "Kaffee", "Kaffeevariationen",
                     "Cafe au lait"]) == "sweets"


# --------------------------------------------------------------------------------------
# Drugstore categories (layer 1, after the food rescue, before the fall to `household`).
#
# The step can only fire where the answer was ALREADY `household`, so it is 0-regression by
# construction — the full-DB diff agreed: 608 rows moved, every one out of `household`, none
# out of a food category. What these tests pin is the part construction does NOT guarantee:
# that each rule picks the RIGHT drugstore aisle, and that the tokens which look obviously
# correct while being typed don't fire on their lookalikes.
# --------------------------------------------------------------------------------------
_DRUG = ["Drogerie und Haushalt", "Produkte", "Drogerie"]  # non-food, no useful leaf
_HAUS = ["Drogerie und Haushalt", "Produkte", "Haushalt"]


@pytest.mark.parametrize(
    "name,path,expected",
    [
        # --- the aisles, via the source's own product-kind nodes -----------------------
        ("AIGNER Cara Mia Ti Amo", _DRUG + ["Parfümerie", "Düfte"], "fragrance"),
        ("Isana Professional Shampoo", _DRUG + ["Haarpflege"], "hair"),
        ("Guido Maria Kretschmer Daycream", _DRUG + ["Körperpflege"], "body"),
        ("taxofit Elektrolyte Tablette", _DRUG + ["Gesundheit", "Nahrungsergänzungsmittel"], "health"),
        ("Felix Katze Nassfutter", ["Tierbedarf und Tierfutter", "Produkte", "Tierfutter"], "pet"),
        # --- and via name tokens, for the paths that dead-end at a brand container ------
        ("Schauma Shampoo", _DRUG + ["Marken Drogerie", "Schauma"], "hair"),
        ("Oral-B Elektrische Zahnbürste", _DRUG + ["Marken", "ORAL-B"], "dental"),
        ("Nivea Deospray", _DRUG + ["Marken Drogerie", "Nivea"], "body"),
        ("Perwoll Waschmittel Flüssig", _HAUS + ["Marken Haushalt", "Henkel"], "laundry"),
        ("Finish Spülmaschinen-caps", _HAUS + ["Calgonit", "Finish"], "cleaning"),
        ("Pampers Sparpack Baby Dry Windel", _DRUG + ["Marken Baby", "Pampers"], "baby"),
    ],
)
def test_drugstore_aisles(name, path, expected):
    assert classify(name, None, path) == expected


@pytest.mark.parametrize(
    "name,path,expected,why",
    [
        # Each of these was caught by the full-DB diff, NOT by reading the rule — the
        # sibling that must not move, paired with the aisle it was wrongly claiming.
        ("Mundharmonika", ["Sonstige", "Produkte", "Musikinstrumente"], "household",
         "a HARMONICA: `mund` must not reach the dental rules"),
        ("Ideenwelt Dusch-Teleskopbürste", _DRUG, "household",
         "a shower BRUSH is hardware; `dusch` must not make it body care"),
        ("Garnier Skin Active 2in1 Vitamin C", _DRUG, "household",
         "a bare `vitamin` is an ingredient claim across cosmetics, not a supplement"),
        ("Axe Duschgel", _DRUG + ["Marken", "Marken Parfum", "Axe"], "body",
         "`Marken Parfum` is a BRAND CONTAINER — Axe also makes shower gel"),
        ("EDEKA Herzstücke Feine Pastete", ["Tierbedarf und Tierfutter", "Marken für Tiere"],
         "household", "`Marken für Tiere` is a brand container holding human food too"),
        # 2026-08-03: now resolves to `body`, and correctly — a Pflegedusche IS a shower
        # product, caught by the new `dusche` TOKEN rather than by the path. The rejection this
        # case documents is unchanged: the `Hautpflege` NODE stays out of the map because it
        # spans face AND body (a RAMA Cremefine hangs off it too).
        ("NIVEA Pflegedusche", _DRUG + ["Hautpflege", "Hautpflegeprodukte", "Creme"], "body",
         "a Pflegedusche is a shower product; the `Hautpflege` NODE is still unmapped"),
        ("Huel Trinkmahlzeit Banana", ["Baby und Kinder", "Baby", "Babynahrung"], "household",
         "`Babynahrung` is a FOOD node; an adult meal drink must not become a drugstore aisle"),
        ("Gillette Fusion5", _DRUG + ["Körperpflege", "Haarentfernung"], "body",
         "hair REMOVAL is shaving — body, not hair care"),
        ("LEIFHEIT Wäscheschirm", _HAUS + ["Textilreinigung", "Textiltrocknung"], "household",
         "`Textilreinigung` covers drying hardware, not just detergent"),
        ("Zugbandmüllbeutel", _HAUS + ["Marken Haushalt", "Swirl"], "household",
         "bin bags were deliberately routed to household by an earlier audit"),
    ],
)
def test_drugstore_rejected_signals(name, path, expected, why):
    assert classify(name, None, path) == expected, why


def test_drugstore_step_cannot_touch_a_food_path():
    """The 0-regression property, as a test rather than an argument: the step lives inside
    the layer-1 non-food branch, so a FOOD path never reaches it — even for a product whose
    name is full of drugstore tokens."""
    food = ["Lebensmittel und Getränke", "Produkte", "Molkereiprodukte", "Joghurt"]
    assert classify("Milram Buttermilch Shampoo-Edition", None, food) == "dairy"


def test_a_food_rescue_still_beats_the_drugstore_step():
    """Order inside layer 1: `_FOOD_RESCUE` runs FIRST, so real food buried under a
    drugstore path stays food. The source files these spare ribs under `Waschmittel`."""
    path = ["Drogerie und Haushalt", "Produkte", "Haushalt", "Textilreinigung", "Waschmittel"]
    assert classify("ASIA GREEN GARDEN Spare Ribs", None, path) == "pork"


# dm sends ONE flat category leaf, not a hierarchy — `_path_nonfood` sees a root that
# isn't the food root, so layer 1 decides and the drugstore step is what resolves it.
@pytest.mark.parametrize(
    "name, path, expected, why",
    [
        # --- the class dm's own taxonomy fixes, with the sibling that must NOT move ----
        ("CATRICE Blush Stick Blushin' Charm 020 Coral Cutie", ["Blush"], "makeup",
         "a blush in shade 'Coral Cutie' was reaching the `coral` DETERGENT brand token"),
        ("Coral Colorwaschmittel", ["Drogerie und Haushalt", "Waschmittel"], "laundry",
         "the counter-example: real Coral detergent must STILL be laundry"),
        ("OGX Scalp Serum ProGrowth + Peptide", ["Haarkur & Haarmaske"], "hair",
         "dm's leaf names the product kind; without it this is an undifferentiated blob"),
        ("M. Asam Toner Magic Care", ["Gesichtswasser"], "face", "a toner is face care"),
        ("NYX PROFESSIONAL MAKEUP Körperöl", ["Körperöl"], "body", "body oil, not face"),
        ("Mivolis Basen-Tabletten", ["Mineralstoffe"], "health", "a supplement"),
        ("Denkmit Bodenreiniger Caps", ["Bodenreiniger"], "cleaning", "a floor cleaner"),
        ("Dein Bestes Katzenleckerli", ["Snacks für Katzen"], "pet",
         "cat treats are pet, not the household catch-all"),
        # --- FOOD leaves: layer 1 can never fall through, so only this step reaches them
        ("LEBENSBAUM Früchtetee Zeit für Dankbarkeit", ["Tee"], "soft_drinks",
         "dm's tea was buried in household; the drugstore step may return a food slug"),
        ("Fisherman's Friend Pastillen", ["Bonbons & Fruchtgummi"], "sweets", "sweets"),
        ("dmBio Kürbiscreme mit Olivenöl", ["Herzhafte Brotaufstriche"], "pantry", "a spread"),
        # --- garden seeds are NOT produce -------------------------------------------
        # `zucchini` is a `_FOOD_RESCUE` token, so WITHOUT the veto this seed packet is
        # served in the Vegetables chip. Note the fix is a veto, not a path-map entry:
        # the food rescue runs first, so a map entry here would be dead code.
        ("Stadt Land blüht Saaten, Zucchini (Zuboda)", ["Saaten & Körner"], "household",
         "a SEED PACKET must not be rescued into fresh produce by the plant's name"),
        ("Stadt Land blüht Saaten, Rucola (Wilde Rauke)", ["Saaten & Körner"], "household",
         "same, via the `rucola` rescue token"),
        ("Zucchini", ["Obst und Gemüse", "Gemüse"], "vegetables",
         "the counter-example: a real zucchini must still be produce"),
        ("Meisterbrot mit Saaten", None, "bakery",
         "the real bread this corpus holds: pathless, so keyword-decided and untouched — "
         "but it is why the veto token is the BRAND and not a bare `saaten`"),
    ],
)
def test_dm_category_leaves(name, path, expected, why):
    assert classify(name, None, path) == expected, why


@pytest.mark.parametrize(
    "name, path, expected, why",
    [
        ("CATRICE Eyeliner- und Lidschattenhelfer", ["Beautyhelfer"], "makeup",
         "`Beautyhelfer` is a CONTAINER (refill bottles AND makeup tools) — mapping it to "
         "`body` DEMOTED this row, which already resolves correctly on its own"),
        ("ebelin Reiseset Refillflaschen", ["Beautyhelfer"], "household",
         "the other half of that container node, correctly left in household"),
        ("trend !t up Lippenbalsam Butter Bliss Soft Tinted 030", ["Lipbalm"], "body",
         "`Lipbalm` is deliberately unmapped: it would move 8 rows body->face for no blob "
         "reduction and disagree with the `lippenbalsam` rule for pathless lip balms"),
    ],
)
def test_dm_rejected_leaves(name, path, expected, why):
    assert classify(name, None, path) == expected, why


def test_dm_leaf_cannot_drag_a_food_path_into_a_drugstore_aisle():
    """The 0-regression property still holds with dm's leaves in the map: the step is
    inside the layer-1 non-food branch, so a real FOOD path never reaches it."""
    food = ["Lebensmittel und Getränke", "Produkte", "Süßwaren", "Bonbons & Fruchtgummi"]
    assert classify("Haribo Goldbären", None, food) == "sweets"


def test_every_drugstore_slug_is_a_real_category():
    """No rule may name a slug the app doesn't serve — the chips come straight from these,
    so a typo would render a category with a missing label. `_DRUGSTORE_RULES` may also
    resolve to plain `household` (a guard entry); the PATH map may not."""
    assert DRUGSTORE_CATEGORIES <= set(CATEGORIES)
    for slug, _tokens in _DRUGSTORE_RULES:
        assert slug in CATEGORIES
    # The PATH map is overwhelmingly drugstore aisles, but a few leaves deliberately
    # resolve elsewhere: dm files tea / savoury spreads / sweets under its own FOOD leaves
    # and layer 1 can never fall through, so this step is the only thing that can rescue
    # them; and `Saaten & Körner` is garden seed packets, which are household. Enumerated
    # rather than relaxed, so a TYPO ("soft_drink") still fails this gate.
    non_aisle = {"soft_drinks", "pantry", "sweets", "household"}
    for node, slug in _DRUGSTORE_PATH_MAP.items():
        assert slug in CATEGORIES, node
        assert slug in DRUGSTORE_CATEGORIES | non_aisle, node


# --- 2026-07-31 audit: a path node naming a CUT or a FORM must not beat the species ------
#
# Reported: "Schweine-Nackensteaks" served as Beef. Each case below is a product that MOVED
# plus the sibling that must NOT move — the sibling is the point, since every one of these
# tokens is a substring risk or an override of a path that is usually right.

STEAK_PATH = ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Fleisch",
              "Fleischzubereitungen", "Steak"]


@pytest.mark.parametrize(
    "name,path,expected,why",
    [
        # The report. `_PATH_MAP["steak"]` is beef and beats the `schwein` keyword at L6.
        ("Schweine-Nackensteaks XXL", STEAK_PATH, "pork", "a pork neck steak is pork"),
        ("Bauerngut Schinkensteaks gewürzt", STEAK_PATH, "pork", "a ham steak is pork"),
        # THE COUNTER-EXAMPLE that decides the fix: the `steak` node must survive, because
        # deleting it drops this onto `Fleischzubereitungen` -> pork. Beef has no keyword here.
        ("Scotland Hills Cowboy Steak", STEAK_PATH, "beef", "a cowboy steak really is beef"),
        # The source's `Putenhackfleisch` leaf is unmapped, so it inherited pork from
        # `Fleischzubereitungen` two levels up. The pre-existing L2 entry had only `puten-`.
        ("FAIR & GUT Putenhackfleisch XXL",
         ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Fleisch",
          "Fleischzubereitungen", "Hackfleisch", "Putenhackfleisch"],
         "poultry", "turkey mince is poultry, not pork"),
    ],
)
def test_species_beats_a_cut_node(name, path, expected, why):
    assert classify(name, None, path) == expected, why


def test_schwein_does_not_claim_guinea_pig_food():
    """ORDER is the rule here: `schwein` is a substring of `Meerschweinchen`, so the L2 entry
    sits AFTER the pet guard. Move it above and a guinea-pig food becomes pork."""
    assert classify("Meerschweinchen Trockenfutter", None, None) == "pet"


def test_milka_is_chocolate_but_milkana_is_still_cheese():
    """`Alpenmilch` is not in `_PATH_MAP` — its parent milk node is — so no node deletion can
    fix this, and the brand map (L4) is below the path (L3). The trailing space in "milka "
    is what keeps Milkana out, exactly as it does at L4."""
    alpen = ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Milch", "Alpenmilch"]
    assert classify("Milka Tafel", None, alpen) == "sweets"
    assert classify("Milkana Tolle Rolle", None, None) == "cheese"


@pytest.mark.parametrize(
    "name,expected",
    [
        # `Knabberzeug > Sticks` is a FORM node. Dropping it is a no-op (its parent answers
        # `snacks` identically — measured over the whole DB), so name the real kinds instead.
        ("Nescafé Sticks 2in1 & 3in1", "coffee"),
        ("GUT&GÜNSTIG Kaffeesticks 2in1", "coffee"),
        ("Mucci Raketeneis", "ice_cream"),
        ("RIO D'ORO Icesticks", "ice_cream"),
        # ...but a genuine crisp under the same node stays a snack.
        ("funny frisch Brezli", "snacks"),
    ],
)
def test_sticks_node_holds_more_than_snacks(name, expected):
    sticks = ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Knabberzeug", "Sticks"]
    assert classify(name, None, sticks) == expected


def test_zespri_kiwi_is_fruit_not_a_soft_drink():
    """A brand-container node again: Zespri sat under a mineral-water brand leaf."""
    water = ["Lebensmittel und Getränke", "Produkte", "Getränke", "Wasser", "Lichtenauer"]
    assert classify("Zespri Kiwi SunGold", None, water) == "fruits"
# --- 2026-07-31 image audit: what the product PHOTO settles ------------------------------
#
# Read from contact sheets of every served product image — the only channel that catches a
# product whose name, brand, path AND caption all read plausibly for the wrong category.

@pytest.mark.parametrize(
    "name,expected,why",
    [
        # Photo: bags of gummy sweets. The fruit words in the names took them to Fruits.
        ("Sweet Corner Apfelringe/Saure Würmer", "sweets", "gummy sweets, not apple rings"),
        ("Sweet Corner Süße Kirschen", "sweets", "a bag of gummy cherries"),
        # ...while a real cherry is untouched.
        ("Süßkirschen Klasse I", "fruits", "actual cherries stay fruit"),
        # Crisps that sat in VEGETABLES, claimed by the paprika keyword.
        ("funny-frisch Jumpys Paprika", "snacks", "crisps, not a vegetable"),
        ("funny-frisch Ringli, Frit-Sticks, Paprika-Ecken", "snacks", "crisps"),
        # ...and a real pepper is untouched.
        ("Spitzpaprika rot", "vegetables", "a real pepper stays a vegetable"),
        # The `other` bucket: real food the house brands leave unnamed.
        ("Weihenstephan Die Extrazarte", "butter", "butter"),
        ("Bauer Der Große Bauer", "dairy", "a yoghurt cup"),
        ("Zetti Knusperflocken", "sweets", "chocolate — 'zetti' alone clashes with Mazzetti"),
        ("EDEKA Herzstücke Khidri-Datteln", "fruits", "dates"),
        ("Massari Rosa L'Aperitivo Spritz", "alcoholic", "an aperitif"),
        ("PRIMADONNA Würzöl", "pantry", "seasoned olive oil"),
        ("Speisezeit Gulaschsuppentopf", "pantry", "tinned soup"),
        # ORDER inside the audit block: a nut CREAM is a spread, so it must be matched before
        # the nut-kernel entry claims it for snacks. Swap the two entries and this flips.
        ("ITALIAMO Pistaziencreme", "pantry", "a spread, not a snack"),
        ("EDEKA Herzstücke Pistazienkerne", "snacks", "the kernels really are a snack"),
    ],
)
def test_photo_audit_moves(name, expected, why):
    assert classify(name, None, None) == expected, why


def test_species_leaf_beats_the_cut_its_parent_names():
    """The source's own leaf names the species while the parent names only the cut, and the
    leaf→root scan threw that away whenever the leaf was unmapped."""
    loin = ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Fleisch",
            "Fleischzubereitungen", "Steak", "Schweinerückensteak"]
    roast = ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Fleisch",
             "Fleischzubereitungen", "Braten", "Rinderbraten"]
    assert classify("BBQ Rückensteaks", None, loin) == "pork"
    assert classify("Black Premium Irischer Rinder-Braten", None, roast) == "beef"


def test_grill_season_turkey_is_rescued_but_grill_hardware_is_not():
    """`Saison und Events` is a non-food root, so layer 1 decides and never falls through —
    only a _FOOD_RESCUE token can reach the meat. The hardware must stay household."""
    grill = ["Saison und Events", "Produkte", "Saison", "Grillsaison", "Grillen", "Grillgut",
             "Grillfleisch", "Grillsteak", "Putensteak"]
    assert classify("BBQ Puten-Ministeaks", None, grill) == "poultry"
    hardware = ["Saison und Events", "Produkte", "Saison", "Grillsaison", "Grillen", "Grill"]
    assert classify("Black Torch Tankstellengrill", None, hardware) == "household"


def test_no_duplicate_keys_in_the_rule_tables():
    """A repeated key in a dict LITERAL silently keeps the last one — this bit while writing
    the audit above (a second `poultry` entry further down ate the first, with no error)."""
    import ast
    import collections

    import app.categories

    tree = ast.parse(open(app.categories.__file__).read())
    for node in ast.walk(tree):
        target = None
        if isinstance(node, ast.AnnAssign):
            target = getattr(node.target, "id", None)
        elif isinstance(node, ast.Assign) and node.targets:
            target = getattr(node.targets[0], "id", None)
        if target in {"_FOOD_RESCUE", "_PATH_MAP", "BRAND_CATEGORY"} and isinstance(
            node.value, ast.Dict
        ):
            keys = [k.value for k in node.value.keys if isinstance(k, ast.Constant)]
            dupes = [k for k, n in collections.Counter(keys).items() if n > 1]
            assert not dupes, f"{target} defines {dupes} twice — the later one silently wins"


def test_preserved_produce_leaves_the_fresh_chip_even_when_rescued():
    """The user's convention (jarred/canned -> pantry) already holds for food-path products
    via the layer-2 form words, but layer 1 DECIDES on a non-food path and never falls
    through — so a jar the rescue found by name stayed in Fruits. The rescue matches the name
    ("Mandarin-Orangen"), which cannot tell a jar from loose fruit; the caption states it."""
    promo = ["Saison und Events", "Produkte", "Aktionen", "Vegan"]
    jar = "Geschält; leicht gezuckert; Abtropfgewicht (ATG) = 560g; 1.062-ml-Glas"
    assert classify("All Seasons Mandarin-Orangen XXL", "All Seasons", promo, jar) == "pantry"
    # The counter-example: the SAME rescue path, fresh product, must stay in the fruit chip.
    assert classify("Nektarinen", None, promo, "Klasse I 1 kg") == "fruits"
    # And the redirect only touches the two fresh-produce slugs — a rescued fish stays fish
    # even when it is sold from a tin.
    assert classify("Deutsche See Thunfisch", None, promo, "Abtropfgewicht 112 g") == "fish"


@pytest.mark.parametrize(
    "name,brand,expected,why",
    [
        # Each of these is a GUARD sitting above a token that would otherwise claim it —
        # layer 2 is first-hit-wins, so the pairs below are really ordering assertions.
        ("Meine Küchenwelt Schweinsöhrchen", None, "bakery", "a palmier pastry, not pork"),
        ("Grillmeister Schweine-Nackensteaks", None, "pork", "...and real pork still is pork"),
        ("Geflügelfleischkäse", None, "poultry", "poultry loaf beats the pork `fleischkäse`"),
        ("Bauerngut Fleischkäse", None, "pork", "...and a plain one stays pork"),
        ("Deluxe Geflügelfond", None, "pantry", "stock in a jar, not poultry"),
        ("HÄUSSLING Sommerdaunendecke", None, "household", "a duvet under a Geflügel node"),
        ("Original Muh-Muhs Sahne-Toffees", None, "sweets", "toffees under a Butter node"),
        ("Tigersnack Tomate Mozzarella", None, "bakery", "a topped bread roll"),
        ("Dr. Oetker Die Ofenfrische Salami", None, "frozen", "a frozen pizza, not salami"),
        ("Speisezeit Kohlrouladen", None, "ready_meals", "a chilled Fertiggericht"),
        ("Bauerngut Rindfleischspieß", "Bauerngut", "beef", "the house-brand map said pork"),
        ("Dr. Quendt Dinkelchen Vollmilch", None, "sweets", "chocolate biscuits, not milk"),
        ("Zum Dorfkrug Rote Grütze", None, "pantry", "compote in a jar"),
        # Vegan brands are layer 0, the only layer above what they IMITATE.
        ("Violife Pizza Mix", "Violife", "vegan", "was in the brand map as cheese"),
        ("MYVAY The Wonder Chunks Chicken-Style", "MYVAY", "vegan", "soy, not chicken"),
    ],
)
def test_photo_audit_batch2(name, brand, expected, why):
    assert classify(name, brand, None) == expected, why


def test_bananen_now_ships_because_the_guard_expresses_what_the_flat_table_could_not():
    """The previous audit REJECTED a bare `bananen` because it dragged a Bananen-Kirsch-Getränk
    out of soft_drinks — the flat table can't say "not a drink". A guard entry ABOVE it can,
    and layer 2 is first-hit-wins. Swap the two entries and the drink breaks."""
    milch = ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Milchprodukte", "Milch"]
    saft = ["Lebensmittel und Getränke", "Produkte", "Getränke", "Saft", "Saftmarken",
            "Rio D'oro"]
    assert classify("Bananen, Fairtrade", None, milch) == "fruits"
    assert classify("RIO D'ORO Bananen-Kirsch-Getränk", None, saft) == "soft_drinks"


# The rescue cases need a NON-FOOD path — that is the whole reason they need a rescue token:
# layer 1 only runs when the path is non-food, and it decides without falling through.
NONFOOD_PATH = ["Saison und Events", "Produkte", "Saison", "Aktionen"]


@pytest.mark.parametrize(
    "name,expected,why",
    [
        # Real FOOD that was sitting in `household`, i.e. behind the Non-food toggle and
        # effectively invisible to the user.
        ("BABYBEL 9er-Netz", "cheese", "a net of Babybel"),
        ("BauernGut Goldgriller", "poultry", "'100% Geflügel' bratwurst"),
        ("Senseo Coffee Pads Classic", "coffee", "coffee pads"),
        ("Krombacher Frische-Fass", "alcoholic", "a 5 l beer keg"),
        ("AMICELLI Milchcreme", "sweets", "chocolate wafer rolls"),
        ("EDEKA Regional Paprika", "vegetables", "fresh peppers"),
        ("Berlin Like Home Baba Ganoush", "pantry", "a dip"),
    ],
)
def test_photo_audit_batch3_food_rescued_from_household(name, expected, why):
    assert classify(name, None, NONFOOD_PATH) == expected, why
    # ...and a genuine non-food item under the same root must stay household.
    assert classify("Black Torch Tankstellengrill", None, NONFOOD_PATH) == "household"


@pytest.mark.parametrize(
    "name,expected,why",
    [
        # Drugstore products stranded in household / the wrong chip (layer 2, so pathless).
        ("Persil Waschmittel Gel", "laundry", "detergent"),
        ("Listerine Advanced", "dental", "mouthwash — it was in the hair chip"),
        ("WC FRISCH Kraft Aktiv", "cleaning", "toilet rim block"),
        # The convention call: heat-and-eat -> ready_meals, spreads/salads stay pantry.
        ("Erasco Eintopf", "ready_meals", "a canned stew is heat-and-eat"),
        ("Popp Brotaufstrich", "pantry", "a spreadable salad stays pantry"),
        ("Dr. Oetker Kuchenbackmischungen", "pantry", "a cake MIX is an ingredient"),
    ],
)
def test_photo_audit_batch3(name, expected, why):
    assert classify(name, None, None) == expected, why


def test_a_blanket_brotaufstrich_is_still_rejected():
    """The narrow spread tokens exist because the blanket one was re-simulated and STILL
    regresses: it drags Rama (margarine) out of butter and the Brunch spread out of cheese."""
    assert classify("Rama Brotaufstrich", None, None) == "butter"
    assert classify("Brunch Brotaufstrich", None, None) == "cheese"


def test_pet_guard_splits_pet_food_from_genuine_household():
    """`topfpflanze` is a houseplant and bare `dental` is human dental care — neither may be
    dragged into `pet` by the split, and the dog chew is named explicitly instead."""
    assert classify("GUT&GÜNSTIG Dental-Sticks", None, None) == "pet"
    assert classify("Colgate Total Zahnpasta", None, None) == "dental"
    assert classify("Kunst-Topfpflanze Sukkulente", None, None) == "household"


@pytest.mark.parametrize(
    "name,expected,why",
    [
        ("Rotkäppchen Minis/Sticks & Dip", "cheese", "Rotkäppchen is the SEKT brand — this is soft cheese"),
        ("Petrella Schnittlauch", "cheese", "a cream-cheese tub, was pork"),
        ("Berliner Perle Helles", "alcoholic", "a beer that was in soft_drinks"),
        ("Krombacher's Fassbrause Maracuja", "soft_drinks", "alkoholfrei, was alcoholic"),
        ("Bruno Gelato Eis", "ice_cream", "gelato tubs, were soft_drinks"),
        ("Dr. Oetker Milchreis", "dairy", "rice pudding pots"),
        ("Milbona Yofrutta mit Schokobits", "dairy", "yoghurt pots, were sweets"),
        ("REWE Bio Tomatenmark", "pantry", "tomato paste is not fresh produce"),
        ("REWE Bio Edamame", "frozen", "the pack states tiefgefroren"),
        ("Dr. Oetker Bistro Baguette", "frozen", "a frozen pizza baguette, was bakery"),
        ("Mohnhappen", "bakery", "a yeast pastry"),
        ("Petersilie", "vegetables", "a fresh bunch"),
        ("REWE Bio Falafel-Bällchen", "vegan", "REWE Bio pflanzlich"),
    ],
)
def test_photo_audit_batch4(name, expected, why):
    assert classify(name, None, None) == expected, why


def test_nutella_and_yogurette_were_rejected_as_broad_tokens():
    """Pinned so they aren't re-"found": unlike `bananen`, whose one false positive was
    NAMEABLE (`bananen-kirsch`), these brands span forms that a substring can't separate —
    the jar vs the ice cream vs the biscuit, the chocolate bar vs the Stieleis."""
    assert classify("Nutella", None, None) == "sweets"
    assert classify("Nutella Ice Cream", None, None) == "ice_cream"
    assert classify("Ferrero Yogurette", None, None) == "sweets"


# --- 2026-08-03 new-week audit: the `other` bucket refilled to 6.4% on the new flyers -------

@pytest.mark.parametrize(
    "name,expected,why",
    [
        ("Altenburger Ziegenrolle", "cheese", "a goat-cheese roll"),
        ("Aoste Stickado", "pork", "air-dried salami sticks"),
        ("Bad Reichenhaller Alpen-Jodsalz XXL", "pantry", "salt"),
        ("Dr. Oetker Ristorante", "frozen", "frozen pizza"),
        ("Dovgan Taschki Pelmeni", "ready_meals", "filled dumplings — heat-and-eat"),
        ("EDEKA Heimatliebe Zwetschen", "fruits", "plums"),
        ("Kosmonaut Hell", "alcoholic", "a 0,5 l Dose with Pfand — beer"),
        ("MALTESERS", "sweets", None),
        ("TRADER JOE'S Macadamia", "snacks", "roasted salted nuts"),
        ("GUT&GÜNSTIG Lieblings-Kaurollchen", "pet", "an Ergänzungsfuttermittel"),
        ("House of Thêom Eau de Parfum", "fragrance", "was in the `other` bucket"),
        ("Pakchoi", "vegetables", None),
        # The GUARD: `macadamia` above would otherwise take this for snacks.
        ("NUII Stieleis Salted Caramel & Australian Macadamia", "ice_cream", "an ice lolly"),
    ],
)
def test_new_week_other_bucket(name, expected, why):
    assert classify(name, None, None) == expected, why or name


@pytest.mark.parametrize(
    "name,caption,expected",
    [
        # These NAMES say nothing at all; only the caption carries the designation.
        ("3 Glocken Genuss Pur", "Teigwaren aus Hartweizen 500 g", "pantry"),
        ("Casa Modena Salame Gran Magro", "feine Salamispezialität 100 g", "pork"),
        ("Heinrichsthaler Der Radeberger", "Käsescheiben, versch. Sorten 125-g", "cheese"),
        ("Salz-Pfefferkrusti", "Weizenkleingebäck verfeinert mit Pfeffer", "bakery"),
        ("Multi 12", "Fruchtsaftgetränk, versch. Sorten", "soft_drinks"),
        ("Proviant", "Erfrischungsgetränke, teilweise koffeinhaltig", "soft_drinks"),
        ("Choceur Peanuts XXL", "Geröstete Erdnüsse, umhüllt von Milchschokolade", "sweets"),
    ],
)
def test_new_week_caption_only_products(name, caption, expected):
    assert classify(name, None, None, caption) == expected


def test_a_caption_signal_must_be_a_designation_not_an_ingredient():
    """`gewürzgurken` correctly files a jar of gherkins as pantry — but "Dillhappen:
    Heringsfilethappen mit Gewürzgurken" is HERRING *with* gherkins, and it was being served as
    pantry until a fish entry went in front. The false positive was nameable, so it is guarded
    rather than the whole signal being dropped."""
    assert classify("Dillhappen", None, None,
                    "Heringsfilethappen mit Gewürzgurken, in einer feinen Soße") == "fish"
    assert classify("Hengstenberg Knax", None, None, "Gewürzgurken 720-ml-Glas") == "pantry"


# --- 2026-08-03 photo audit + four convention calls -----------------------------------------

@pytest.mark.parametrize(
    "name,expected,why",
    [
        # The CUT-vs-SPECIES class, this week as Rouladen/Braten/Gulasch.
        ("BauernGut Burger-Patty", "beef", "the label reads 'bestes Rindfleisch'"),
        ("Eigene Herstellung Lamm-Spieß »Despacito«", "other_meat", "lamb"),
        ("Billie Green Frikadellen", "vegan", "VEGANE FRIKADELLEN on the pack"),
        ("GUT&GÜNSTIG Paniermehl", "pantry", "breadcrumbs, not meat"),
        ("Knorr Fix Air Fryer Hähnchen Döner Style", "pantry", "a 30 g seasoning sachet"),
        ("Tischfertig Hühnerfrikassee", "ready_meals", "ready-to-serve"),
        ("Rama Cremfine", "dairy", "pourable cooking cream, not a spread"),
        ("Nestlé Nesquik", "pantry", "cocoa powder"),
        ("Kilbeggan Irish Whiskey", "alcoholic", "was in soft_drinks"),
        ("Starbucks Caffè Latte", "coffee", "chilled latte cups"),
        ("EDEKA Bio Lassi Mango", "dairy", "a Joghurtdrink"),
        ("NIXE Thunfisch Filets", "fish", "tinned tuna, was in soft_drinks"),
        ("Jever Fun 0.0%", "soft_drinks", "alcohol-free pilsener"),
        ("Frische Lauchterrine", "cheese", "Landfrischkäse with leek"),
        ("Golßener Spreewälder Gurkensülze", "pork", "meat aspic"),
        ("Chio Tortillas Wild Paprika", "snacks", "tortilla chips, were bakery"),
        ("Loacker Thins", "sweets", "wafers"),
        ("Kathi Tortenmehl", "pantry", "a Backmischung"),
    ],
)
def test_photo_audit_2026_08_03(name, expected, why):
    assert classify(name, None, None) == expected, why


@pytest.mark.parametrize(
    "name,leaf,expected",
    [
        # These need the real PATH: pathless the old `rind`/`kalb` keywords already answer beef,
        # so a pathless test passes with the rule REMOVED and proves nothing. The bug is that
        # `Rouladen` and `Schnitzel` are CUT nodes mapped to pork, and layer 3 beats layer 6.
        ("BLACK PREMIUM Irische Rinder-Rouladen", "Rouladen", "beef"),
        ("Black Morocco Irische Rinder-Rouladen", "Rouladen", "beef"),
        ("Kalbs-Schnitzel", "Schnitzel", "beef"),
        # ...and the sibling that must NOT move: a real pork schnitzel under the same node.
        ("Bauerngut Schweineschnitzel", "Schnitzel", "pork"),
    ],
)
def test_the_cut_node_must_not_outrank_the_species(name, leaf, expected):
    path = ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Fleisch",
            "Fleischzubereitungen", leaf]
    assert classify(name, None, path) == expected


@pytest.mark.parametrize(
    "name,expected,convention",
    [
        # Four calls the user made on 2026-08-03.
        ("Kinder Milchschnitte", "sweets", "milk-cream snack cakes are sweets"),
        ("Ferrero Kinder Maxi King", "sweets", "...and its sibling already was — the split is fixed"),
        ("ALDI SPORTS High-Protein-Pulver", "health", "sports-FORMAT nutrition -> health"),
        ("Schäfer´s High-Proteinbrot", "bakery", "...but an ordinary food keeps its category"),
        ("Yfood Classic Choco", "soft_drinks", "a drinkable meal replacement is a drink"),
        ("Bauerngut Eiersalat mit Schnittlauch", "ready_meals", "a deli salad is prepared food"),
        ("Popp Feinster Fleischsalat", "ready_meals", "same"),
    ],
)
def test_conventions_2026_08_03(name, expected, convention):
    assert classify(name, None, None) == expected, convention


def test_the_guards_that_the_full_diff_forced():
    """Every one of these was a REAL regression in the first simulation, not a hypothetical.

    `lassi` is a substring of "Classic"/"Classico"/"Klassik" and dragged Dallmayr, Red Bull and
    Langnese into dairy; `müsli` claims a Müsli*riegel* (a bar) and a Joghurt topped with
    muesli; `oreo`/`nutella` name ice cream as well as biscuits and spread.
    """
    assert classify("Dallmayr Classic", None, None) == "coffee"
    assert classify("Red Bull Energydrink Classic", None, None) == "soft_drinks"
    assert classify("Corny Müsliriegel Milch Classic", None, None) == "sweets"
    assert classify("Kölln Schoko-Hafer-Müsli", None, None) == "pantry"
    assert classify("bio Joghurt & Crispy Müsli", None, None) == "dairy"


def test_a_bare_alkoholfrei_is_still_rejected():
    """Re-confirmed on this week's data: ~30 real beers carry "oder alkoholfrei" as a VARIANT
    note, so the bare word would empty the beer aisle. Only 0.0 products are named."""
    assert classify("Paulaner Weißbier oder alkoholfrei", None, None) == "alcoholic"
    assert classify("Jever Fun 0.0%", None, None) == "soft_drinks"


# --- 2026-08-03 photo audit: the household + drugstore sheets -------------------------------
#
# Both fixes live INSIDE layer 1, which only runs when the path is non-food — so they are safe
# by construction and every test below must pass a non-food path. A pathless call proves nothing.

NONFOOD = ["Saison und Events", "Produkte", "Saison", "Aktionen"]


@pytest.mark.parametrize(
    "name,expected,why",
    [
        # Real FOOD hidden behind the Non-food toggle, where the user cannot see it.
        ("Backfisch", "fish", "breaded pollock fillets"),
        ("BBQ Nackensteaks XXL", "pork", "raw marinated neck steaks"),
        ("EDEKA Bio Hähnchenflügel", "poultry", "raw chicken wings"),
        ("EDEKA Herzstücke Laugen-Burger-Buns", "bakery", "pretzel burger buns"),
        ("Gazi Grill- und Pfannenkäse", "cheese", "grilling cheese"),
        ("Kölln Blütenzarte Haferflocken", "pantry", "rolled oats"),
        ("REWE Beste Wahl Speisekartoffeln", "vegetables", "loose potatoes"),
        ("REWE to go Sweet Ananas", "fruits", "fresh pineapple chunks"),
        ("Tchibo Feine Milde", "coffee", "1 kg of whole beans"),
        # `nutella` was REJECTED as a broad layer-2 token (it claims the ice cream and the
        # biscuits). As a GATED rescue token it cannot reach either, so it ships here.
        ("Ferrero Nutella", "sweets", "a jar, and the gate makes the token safe"),
    ],
)
def test_food_rescued_from_household(name, expected, why):
    assert classify(name, None, NONFOOD) == expected, why
    # ...and genuine non-food under the same root must stay household.
    assert classify("Black Torch Tankstellengrill", None, NONFOOD) == "household"


@pytest.mark.parametrize(
    "name,expected",
    [
        ("BETTY BARCLAY Woman Eau de Parfum", "fragrance"),
        ("Garnier Nutrisse Ultra Crème Color", "hair"),
        ("L'Oréal Paris Anti-Falten Experte", "face"),
        ("Alterra Aromadusche Glücksgefühl", "body"),
        ("Bullrich Heilerde Kapseln", "health"),
        ("Bübchen Baby Wundschutzcreme", "baby"),
        ("Dan Klorix Hygiene-Reiniger", "cleaning"),
        ("Calgon Wasserenthärter 4-in-1", "laundry"),
        ("Beneful Hund Trockennahrung", "pet"),
        ("CACHET Katzentoilette", "pet"),
    ],
)
def test_drugstore_products_leave_the_grocery_household_chip(name, expected):
    assert classify(name, None, NONFOOD) == expected


def test_the_drugstore_additions_are_APPENDED_so_existing_rules_win():
    """Order is the rule here. Inserted at the FRONT, the new `duschgel` token made a Cien Kids
    "2in1 Shampoo & Duschgel" resolve to body; appended, the existing `shampoo` rule still wins."""
    assert classify("Cien Kids 2in1 Shampoo & Duschgel", None, NONFOOD) == "hair"


def test_olia_is_qualified_because_it_is_a_substring_of_angustifolia():
    """The full-corpus diff missed this and the SUITE caught it: a bare `olia` (the Garnier
    hair-colour line) fires inside "Lavendel angustifolia" and turned a garden plant into a
    hair product."""
    assert classify("Lavendel angustifolia", None, ["Heimwerken und Garten", "Marken"]) == "household"
    assert classify("Garnier Olia Coloration", None, NONFOOD) == "hair"


# --- 2026-08-03, part 2: the last five conventions + two rescue leaks -----------------------

# The source's real garden path for a potted plant. It matters that this is the WHOLE path:
# layer 1 decides on it and never falls through, so a pathless call exercises a different rule.
GARDEN = ["Heimwerken und Garten", "Produkte", "Garten", "Pflanzen ", "Gartenbepflanzung",
          "Gartenpflanzen", "Pflanzen", "Bäume", "Sträucher", "Obststräucher",
          "Beerensträucher", "Heidelbeerstrauch", "Heidelbeere"]
KAESE = ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Milchprodukte", "Käse"]
FISCH = ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Fisch", "Fischzubereitung",
         "Fischbrötchen"]


def test_a_living_plant_named_after_its_fruit_is_not_produce():
    """Served LIVE in the Fruits chip: a 50 cm blueberry BUSH at 4,99 EUR. `heidelbeere` is a
    `_FOOD_RESCUE` token and the plant arrives on a garden path, so layer 1 rescued it — and the
    `topfcover` -> household entry in `_FORM_OVERRIDES` sits at layer 2, which layer 1 never
    reaches. The veto is the only thing that can fix the real row, so this test MUST pass the
    real path; pathless it passes with the veto removed and proves nothing.
    """
    assert classify("Heidelbeere im Topfcover", None, GARDEN) == "household"
    # ...while a real punnet of blueberries under a promo/pet node still gets rescued. That is
    # the whole point of the rescue and the veto must not cost it.
    assert classify("REWE Regional Heidelbeeren", None, PET) == "fruits"
    assert classify("ALL SEASONS Kulturheidelbeeren", None, NONFOOD) == "fruits"


def test_the_layer_2_potted_plant_entry_covers_the_pathless_copy():
    """The source ships the same plants without a path too, where layer 1 is skipped entirely.
    Both layers earn their place; neither alone covers both shapes."""
    assert classify("Heidelbeere im Topfcover", None, None) == "household"
    assert classify("XXL-Basilikum im Topf", None, None) == "household"
    assert classify("XXL-Basilikum im Topf", None, GARDEN) == "household"
    # `basilikum` alone would take this, which is why the token carries "im topf".
    assert classify("ZOTT Zottarella-Minis Classic oder Basilikum", None, None) == "cheese"


def test_a_coffee_mug_is_not_coffee():
    """`_FOOD_RESCUE` carries a bare `kaffee` on purpose (the narrow `kaffeepad` form made the
    veto dead code), and it was rescuing porcelain: two `Kaffeebecher` were served in the Coffee
    chip. A bare `becher` is NOT usable as the veto — Becherovka is a liqueur, Knorr Snackbecher
    is pantry, and Jacobs Instant-Becherportionen is genuinely coffee."""
    assert classify("GUT&GÜNSTIG Kaffeebecher", None, ["Möbel und Wohnen", "Kaffeebecher"]) == "household"
    # Real rows, with the paths the source actually sends them on.
    assert classify("Jacobs Instant-Becherportionen", "Jacobs",
                    ["Lebensmittel und Getränke", "Produkte", "Getränke", "Heißgetränk",
                     "Kaffee"]) == "coffee"
    assert classify("Becherovka Kräuterlikör", None, None) == "alcoholic"
    assert classify("Knorr Snackbecher", None, None) == "pantry"
    # ...and the rescue the veto must not cost: real coffee under a non-food path.
    assert classify("Senseo Classic", None, ["Elektronik und Technik", "Senseo"]) == "coffee"


@pytest.mark.parametrize(
    "name,expected,why",
    [
        # BREADED cheese is a freezer product (user's call). It was split across two chips —
        # proof that leaving it alone was not a stable answer.
        ("CHEF SELECT Mozzarella-Sticks", "frozen", "Tiefgefroren 750 g; was cheese"),
        ("Alpenhain Mozzarella Sticks", "frozen", "same product, was snacks — the split"),
        ("EDEKA Herzstücke Mini-Backkäse", "frozen", "knusprig paniert, vorgebacken"),
        ("GUT&GÜNSTIG Back-Camembert", "frozen", "fertig paniert und knusprig vorgebacken"),
        # ...and plain baked/grilled cheese is NOT breaded and must stay put.
        ("Rougette Ofenkäse", "cheese", "cheese for the oven, no coating"),
        ("EDEKA Herzstücke Halloumi Grillkäse", "cheese", "grilling cheese"),
        ("Galbani Mozzarella", "cheese", "just mozzarella"),
        ("Gazi Grill- und Pfannenkäse", "cheese", "same"),
    ],
)
def test_breaded_cheese_is_frozen_but_baked_cheese_is_cheese(name, expected, why):
    # The Käse PATH is what makes this a layer-2 job: at layer 6 the path would win first.
    assert classify(name, None, KAESE) == expected, why


def test_a_filled_fish_roll_is_a_ready_meal():
    """User's call: one serving you eat as it is, like the deli salads. It has to beat the
    source's own `Fisch > Fischzubereitung` path, hence layer 2."""
    assert classify("Fischbrötchen", None, FISCH) == "ready_meals"
    # ORDER: this entry sits ABOVE the `matjes` guard. Appended after it, the full-corpus diff
    # showed "Fischbrötchen Rauchmatjes" staying in fish — the same product in two chips.
    assert classify("Fischbrötchen Rauchmatjes", None, FISCH) == "ready_meals"
    # The fillings on their own are still fish, and `matjes` still guards `senf`.
    assert classify("Matjes Honig-Senf", None, None) == "fish"
    assert classify("Backfisch", None, None) == "fish"
    assert classify("Seelachsschnitzel", None, None) == "fish"


@pytest.mark.parametrize(
    "name,expected,why",
    [
        # User's call: industrially packaged, individually-portioned cake is confectionery.
        ("GUT&GÜNSTIG Mini-Muffins", "sweets", "225 g Beutel"),
        ("KUCHENZAUBER Muffins XXL", "sweets", "packaged muffins"),
        ("Baileys Muffins", "sweets", "the row the `muffin` entry was originally written for"),
        ("Schoko Donut mit Schokostreusel", "sweets", "3 Stück, packaged"),
        ("DUNKIN' Donuts Kakao Haselnuss", "sweets", "2er-Pack"),
        ("NESTLÉ Yes Kuchenriegel", "sweets", "3 x 10,67 g cake BARS"),
        ("FINEST BAKERY Mini-Kuchen", "sweets", "packaged Zitronen-/Marmorkuchen"),
        ("Deluxe Baklava Pistazie", "sweets", "already resolved this way — pinned"),
        # ...and cake sold as cake stays in Bakery. A bare `kuchen`/`torte` token was simulated
        # and rejected because it drags every one of these along with it.
        ("Flammkuchen", "bakery", "SAVOURY — the reason a bare `kuchen` is unusable"),
        ("Medovnik Schichttorte", "bakery", "Gekühlt"),
        ("NOSTJA Frischkuchen", "bakery", "Gekühlt"),
        ("Schäfer's Kuchenglück Apfel", "bakery", "fresh from the in-store bakery"),
        ("Zupfstreuselkuchen", "bakery", "fresh tray bake"),
    ],
)
def test_packaged_cake_formats_are_sweets_but_cake_stays_bakery(name, expected, why):
    assert classify(name, None, None) == expected, why


def test_the_savoury_donut_guard():
    """`MEIN BESTES Filled-Pizza-Donut` is a cheese-filled pizza snack. Layer 2 outranks the
    `Hartkäse` path node that gets it right, so the sweets block needs a guard above it."""
    hartkaese = ["Lebensmittel und Getränke", "Produkte", "Lebensmittel", "Milchprodukte",
                 "Käse", "Hartkäse"]
    assert classify("MEIN BESTES Filled-Pizza-Donut", None, hartkaese) == "cheese"
    assert classify("MEIN BESTES Filled-Pizza-Donut", None, None) == "cheese"


def test_every_rice_cake_stays_in_snacks():
    """User's call, recorded so a later audit does not "fix" it: the rice cake is the product
    and the chocolate is a variant of it, so the line lives in ONE chip. `_OVERRIDES` already
    puts `reiswaffel` ahead of the `waffel` -> sweets rule; this pins that it stays that way
    even when the name says Schoko."""
    assert classify("EDEKA Bio Reiswaffeln", None, None) == "snacks"
    assert classify("Schoko-Reiswaffeln", None, None) == "snacks"
    assert classify("Reiswaffeln mit Vollmilchschokolade", None, None) == "snacks"
    # The sibling that proves the override is doing work: a plain wafer is still sweets.
    assert classify("Amicelli Waffelröllchen", None, None) == "sweets"


# --- 2026-08-04: two defects the sub-group work surfaced -------------------------------------

KOERPER = ["Drogerie und Haushalt", "Produkte", "Drogerie", "Körperpflege"]


def test_mundspuelung_is_dental_not_hair():
    """`_DRUGSTORE_RULES` is first-hit-wins and the hair rule's bare `spülung` sat ABOVE the
    dental block that already listed `mundspülung` — so five Listerine/meridol mouthwashes were
    served in the HAIR aisle. Found by tallying tokens per category, not by reading the table.

    (The `mundspülung` entry in `_FORM_OVERRIDES` cannot help here: that is layer 2, and layer 1
    decides a non-food path without ever falling through — so this test MUST pass a path.)
    """
    assert classify("Listerine Mundspülung", None, NONFOOD) == "dental"
    assert classify("meridol Mundspülung Zahnfleischschutz", None, NONFOOD) == "dental"
    # ...and a real hair conditioner still resolves to hair, which is what `spülung` is for.
    assert classify("Gliss Kur Spülung", None, NONFOOD) == "hair"
    assert classify("Haarspülung Repair", None, NONFOOD) == "hair"


def test_paper_goods_are_household_not_body_care():
    """The source files toilet roll and tissues under `Körperpflege`, so the drugstore PATH MAP
    was serving them as Body & Shower. They were also SPLIT — 23 rows household vs 22 body for
    `toilettenpapier` alone — so leaving them was not a stable answer either. `_DRUGSTORE_VETO`
    runs before the path map, so it is the only lever that reaches them."""
    for name in ("Zewa Toilettenpapier", "GUT&GÜNSTIG Taschentücher",
                 "Renova Textilpapier-Küchenrolle", "Cottonelle Feuchtes Toilettenpapier"):
        assert classify(name, None, KOERPER) == "household", name
    # The sibling that must NOT move: genuine body care under the same node.
    assert classify("Nivea Duschgel", None, KOERPER) == "body"
    assert classify("Dove Deospray", None, KOERPER) == "body"


# --- Structural guards on the ordered rule tables (2026-08-04) --------------------------------
# Three times in one day a rule was written for a product it could never reach. These two tests
# make that class fail at review time instead of being discovered by accident months later.

_ORDERED_TABLES = ("_FORM_OVERRIDES", "_CAPTION_SIGNALS", "_OVERRIDES", "_RULES",
                   "_DRUGSTORE_RULES")


def _shadowed_tokens(table_name):
    """Entries that can never fire, with the entry that eats them.

    These tables are scanned in order and match with `token in text`, so a later token T is
    unreachable when an EARLIER token is a SUBSTRING of it — everything matching T matched the
    earlier one first. Substring, not equality: `protein-pulver` swallows `high-protein-pulver`,
    and `torte` swallows `tortellini`. Only a differing SLUG is a defect; a same-slug repeat is
    the ordering idiom used all over this file (a guard restated inside its semantic block).
    """
    import app.categories as mod
    table = getattr(mod, table_name)
    flat = [(i, slug, tok) for i, (slug, toks) in enumerate(table) for tok in toks]
    out = []
    for j, (idx, slug, tok) in enumerate(flat):
        winner = next((e for e in flat[:j] if e[2] in tok), None)
        if winner and winner[1] != slug:
            out.append((table_name, winner, (idx, slug, tok)))
    return out


def test_no_rule_is_shadowed_by_an_earlier_one_with_a_different_slug():
    """A shadowed entry is worse than dead code: it *looks* like the answer while a different
    one is being served, which is exactly how "Tortellini" resolved to BAKERY (via `torte`) and
    a baby shampoo to HAIR (via `shampoo`) — both entries existed and neither could fire.
    """
    found = [f for name in _ORDERED_TABLES for f in _shadowed_tokens(name)]
    assert not found, "unreachable rules:\n" + "\n".join(
        f"  {t}: [{w[0]}]{w[1]} {w[2]!r} always wins over [{d[0]}]{d[1]} {d[2]!r}"
        for t, w, d in found
    )


# Drugstore-slug tokens that live in `_FORM_OVERRIDES` (layer 2) but NOT in `_DRUGSTORE_RULES`
# (layer 1). A drugstore product reaches the drugstore step only by arriving on a non-food path,
# and layer 1 decides such a path without ever falling through — so for those products the
# layer-2 entry is unreachable BY CONSTRUCTION. They still fire for a pathless copy, which is why
# the drift is silent. Empty this list by mirroring a token into `_DRUGSTORE_RULES`, each one
# simulated over the full corpus first: `vogelfutter` would turn a "Vogelfutterhaus" (a bird
# feeder, household) into pet food. It is a RATCHET — it may shrink, never grow.
_UNMIRRORED_DRUGSTORE_TOKENS = {
    "body": {"bodycream", "carefree"},
    "cleaning": {"allzwecktücher", "wc-spüler"},
    "dental": {"blend-a-dent", "colgate", "listerine"},
    "hair": {"strong power"},
    "health": {"eaa ", "protein-pulver", "proteinpulver"},
    "pet": {"beef stick", "coshida", "dental-stick", "ergänzungsfuttermittel", "hello my cat",
            "hundenahrung", "hygienestreu", "katzensticks", "kaurollchen", "kaurollen",
            "kausnack", "kaustange", "lieblingsmenü", "nassfutter", "nassnahrung", "tierfutter",
            "tiernahrung", "trockenfutter", "trockennahrung", "vogelfutter"},
}


def test_the_two_drugstore_tables_do_not_drift_further():
    """Measured 2026-08-04: 31 of the 40 drugstore tokens in `_FORM_OVERRIDES` were unreachable
    for any product carrying a path — which is why "Hundetrockenfutter" resolves to `pet`
    pathless but `household` with a real non-food path, half-breaking the pet convention.

    Fixing them was deferred (no served offer is affected this week). This pins the baseline so
    a NEW one fails immediately, at the moment the mistake is made.
    """
    from app.categories import _DRUGSTORE_RULES, _FORM_OVERRIDES
    drugstore_slugs = {"hair", "face", "body", "dental", "makeup", "fragrance", "baby",
                       "health", "cleaning", "laundry", "pet"}
    reachable = {tok for _slug, toks in _DRUGSTORE_RULES for tok in toks}
    missing = {}
    for slug, toks in _FORM_OVERRIDES:
        if slug in drugstore_slugs:
            gap = {t for t in toks if t not in reachable}
            if gap:
                missing.setdefault(slug, set()).update(gap)
    new = {s: sorted(t - _UNMIRRORED_DRUGSTORE_TOKENS.get(s, set())) for s, t in missing.items()}
    new = {s: t for s, t in new.items() if t}
    assert not new, (
        f"new unreachable drugstore rule(s): {new}. A layer-2 drugstore token only fires for a "
        "PATHLESS product — mirror it into _DRUGSTORE_RULES (simulate over the corpus first)."
    )
    # ...and the ratchet may only tighten: a token that got mirrored must leave the allowlist.
    stale = {s: sorted(t - missing.get(s, set())) for s, t in _UNMIRRORED_DRUGSTORE_TOKENS.items()}
    stale = {s: t for s, t in stale.items() if t}
    assert not stale, f"allowlist is stale — these are reachable now, drop them: {stale}"


# --- 2026-08-08: the "other" bucket audit -------------------------------------------------
# `other` is the fallback, so nothing REACHES these rules except a product that no layer could
# answer. Every product below fell all seven layers through to `other`, verified with explain().
#
# The finding that made this urgent: the app's Non-food toggle filters `household` and ONLY
# `household` (`dealFilters.ts`: `offers.filter((o) => o.category !== 'household')`), so a
# non-food product sitting in `other` renders in the middle of the grocery list. A deck chair,
# two Pokémon toys, two children's books and a mobile-phone plan were doing exactly that.

# The brand-leaf food path these products carry: a food ROOT that dead-ends on a brand, so
# layer 1 never fires (it is not non-food) and layer 3 finds no category node.
BRAND_LEAF = ["Lebensmittel und Getränke", "Marken", "Marken Lebensmittel", "EDEKA"]


@pytest.mark.parametrize(
    "name, brand, expected, why",
    [
        ("Lock&Lock Frischhaltedosen", "Lock&Lock", "household", "plastic storage boxes"),
        ("CRAZE Kreativspiel", "CRAZE", "household", "a children's craft toy"),
        ("SANSIBAR Liegestuhl", "SANSIBAR", "household", "a deck chair"),
        ("Pokémon Plüsch", "Pokémon", "household", "a plush toy"),
        ("Pokémon Battle Spinner", "Pokémon", "household", "a toy"),
        ("Leselöwen Leselernbuch", None, "household", "children's reading books"),
        ("Lernblock/Kompaktwissen & Vorschul-/Schulanfänger-Buch", None, "household", "books"),
    ],
)
def test_non_food_in_other_is_moved_to_household_so_the_toggle_can_hide_it(
    name, brand, expected, why
):
    """These are pathless, so only the name can decide. They live in the LAST `_RULES` tuple,
    which is what makes them safe: a token there can only ever catch a product that would
    otherwise fall through to `other`."""
    assert classify(name, brand) == expected, why


def test_a_sim_card_filed_under_the_food_root_still_reaches_household():
    """The structural case. The source files Lidl's mobile plan under
    `Lebensmittel und Getränke > ... > LIDL Connect Classic` — a FOOD root — so layer 1's
    non-food branch can never see it and no amount of path work would help. A pathless test
    would pass without proving that, so this one MUST pass the real path."""
    sim_path = [
        "Lebensmittel und Getränke", "Marken", "Marken Lidl Lebensmittel", "LIDL Connect Classic",
    ]
    assert classify("Lidl Connect Unlimited on Demand S", "Lidl Connect", sim_path) == "household"


@pytest.mark.parametrize(
    "name, brand, expected, why",
    [
        ("Deutscher Spitzkohl, lose", None, "vegetables", "loose cabbage, no path at all"),
        ("Deutscher Chinakohl", None, "vegetables", "same"),
        ("Florette Sommergenuss", "Florette", "vegetables", "a bagged salad"),
        ("Mein bestes Pekannuss-Tasche", "Mein bestes", "bakery", "a filled Plunderteig pastry"),
        ("Caprese-Snack", None, "bakery", "photo: baked at the in-store SB-Marktbäckerei"),
        ("ASIA GREEN GARDEN Maiskölbchen", "ASIA GREEN GARDEN", "pantry", "pickled, in a jar"),
        ("EDEKA Bio Kräuter", "EDEKA Bio", "pantry", "culinary herbs, like Petersilie"),
        ("Hellmann's Chili", "Hellmann's", "pantry", "a sauce"),
        ("Remia Yildriz", "Remia", "pantry", "a kebab sauce"),
        ("Ya'ummi Classic Samurai", "Ya'ummi", "pantry", "a sauce"),
        ("Zörbiger Überrübe", "Zörbiger", "pantry", "a sweet spread; spreads stay pantry"),
        ("Original Zörbiger Über Rübe", "Zörbiger", "pantry", "same product, spelled apart"),
        ("Capico Knusper Röllchen", "Capico", "sweets", "filled wafer rolls"),
        ("Frikoni High Protein Dessert", "Frikoni", "dairy", "a pudding, like Ehrmann's"),
    ],
)
def test_food_rescued_from_the_other_bucket(name, brand, expected, why):
    assert classify(name, brand) == expected, why


def test_a_pasta_bag_is_recognised_from_its_caption_alone():
    """"EDEKA Genussmomente" is the whole stored name — the source drops the "Teigwaren" line
    from the title. `versch. Ausformungen` (pasta SHAPES) is the flyers' own designation: 21 of
    the 22 stored offers carrying it were already pantry."""
    assert classify(
        "EDEKA Genussmomente", None, BRAND_LEAF,
        "traditionelle Herstellung, versch. Ausformungen 500g Beutel",
    ) == "pantry"


def test_berief_oat_drink_matches_the_other_oat_drinks():
    """Oatly/Alpro/MYVAY oat drinks all resolve to `vegan` at layer 0, so Berief's falling to
    `other` split one product across two chips on brand alone."""
    assert classify("Berief Bio Haferdrink", "Berief", BRAND_LEAF) == "vegan"
    assert classify("Oatly Haferdrink", "Oatly") == "vegan"


@pytest.mark.parametrize(
    "name, brand, unit, path, expected, why",
    [
        # `kohl` (rejected): fires inside Holzkohle. household is the LAST tuple, so a `kohl`
        # token in vegetables would take charcoal off the grill and into the produce chip.
        ("Grillmeister Holzkohle", "Grillmeister", "zum Grillen 3 kg", BRAND_LEAF,
         "household", "charcoal is not a cabbage"),
        # `pekannuss` (rejected) — see test_a_bare_nut_word_would_claim_the_nut below for the
        # case that actually discriminates. The branded pack is snacks via the brand map.
        ("Alesto Pekannusskerne", "Alesto", "Naturbelassen. 200 g", BRAND_LEAF,
         "snacks", "actual nuts, not a nut pastry"),
        # `kräuter` (rejected): 54 stored rows across 13 categories. Three of them:
        ("Bresso Feine Kräuter", "Bresso", "8 x 15-g-Pckg.", None, "cheese", "a cream cheese"),
        ("Jägermeister Kräuterlikör", "Jägermeister", "35% Vol. 0,7-l-Fl.", None,
         "alcoholic", "a herbal liqueur"),
        ("GUT&GÜNSTIG Kräuterbaguette", "GUT&GÜNSTIG", "vorgebacken", None, "bakery", "bread"),
        # `saucen` as a CAPTION signal (rejected): designation, not ingredient — the sauce here
        # is what the nuggets come WITH. This is why the three sauces got brand entries instead.
        ("GUT&GÜNSTIG Chicken Nuggets", "GUT&GÜNSTIG", "mit Pommes und Saucen 300/350 g Schale",
         BRAND_LEAF, "poultry", "chicken served with sauces is still chicken"),
    ],
)
def test_the_tokens_the_corpus_diff_rejected(name, brand, unit, path, expected, why):
    """Each of these looked obviously right while being typed and was killed by simulating it
    over all 8,310 stored products. They are pinned so the next audit does not re-add them."""
    assert classify(name, brand, path, unit) == expected, why


def test_the_florette_cheese_is_saved_by_its_caption_not_by_luck():
    """`florette` -> vegetables is only safe because "Fromager d'Affinois Florette" — which
    arrives on a `Florette` BRAND-LEAF path, so the path cannot help — is caught by the CHEESE
    CAPTIONS at layer 2b, four layers above the keyword. Two of them cover it independently
    (`fett i. tr` wins, `weichkäse` would), so removing either alone changes nothing; it takes
    dropping the caption block to put a goat cheese in the vegetable chip. Worth stating,
    because it means no single-token sabotage can prove this test bites."""
    assert classify(
        "Fromager d’Affinois Florette", None,
        ["Lebensmittel und Getränke", "Marken", "Marken Lebensmittel", "Florette"],
        "franz. Weichkäse aus Ziegenmilch, mild-cremiger Geschmack, 45% Fett i. Tr. 125 g",
    ) == "cheese"


def test_a_bare_nut_word_would_claim_the_nut_itself():
    """Why the bakery rule is `nuss-tasche` and not `pekannuss`.

    The obvious counter-example — "Alesto Pekannusskerne" — does NOT discriminate: `alesto` sits
    in the brand map at layer 4, which outranks these keywords whatever they say. The case that
    does is an unbranded pack, which has nothing above layer 6 to save it. It has no readable
    signal at all today, and `other` is the honest answer for it; what it must never be is a
    pastry."""
    assert classify("Alesto Pekannusskerne", "Alesto") == "snacks"  # saved by the brand map
    assert classify("Pekannusskerne", None) != "bakery"
    # ...while the pastry the rule was written for still resolves.
    assert classify("Mein bestes Pekannuss-Tasche", "Mein bestes") == "bakery"


# --- 2026-08-09 flyer-week audit ------------------------------------------------------------
# The `other` chip refilled to 63 products (4.3%) on the new week. Almost all of them sit on a
# BRAND-LEAF path (`… > Marken > Marken Lebensmittel > <brand>`), which carries no category, so
# the path layer correctly declines and only name/caption rules can reach them.


@pytest.mark.parametrize(
    "name, brand, expected, why",
    [
        ("Lily & Dan Jogginganzug", "Lily & Dan", "household", "a tracksuit"),
        ("COOX Gugelhupfform", "COOX", "household", "a baking tin, not a cake"),
        ("Feigenkaktus „Hands up«", None, "household", "a living cactus"),
    ],
)
def test_the_new_weeks_non_food_reaches_household(name, brand, expected, why):
    """Same argument as the previous audit: only `household` is hidden by the app's Non-food
    toggle, so a non-food product that falls through to `other` renders among the groceries.
    These live in the LAST `_RULES` tuple, so they can only catch what was already `other`."""
    assert classify(name, brand) == expected, why


def test_the_cactus_rule_is_the_species_not_the_pot():
    """A `topfcover` token already existed for exactly this class of product, and it could not
    fire: the flyer wrote the caption as "in dekorativem **Pot**cover". Keying on `kaktus`
    instead makes the rule independent of how the pot is spelled — and it must leave the plain
    potted cactus, which was already correct, exactly where it is."""
    assert classify("Feigenkaktus „Hands up«", None, None, "in dekorativem Potcover") == "household"
    assert classify("Kaktus", None, None, "Für drinnen, Versch. Sorten. ca. 15-20 cm") == "household"


@pytest.mark.parametrize(
    "name, brand, unit, expected",
    [
        ("BBQ Oktopus-Arme", None, "Vorgekocht; zum Braten", "fish"),
        ("Pulpo", None, "Aus dem Ostatlantik, fertig gegart", "fish"),
        ("Osso Buco", None, "vom Kalb, in der Bratfolie", "beef"),
        ("Best Burger Hamburger Pattys", "Best Burger", "vom Rind", "beef"),
        ("Deluxe Barbarie Entenbrustfilet", "Deluxe", "Ca. 293-450 g", "poultry"),
        ("Gut Drei Eichen Sülzkotelett", "Gut Drei Eichen", "Mit Ei und Gurke", "pork"),
        ("Rasting Magerer Aspikaufschnitt", "Rasting", "mit Gemüse", "pork"),
        ("MILSANI Prima Donna Maturo", "MILSANI", "Käsespezialität in Scheiben", "cheese"),
        ("PRÉSIDENT Carré Gourmet/Snack", "PRÉSIDENT", "Snack in versch. Sorten", "cheese"),
        ("Ergüllü Weißer Grieche", "Ergüllü", "mediterrane Spezialitäten", "cheese"),
        ("Mein Bestes Börekstange Gyros-Style", "Mein Bestes", "Teigstange, gefüllt", "bakery"),
        ("GUT&GÜNSTIG Bienenstich", "GUT&GÜNSTIG", "nach traditionellen Rezepten", "bakery"),
        ("Brandt Minis", "Brandt", "versch. Sorten 120-g-Btl.", "bakery"),
        ("Dr. Oetker La Mia Grabde oder Famillia", "Dr. Oetker", "Pizza, versch. Sorten", "frozen"),
        ("Double Cheeseburger", None, "Je 1,05 kg, 6er-Pack", "frozen"),
        ("Block House Block Burger", "Block House", "tiefgefroren", "frozen"),
        ("Sol & Mar Teigtaschen", "Sol & Mar", "Versch. Sorten, tiefgefroren", "ready_meals"),
        ("Ben's Original Street Food", "Ben's Original", "versch. Sorten, 250 g", "ready_meals"),
        ("Pringles", None, "Stapelchips, versch. Sorten", "snacks"),
        ("Kellogg's Cheez-it", "Kellogg's", "versch. Sorten 120g Beutel", "snacks"),
        ("TRADER JOE'S Cashew-kerne", "TRADER JOE'S", "Naturbelassen 200-g-Beutel", "snacks"),
        ("Balisto", None, "Versch. Sorten, z. B. Korn", "sweets"),
        ("Kinder Country", "Kinder", "Je 376 g Standardpackung", "sweets"),
        ("Aseli Riesenmäuse", "Aseli", "Schaumzucker 155g Packung", "sweets"),
        ("Dr Pepper Classic", "Dr Pepper", "Cola, Koffeinhaltig 0,33-L-Dose", "soft_drinks"),
        ("Oberbräu Hell", "Oberbräu", "20 x 0,5-l-Fl.-Kasten", "alcoholic"),
        ("EDEKA Bio Ahornsirup", "EDEKA Bio", "aus Kanada Grad A", "pantry"),
        ("Henglein Eierspätzle", "Henglein", "pfannenfertig 400-g-Btl.", "pantry"),
        ("REWE Beste Wahl Suppengrün", "REWE Beste Wahl", "Deutschland 500-g-Pckg.", "vegetables"),
        ("Tchibo Feine Milde", "Tchibo", "Natur-Mild, gemahlen 4x 250g", "coffee"),
    ],
)
def test_the_new_weeks_other_bucket_is_routed(name, brand, unit, expected):
    """Every one of these arrives on a brand-leaf path, so the path is passed for realism but
    cannot decide — pass it, because a pathless test would prove less than the real row does."""
    assert classify(name, brand, BRAND_LEAF, unit) == expected


def test_oreo_is_safe_in_sweets_only_because_a_layer_2_form_word_takes_the_ice_cream():
    """`oreo` is a multi-category brand — the biscuit AND a Stieleis — which is normally
    disqualifying. It ships anyway because the two are separated by LAYER: `stieleis` sits in
    `_FORM_OVERRIDES` at layer 2 and claims the ice cream before this keyword table is ever
    reached.

    The first version of this docstring said the separation came from the `ice_cream` tuple
    running before `sweets` within `_RULES`. That was wrong — explain() shows layer 2 deciding,
    so those tuples never get a turn — and it matters, because it points a future editor at the
    wrong guard when they go to change one.

    Like the Florette cheese below, NO SINGLE-TOKEN SABOTAGE CAN PROVE THIS TEST BITES:
    `stieleis` appears five times (`_PATH_MAP`, two `_FORM_OVERRIDES` entries, a caption signal
    and the `ice_cream` keyword tuple), so removing any one leaves the other four holding. It
    takes disabling all five to turn the ice cream into a biscuit — which is how it was
    verified, and is worth stating so a future audit does not read a green single-token break
    as "this test is decoration"."""
    assert classify("Oreo", None, BRAND_LEAF, "kakaohaltiger Doppelkeks") == "sweets"
    assert classify("Oreo Stieleis XXL", None, BRAND_LEAF, "Versch. Sorten, Tiefgefroren") == "ice_cream"


def test_a_hundred_percent_juice_caption_beats_the_flavour_word_in_the_name():
    """The caption layer earns its place here: "Tabaluga Pausen-Drink Mehrfrucht-Karotte" was
    served in **Vegetables**, because `karotte` fires at layer 6 and only a signal above it can
    win. It is a designation ("100% Saft"), not an ingredient, which is the bar for this table."""
    assert classify(
        "Tabaluga Pausen-Drink Mehrfrucht-Karotte", "Tabaluga", BRAND_LEAF,
        "100% Saft, versch. Sorten 0,3 l PET",
    ) == "soft_drinks"


@pytest.mark.parametrize(
    "name, brand, unit, rejected_slug, why",
    [
        ("Corsaire Réserve du Président", "Corsaire", "Frankreich trocken 0,75-l-Fl.", "cheese",
         "a bare `président` files a French dry wine as cheese — it has NO path at all"),
        ("FIN CARRÉ Tafelschokolade", "FIN CARRÉ", "Versch. Sorten 100 g", "cheese",
         "a bare `carré` takes Lidl's pathless chocolate — cheese runs before sweets"),
        ("LYTTOS Natives Olivenöl extra", "LYTTOS", "Griechenland 0,75 l", "snacks",
         "`lyttos` is a brand-leaf range spanning 8 categories with no path to save it"),
        ("GUT&GÜNSTIG Erdnussflips", "GUT&GÜNSTIG", "mit 33% gemahlenen Erdnüssen 200g", "coffee",
         "a `gemahlen` caption is an INGREDIENT note, not a designation"),
        ("Herta Finesse Hähnchenbrust", "Herta", "versch. Sorten", "pork",
         "`herta finesse` spans pork and poultry, so the bare flyer name stays in `other`"),
    ],
)
def test_the_tokens_this_weeks_corpus_diff_rejected(name, brand, unit, rejected_slug, why):
    """Candidates that read as obviously correct while being typed, killed by simulating them
    over all 9,582 distinct stored products.

    These five are the ones whose rejection is LOAD-BEARING — each product carries no path, or
    a brand-leaf path, so nothing above layer 6 would have saved it. Three further candidates
    (`paula`, `cashew`, `beren`) were also rejected but measured PRECAUTIONARY: Paulaner,
    Cashewmus and Berentzen are each held by a real layer-3 path today, so the narrower tokens
    that shipped buy independence from that path rather than fixing a live collision. Saying so
    matters — a comment claiming a guard is what holds the line, when the path is, is the kind
    of wrong mechanism claim that gets a good rule deleted later.

    `président` is the one the corpus diff alone would have missed: the wine it steals was
    sitting in `other`, so it counted as a RESCUE rather than as a conflict. Only reading what
    actually moved caught it.
    """
    assert classify(name, brand, None, unit) != rejected_slug, why


@pytest.mark.parametrize(
    "name, leaf, expected",
    [
        ("Serum Kollagen, 30 ml", "Serum & Kur", "face"),
        ("Serum Sensitive, 30 ml", "Gesichtspflege für Männer", "face"),
        ("Babyflasche aus Glas First Choice weiß", "Babyflaschen & Kinderflaschen", "baby"),
    ],
)
def test_dm_leaves_that_read_like_a_mapped_one_but_share_no_key(name, leaf, expected):
    """`_DRUGSTORE_PATH_MAP` is an EXACT per-node lookup, so "Gesichtspflege für Männer" gets
    nothing from the "gesichtspflege" entry sitting right above it. dm sends a single flat leaf,
    so there is no parent to fall back to and these blobbed into `household`."""
    assert classify(name, None, ["Drogerie und Haushalt", "Produkte", "Drogerie", leaf]) == expected


def test_the_drugstore_household_blob_is_mostly_honest():
    """Guards against over-eager 'fixing' of a number that is not a bug. On 2026-08-09 the
    drugstore vertical read 63% household and that was CORRECT — dm was clearing children's
    clothing (102 of 131 rows). A T-shirt belongs in household; only a handful were real
    misses. Pinned so a future audit does not chase the percentage."""
    for name, leaf in [
        ("T-Shirt mit Nilpferd-Muster, beige", "Kinderpullover & -shirts"),
        ("Shorts aus Denim, blau, Gr. 98", "Kinderhosen"),
        ("Mütze aus Strick mit Fuchs-Muster", "Kinderhandschuhe, -mützen & -schals"),
        ("Duftkerze im Glas mit Blumen, 1 St", "Duftkerzen"),
    ]:
        assert classify(name, None, ["Drogerie und Haushalt", "Produkte", "Drogerie", leaf]) \
            == "household", f"{leaf} is not a miscategorisation"


# --- 2026-08-09 photo sweep -----------------------------------------------------------------
# 1,843 served products as contact sheets, reviewed against the category each was assigned.
# This is the class a keyword audit structurally cannot find: the name, brand, path AND caption
# all read plausibly for the wrong answer, and only the picture settles it.

NONFOOD_PATH = ["Tierbedarf und Tierfutter", "Marken für Tiere"]


@pytest.mark.parametrize(
    "name, brand, expected, why",
    [
        ("Bauerngut Grillkotelett", "Bauerngut", "pork", "raw pork chops"),
        ("Bauerngut Hähnchenschenkel", "Bauerngut", "poultry", "raw chicken legs"),
        ("Frische Schweine Schälrippe", None, "pork", "raw pork spare ribs"),
        ("GOLDEN SEAFOOD Garnelen", "GOLDEN SEAFOOD", "fish", "raw peeled prawns"),
        ("LYTTOS Kritharaki", "LYTTOS", "pantry", "Greek orzo pasta"),
        ("EDEKA Bio Dinkelkrusti", "EDEKA Bio", "bakery", "bake-off bread rolls"),
        ("Melitta Café Pads", "Melitta", "coffee", "coffee pads — the flyer writes 'Café'"),
        ("Zwetschgen", None, "fruits", "fresh plums"),
        ("summerstar ruby Grapefruit", "summerstar", "fruits", "fresh grapefruit"),
        ("Durstlöscher Eistee Pfirsich-Geschmack", None, "soft_drinks", "iced tea cartons"),
        ("REWE Bio Sonnenmais", "REWE Bio", "vegetables", "a tin of sweetcorn"),
    ],
)
def test_food_hiding_in_the_household_bucket_is_rescued(name, brand, expected, why):
    """The highest-value class in the sweep: the app hides `household` behind its Non-food
    toggle, so an edible product here is invisible to the user entirely.

    **The non-food path is mandatory in this test.** Layer 1 decides on it and never falls
    through, so `_FOOD_RESCUE` is the only table that can reach these — a rule written at layer
    2 or 6 would be unreachable, and a PATHLESS call would pass while proving nothing. The real
    paths were as absurd as this fixture: chicken legs under `Elektronik und Technik > Marken >
    Samsung`, prawns and plums under `Tierbedarf > Marken für Tiere`.
    """
    assert classify(name, brand, NONFOOD_PATH) == expected, why


@pytest.mark.parametrize("name", ["Cesar Hund Nassfutter", "Gourmet Gold",
                                  "Gourmet Revelations Mousse mit Lachs",
                                  "Winston Hund Feinschmeckerli"])
def test_pet_food_reaches_the_pet_chip_not_household(name):
    """These arrive on a `Tierbedarf` path, so layer 1 owns them and the fix belongs in
    `_DRUGSTORE_RULES`, which runs inside that branch — NOT the layer-2 pet guard, which never
    gets a turn for a pathed product. A bare ` hund` was simulated and REJECTED: "Oma Hartmanns
    Kalter Hund" is a German fridge cake."""
    assert classify(name, None, NONFOOD_PATH) == "pet"


@pytest.mark.parametrize(
    "name, was",
    [("Seelachsschnitzel-Brötchen", "fish"), ("Fleischkäse im Brötchen", "pork"),
     ("Curry-Chicken-Panini", "poultry")],
)
def test_the_counter_sandwich_is_one_class_not_five(name, was):
    """The single most useful finding of the sweep, because it is a CLASS and not a row: a
    filled roll sold by the Stück was landing in five different categories depending on which
    filling word won — fish, pork, poultry, cheese. They are the same thing, and the app already
    routes `fischbrötchen` to ready_meals, so this only extends a call it had already made."""
    assert classify(name, None) == "ready_meals", f"was {was}"


@pytest.mark.parametrize(
    "name, expected, why",
    [
        ("LYTTOS Bifteki Classic", "pork", "minced-meat patties named after their cheese filling"),
        ("LYTTOS Mini-Bifteki", "pork", "same range, 'Vom Schwein' in the caption"),
        ("Bauerngut Kalbsvorderhaxe", "beef", "a veal shank; veal is already beef elsewhere"),
        ("Bauerngut Rindsbratwurst Merguez", "beef", "100% beef sausage"),
        ("FAIRGLOBE Bio Hochland Kaffee", "coffee", "instant coffee taken by a CHEESE brand"),
        ("GUT&GÜNSTIG Bacon-Snack", "snacks", "puffed corn; bacon is the flavour"),
        ("Leerdammer Knusper-Minis Natur", "frozen", "breaded cheese — the app's own convention"),
        ("demeter Mogli-Quetschie", "fruits", "a 100% fruit puree pouch, filed as dairy"),
    ],
)
def test_products_whose_photo_contradicts_every_text_signal(name, expected, why):
    assert classify(name, None) == expected, why


def test_an_alcohol_free_only_brand_is_a_soft_drink():
    """Clausthaler makes nothing else, so the name alone settles it. Two products in the same
    flyer were deliberately NOT fixed: Carlsberg 0.0 and Peroni Nastro Azzurro 0.0 both show
    "0.0" on the PHOTO only — the stored name says "Carlsberg BEER" and "Peroni Nastro
    Azzurro", and both brands also sell real beer. There is no text signal to key on, so
    inventing one would be guessing."""
    assert classify("Clausthaler", "Clausthaler", None, "alkoholfreies Bier") == "soft_drinks"
    assert classify("Carlsberg BEER", "Carlsberg") != "soft_drinks", (
        "with no 0.0 in the stored text, guessing either way is worse than not guessing"
    )


def test_a_salad_dressing_guard_must_sit_above_the_yoghurt_token():
    """`joghurt` is a substring of `joghurt dressing` and sits at layer 2 index 2, so appending
    the guard below it made it dead code — which the shadowing ratchet caught on the first run.
    A flat first-hit-wins table can only express "not a yoghurt" as an entry placed ABOVE."""
    assert classify("GUT&GÜNSTIG Joghurt Dressing", "GUT&GÜNSTIG") == "pantry"
    assert classify("GUT&GÜNSTIG Fruchtjoghurt", "GUT&GÜNSTIG") == "dairy", "the token still works"


def test_a_micellar_water_is_not_a_drink():
    """`wasser` had "LACURA Mizellenwasser" in `soft_drinks` — a facial cleanser in the
    beverages chip."""
    assert classify("LACURA Mizellenwasser", "LACURA", None, "Mit Macadamianussöl 400-ml") == "face"


# --- 2026-08-09: drugstore aisles reachable without a path -----------------------------------


@pytest.mark.parametrize(
    "name, expected",
    [("Formil Feinwaschmittel", "laundry"), ("Alpecin Coffein Shampoo", "hair"),
     ("Sensodyne Zahnpasta", "dental"), ("Frosch Scheuermilch", "cleaning"),
     ("Pampers Baby Dry", "baby")],
)
def test_a_drugstore_product_reaches_its_aisle_without_a_path(name, expected):
    """`_DRUGSTORE_RULES` runs INSIDE layer 1, which only a NON-FOOD path reaches — so 226 of
    its 237 tokens were dead for a product with no path at all. A pathless "Formil
    Feinwaschmittel" matched `waschmittel` in the household tuple at layer 6 and stopped there.

    The drift ratchet had only ever guarded the other direction (31 layer-2 tokens dead for a
    PATHED product), so the larger half was silent. Fixed with data, not a new layer: the aisles
    are spliced into `_RULES` immediately before the household tuple.
    """
    assert classify(name, None) == expected


def test_the_spliced_aisles_cannot_reach_a_product_a_food_rule_wants():
    """What makes the splice zero-regression: it sits AFTER every food tuple, so a drugstore
    token can only ever catch something that was going to be `household` or `other` anyway.
    Measured over the corpus: 5 products moved, 0 out of a real category.

    `Bio Kokosmilch` is the case that proves the ordering — `milch` (dairy, tuple 22) has to win
    over the `body` aisle, which carries `körpermilch`/`sonnenmilch`."""
    assert classify("Bio Kokosmilch", None) == "dairy"
    assert classify("GUT&GÜNSTIG Apfelsaft", "GUT&GÜNSTIG") == "soft_drinks"


@pytest.mark.parametrize(
    "name, expected, swallowed_by",
    [("Odol-med3 Mundwasser", "dental", "`wasser` -> soft_drinks"),
     ("Sensodyne Zahnpasta", "dental", "`pasta` -> pantry"),
     ("Isana Med Körpermilch", "body", "`milch` -> dairy"),
     ("Em-eukal Hustenbonbon", "health", "`bonbon` -> sweets"),
     ("Calgon Wasserenthärter", "laundry", "`wasser` -> soft_drinks"),
     ("Frosch Scheuermilch", "cleaning", "`milch` -> dairy")],
)
def test_german_compounds_that_hide_a_toiletry_inside_a_food_word(name, expected, swallowed_by):
    """German compounding puts a food word inside a toiletry, so the aisles needed guards ABOVE
    the food tuples. Every one of these is already correct in today's corpus — decided at layer
    1 by its non-food path — which is exactly why the guard has to exist now: the failure is
    invisible until a chain ships one of these WITHOUT a path."""
    assert classify(name, None) == expected, f"would be swallowed by {swallowed_by}"
