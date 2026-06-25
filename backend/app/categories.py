"""Canonical product categories and the classifier.

`classify(name, brand, category_path)` applies, in order:

1. **Non-food source path** — if the Bonial `categoryPaths` isn't under the food
   root, it's non-food → "household".
2. **Definitive form words** — limonade / saft / joghurt / chips beat even a
   *mis-filed* food path (the source files "Bananenchips" under Obst). Form words
   only — never a mere flavour — and space-guarded vs fruit superstrings
   ("nektar " vs "Nektarine").
3. **Food taxonomy node** — the most specific known node (an *intermediate* node;
   the leaf is often a brand, e.g. `…> Käse > Weichkäse` → cheese).
4. **Brand map** — unambiguous brands → one category (a brand beats a flavour word:
   Häagen-Dazs "…Chocolate" is frozen, not sweets).
5. **Flavour overrides** — a flavour word can't beat the real category ("Mango" in a
   sparkling-wine name).
6. **German-keyword rules** — first hit wins, specific buckets before broad.

The path handles the big, diverse flyer catalog deterministically; the keyword
layers cover coupons and brand-only flyer food. No LLM.
"""
from __future__ import annotations

from typing import List, Optional

# slug -> human label shown in the app
CATEGORIES: dict[str, str] = {
    "fruits": "Fruits",
    "vegetables": "Vegetables",
    "beef": "Beef",
    "poultry": "Chicken & Poultry",
    "pork": "Pork & Sausage",
    "fish": "Fish & Seafood",
    "butter": "Butter",
    "cheese": "Cheese",
    "dairy": "Milk & Dairy",
    "bakery": "Bakery",
    "frozen": "Frozen",
    "sweets": "Sweets & Chocolate",
    "snacks": "Snacks",
    "beverages": "Beverages",
    "pantry": "Pantry & Dry Goods",
    "household": "Household & Non-food",
    "other": "Other",
}

# Bonial level-1 node for food; anything else is non-food.
FOOD_ROOT = "lebensmittel und getränke"

