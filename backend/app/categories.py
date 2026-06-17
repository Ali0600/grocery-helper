"""Canonical product categories and the classifier.

`classify(name, brand, category_path)` applies, in order:

1. **Source taxonomy path** (Bonial `categoryPaths`, flyer offers only): if the
   path isn't under the food root it's non-food → "household"; otherwise the most
   specific known taxonomy node wins (e.g. `…> Käse > Weichkäse` → cheese).
2. **Brand map** — unambiguous brands → one category.
3. **Override tokens** — high-priority words so a flavour word can't beat the
   real category (e.g. "Mango" in a sparkling-wine name).
4. **German-keyword rules** — first hit wins, specific buckets before broad.

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
    "backwaren": "bakery", "gebäck": "bakery", "feingebäck": "bakery", "brot": "bakery",
    "snacks": "snacks", "knabberartikel": "snacks",
    # produce
    "obst": "fruits", "kernobst": "fruits", "steinobst": "fruits", "beeren": "fruits",
    "zitrusfrüchte": "fruits", "gemüse": "vegetables", "salat": "vegetables",
    # pantry
    "öl": "pantry", "öl, essig, salatdressig": "pantry", "essig": "pantry",
    "brotaufstrich": "pantry", "honig": "pantry", "antipasti": "pantry", "tapas": "pantry",
    "feinkost": "pantry", "feinkostlebensmittel": "pantry",
}

# (slug, [German keywords]); first matching rule wins.
_RULES: list[tuple[str, list[str]]] = [
    ("frozen", ["tiefkühl", "tiefkuehl", "tk-", "tk ", "gefrier", "eiscreme", "speiseeis",
                "stieleis", "eis am stiel", "gelatelli", "gelati", "langnese", "cornetto", "magnum", "plombir",
                "pizza", "steinofen"]),
    ("fish", ["fisch", "lachs", "thunfisch", "garnele", "forelle", "hering", "sardin", "sardelle",
              "scampi", "matjes", "meeresfrüchte", "octopus", "tentakel", "kalmar", "calamares"]),
    ("poultry", ["hähnchen", "haehnchen", "huhn", "hühner", "pute", "puten", "geflügel", "chicken", "corned turkey"]),
    # "gulasch"/"steak" are intentionally NOT here — they appear in Schweinegulasch
    # / Schweinesteak (pork); beef relies on "rind" and beef-specific cuts.
    ("beef", ["rind", "rinder", "tafelspitz", "angus", "t-bone", "rumpsteak", "rib eye", "hüftsteak"]),
    ("pork", ["schwein", "schnitzel", "hackfleisch", "hack ", " mett", "bratwurst", "wurst", "würstchen",
              "speck", "schinken", "salami", "kasseler", "leberkäse", "chorizo", "jamón", "jamon", "serrano",
              "fuet", "lyoner", "frikadelle", "kaminwurzerl", "bacon", "kebab", "cevapcici", "corned", "kaninchen", "rügenwalder"]),
    ("butter", ["markenbutter", "deutsche butter", "süßrahm", "suessrahm", "butter ", "margarine", "rama"]),
    ("cheese", ["käse", "kaese", "gouda", "mozzarella", "feta", "camembert", "parmesan", "frischkäse",
                "emmentaler", "edamer", "grana", "manchego", "obazda", "zottarella", "queso", "brunch"]),
    ("dairy", ["milch", "joghurt", "jogurt", "quark", "sahne", "schmand", "buttermilch", "pudding", "skyr",
               "almighurt", "ehrmann", "kefir", "ayran", "grütze", "milchreis", "fruchtzwerge", "monte ", "paradies creme"]),
    ("fruits", ["apfel", "äpfel", "banane", "erdbeer", "traube", "orange", "zitrone", "birne", "kiwi", "beere",
                "mango", "ananas", "melone", "pfirsich", "nektarine", "clementine", "mandarine", "avocado",
                "aprikose", "physalis", "pflaume", "kirsche"]),
    ("vegetables", ["tomate", "gurke", "salat", "kartoffel", "zwiebel", "paprika", "möhre", "moehre", "karotte",
                    "brokkoli", "blumenkohl", "spinat", "zucchini", "champignon", "pilz", "knoblauch", "lauch",
                    "sellerie", "kürbis", "rucola", "spargel"]),
    ("bakery", ["brot", "brötchen", "broetchen", "baguette", "croissant", "toast", "kuchen", "gebäck", "brezel",
                "crusti", "donut", "törtchen", "nata", "magdalena", "muffin", "torte", "linzeraugen", "nusshappen"]),
    ("sweets", ["schokolade", "schoko", "praline", "keks", "bonbon", "gummibär", "riegel", "waffel", "nutella",
                "milka", "haribo", "ritter sport", "toffifee", "duplo", "snickers", "twix", "ferrero", "hanuta",
                "loacker", "celebrations", "nudossi", "kinder cards", "fritt", "sondey", "tenerezze"]),
    ("snacks", ["chips", "cracker", "nüsse", "nuesse", "erdnuss", "popcorn", "salzstange", "flips", "tortilla",
                "studentenfutter", "alesto", "trockenfrüchte", "knabber", "bake rolls", "snackmix", "knusper"]),
    ("beverages", ["wasser", "cola", "limo", "saft", " bier", "wein", "kaffee", " tee", "energy", "schorle",
                   "spezi", "fanta", "sprite", "nektar", "vodka", "champagner", "pilsener", "sangria", "doppelkorn",
                   "goldkrone", "weinbrand", "licor", "pepsi", "solevita", "san miguel", "holsten", "moët", "moet",
                   "absolut", "korol", "cimarosa", "sauvignon", "espresso", "caffè", "caffe", "lavazza", "dallmayr",
                   "latte", "aloe vera"]),
    ("pantry", ["nudel", "pasta", "teigwaren", "reis", "mehl", "zucker", " öl", "olivenöl", "essig", "konserve",
                "sauce", "soße", "gewürz", "müsli", "haferflocken", "honig", "marmelade", "ketchup", "senf",
                "oliven", "kichererbsen", "aioli", "artischocken", "paella", "lupinen", "antipasti", "tapas"]),
    ("household", ["spülmittel", "spuelmittel", "waschmittel", "toilettenpapier", "küchenrolle", "reiniger",
                   "windel", "müllbeutel", "weichspüler", "oleander", "pflanze", "blume", "kleid", "jacke", "schuhe",
                   "garten", "werkzeug", "kissen", "bettdecke", "matratze", "wäschest", "haushaltshelfer",
                   "küchenhelfer", "rätselbuch", "autozubehör", "grillhelfer", "grillzubehör", "schreibwaren",
                   "geschenkpapier", "reinigung", "e-bike", "e-scooter", "ventilator", "staubsauger", "klimagerät",
                   "luftkühler", "bügeleisen", "bügelstation", "fritteuse", "shampoo", "duschgel", "zahnbürste",
                   "rasierer", "haartrockner", "batterien", "kosmetik", "sonnenschutz", "pavillon", "fahrradträger",
                   "fahrradanhänger", "wanduhr", "kühltasche", "chrysanthemen", "lavendel", "palme", "kreuzfahrt", "hotel"]),
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

# High-priority tokens checked before _RULES. Short tokens are space-padded.
_OVERRIDES: list[tuple[str, list[str]]] = [
    ("beverages", ["sekt", "frizzante", "secco", "prosecco", "hugo", "aperol", "likör", "aperitif",
                   "glühwein", "wodka", "whisky", "pilsener", "eistee", "ice tea", " gin ", " rum "]),
    ("sweets", ["mister choc", "choco"]),
]


def _from_path(category_path: List[str]) -> Optional[str]:
    if not category_path:
        return None
    if category_path[0].strip().lower() != FOOD_ROOT:
        return "household"  # any non-food taxonomy
    for node in reversed(category_path):  # most specific first
        slug = _PATH_MAP.get(node.strip().lower())
        if slug:
            return slug
    return None  # food, but only brand-organized -> fall through to keywords


def classify(name: str, brand: str | None = None, category_path: Optional[List[str]] = None) -> str:
    """Map a product (name + optional brand + optional source path) to a slug."""
    by_path = _from_path(category_path or [])
    if by_path:
        return by_path

    text = f" {name.lower()} {(brand or '').lower()} "
    brand_text = (brand or "").lower()
    for brand_key, slug in BRAND_CATEGORY.items():
        if brand_key in brand_text or brand_key in text:
            return slug
    for slug, tokens in _OVERRIDES:
        for token in tokens:
            if token in text:
                return slug
    for slug, keywords in _RULES:
        for kw in keywords:
            if kw in text:
                return slug
    return "other"


def label(slug: str) -> str:
    return CATEGORIES.get(slug, "Other")
