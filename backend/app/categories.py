"""Canonical product categories and the classifier.

`classify(name, brand, category_path)` applies, in order:

0. **Vegan** — an explicitly-vegan product (name/brand says vegan/pflanzlich, or a
   vegan-only brand like Vemondo) is its own category, beating every other signal
   (cross-cutting by choice — a vegan cheese is filed under "vegan", not "cheese").
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

from .vegan import is_vegan

# slug -> human label shown in the app
# Insertion order drives the filter-chip order (GET /api/categories iterates this dict).
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
    "ice_cream": "Ice Cream",
    "sweets": "Sweets & Chocolate",
    "snacks": "Snacks",
    "soft_drinks": "Soft Drinks",  # beverages split: non-alcoholic (soda/juice/water/coffee/tea)
    "alcoholic": "Alcoholic",  # beverages split: beer/wine/sekt/spirits
    "pantry": "Pantry & Dry Goods",
    "vegan": "Vegan",  # moved to the back of the food chips (per the user)
    "other": "Other",
    "household": "Household & Non-food",
}

# Bonial level-1 node for food; anything else is non-food.
FOOD_ROOT = "lebensmittel und getränke"

# Bonial taxonomy node (lowercased) -> our slug. Scanned most-specific first, so
# generic nodes like "fleisch" are intentionally omitted (left to the keyword
# layer, which can tell beef/poultry/pork apart from the product name).
_PATH_MAP: dict[str, str] = {
    # beverages — split into alcoholic vs soft drinks (all non-alcoholic incl. coffee/tea/water)
    "getränke": "soft_drinks", "alkoholische getränke": "alcoholic", "wein": "alcoholic",
    "weißwein": "alcoholic", "rotwein": "alcoholic", "roséwein": "alcoholic",
    "rosé": "alcoholic", "rebsorten": "alcoholic", "spirituosen": "alcoholic",
    "weinbrand": "alcoholic", "likör": "alcoholic", "bier": "alcoholic",
    "biermarken": "alcoholic", "saft": "soft_drinks", "softdrinks": "soft_drinks",
    "limonade": "soft_drinks", "kaffee": "soft_drinks", "tee": "soft_drinks", "sekt": "alcoholic",
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
    # ice cream (the source's "Eis" nodes are specifically ice cream, not savoury frozen)
    "eis": "ice_cream", "stieleis": "ice_cream", "eis am stiel": "ice_cream", "speiseeis": "ice_cream",
    # frozen / sweets / bakery / snacks
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
    "softdrinkmarken": "soft_drinks", "saftmarken": "soft_drinks", "saftsorten": "soft_drinks",
    "wassermarken": "soft_drinks", "sektmarken": "alcoholic", "marken getränke": "soft_drinks",
    "wasser": "soft_drinks", "mineralwasser": "soft_drinks", "heißgetränk": "soft_drinks",
    "heißgetränke": "soft_drinks", "grüner tee": "soft_drinks", "matcha": "soft_drinks",
    "schaumwein": "alcoholic", "whisky": "alcoholic", "whiskey": "alcoholic", "gin": "alcoholic",
    "wodka": "alcoholic", "aperitif": "alcoholic", "sprite": "soft_drinks",
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
    # Ice cream before frozen (and before sweets, so "Snickers Ice Cream" isn't sweets).
    # " eis " is the standalone word only — space-padded so it can't fire inside Fleisch /
    # Reis / Eisberg / Eistee / Eiweiß (verified against the live catalog: 0 leaks).
    ("ice_cream", ["eiscreme", "speiseeis", "ice cream", "stieleis", "eis am stiel", "wassereis",
                   "soft-eis", "softeis", "milcheis", "fruchteis", "sandwich-eis", "sandwich eis",
                   "eisbecher", " eis ", "sorbet", "gelato", "plombir", "cremissimo", "magnum",
                   "cornetto", "pirulo", "nogger", "solero", "calippo", "viennetta", "nuii"]),
    ("frozen", ["tiefkühl", "tiefkuehl", "tk-", "tk ", "gefrier", "pizza", "steinofen", "pommes",
                "wedges", "burrito", "piccolini"]),
    ("fish", ["fisch", "lachs", "thunfisch", "garnele", "forelle", "hering", "sardin", "sardelle",
              "scampi", "matjes", "meeresfrüchte", "octopus", "tentakel", "kalmar", "calamares", "prawn"]),
    ("poultry", ["hähnchen", "haehnchen", "huhn", "hühner", "pute", "puten", "geflügel", "chicken",
                 "corned turkey", "knusperdino", "wachtel"]),  # Knusperdinos = Hähnchenbrust nuggets
    # "gulasch"/"steak" are intentionally NOT here — they appear in Schweinegulasch
    # / Schweinesteak (pork); beef relies on "rind" and beef-specific cuts.
    ("beef", ["rind", "rinder", "tafelspitz", "angus", "t-bone", "rumpsteak", "rib eye", "hüftsteak",
              "burger patties", "smash burger", "kalb", "bavette", "chuck-eye", "chuck eye"]),
    ("pork", ["schwein", "schnitzel", "hackfleisch", "hack ", " mett", "bratwurst", "wurst", "würstchen",
              "speck", "schinken", "salami", "kasseler", "leberkäse", "chorizo", "jamón", "jamon", "serrano",
              "fuet", "lyoner", "frikadelle", "kaminwurzerl", "bacon", "kebab", "cevapcici", "corned", "kaninchen", "rügenwalder",
              "pastrami", "mortadella", "kabanos", "krustenbraten", "sparerib", "rippchen", " lamm",
              # "würst" catches the umlaut plurals the bare "wurst" misses (Bockwürste,
              # Bratwürste); "haxe" is the pork knuckle — Kalbs-/Putenhaxe are safe because
              # the beef/poultry rules run first.
              "spare rib", "nackensteak", "würst", "haxe"]),
    ("butter", ["markenbutter", "deutsche butter", "süßrahm", "suessrahm", "butter ", "margarine", "rama", "kaergarden"]),
    ("cheese", ["käse", "kaese", "gouda", "mozzarella", "feta", "camembert", "parmesan", "frischkäse",
                "emmentaler", "edamer", "grana", "manchego", "obazda", "zottarella", "queso", "brunch",
                "burrata", "kashkaval", "kasländer"]),
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
                "pane ", "tigerkruste", "grillkruste", "holzfäller", "knusperjung",  # Weizenbrötchen
                "focaccia"]),
    ("vegetables", ["tomate", "gurke", "salat", "kartoffel", "zwiebel", "paprika", "möhre", "moehre", "karotte",
                    "brokkoli", "blumenkohl", "spinat", "zucchini", "champignon", "pilz", "knoblauch", "lauch",
                    "sellerie", "kürbis", "rucola", "spargel", "kohlrabi", "coleslaw", "kresse"]),
    ("sweets", ["schokolade", "schoko", "praline", "keks", "bonbon", "gummibär", "riegel", "waffel", "nutella",
                "milka", "haribo", "ritter sport", "toffifee", "duplo", "snickers", "twix", "ferrero", "hanuta",
                "loacker", "celebrations", "nudossi", "kinder cards", "fritt", "sondey", "tenerezze",
                "fruchtgummi", "big choc", "smarties", "amicelli", "daim", "m&m", "maxi king",
                # "cheesecake" is a dessert either way (a Becher one is still sweet); the
                # ice_cream rule + the brand layer both run first, so Ben & Jerry's is safe.
                "kinder bueno", "bärchen", "profiterole", "cheesecake", "knister-pop"]),
    # NOTE: "knusper" removed — it's a coating adjective, not a snack noun; it mis-caught cat food
    # (Knuspermenü), chicken nuggets (Knusperdinos) and bread rolls (Knusperjungs), and matched 0
    # real snacks in the live feed. Specific "knusper*" products are pinned above (poultry/bakery).
    ("snacks", ["chips", "cracker", "nüsse", "nuesse", "erdnuss", "popcorn", "salzstange", "flips", "tortilla",
                "studentenfutter", "alesto", "trockenfrüchte", "knabber", "bake rolls", "snackmix",
                "walnusskern"]),
    ("alcoholic", [" bier", "lagerbier", " pils", "wein", "vodka", "champagner", "pilsener", "sangria",
                   "doppelkorn", "goldkrone", "weinbrand", "licor", "san miguel", "holsten", "moët", "moet",
                   "absolut", "korol", "cimarosa", "sauvignon", "primitivo"]),
    ("soft_drinks", ["wasser", "cola", "limo", "saft", "kaffee", " tee", "energy", "schorle", "spezi",
                     "fanta", "sprite", "nektar", "pepsi", "solevita", "espresso", "caffè", "caffe",
                     "lavazza", "dallmayr", "latte", "aloe vera", "smoothie", "bella crema"]),
    ("pantry", ["nudel", "noodles", "pasta", "teigwaren", "porridge", "reis", "mehl", "zucker", " öl", "olivenöl", "essig", "konserve",
                "sauce", "soße", "gewürz", "müsli", "haferflocken", "honig", "marmelade", "ketchup", "senf",
                "oliven", "kichererbsen", "aioli", "artischocken", "paella", "lupinen", "antipasti", "tapas",
                "penne", "fusilli", "spaghetti", "tagliatelle", "tortellini", "ravioli", "baked beans",
                "hummus", "tofu", "tempeh", "falafel", "mayonnaise", "maultaschen", "tahina", "tahin",
                "rapskernöl", "kernöl", "rapsöl", "sonnenblumenöl", "pinienkerne", "allioli",
                # "suppe " keeps the trailing space on purpose: it matches "Gulasch-Suppe"
                # but not Suppengrün (vegetables) or Suppenhuhn/-fleisch, which would
                # otherwise reach pantry — it sits second-to-last, so it can't be outranked.
                "fleischalternativ", "like meat", "likemeat", "nesquik",
                "suppe ", "eintopf", "eintöpf", "lasagne-blätter", "lasagneblätter", "gigli "]),
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
    "allini": "alcoholic", "mister choc": "sweets", "ritter sport": "sweets", "milka": "sweets",
    "iglo": "frozen", "gelatelli": "ice_cream", "langnese": "ice_cream", "bon gelati": "ice_cream",
    "schöller": "ice_cream", "ben & jerry's": "ice_cream", "ben & jerry": "ice_cream",
    "gustavo gusto": "frozen", "ferrero": "sweets", "loacker": "sweets", "rondo": "sweets",
    "dulano": "pork", "meica": "pork", "brunch": "cheese", "kerrygold": "butter",
    "valensina": "soft_drinks", "lipton": "soft_drinks", "volvic": "soft_drinks",
    "schogetten": "sweets", "berggold": "sweets", "häagen-dazs": "ice_cream",
    # REWE flyer brands (paths are often brand-only -> no taxonomy node to use)
    "mirée": "cheese", "miree": "cheese", "salakis": "cheese", "leerdammer": "cheese",
    "bergader": "cheese", "violife": "cheese", "rotkäppchen": "alcoholic",
    "deutsche see": "fish", "katjes": "sweets", "lay's": "snacks", "lorenz ": "snacks",
    "nuii": "ice_cream", "danone": "dairy",
    # EDEKA flyer brands (single-category; the house lines Gut&Günstig / EDEKA /
    # EDEKA Herzstücke / EDEKA Bio are multi-category -> left to path+keywords).
    "schäfer's": "bakery", "mestemacher": "bakery", "elpozo": "pork",
    "citterio": "pork", "steinhaus": "pork", "houdek": "pork",
    "bauern gut": "pork", "bauerngut": "pork", "wiesenhof": "poultry",
    "frosta": "frozen", "mccain": "frozen", "mövenpick": "ice_cream", "moevenpick": "ice_cream",
    "hochland": "cheese", "trolli": "sweets", "nescafé": "soft_drinks", "nescafe": "soft_drinks",
    "chio": "snacks", "sonnen bassermann": "pantry", "edeka zuhause": "household",
    # more single-category food brands (from the live "other" survey across all 3 chains).
    # Multi-category house brands (Milbona, Gut&Günstig, Metzgerfrisch, Butchers, ja!,
    # Dr. Oetker, Deluxe, Costa) are intentionally left to the path/keyword layers.
    "knorr": "pantry", "maggi": "pantry", "erasco": "pantry", "barilla": "pantry", "kühne": "pantry",
    "bonne maman": "pantry",  # jam / preserves (the source's brand-only path leaves it to keywords)
    "kunella": "pantry", "zentis": "pantry", "acentino": "pantry", "rapso": "pantry",
    "belbake": "pantry", "hela": "pantry", "oryza": "pantry", "bonduelle": "vegetables",
    "harry": "bakery", "wasa ": "snacks", "ültje": "snacks", "alesto": "snacks",
    "bahlsen": "sweets", "marabou": "sweets",
    "saint agur": "cheese", "rougette": "cheese", "petrella": "cheese", "almette": "cheese",
    "géramont": "cheese", "geramont": "cheese", "becel": "butter",
    "florida eis": "ice_cream", "leffe": "alcoholic", "heineken": "alcoholic",
    "starbucks": "soft_drinks", "wiltmann": "pork", "wilhelm brandenburg": "pork",
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
    # ALDI: single-category brands only. Its multi-category house brands (MILSANI, Trader
    # Joe's, Meine Metzgerei, GOURMET FINEST CUISINE) are deliberately left to the keyword
    # layer, like Gut&Günstig / Deluxe / Dr.Oetker. "tuc "/"joie " keep a trailing space —
    # these are matched as substrings, so a bare 3-4 letter key would fire mid-word (cf.
    # "lorenz " swallowing Lorenzo).
    "halloren": "sweets", "storck": "sweets", "ahoj": "sweets", "philadelphia": "cheese",
    "eberswalder": "pork", "pottkieker": "pantry", "tuc ": "snacks",
    "workzone": "household", "joie ": "household",
}

# Definitive *form* words (and single-category product brands): a product literally called a
# limonade / saft / joghurt / chips — or a Froop / Müllermilch / Vilsa — IS that category, so
# these beat even a mis-filed food taxonomy path (the source files "Bananenchips" under Obst,
# the flavoured water "Vilsa H2 Obst …" under Obst). Only words that pin the category by form
# or an unambiguous brand, never a mere flavour — so a frozen "…Schoko" brand isn't dragged
# here. Space-guarded where a fruit word is a superstring ("nektar " vs "Nektarine").
_FORM_OVERRIDES: list[tuple[str, list[str]]] = [
    ("soft_drinks", ["limonade", "schorle", "nektar ", "smoothie", "saft ", "fruchtsaft", "vilsa",
                     "alkoholfrei"]),  # alkoholfrei beer/wine -> soft, beating a "Bier"/"Wein" path
    # Spirits / premixed drinks the source mis-files under a soft or brand-beverage node:
    # Jägermeister (Dessert>Eis), Havana Club Dosen (Softdrinks>Cola), a Nordhäuser Williams
    # pear brandy (Marken Getränke), a hard seltzer (Softdrinks>Energydrink).
    ("alcoholic", ["jägermeister", "havana club", "nordhäuser", "hard seltzer"]),
    # Pet care / cat food the source files under a food node (dog Dental-Sticks in Knabberzeug>
    # Sticks; "Hello my cat" under the Gut&Günstig house brand) — must beat the path.
    ("household", ["dental", "hello my cat"]),
    # Breaded chicken drumsticks the source dumps into Knabberzeug>Sticks (a snacks node); no
    # ice-cream "Drumstick" is in the feed, so this is unambiguous poultry.
    ("poultry", ["drumstick"]),
    ("dairy", ["joghurt", "jogurt", "froop", "skyr", "müllermilch", "fruchtzwerge", "fruchtquark"]),
    ("snacks", ["chips", "trüfrü", "trufru"]),  # freeze-dried fruit snack filed under Obst
    # Root veg the source sometimes mis-files under "Dessert > Eis" (a carrot is not ice cream).
    # After beverages/dairy so Möhrensaft/Möhrenjoghurt still win their form.
    ("vegetables", ["möhre", "möhren"]),
    # Poultry sausage/cold cuts. THE biggest mis-file cluster (~20 products): the source files
    # them under "Wurstwaren > Wurst > Brühwurst"/"Fleisch > Fleischzubereitungen", which map to
    # pork, and a path beats a keyword — so "Gutfried Hähnchen-Fleischwurst" and "Langewiesche
    # Putenbrust" landed in pork. Proven by the same product classifying BOTH ways depending on
    # whether its path was a Wurstwaren node or a brand leaf. Only layer 2 can beat the path.
    ("poultry", ["geflügel", "hähnchen", "hähnchenbrust", "putenbrust", "puten-", "truthahn"]),
]

# What the flyer CAPTION says the product is. Read from `Offer.unit`, which holds the source's
# descriptive line ("55% Fett i. Tr. 150g Packung", "der leckere Geflügel-Aufschnitt", "Blätterteig
# mit einer Füllung aus Apfelstückchen"). The name is a marketing string and lies constantly — a
# flavour word in it steals the product ("Bauer Diplomat Paprika" is a CHEESE, "Müller & Müller
# Truthahnbrust mit Paprikarand" is POULTRY) — while the caption states the legal/product
# designation. Checked AFTER the name form-words above (those are proven and specific) but BEFORE
# the source path, so it can beat a mis-filed path.
#
# These must be DESIGNATIONS, not ingredients — every entry was checked against all stored offers
# and only kept if it moved nothing correct. Deliberately rejected: bare "frischkäse" (moves a
# Coppenrath *cheesecake*), bare "schmelzkäse" (moves a cracker+sausage snack box that merely
# contains some), "plunderteig" (a poultry-filled pastry roll is arguably not bakery), and
# "gebäck"/"rindfleisch" (hit sweets and mixed Bratwurst respectively).
_CAPTION_SIGNALS: list[tuple[str, list[str]]] = [
    # "45% Fett i. Tr." is a legal fat-in-dry-matter declaration; only cheese carries it.
    ("cheese", ["fett i. tr", "fett i.tr", "schnittkäse", "weichkäse", "hartkäse", "brühkäse",
                "reibekäse", "frischkäsezubereitung", "schmelzkäsezubereitung", "käse-frischpack"]),
    ("bakery", ["blätterteig", "hefeteig", "hefefeingebäck", "mürbeteig"]),
    # "Lachs" is a German LOIN cut as well as salmon: Lachsschinken / Graved Lachsfleisch /
    # Schweinelachsschinken are cured PORK, and only the caption says so.
    ("pork", ["vom schwein", "schweinebauch", "schweinerücken", "schweinefleisch", "schweinelachs"]),
    ("ice_cream", ["stieleis", "eiscreme"]),
]

# Flavour / drink-type tokens (and specific compounds that must beat a generic fruit
# substring) checked after the brand map but before _RULES, so a flavour word can't beat
# the real category (e.g. "Mango" in a sparkling-wine name) and a compound noun beats its
# misleading prefix ("Pflaumentomaten" is a tomato, "Apfelessig" is vinegar) — but a brand
# still wins (Häagen-Dazs "…Chocolate" is frozen, not sweets). Short tokens are space-padded.
_OVERRIDES: list[tuple[str, list[str]]] = [
    ("alcoholic", ["sekt", "frizzante", "secco", "prosecco", "hugo", "aperol", "bellini", "likör",
                   "aperitif", "glühwein", "wodka", "whisky", "pilsener", " gin ", " rum "]),
    ("soft_drinks", ["eistee", "ice tea"]),  # iced tea is a soft drink, not alcohol/ice cream
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


def classify(
    name: str,
    brand: str | None = None,
    category_path: Optional[List[str]] = None,
    unit: str | None = None,
) -> str:
    """Map a product (name + optional brand + source path + flyer caption) to a slug.

    `unit` is the source's descriptive line (see `_CAPTION_SIGNALS`). It's optional so old
    callers keep working, but pass it when you have it: the name is a marketing string that
    lies, and the caption states what the product actually is.
    """
    path = category_path or []
    # 0. Explicitly-vegan products are their own category (the user's choice: vegan is a
    #    section, so a vegan cheese moves out of Cheese). First, so it also rescues vegan
    #    *food* the source mis-files under a non-food path (REWE plant-based → "household").
    if is_vegan(name, brand):
        return "vegan"
    # 1. A non-food source path is authoritative ("Sektkühler" is household, not a drink).
    if _path_nonfood(path):
        return "household"
    text = f" {name.lower()} {(brand or '').lower()} "
    # 2. Definitive form words beat a *mis-filed food* path (Bananenchips under Obst, etc).
    for slug, tokens in _FORM_OVERRIDES:
        if any(token in text for token in tokens):
            return slug
    # 2b. What the CAPTION says it is. Beats the path below, because the path is frequently
    #     mis-filed (a cheese under "Gemüse > Kohl", a pastry under "Obst > Rosinen") while the
    #     caption carries the product's own designation.
    if unit:
        caption = f" {unit.lower()} "
        for slug, tokens in _CAPTION_SIGNALS:
            if any(token in caption for token in tokens):
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