# Bonial taxonomy node (lowercased) -> our slug. Scanned most-specific first, so
# generic nodes like "fleisch" are intentionally omitted (left to the keyword
# layer, which can tell beef/poultry/pork apart from the product name).
_PATH_MAP: dict[str, str] = {
    # beverages
    "getränke": "beverages", "alkoholische getränke": "beverages", "wein": "beverages",
    "weißwein": "beverages", "rotwein": "beverages", "roséwein": "beverages",
    "rosé": "beverages", "rebsorten": "beverages", "spirituosen": "beverages",
    "weinbrand": "beverages", "likör": "beverages", "bier": "beverages",
    "biermarken": "beverages", "saft": "beverages", "softdrinks": "beverages",
    "limonade": "beverages", "kaffee": "beverages", "tee": "beverages", "sekt": "beverages",
    # meat & sausage -> pork bucket
    "wurst": "pork", "wurstwaren": "pork", "brühwurst": "pork", "rohwurst": "pork",
    "fleischwurst": "pork", "würstchen": "pork", "chorizo": "pork", "salami": "pork",
    "schinken": "pork", "fleischzubereitungen": "pork", "bacon": "pork",
    # specific meats (more specific than the path's generic "Fleisch")
    "rind": "beef", "rindfleisch": "beef", "steak": "beef",
    "geflügel": "poultry", "pute": "poultry", "hähnchen": "poultry", "huhn": "poultry",
    # fish
    "fisch": "fish", "lachs": "fish", "meeresfrüchte": "fish", "thunfisch": "fish",
    "räucherfisch": "fish",
    # dairy / cheese / butter
    "käse": "cheese", "weichkäse": "cheese", "hartkäse": "cheese",
    "frischkäse": "cheese", "schnittkäse": "cheese",
    "milch": "dairy", "milchprodukte": "dairy", "joghurt": "dairy", "quark": "dairy",
    "sahne": "dairy", "butter": "butter",
    # frozen / sweets / bakery / snacks
    "eis": "frozen", "stieleis": "frozen", "eis am stiel": "frozen", "speiseeis": "frozen",
    "süßigkeiten": "sweets", "schokolade": "sweets", "pralinen": "sweets", "bonbons": "sweets",
    "fruchtgummi": "sweets",
    "backwaren": "bakery", "gebäck": "bakery", "feingebäck": "bakery", "brot": "bakery",
    "snacks": "snacks", "knabberartikel": "snacks", "knabberzeug": "snacks",
    "salzgebäck": "snacks", "cracker": "snacks", "proteinriegel": "snacks",
    # produce
    "obst": "fruits", "kernobst": "fruits", "steinobst": "fruits", "beeren": "fruits",
    "zitrusfrüchte": "fruits", "gemüse": "vegetables", "salat": "vegetables",
    # pantry
    "öl": "pantry", "öl, essig, salatdressig": "pantry", "essig": "pantry",
    "brotaufstrich": "pantry", "honig": "pantry", "antipasti": "pantry", "tapas": "pantry",
    "feinkost": "pantry", "feinkostlebensmittel": "pantry",
    "teigwaren": "pantry", "nudeln": "pantry", "cerealien": "pantry", "haferbrei": "pantry",
    # --- expanded from a live taxonomy survey across all 3 chains ---
    # beverages (spirit types, soft-drink/water/juice/sekt "…marken" group nodes)
    "softdrinkmarken": "beverages", "saftmarken": "beverages", "saftsorten": "beverages",
    "wassermarken": "beverages", "sektmarken": "beverages", "marken getränke": "beverages",
    "wasser": "beverages", "mineralwasser": "beverages", "heißgetränk": "beverages",
    "heißgetränke": "beverages", "grüner tee": "beverages", "matcha": "beverages",
    "schaumwein": "beverages", "whisky": "beverages", "whiskey": "beverages", "gin": "beverages",
    "wodka": "beverages", "aperitif": "beverages", "sprite": "beverages",
    # bakery (bread types)
    "weißbrot": "bakery", "weissbrot": "bakery", "mischbrot": "bakery", "vollkornbrot": "bakery",
    "weizenbrot": "bakery", "toastbrot": "bakery", "ciabatta": "bakery", "fladenbrot": "bakery",
    "baguette": "bakery",
    # produce
    "melone": "fruits", "wassermelone": "fruits", "zwiebeln": "vegetables", "zwiebel": "vegetables",
    "lauch": "vegetables", "paprika": "vegetables", "wurzelgemüse": "vegetables",
    "kartoffeln": "vegetables",
    # meat & sausage (pork bucket), poultry, fish
    "streichwurst": "pork", "leberwurst": "pork", "bratwurst": "pork", "kochschinken": "pork",
    "rohschinken": "pork", "mettwurst": "pork", "hähnchenspieße": "poultry",
    "fischzubereitung": "fish", "räucherlachs": "fish",
    # pantry / snacks / butter
    "würzmittel": "pantry", "saucen": "pantry", "salatdressing": "pantry", "backzutaten": "pantry",
    "backpulver": "pantry", "chips": "snacks", "sticks": "snacks", "kräuterbutter": "butter",
    "baked beans": "pantry", "grießbrei": "pantry", "veganes schnitzel": "pantry",
}

