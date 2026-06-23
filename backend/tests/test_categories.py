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
        ("Rotkäppchen Rosé Trocken", "Rotkäppchen", _BRAND_ONLY, "beverages"),
        ("Deutsche See Pulpo-Arme", "Deutsche See", _BRAND_ONLY, "fish"),
        ("Katjes Fruchtgummi", "Katjes", _BRAND_ONLY, "sweets"),
        ("Lay's Gesalzen", "Lay's", _BRAND_ONLY, "snacks"),
        ("Nuii Ice Cream Salted Caramel", "Nuii", _BRAND_ONLY, "frozen"),
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
        ("Estrella Damm Spanisches Lagerbier", "Estrella Damm", None, "beverages"),
        ("Radeberger Pilsner", "Radeberger", None, "beverages"),
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
        ("Lammkeule in Scheiben", None, "pork"),                  # keyword " lamm"
        ("Houdek Kabanos", "Houdek", "pork"),
        ("Bauern Gut Spareribs", "Bauern Gut", "pork"),
        ("Schäfer's Delikatess Plunder", "Schäfer's", "bakery"),  # brand
        ("EDEKA Herzstücke 8 Protein-Wraps", "EDEKA", "bakery"),  # keyword "wrap"
        ("Gut&Günstig Blätterteig-Vanillestange", "Gut&Günstig", "bakery"),
        ("Alnatura Bio Penne, Fusilli oder Spaghetti", "Alnatura", "pantry"),
        ("EDEKA Bio My Veggie Falafel", "EDEKA Bio", "pantry"),
        ("Mövenpick Edle Komposition", "Mövenpick", "frozen"),    # brand
        ("Frosta Fertiggerichte", "Frosta", "frozen"),
        ("McCain Pickers", "McCain", "frozen"),
        ("Hochland Sandwich Scheiben", "Hochland", "cheese"),
        ("Trolli Fruchtgummi", "Trolli", "sweets"),
        ("Nescafé frappé", "Nescafé", "beverages"),
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
        ([_FOOD, "Produkte", "Getränke", "Wasser"], "beverages"),
        ([_FOOD, "Produkte", "Getränke", "Schaumwein"], "beverages"),
        ([_FOOD, "Marken", "Marken Getränke", "Softdrinkmarken"], "beverages"),
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
        ("Bürger Maultaschen", "Bürger", "pantry"),
        ("EDEKA Bio Smoothie", "EDEKA Bio", "beverages"),
        ("Costa Pacific Prawns", "Costa", "fish"),
        ("Kalbs-Hals", None, "beef"),
        ("ja! Delikatess Mayonnaise", "ja!", "pantry"),
        ("Floristenstrauß der Saison", None, "household"),
        # non-regression guards: the new short tokens must not steal real categories
        ("Steinhaus Original Krustenbraten", "Steinhaus", "pork"),  # not bakery (grill/tigerkruste)
        ("Champagner Brut", None, "beverages"),  # "pane " must not catch it
        # fruit-flavoured items that are NOT fruit (confirmed against the product images)
        ("Bellini Pfirsich 0,0%", None, "beverages"),  # peach sparkling drink, not "pfirsich"
        ("EDEKA Herzstücke Bananenchips", "EDEKA Herzstücke", "snacks"),  # chips, not "banane"
        ("Gut&Günstig Zitronenlimonade", "Gut&Günstig", "beverages"),  # lemonade, not "zitrone"
        ("Müller Froop Pfirsich-Maracuja", "Müller", "dairy"),  # yogurt, not "pfirsich"
        ("Apfelsaft naturtrüb", None, "beverages"),  # juice, not "apfel"
        ("Erdbeer Joghurt", None, "dairy"),  # yogurt, not "erdbeere"
        # real fruit must still classify as fruit
        ("Aprikosen, lose", None, "fruits"),
        ("Zespri SunGold Kiwi", "Zespri", "fruits"),
        ("Rote Äpfel", None, "fruits"),
    ],
)
def test_classify_expanded_names(name, brand, expected):
    assert classify(name, brand) == expected


def test_classify_name_only_still_works():
    # brand is optional
    assert classify("Tiefkühl Pizza Salami") == "frozen"


def test_unknown_is_other():
    assert classify("Zzz Quux Widget", None) == "other"


def test_every_result_is_a_known_category():
    for name in ["Bananen", "Gouda", "Cola", "Mystery item 123"]:
        assert classify(name) in CATEGORIES
