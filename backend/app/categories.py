"""Canonical product categories and a German-keyword classifier.

Lidl/Rewe offer names are in German, so the classifier matches German keywords.
Rules are checked top-to-bottom and the first hit wins, so more specific buckets
(frozen, individual meats, butter) are listed before broader ones. Tune the
keyword lists against real scraped data during test runs.
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


def classify(name: str) -> str:
    """Map a raw product name to a canonical category slug."""
    text = f" {name.lower()} "
    for slug, keywords in _RULES:
        for kw in keywords:
            if kw in text:
                return slug
    return "other"


def label(slug: str) -> str:
    return CATEGORIES.get(slug, "Other")