# (slug, [German keywords]); first matching rule wins.
_RULES: list[tuple[str, list[str]]] = [
    ("frozen", ["tiefkühl", "tiefkuehl", "tk-", "tk ", "gefrier", "eiscreme", "speiseeis", "ice cream",
                "stieleis", "eis am stiel", "gelatelli", "gelati", "langnese", "cornetto", "magnum", "plombir",
                "sorbet", "pizza", "steinofen", "pommes", "wedges", "burrito", "piccolini"]),
    ("fish", ["fisch", "lachs", "thunfisch", "garnele", "forelle", "hering", "sardin", "sardelle",
              "scampi", "matjes", "meeresfrüchte", "octopus", "tentakel", "kalmar", "calamares", "prawn"]),
    ("poultry", ["hähnchen", "haehnchen", "huhn", "hühner", "pute", "puten", "geflügel", "chicken", "corned turkey"]),
    # "gulasch"/"steak" are intentionally NOT here — they appear in Schweinegulasch
    # / Schweinesteak (pork); beef relies on "rind" and beef-specific cuts.
    ("beef", ["rind", "rinder", "tafelspitz", "angus", "t-bone", "rumpsteak", "rib eye", "hüftsteak",
              "burger patties", "smash burger", "kalb", "bavette", "chuck-eye", "chuck eye"]),
    ("pork", ["schwein", "schnitzel", "hackfleisch", "hack ", " mett", "bratwurst", "wurst", "würstchen",
              "speck", "schinken", "salami", "kasseler", "leberkäse", "chorizo", "jamón", "jamon", "serrano",
              "fuet", "lyoner", "frikadelle", "kaminwurzerl", "bacon", "kebab", "cevapcici", "corned", "kaninchen", "rügenwalder",
              "pastrami", "mortadella", "kabanos", "krustenbraten", "sparerib", "rippchen", " lamm",
              "spare rib", "nackensteak"]),
    ("butter", ["markenbutter", "deutsche butter", "süßrahm", "suessrahm", "butter ", "margarine", "rama", "kaergarden"]),
    ("cheese", ["käse", "kaese", "gouda", "mozzarella", "feta", "camembert", "parmesan", "frischkäse",
                "emmentaler", "edamer", "grana", "manchego", "obazda", "zottarella", "queso", "brunch",
                "burrata", "kashkaval"]),
    ("dairy", ["milch", "joghurt", "jogurt", "quark", "sahne", "schmand", "buttermilch", "pudding", "skyr",
               "almighurt", "ehrmann", "kefir", "ayran", "grütze", "milchreis", "fruchtzwerge", "monte ", "paradies creme",
               "crème fraîche", "creme fraiche", "crème fraiche", "zaziki", "tzatziki", "milchschnitte", "pingui"]),
    ("fruits", ["apfel", "äpfel", "banane", "erdbeer", "traube", "orange", "zitrone", "limette", "birne", "kiwi", "beere",
                "mango", "ananas", "melone", "pfirsich", "nektarine", "clementine", "mandarine", "avocado",
                "aprikose", "physalis", "pflaume", "kirsche", "grapefruit"]),
    # Bakery before vegetables so a veg-named *bread* (Knoblauchbrot, Zwiebelkuchen) is
    # bakery, not vegetables — the product word ("brot") should beat the flavour ("knoblauch").
    ("bakery", ["brot", "brötchen", "broetchen", "baguette", "croissant", "toast", "kuchen", "gebäck", "brezel",
                "crusti", "donut", "törtchen", "nata", "magdalena", "muffin", "torte", "linzeraugen", "nusshappen",
                "buns", "laugen", "lauge", "plunder", "pita", "wrap", "blätterteig",
                "pane ", "tigerkruste", "grillkruste", "holzfäller"]),
    ("vegetables", ["tomate", "gurke", "salat", "kartoffel", "zwiebel", "paprika", "möhre", "moehre", "karotte",
                    "brokkoli", "blumenkohl", "spinat", "zucchini", "champignon", "pilz", "knoblauch", "lauch",
                    "sellerie", "kürbis", "rucola", "spargel", "kohlrabi", "coleslaw"]),
    ("sweets", ["schokolade", "schoko", "praline", "keks", "bonbon", "gummibär", "riegel", "waffel", "nutella",
                "milka", "haribo", "ritter sport", "toffifee", "duplo", "snickers", "twix", "ferrero", "hanuta",
                "loacker", "celebrations", "nudossi", "kinder cards", "fritt", "sondey", "tenerezze",
                "fruchtgummi", "big choc", "smarties", "amicelli", "daim", "m&m", "maxi king",
                "kinder bueno", "bärchen"]),
    ("snacks", ["chips", "cracker", "nüsse", "nuesse", "erdnuss", "popcorn", "salzstange", "flips", "tortilla",
                "studentenfutter", "alesto", "trockenfrüchte", "knabber", "bake rolls", "snackmix", "knusper"]),
    ("beverages", ["wasser", "cola", "limo", "saft", " bier", "lagerbier", " pils", "wein", "kaffee", " tee", "energy", "schorle",
                   "spezi", "fanta", "sprite", "nektar", "vodka", "champagner", "pilsener", "sangria", "doppelkorn",
                   "goldkrone", "weinbrand", "licor", "pepsi", "solevita", "san miguel", "holsten", "moët", "moet",
                   "absolut", "korol", "cimarosa", "sauvignon", "espresso", "caffè", "caffe", "lavazza", "dallmayr",
                   "latte", "aloe vera", "primitivo", "smoothie", "bella crema"]),
    ("pantry", ["nudel", "noodles", "pasta", "teigwaren", "porridge", "reis", "mehl", "zucker", " öl", "olivenöl", "essig", "konserve",
                "sauce", "soße", "gewürz", "müsli", "haferflocken", "honig", "marmelade", "ketchup", "senf",
                "oliven", "kichererbsen", "aioli", "artischocken", "paella", "lupinen", "antipasti", "tapas",
                "penne", "fusilli", "spaghetti", "tagliatelle", "tortellini", "ravioli", "baked beans",
                "hummus", "tofu", "tempeh", "falafel", "mayonnaise", "maultaschen", "tahina", "tahin",
                "rapskernöl", "kernöl", "rapsöl", "sonnenblumenöl", "pinienkerne", "allioli",
                "fleischalternativ", "like meat", "likemeat", "nesquik"]),
    ("household", ["spülmittel", "spuelmittel", "waschmittel", "toilettenpapier", "küchenrolle", "reiniger",
                   "windel", "müllbeutel", "weichspüler", "oleander", "pflanze", "blume", "kleid", "jacke", "schuhe",
                   "garten", "werkzeug", "kissen", "bettdecke", "matratze", "wäschest", "haushaltshelfer",
                   "küchenhelfer", "rätselbuch", "autozubehör", "grillhelfer", "grillzubehör", "schreibwaren",
                   "geschenkpapier", "reinigung", "e-bike", "e-scooter", "ventilator", "staubsauger", "klimagerät",
                   "luftkühler", "bügeleisen", "bügelstation", "fritteuse", "shampoo", "duschgel", "zahnbürste",
                   "rasierer", "haartrockner", "batterien", "kosmetik", "sonnenschutz", "pavillon", "fahrradträger",
                   "fahrradanhänger", "wanduhr", "kühltasche", "chrysanthemen", "lavendel", "palme", "kreuzfahrt", "hotel",
                   "holzkohle", "grillkohle", "brikett", "grillmatte", "haushaltstuch", "müllbeutel", "papierbeutel",
                   "hortensie", "floristen", "blumenstrauß", "keramikgrill", "hundespielzeug", "plüschtier",
                   "spielzeug", "prospekthülle", "auto laden"]),
]

