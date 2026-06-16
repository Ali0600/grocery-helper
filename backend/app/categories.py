"""Canonical product categories and a German-keyword classifier.

Lidl/Rewe offer names are in German. `classify()` applies three layers in order:
an unambiguous brand -> category map, high-priority override tokens, then an
ordered German-keyword ruleset (first hit wins, specific buckets before broad
ones). The layering stops a flavour/brand word from winning over the real
category (e.g. "Mango" in a sparkling-wine name). Tune against real scraped data.
"""
from __future__ import annotations

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

# (slug, [German keywords]); first matching rule wins.
_RULES: list[tuple[str, list[str]]] = [
    ("frozen", ["tiefkühl", "tiefkuehl", "tk-", "tk ", "gefrier", "eiscreme", "speiseeis"]),
    ("fish", ["fisch", "lachs", "thunfisch", "garnele", "forelle", "hering", "sardin", "scampi", "matjes"]),
    ("poultry", ["hähnchen", "haehnchen", "huhn", "hühner", "pute", "puten", "geflügel", "chicken"]),
    ("beef", ["rind", "rinder", "tafelspitz", "gulasch"]),
    ("pork", ["schwein", "schnitzel", "hackfleisch", "hack ", "mett", "bratwurst", "wurst", "speck", "schinken", "salami", "kasseler", "leberkäse"]),
    ("butter", ["markenbutter", "deutsche butter", "süßrahm", "suessrahm", "butter ", "margarine", "rama"]),
    ("cheese", ["käse", "kaese", "gouda", "mozzarella", "feta", "camembert", "parmesan", "frischkäse", "emmentaler"]),
    ("dairy", ["milch", "joghurt", "jogurt", "quark", "sahne", "schmand", "buttermilch", "pudding", "skyr", "almighurt", "ehrmann", "kefir", "ayran", "grütze", "milchreis"]),
    ("fruits", ["apfel", "äpfel", "banane", "erdbeer", "traube", "orange", "zitrone", "birne", "kiwi", "beere", "mango", "ananas", "melone", "pfirsich", "nektarine", "clementine", "mandarine", "avocado", "aprikose", "physalis", "pflaume", "kirsche"]),
    ("vegetables", ["tomate", "gurke", "salat", "kartoffel", "zwiebel", "paprika", "möhre", "moehre", "karotte", "brokkoli", "blumenkohl", "spinat", "zucchini", "champignon", "pilz", "knoblauch", "lauch", "sellerie", "kürbis", "rucola", "spargel"]),
    ("bakery", ["brot", "brötchen", "broetchen", "baguette", "croissant", "toast", "kuchen", "gebäck", "brezel", "crusti"]),
    ("sweets", ["schokolade", "schoko", "praline", "keks", "bonbon", "gummibär", "riegel", "waffel", "nutella", "milka", "haribo", "ritter sport", "toffifee", "duplo", "snickers", "twix"]),
    ("snacks", ["chips", "cracker", "nüsse", "nuesse", "erdnuss", "popcorn", "salzstange", "flips", "tortilla", "studentenfutter", "alesto", "trockenfrüchte", "knabber"]),
    ("beverages", ["wasser", "cola", "limo", "saft", " bier", "wein", "kaffee", " tee", "energy", "schorle", "spezi", "fanta", "sprite", "nektar"]),
    ("pantry", ["nudel", "pasta", "reis", "mehl", "zucker", " öl", "olivenöl", "essig", "konserve", "sauce", "soße", "gewürz", "müsli", "haferflocken", "honig", "marmelade", "ketchup", "senf"]),
    ("household", ["spülmittel", "spuelmittel", "waschmittel", "toilettenpapier", "küchenrolle", "reiniger", "windel", "müllbeutel", "weichspüler",
                   "vileda", "wäscheständer", "wäschest", "matratze", "esmara", "livarno", "parkside", "crivit", "silvercrest", "oleander", "pflanze", "blume", "kleid", "jacke", "schuhe", "garten", "werkzeug", "kissen", "bettdecke",
                   "tapedesign", "jes collection", "haushaltshelfer", "küchenhelfer", "rätselbuch", "crelando", "ultimate speed", "autozubehör", "grillhelfer", "grillzubehör", "schreibwaren", "geschenkpapier", "reinigung", "w5 "]),
]


# Unambiguous brand -> category, checked first (highest priority). Only brands
# that map to exactly one category belong here; multi-category house brands
# (Milbona = milk/cheese/butter, Metzgerfrisch = any meat) are left to _RULES.
BRAND_CATEGORY: dict[str, str] = {
    "allini": "beverages",  # Sekt / Secco / Frizzante
    "mister choc": "sweets",  # chocolate
    "ritter sport": "sweets",
    "milka": "sweets",
    "iglo": "frozen",  # frozen-food brand
    # non-food house brands
    "parkside": "household",
    "esmara": "household",
    "livarno": "household",
    "crelando": "household",
    "vileda": "household",
    "ultimate speed": "household",
    "tapedesign": "household",
    "jes collection": "household",
    "silvercrest": "household",
    "crivit": "household",
    "w5": "household",
}

# High-priority tokens checked before the generic _RULES, so a flavour/type word
# can't win over the real category. Short tokens are space-padded to avoid false
# hits (e.g. " gin " vs "ginger").
_OVERRIDES: list[tuple[str, list[str]]] = [
    ("beverages", ["sekt", "frizzante", "secco", "prosecco", "hugo", "aperol",
                   "likör", "aperitif", "glühwein", "wodka", "whisky", " gin ", " rum "]),
    ("sweets", ["mister choc", "choco"]),
]


def classify(name: str, brand: str | None = None) -> str:
    """Map a raw product (name + optional brand) to a canonical category slug.

    Precedence: unambiguous brand map -> high-priority override tokens ->
    ordered German-keyword rules -> "other".
    """
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
