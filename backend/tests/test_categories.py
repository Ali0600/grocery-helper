"""Categorization guards against real-world miscategorizations.

Cases drawn from a live Lidl Berlin snapshot where the old name-only classifier
misfired (a flavour/brand word won over the real category).
"""
import pytest

from app.categories import BRAND_CATEGORY, CATEGORIES, classify


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
        ("Popp Fleischsalat", "Popp", "pork"),  # sausage-based deli salad, not "salat"
        ("HEINZ Tomatenketchup", "HEINZ", "pantry"),  # ketchup, not "tomate"
        ("Golßener Kartoffelsalat", "Golßener", "pantry"),  # prepared salad, not "kartoffel"
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
        ("GUT&GÜNSTIG Dental-Sticks", "GUT&GÜNSTIG", _KNAB_STICKS, "household"),
        ("GUT&GÜNSTIG Chicken-Drumsticks", "GUT&GÜNSTIG", _KNAB_STICKS, "poultry"),
        # a real snack stick still classifies as snacks (the path node itself is unchanged)
        ("funny frisch Brezli", "funny frisch", _KNAB_STICKS, "snacks"),
        # Gut&Günstig house-brand lines: opaque names, no product node → pinned by keyword
        ("GUT&GÜNSTIG Hello my cat Knuspermenü", "GUT&GÜNSTIG", _GUG, "household"),
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
        ("Pottkieker Beste Eintöpfe", "pantry"),
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
        ("GUT&GÜNSTIG Spülmaschinen-Spezialsalz", "GUT&GÜNSTIG", "household", "dishwasher salt"),
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
        ("Fleischkäse im Brötchen", None, "pork", "a meat loaf, not cheese"),
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
        ("Bauern Gut Eiersalat mit Schnittlauch", "pork", "a deli salad"),
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


def test_rama_cremefine_stays_out_of_butter():
    """A cooking cream, not a spread. Its Drogerie (non-food) path catches it at layer 1, before the
    'rama ' butter override at layer 2 — so the override can't sweep it in."""
    path = ["Drogerie und Haushalt", "Produkte", "Drogerie", "Körperpflege", "Creme"]
    assert classify("RAMA Cremefine", "RAMA", path) == "household"


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
# layer-2 household override now catches pet food before the meat/coffee/snacks keywords AND before a
# mis-filed food path (Sheba cat food sits under a "Fisch" node). ---

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
def test_pet_food_is_household_not_a_food_chip(name, path, was):
    assert classify(name, None, path) == "household", f"was {was}"


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
        ("MILSANI Activedrink XXL", "soft_drinks"),
        ("Rotbäckchen", "soft_drinks"),
        ("Von Herzen Regional Scharfe Gemüsesäfte", "soft_drinks"),
    ],
)
def test_drinks_on_a_brand_leaf_path_land_right(name, expected):
    assert classify(name, None, None) == expected


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
    assert classify("POPP Fleischsalat", "POPP", None, "Brotaufstrich, 150-g-Becher") == "pork"
    assert classify("Bauern Gut Eiersalat", "Bauern Gut", None, "Brotaufstrich 150 g") == "pork"


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