# Unambiguous brand -> category. Multi-category house brands (Milbona, Metzgerfrisch,
# Sol & Mar, Zott) are left to the path / keyword layers.
BRAND_CATEGORY: dict[str, str] = {
    "allini": "beverages", "mister choc": "sweets", "ritter sport": "sweets", "milka": "sweets",
    "iglo": "frozen", "gelatelli": "frozen", "langnese": "frozen", "bon gelati": "frozen",
    "gustavo gusto": "frozen", "ferrero": "sweets", "loacker": "sweets", "rondo": "sweets",
    "dulano": "pork", "meica": "pork", "brunch": "cheese", "kerrygold": "butter",
    "valensina": "beverages", "lipton": "beverages", "volvic": "beverages",
    "schogetten": "sweets", "berggold": "sweets", "häagen-dazs": "frozen",
    # REWE flyer brands (paths are often brand-only -> no taxonomy node to use)
    "mirée": "cheese", "miree": "cheese", "salakis": "cheese", "leerdammer": "cheese",
    "bergader": "cheese", "violife": "cheese", "rotkäppchen": "beverages",
    "deutsche see": "fish", "katjes": "sweets", "lay's": "snacks", "lorenz": "snacks",
    "nuii": "frozen", "danone": "dairy",
    # EDEKA flyer brands (single-category; the house lines Gut&Günstig / EDEKA /
    # EDEKA Herzstücke / EDEKA Bio are multi-category -> left to path+keywords).
    "schäfer's": "bakery", "mestemacher": "bakery", "elpozo": "pork",
    "citterio": "pork", "steinhaus": "pork", "houdek": "pork",
    "bauern gut": "pork", "bauerngut": "pork", "wiesenhof": "poultry",
    "frosta": "frozen", "mccain": "frozen", "mövenpick": "frozen", "moevenpick": "frozen",
    "hochland": "cheese", "trolli": "sweets", "nescafé": "beverages", "nescafe": "beverages",
    "chio": "snacks", "sonnen bassermann": "pantry", "edeka zuhause": "household",
    # more single-category food brands (from the live "other" survey across all 3 chains).
    # Multi-category house brands (Milbona, Gut&Günstig, Metzgerfrisch, Butchers, ja!,
    # Dr. Oetker, Deluxe, Costa) are intentionally left to the path/keyword layers.
    "knorr": "pantry", "maggi": "pantry", "erasco": "pantry", "barilla": "pantry", "kühne": "pantry",
    "kunella": "pantry", "zentis": "pantry", "acentino": "pantry", "rapso": "pantry",
    "belbake": "pantry", "hela": "pantry", "oryza": "pantry", "bonduelle": "vegetables",
    "harry": "bakery", "wasa ": "snacks", "ültje": "snacks", "alesto": "snacks",
    "bahlsen": "sweets", "marabou": "sweets",
    "saint agur": "cheese", "rougette": "cheese", "petrella": "cheese", "almette": "cheese",
    "géramont": "cheese", "geramont": "cheese", "becel": "butter",
    "florida eis": "frozen", "leffe": "beverages", "heineken": "beverages",
    "starbucks": "beverages", "wiltmann": "pork", "wilhelm brandenburg": "pork",
    "baldauf": "cheese", "wagner": "frozen", "purina": "household", "pedigree": "household",
    # non-food house / appliance / care / fashion brands
    "parkside": "household", "esmara": "household", "livarno": "household", "crelando": "household",
    "vileda": "household", "ultimate speed": "household", "tapedesign": "household",
    "jes collection": "household", "silvercrest": "household", "crivit": "household", "w5": "household",
    "tronic": "household", "lupilu": "household", "philips": "household", "bosch": "household",
    "krups": "household", "tefal": "household", "cien": "household", "nivea": "household",
    "oral-b": "household", "colgate": "household", "pantene": "household", "remington": "household",
    "telefunken": "household", "zündapp": "household", "bestway": "household", "comfee": "household",
    "midea": "household", "swiffer": "household", "finish": "household", "energizer": "household",
    "wenko": "household", "whiskas": "household", "head & shoulders": "household", "l'oréal": "household",
    "karibu": "household", "cleanmaxx": "household", "auriol": "household", "mexx": "household",
    "qeridoo": "household", "eufab": "household", "ridder": "household", "pergoline": "household",
}

# Definitive *form* words (and single-category product brands): a product literally called a
# limonade / saft / joghurt / chips — or a Froop / Müllermilch / Vilsa — IS that category, so
# these beat even a mis-filed food taxonomy path (the source files "Bananenchips" under Obst,
# the flavoured water "Vilsa H2 Obst …" under Obst). Only words that pin the category by form
# or an unambiguous brand, never a mere flavour — so a frozen "…Schoko" brand isn't dragged
# here. Space-guarded where a fruit word is a superstring ("nektar " vs "Nektarine").
_FORM_OVERRIDES: list[tuple[str, list[str]]] = [
    ("beverages", ["limonade", "schorle", "nektar ", "smoothie", "saft ", "fruchtsaft", "vilsa"]),
    ("dairy", ["joghurt", "jogurt", "froop", "skyr", "müllermilch", "fruchtzwerge", "fruchtquark"]),
    ("snacks", ["chips", "trüfrü", "trufru"]),  # freeze-dried fruit snack filed under Obst
]

# Flavour / drink-type tokens (and specific compounds that must beat a generic fruit
# substring) checked after the brand map but before _RULES, so a flavour word can't beat
# the real category (e.g. "Mango" in a sparkling-wine name) and a compound noun beats its
# misleading prefix ("Pflaumentomaten" is a tomato, "Apfelessig" is vinegar) — but a brand
# still wins (Häagen-Dazs "…Chocolate" is frozen, not sweets). Short tokens are space-padded.
_OVERRIDES: list[tuple[str, list[str]]] = [
    ("beverages", ["sekt", "frizzante", "secco", "prosecco", "hugo", "aperol", "bellini", "likör",
                   "aperitif", "glühwein", "wodka", "whisky", "pilsener", "eistee", "ice tea",
                   " gin ", " rum "]),
    ("sweets", ["mister choc", "choco"]),
    # compound nouns whose prefix is a produce word (would otherwise land in vegetables/fruits):
    # prepared deli salads + condiments are not raw produce.
    ("pork", ["fleischsalat", "wurstsalat"]),  # sausage-based deli salad, not "salat"
    ("vegetables", ["pflaumentomate"]),
    ("pantry", ["apfelessig", "weinessig", "obstessig", "balsamico",
                "ketchup", "kartoffelsalat", "kartoffel-salat"]),
]


def _path_nonfood(category_path: List[str]) -> bool:
    """True if the source taxonomy files this outside the food root (-> household)."""
    return bool(category_path) and category_path[0].strip().lower() != FOOD_ROOT


def _path_node(category_path: List[str]) -> Optional[str]:
    """Most-specific known food taxonomy node -> slug, else None (the leaf is often a brand)."""
    for node in reversed(category_path):
        slug = _PATH_MAP.get(node.strip().lower())
        if slug:
            return slug
    return None


def classify(name: str, brand: str | None = None, category_path: Optional[List[str]] = None) -> str:
    """Map a product (name + optional brand + optional source path) to a slug."""
    path = category_path or []
    # 1. A non-food source path is authoritative ("Sektkühler" is household, not a drink).
    if _path_nonfood(path):
        return "household"
    text = f" {name.lower()} {(brand or '').lower()} "
    # 2. Definitive form words beat a *mis-filed food* path (Bananenchips under Obst, etc).
    for slug, tokens in _FORM_OVERRIDES:
        if any(token in text for token in tokens):
            return slug
    # 3. The food taxonomy node (an *intermediate* node; the leaf is often a brand).
    node = _path_node(path)
    if node:
        return node
    # 4. Unambiguous brand (a brand beats a flavour word: Häagen-Dazs Chocolate is frozen).
    brand_text = (brand or "").lower()
    for brand_key, slug in BRAND_CATEGORY.items():
        if brand_key in brand_text or brand_key in text:
            return slug
    # 5. Flavour/priority overrides, then 6. German-keyword rules.
    for slug, tokens in _OVERRIDES:
        if any(token in text for token in tokens):
            return slug
    for slug, keywords in _RULES:
        if any(kw in text for kw in keywords):
            return slug
    return "other"


def label(slug: str) -> str:
    return CATEGORIES.get(slug, "Other")
