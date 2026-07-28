"""Canonical product categories and the classifier.

`classify(name, brand, category_path)` applies, in order:

0. **Vegan** — an explicitly-vegan product (name/brand says vegan/pflanzlich, or a
   vegan-only brand like Vemondo) is its own category, beating every other signal
   (cross-cutting by choice — a vegan cheese is filed under "vegan", not "cheese").
1. **Non-food source path** — if the Bonial `categoryPaths` isn't under the food
   root, it's non-food → "household" — UNLESS a *high-confidence* food noun rescues
   it first (`_food_rescue`): the source dumps real produce/fish under generic pet /
   garden / promo nodes (Nektarinen under `Tierbedarf > Marken für Tiere`), so a
   specific food noun with no plant/clothing/pet veto beats the mis-filed path.
2. **Definitive form words** — limonade / saft / joghurt / chips beat even a
   *mis-filed* food path (the source files "Bananenchips" under Obst). Form words
   only — never a mere flavour — and space-guarded vs fruit superstrings
   ("nektar " vs "Nektarine").
2b. **Flyer caption** (`unit`) — what the source *says the product is* ("55% Fett i. Tr.").
   Before the path, because the path is frequently mis-filed while the caption carries
   the product's own designation.
3. **Food taxonomy node** — the most specific known node (an *intermediate* node;
   the leaf is often a brand, e.g. `…> Käse > Weichkäse` → cheese).
4. **Brand map** — unambiguous brands → one category (a brand beats a flavour word:
   Häagen-Dazs "…Chocolate" is frozen, not sweets).
5. **Flavour overrides** — a flavour word can't beat the real category ("Mango" in a
   sparkling-wine name).
6. **German-keyword rules** — first hit wins, specific buckets before broad.

The path handles the big, diverse flyer catalog deterministically; the keyword
layers cover coupons and brand-only flyer food. No LLM.

`explain()` returns the same answer plus a per-layer trace — which rule fired, which
layers were skipped and why, and what the losing layers *would* have said.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, List, Literal, Optional

from .vegan import vegan_match

# slug -> human label shown in the app
# Insertion order drives the filter-chip order (GET /api/categories iterates this dict).
CATEGORIES: dict[str, str] = {
    "fruits": "Fruits",
    "vegetables": "Vegetables",
    "beef": "Beef",
    "poultry": "Chicken & Poultry",
    "pork": "Pork & Sausage",
    "other_meat": "Lamb & Other Meat",  # lamb / rabbit / game — the meats that aren't beef/pork/poultry
    "fish": "Fish & Seafood",
    "butter": "Butter",
    "cheese": "Cheese",
    "dairy": "Milk & Dairy",
    "eggs": "Eggs",  # a thin chip (few branded egg offers) but its own aisle
    "bakery": "Bakery",
    "frozen": "Frozen",
    "ready_meals": "Ready Meals",  # prepared/heat-and-eat: Fertiggerichte, sushi, Maultaschen, döner
    "ice_cream": "Ice Cream",
    "sweets": "Sweets & Chocolate",
    "snacks": "Snacks",
    # Coffee is its own aisle, not a soft drink: it was 27% of soft_drinks (117 of 441 stored
    # offers) and a bag of beans has nothing to do with a bottle of cola. Tea stays in
    # soft_drinks on purpose — what the feed carries is almost entirely ready-to-drink iced
    # tea / kombucha, which really is a soft drink.
    "coffee": "Coffee",
    "soft_drinks": "Soft Drinks",  # beverages split: non-alcoholic (soda/juice/water/tea)
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
    "limonade": "soft_drinks", "kaffee": "coffee", "tee": "soft_drinks", "sekt": "alcoholic",
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
    # Lamb / rabbit / game — the meats that aren't beef/pork/poultry. BEFORE fish (so "Lammlachs",
    # a lamb LOIN the source files under "Fleisch > Lamm", isn't caught by the "lachs" fish rule)
    # and BEFORE pork (which used to own " lamm"/"kaninchen"). " lamm"/"reh " keep a leading/padded
    # space so they can't fire inside Fla(mm)kuchen / ve(rzehr); bare "wild" is avoided (Wildlachs
    # is fish).
    ("other_meat", [" lamm", "lamm-", "kaninchen", "hase ", "hirsch", "reh ", "rehkeule", "rehrücken",
                    "rehragout", "wildbret", "wildgulasch", "wildragout"]),
    # Ice cream before frozen (and before sweets, so "Snickers Ice Cream" isn't sweets).
    # " eis " is the standalone word only — space-padded so it can't fire inside Fleisch /
    # Reis / Eisberg / Eistee / Eiweiß (verified against the live catalog: 0 leaks).
    ("ice_cream", ["eiscreme", "speiseeis", "ice cream", "stieleis", "eis am stiel", "wassereis",
                   "soft-eis", "softeis", "milcheis", "fruchteis", "sandwich-eis", "sandwich eis",
                   "eisbecher", " eis ", "sorbet", "gelato", "plombir", "cremissimo", "magnum",
                   "cornetto", "pirulo", "nogger", "solero", "calippo", "viennetta", "nuii",
                   # 2026-07-28 audit: frozen ice treats the source leaves in Other.
                   "little moons", "mochi", "ice-bites"]),
    ("frozen", ["tiefkühl", "tiefkuehl", "tk-", "tk ", "gefrier", "pizza", "steinofen", "pommes",
                "wedges", "burrito", "piccolini"]),
    ("fish", ["fisch", "lachs", "thunfisch", "garnele", "forelle", "hering", "sardin", "sardelle",
              "scampi", "matjes", "meeresfrüchte", "octopus", "tentakel", "kalmar", "calamares", "prawn"]),
    ("poultry", ["hähnchen", "haehnchen", "huhn", "hühner", "pute", "puten", "geflügel", "chicken",
                 "corned turkey", "knusperdino", "wachtel"]),  # Knusperdinos = Hähnchenbrust nuggets
    # "gulasch"/"steak" are intentionally NOT here — they appear in Schweinegulasch
    # / Schweinesteak (pork); beef relies on "rind" and beef-specific cuts.
    # "angus" stays UNPADDED on purpose. It does fire inside "Lavendel angustifolia", but a
    # leading-space guard breaks the real "Black-Angus-Chipolata" (hyphen, not space) and the plant
    # is already caught by its non-food path. Verified: guarding it costs a beef row and saves none.
    ("beef", ["rind", "rinder", "tafelspitz", "angus", "t-bone", "rumpsteak", "rib eye", "hüftsteak",
              "burger patties", "smash burger", "kalb", "bavette", "chuck-eye", "chuck eye",
              "teres major"]),  # a beef shoulder cut ("Black Premium Teres Major")
    ("pork", ["schwein", "schnitzel", "hackfleisch", "hack ", " mett", "bratwurst", "wurst", "würstchen",
              "speck", "schinken", "salami", "kasseler", "leberkäse", "chorizo", "jamón", "jamon", "serrano",
              "fuet", "lyoner", "frikadelle", "kaminwurzerl", "bacon", "kebab", "cevapcici", "corned", "rügenwalder",
              # " lamm" and "kaninchen" moved to `other_meat` (runs earlier); "kebab" stays because
              # a Dönertasche is claimed by ready_meals first, and a plain kebab sausage is pork.
              "pastrami", "mortadella", "kabanos", "krustenbraten", "sparerib", "rippchen",
              # "würst" catches the umlaut plurals the bare "wurst" misses (Bockwürste,
              # Bratwürste); "haxe" is the pork knuckle — Kalbs-/Putenhaxe are safe because
              # the beef/poultry rules run first.
              "spare rib", "nackensteak", "würst", "haxe",
              # 2026-07-28 flyer audit: sausage/cured pork the house brands leave in Other.
              # "die thüringer" is the sausage BRAND phrase, not bare "thüringer" — the latter would
              # wrongly grab "Mischgemüse Thüringer Art" (a vegetable). sucuk is filed pork by the
              # sausage convention (the chip is "Pork & Sausage").
              "tyrolini", "sucuk", "salametti", "pancetta", "spanferkel", "die thüringer"]),
    # Margarine/spread brands moved to _FORM_OVERRIDES (they need to beat a "Margarine" path node);
    # the bare "rama" here was also a latent Ramazzotti bug, hidden only by that amaro's alcoholic path.
    ("butter", ["markenbutter", "deutsche butter", "süßrahm", "suessrahm", "butter "]),
    ("cheese", ["käse", "kaese", "gouda", "mozzarella", "feta", "camembert", "parmesan", "frischkäse",
                "emmentaler", "edamer", "grana", "manchego", "obazda", "zottarella", "queso", "brunch",
                "burrata", "kashkaval", "kasländer",
                # Cheese TYPES/names the house brands (Milbona, Milsani) file under a brand-leaf path
                # with no "käse" in the name: "Maasdamer" is always cheese; "Badejunge" is the Rügener
                # cheese; "Tolle Rolle" is the Milkana spreadable cheese (Milkana itself is multi-form
                # — Frischeschale is dairy — so only the specific name, not the brand).
                "maasdamer", "badejunge", "tolle rolle",
                "harzer"]),  # Harzer (sour-milk cheese), e.g. "Blankenburg Harzer Kräuterhexe"
    ("dairy", ["milch", "joghurt", "jogurt", "quark", "sahne", "schmand", "buttermilch", "pudding", "skyr",
               "almighurt", "ehrmann", "kefir", "ayran", "grütze", "milchreis", "fruchtzwerge", "monte ", "paradies creme",
               "crème fraîche", "creme fraiche", "crème fraiche", "zaziki", "tzatziki", "milchschnitte", "pingui"]),
    # Eggs. Space-padded " eier " matches the standalone word ("Bio Eier") but NOT the compounds
    # that are a different product: Eierlikör (alcoholic), Eiersalat (a deli salad -> pork),
    # Eierkuchenmehl (bakery), Eierkocher (an appliance). "freilandei"/"bodenhaltung" catch the
    # descriptive egg names. A thin category (few branded egg offers) but its own aisle by request.
    ("eggs", [" eier ", " eier,", " eier.", "freilandei", "bodenhaltung", "frühstücksei",
              "bio-eier", "eier 10", "eier 6"]),
    ("fruits", ["apfel", "äpfel", "banane", "erdbeer", "traube", "orange", "zitrone", "limette", "birne", "kiwi", "beere",
                "mango", "ananas", "melone", "pfirsich", "nektarine", "clementine", "mandarine", "avocado",
                "aprikose", "physalis", "pflaume", "kirsche", "grapefruit"]),
    # Bakery before vegetables so a veg-named *bread* (Knoblauchbrot, Zwiebelkuchen) is
    # bakery, not vegetables — the product word ("brot") should beat the flavour ("knoblauch").
    ("bakery", ["brot", "brötchen", "broetchen", "baguette", "croissant", "toast", "kuchen", "gebäck", "brezel",
                "ciabatta",  # a taxonomy node already, but the keyword layer had no entry
                "crusti", "donut", "törtchen", "nata", "magdalena", "muffin", "torte", "linzeraugen", "nusshappen",
                "buns", "laugen", "lauge", "plunder", "pita", "wrap", "blätterteig",
                "pane ", "tigerkruste", "grillkruste", "holzfäller", "knusperjung",  # Weizenbrötchen
                # ALDI's Cucina "Limonaie"/"Colombine" are "Feines Gebäck nach italienischer Art"
                # (200-g-Packung) — the word Gebäck is only on the flyer artwork, never in the
                # payload, so the product name is the only handle. Pinned like "knusperjung".
                "limonaie", "colombine",
                # 2026-07-28 audit: breads/pastries the house brands leave in Other.
                "bagel", "simit", "streuseltaler", "zwieback", "croutons",
                "focaccia"]),
    ("vegetables", ["tomate", "gurke", "salat", "kartoffel", "zwiebel", "paprika", "möhre", "moehre", "karotte",
                    "brokkoli", "blumenkohl", "spinat", "zucchini", "champignon", "pilz", "knoblauch", "lauch",
                    "sellerie", "kürbis", "rucola", "spargel", "kohlrabi", "coleslaw", "kresse",
                    # Green beans, spelled out rather than a bare "bohnen": that would also claim
                    # Kidneybohnen (a pantry pulse, cf. "kichererbsen"), coffee "Ganze Bohnen", and
                    # "Bio-Cracker mit Ackerbohnen" — vegetables runs before snacks/pantry.
                    "buschbohnen", "brechbohnen", "prinzessbohnen", "stangenbohnen", "grüne bohnen",
                    # Mushrooms the source leaves in Other (the "pilz"/"champignon" words don't reach them).
                    "pfifferling", "portobello"]),
    # Trailing spaces are load-bearing: "milka" fires inside Milkana (a cheese) and "fritt" inside
    # Heißluftfritteuse (an appliance) — today only a non-food path hides the latter.
    ("sweets", ["schokolade", "schoko", "praline", "keks", "bonbon", "gummibär", "riegel", "waffel", "nutella",
                "milka ", "haribo", "ritter sport", "toffifee", "duplo", "snickers", "twix", "ferrero", "hanuta",
                "loacker", "celebrations", "nudossi", "kinder cards", "fritt ", "sondey", "tenerezze",
                "fruchtgummi", "big choc", "smarties", "amicelli", "daim", "m&m", "maxi king",
                # "cheesecake" is a dessert either way (a Becher one is still sweet); the
                # ice_cream rule + the brand layer both run first, so Ben & Jerry's is safe.
                "kinder bueno", "bärchen", "profiterole", "cheesecake", "knister-pop",
                # 2026-07-28 audit: confectionery the house brands leave in Other.
                "chokis", "hitschies", "nippon"]),
    # NOTE: "knusper" removed — it's a coating adjective, not a snack noun; it mis-caught cat food
    # (Knuspermenü), chicken nuggets (Knusperdinos) and bread rolls (Knusperjungs), and matched 0
    # real snacks in the live feed. Specific "knusper*" products are pinned above (poultry/bakery).
    ("snacks", ["chips", "cracker", "nüsse", "nuesse", "erdnuss", "popcorn", "salzstange", "flips", "tortilla",
                "studentenfutter", "alesto", "trockenfrüchte", "knabber", "bake rolls", "snackmix",
                "walnusskern"]),
    ("alcoholic", [" bier", "lagerbier", " pils", "wein", "vodka", "champagner", "pilsener", "sangria",
                   "doppelkorn", "goldkrone", "weinbrand", "licor", "san miguel", "holsten", "moët", "moet",
                   "absolut", "korol", "cimarosa", "sauvignon", "primitivo"]),
    # Padding is load-bearing here too: bare "limo" claims Limonaie (an Italian lemon BISCUIT),
    # "spezi" claims Spezialsalz/Spezialmehl, and "latte" claims an Induktionskochplatte.
    # "Limonade" itself is caught a layer earlier, so "limo " only needs the standalone word.
    # Coffee runs BEFORE soft_drinks — they no longer share keywords, but keeping the narrower
    # category first makes the precedence explicit if either list grows.
    # Deliberately NOT brand keywords here, each measured against the stored offers:
    #   * "tchibo" — sells clothing and homeware too (7 of 11 stored rows are household,
    #     e.g. "Tchibo Top"); a brand keyword would drag them into coffee.
    #   * "melitta" — also filters and machines ("Melitta Barista" is a coffee *machine*).
    #   * "cappuccino" — zero stored rows, and it is a chocolate/ice-cream flavour word.
    # "jacobs" IS safe: all 18 stored rows are coffee, and it rescues 2 that fell to "other".
    # Machines are not at risk from these: a Kaffeevollautomat carries a non-food path, which
    # layer 1 claims for household long before this layer.
    ("coffee", ["kaffee", "espresso", "caffè", "caffe", "lavazza", "dallmayr", " latte",
                "bella crema", "röstkaffee", "jacobs",
                # "bellacrema" (no space) is the "Melitta BellaCrema" spelling the spaced
                # "bella crema" keyword misses.
                "bellacrema",
                # "rondo " is space-guarded so it can't fire mid-word; a Bahlsen Rondo biscuit
                # is caught by the "bahlsen" brand entry a layer earlier.
                # ("ganze bohnen"/"iced coffee" are layer-2 form words — see _FORM_OVERRIDES.)
                "rondo "]),
    ("soft_drinks", ["wasser", "cola", "limo ", "saft", " tee", "energy", "schorle", " spezi ",
                     "fanta", "sprite", "nektar", "pepsi", "solevita", "aloe vera", "smoothie",
                     # 2026-07-28 audit: drinks the house brands leave in Other. "iso light" is
                     # space/word-guarded (vs Isomalt/isotonisch); "gemüsesaft"/"gemüsesäfte"
                     # because the plural "-säfte" isn't caught by the bare "saft".
                     "rotbäckchen", "iso light", "activedrink", "gemüsesaft", "gemüsesäfte"]),
    ("pantry", ["nudel", "noodles", "pasta", "teigwaren", "porridge", "reis", "mehl", "zucker", " öl", "olivenöl", "essig", "konserve",
                "sauce", "soße", "gewürz", "müsli", "haferflocken", "honig", "marmelade", "ketchup", "senf",
                "oliven", "kichererbsen", "kidneybohnen", "kidney-bohnen", "aioli", "artischocken", "paella", "lupinen", "antipasti", "tapas",
                "penne", "fusilli", "spaghetti", "tagliatelle", "tortellini", "ravioli", "baked beans",
                "hummus", "tofu", "tempeh", "falafel", "mayonnaise", "maultaschen", "tahina", "tahin",
                "rapskernöl", "kernöl", "rapsöl", "sonnenblumenöl", "pinienkerne", "allioli",
                # "suppe " keeps the trailing space on purpose: it matches "Gulasch-Suppe"
                # but not Suppengrün (vegetables) or Suppenhuhn/-fleisch, which would
                # otherwise reach pantry — it sits second-to-last, so it can't be outranked.
                "fleischalternativ", "like meat", "likemeat", "nesquik",
                "suppe ", "eintopf", "eintöpf", "lasagne-blätter", "lasagneblätter", "gigli "]),
    ("household", ["spülmittel", "spuelmittel", "spülmaschinen", "waschmittel", "toilettenpapier", "küchenrolle", "reiniger",
                   "windel", "müllbeutel", "weichspüler", "oleander", "pflanze", "blume", "kleid", "jacke", "schuhe",
                   "garten", "werkzeug", "kissen", "bettdecke", "matratze", "wäschest", "haushaltshelfer",
                   "küchenhelfer", "rätselbuch", "autozubehör", "grillhelfer", "grillzubehör", "schreibwaren",
                   "geschenkpapier", "reinigung", "e-bike", "e-scooter", "ventilator", "staubsauger", "klimagerät",
                   "luftkühler", "bügeleisen", "bügelstation", "fritteuse", "shampoo", "duschgel", "zahnbürste",
                   "rasierer", "haartrockner", "batterien", "kosmetik", "sonnenschutz", "pavillon", "fahrradträger",
                   # "chrysanthem" (not the plural) also catches the singular "Chrysantheme".
                   "fahrradanhänger", "wanduhr", "kühltasche", "chrysanthem", "lavendel", "palme", "kreuzfahrt", "hotel",
                   "holzkohle", "grillkohle", "brikett", "grillmatte", "haushaltstuch", "müllbeutel", "papierbeutel",
                   "hortensie", "floristen", "blumenstrauß", "keramikgrill", "hundespielzeug", "plüschtier",
                   "spielzeug", "prospekthülle", "auto laden"]),
]

# Unambiguous brand -> category. Multi-category house brands (Milbona, Metzgerfrisch,
# Sol & Mar, Zott) are left to the path / keyword layers — a brand entry beats every keyword, so a
# brand that spans categories mis-files every product whose path is a brand leaf. Removed for that
# reason: "rondo" (Bahlsen biscuits AND Röstfein coffee — all 3 live rows are coffee; the roaster
# brand "röstfein" + a space-guarded "rondo " keyword cover them).
#
# Two members of that class deliberately STAY, because removing them costs more than it saves —
# each is pinned by a test so the trade-off doesn't get silently "fixed" later:
#   * "mövenpick" (ice cream AND coffee) — its coffees are rescued a layer EARLIER instead (the
#     "ganze bohnen"/"iced coffee" form words, which beat the brand map), while a bare "Mövenpick
#     Edle Komposition" carries no other signal and falls to "other" without the brand entry.
#   * "kerrygold" (butter AND cheese) — all live rows classify correctly (its cheeses carry "Käse"
#     in the name or a Käse path node), and removing it would drop "Kerrygold extra XXL", whose
#     name and caption never say "butter", into "other". Revisit if a Kerrygold cheese lands in
#     butter.
# Trailing spaces on short keys ("milka ", "trolli ") stop them firing inside Milkana (a cheese)
# and Trollinger (a wine); cf. "lorenz " vs Lorenzo.
BRAND_CATEGORY: dict[str, str] = {
    "allini": "alcoholic", "mister choc": "sweets", "ritter sport": "sweets", "milka ": "sweets",
    "iglo": "frozen", "gelatelli": "ice_cream", "langnese": "ice_cream", "bon gelati": "ice_cream",
    "schöller": "ice_cream", "ben & jerry's": "ice_cream", "ben & jerry": "ice_cream",
    "gustavo gusto": "frozen", "ferrero": "sweets", "loacker": "sweets",
    "dulano": "pork", "meica": "pork", "brunch": "cheese", "kerrygold": "butter",
    # Stockmeyer is single-category pork cold cuts (Salami, Sonntags-Frühstück). NOT Block House —
    # the steakhouse brand also sells garlic BREAD ("BLOCK HOUSE Brot XXL Knoblauch" → bakery), so
    # its two burgers stay in Other rather than risk that (pinned by test_classify_expanded_names).
    "stockmeyer": "pork",
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
    "hochland": "cheese", "trolli ": "sweets", "nescafé": "coffee", "nescafe": "coffee",
    "röstfein": "coffee", "reinert": "pork",
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
    # Single-category cheese brands the source leaves on a bare brand-leaf path (no "käse" in the
    # name): Rücker (Alter Schwede + Grill-/Pfannenkäse) and Grünländer (Hochland's cheese line).
    "rücker": "cheese", "rucker": "cheese", "grünländer": "cheese", "grünlander": "cheese",
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
    # --- entries that must PRECEDE the generic drink forms below (first hit wins) ---
    # A "-dicksaft"/"Goldsaft" is a SYRUP, not a juice: the "saft " guard only pins the trailing
    # side, so "Agavendicksaft " / "Grafschafter Goldsaft " match it and land in soft_drinks.
    # Their captions say what they are ("ideal zum Süßen", "Herzhaft-süßer Brotaufstrich").
    ("pantry", ["dicksaft", "goldsaft", "rübensaft"]),
    # "X oder/auch alkoholfrei" is a MULTI-VARIANT beer offer (Benediktiner Hell, Festbier oder
    # alkoholfrei), not an alcohol-free product — the bare "alkoholfrei" below would file the whole
    # beer as a soft drink. Only the standalone designation counts.
    ("alcoholic", ["oder alkoholfrei", "auch alkoholfrei"]),
    # A Weinschorle is wine + water: alcoholic. Must precede the "schorle" form word.
    ("alcoholic", ["weinschorle"]),
    ("soft_drinks", ["limonade", "schorle", "nektar ", "smoothie", "saft ", "fruchtsaft", "vilsa",
                     # Spezi (cola-orange) is a soft drink the source files under "Bier > Biermarken
                     # > Paulaner", so only layer 2 can rescue it. Padded BOTH sides: an unpadded
                     # "spezi" fires inside Spezialsalz / Spezialmehl / Käsespezialitäten.
                     " spezi ",
                     "alkoholfrei"]),  # alkoholfrei beer/wine -> soft, beating a "Bier"/"Wein" path
    # Coffee that a multi-category brand would otherwise claim: Mövenpick is ice cream AND coffee,
    # so "Mövenpick Ganze Bohnen" was ice_cream and its chilled RTD "Iced Coffee" ("220-ml-Becher",
    # "koffeinhaltig") was too — the source files the latter under its own "Eis" node. Rescuing them
    # HERE (layer 2 beats both the path and the brand map) keeps "mövenpick" -> ice_cream usable for
    # the actual ice creams, which have no other signal. "iced coffee" also carries the English
    # spelling that the German "kaffee" keyword can't reach.
    ("coffee", ["iced coffee", "eiskaffee", "ganze bohnen"]),
    # Spirits / premixed drinks the source mis-files under a soft or brand-beverage node:
    # Jägermeister (Dessert>Eis), Havana Club Dosen (Softdrinks>Cola), a Nordhäuser Williams
    # pear brandy (Marken Getränke), a hard seltzer (Softdrinks>Energydrink).
    ("alcoholic", ["jägermeister", "havana club", "nordhäuser", "hard seltzer"]),
    # Pet care / pet food the source files under a food node or leaves pathless with a meat word
    # in the name — must beat both the path (L3) and the meat keywords (L6). Real cases fixed:
    # "Orlando Hundetrockennahrung Rind" was BEEF; "ROMEO Kauknochen aus Kaffeeholz" was COFFEE;
    # "Sheba Katzennassfutter Filets" (a "Fisch" path) was FISH; "Coshida Knabbersnacks" was SNACKS.
    # Every token verified pet-only over the DB — the "-nahrung"/"-futter" stems are animal-only
    # (baby food is Anfangs-/Säuglings-/Trink-nahrung, none of which match), and `coshida`/`sheba`
    # are single-category pet brands (unlike Orlando, which also sells human Mexican food).
    ("household", ["dental", "hello my cat", "topfpflanze",
                   "trockennahrung", "nassnahrung", "nassfutter", "trockenfutter", "hundefutter",
                   "hundenahrung", "tierfutter", "tiernahrung", "vogelfutter", "katzenstreu",
                   "kausnack", "kaurollen", "kauknochen", "kaustange", "coshida", "sheba"]),
    # Breaded chicken drumsticks the source dumps into Knabberzeug>Sticks (a snacks node); no
    # ice-cream "Drumstick" is in the feed, so this is unambiguous poultry.
    ("poultry", ["drumstick"]),
    ("dairy", ["joghurt", "jogurt", "froop", "skyr", "müllermilch", "fruchtzwerge", "fruchtquark"]),
    # Freeze-dried fruit is a shelf-stable SNACK, not frozen food — "gefrier" alone reads
    # "Gefriergetrocknete Himbeeren" as tiefkühl.
    ("snacks", ["chips", "trüfrü", "trufru", "gefriergetrocknet"]),
    # "Lachs" is a German LOIN cut as well as a salmon: a Lachsschinken is cured PORK, but the
    # fish rule ("lachs") runs first and the source files one under "Bier > Biermarken > Radeberger".
    ("pork", ["lachsschinken"]),
    # A Fleischkäse (Leberkäse) is a meat loaf — the "käse" cheese rule steals it whenever the
    # source gives it no Wurstwaren path.
    ("pork", ["fleischkäse"]),
    # Beef mince the source files under "Fleisch > Fleischzubereitungen" (-> pork). Only the
    # explicit compound: "Hackfleisch gemischt aus Rind und Schwein" is legitimately pork.
    ("beef", ["rinderhack", "rinder-hack"]),
    # Fish the source dumps under a BEER brand node ("Bier > Biermarken > Golden" -> alcoholic).
    # Both words are unambiguous fish, unlike the bare "lachs" above. `lachsforelle`/`thunfischfilet`
    # rescue "Golden Seafood Lachsforelle" & co. off the same beer-brand nodes (2026-07-28 audit).
    ("fish", ["lachsfilet", "backfisch", "lachsforelle", "thunfischfilet"]),
    # More strays the source files under a Sekt/Beer node (-> alcoholic): a chewing gum under
    # "Dom Perignon", a soured-cream butter under "Veltins". L2 so they beat that path.
    ("sweets", ["kaugummi"]),
    ("butter", ["fassbutter"]),
    # A croissant is bakery whatever it's filled with — "schinken" (pork) outranks "brot"/"gebäck"
    # in the keyword rules, so a Schinken-Käse-Croissant lands in pork.
    ("bakery", ["croissant"]),
    # Root veg the source sometimes mis-files under "Dessert > Eis" (a carrot is not ice cream).
    # After beverages/dairy so Möhrensaft/Möhrenjoghurt still win their form.
    ("vegetables", ["möhre", "möhren"]),
    # Prepared / heat-and-eat meals. A layer-2 override because the source scatters them under a
    # mis-filed path the keyword layer can't beat ("Sushi4You"->Feinkost, "Curry King"->Würzmittel,
    # "iglo Fertiggerichte"->Nudeln) AND under brands that would otherwise win ("frosta"->frozen,
    # "meica"->pork, a "YOUCOOK … Chicken"->poultry). Anchored on the designation "fertiggericht" +
    # unambiguous ready products; this consolidates ALL Fertiggerichte into one aisle regardless of
    # shelf. NOTE: "gekühlt" is NOT a signal — it means "chilled" and sits on ~100 fridge staples
    # (butter, cheese, cold cuts). "dönertasche" (not bare "döner", vs a Döner spice); chilled
    # pizza is deliberately left in `frozen` (splitting pizza by shelf is more confusing than help).
    ("ready_meals", ["fertiggericht", "youcook", "you cook", "sushi", "curry king", "dönertasche",
                     "maultaschen"]),
    # Margarine / plant spreads -> butter (the user groups them with butter). The source files
    # them under a "Pflanzlicher Brotaufstrich > Margarine" node that maps to nowhere, so they fell
    # to pantry/other; the designation "margarine" and the unambiguous spread brands pin them.
    # "rama " keeps a trailing space: it must not touch "Ramazzotti" (an amaro — no space after
    # "rama") — and "RAMA Cremefine" (a cooking cream) is already caught at layer 1 by its Drogerie
    # path, before this layer, so it stays out of butter.
    ("butter", ["margarine", "rama ", "lätta", "latta", "deli reform", "kærgården", "kaergården",
                "kaergarden", "sanella", "becel"]),
    # Vegetarian (NOT vegan) products filed by their MAIN INGREDIENT, per the user: Valess is a
    # milk-protein product -> cheese, but the source files it under "Fleisch > Schnitzel" (its
    # meat-substitute shape), so only a layer-2 override can move it. `vegetarisch != vegan`
    # (documented) — a vegan brand would already have been caught at layer 0.
    ("cheese", ["valess"]),
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
    # A Fassbrause is by definition an alcohol-free soft drink; the source files Veltins' one
    # under "Bier > Biermarken > Veltins". NOTE: a bare "alkoholfrei" caption signal was tried and
    # REJECTED — ~30 real beers carry "auch/teilw. alkoholfrei" in the caption (a variant note,
    # not the product), so it would empty the beer aisle into soft_drinks.
    ("soft_drinks", ["fassbrause"]),
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
    # " sekt" is padded on the leading side: bare "sekt" fires inside "Insektenabwehr" /
    # "Insektenstichheiler" — today only their non-food path hides it.
    ("alcoholic", [" sekt", "frizzante", "secco", "prosecco", "hugo", "aperol", "bellini", "likör",
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


# Real food the source scatters under a NON-food path. The offending leaves are generic buckets that
# carry no real category — pet-brand nodes (`Tierbedarf > Marken für Tiere`), promo/loyalty nodes
# (`Saison und Events > Payback`), or a bare brand (`Marken > REWE Beste Wahl`) — so REWE's regional
# produce, Deutsche See fish, etc. land in "household". These are HIGH-CONFIDENCE food nouns: specific
# enough that a plant / appliance / garment / pet food can't carry them (the generic produce keywords
# like "salat"/"tomate" are deliberately NOT reused — they'd catch a Salatschleuder or a Tomaten-
# pflanze). A rescue only fires when the path is non-food AND no `_RESCUE_VETO` word is present, so a
# food-path item (an Erdbeer-Joghurt) is never pulled into fruits.
_FOOD_RESCUE: dict[str, list[str]] = {
    "fruits": ["nektarine", "plattpfirsich", "aprikose", "brombeere", "himbeere", "erdbeere",
               "pflaume", "wassermelone", "honigmelone", "kirsche", "heidelbeere", "blaubeere",
               "stachelbeere", "johannisbeere", " mango", "papaya", "weintraube"],
    "vegetables": ["rispentomate", "romatomate", "cherrytomate", "kulturchampignon", "champignon",
                   "zucchini", "rucola", "feldsalat", "wildkräuter salat"],
    "fish": ["deutsche see", "lachsfilet", "pangasius", "räucher-garnele"],
    "poultry": ["maishähnchen", "geflügelsalat", "geflügel-fleischsalat", "hähnchen-grillplatte"],
    "snacks": ["jumbo erdnüsse", "erdnusskerne", "erdnuss-flip", "cashew", "walnusskern", "reiswaffel"],
    "bakery": ["roggenmischbrot", "vollkornbrot", "mehrkornbrot"],
    "pantry": ["guacamole", "tomatenketchup", "agavendicksaft", "quinoa"],
    "beef": ["ochsen-bäckchen", "ochsenbäckchen"],
    # Pork the source files under a non-food "Grillfleisch"/promo node → household ("Hausmarke
    # Schweine-Nackensteaks"). `nackensteak` is already a pork keyword, but the path wins first, so
    # the rescue re-claims it. Specific enough that only pork carries them.
    "pork": ["schweinenacken", "schweine-nacken"],
    # Grated cheese the source mis-files under a PET-brand node ("Milsani Reibekäse XXL" under
    # "Marken für Tiere"). Real cheese, not pet food, so it's a rescue — the pet guard's tokens
    # don't match "reibekäse", and no pet product carries the word.
    "cheese": ["reibekäse", "reibekase"],
    # Drinkable coffee filed under a non-food node (Senseo pads and a REWE Bio Caffè Crema sit
    # there). The APPLIANCES that share these words — Kaffeevollautomat, Espressomaschine,
    # Filterkaffeemaschine, "Melitta Barista" — are genuinely household and are held there by
    # `_RESCUE_VETO` below; that veto is what makes rescuing on "kaffee" safe at all.
    # A bare "kaffee" on purpose, NOT the narrower "kaffeepad"/"kaffeekapsel": the narrow form
    # happened to give the same answer, but only because no appliance name contains those words —
    # which made `_RESCUE_VETO` below dead code that no test could exercise. With "kaffee" the veto
    # is load-bearing and measurable: removing it leaks 7 machines (Kaffeevollautomat x3,
    # Filterkaffeemaschine x2, DeLonghi x2) into Coffee. "espresso" is deliberately NOT here —
    # it would drag in a "CROFTON Espressokocher" (a moka pot).
    "coffee": ["kaffee", "caffè crema", "ganze bohnen"],
}

# If any of these appear in the name, the food noun is a coincidence and the non-food path stands:
# a garden plant, a garment, cookware/DIY material, or pet food — the things that legitimately live
# under the non-food roots and happen to share a word with a produce/meat noun ("Mango" the fashion
# brand, "Kirschholz" furniture, "Tomatenpflanze", "Good Boy … Knabbermix" cat treats).
_RESCUE_VETO: list[str] = [
    "pflanze", "hyazinth", "röschen", "strauch", "saatgut", " samen", "topfrose", "kunstblume",
    "schleierkraut", " beet", "kübel", "blumen", "baumschule",
    " hose", "shirt", "jacke", "socken", "kleid", "pulli", "pullover", "jeans", "leggings",
    " holz", "möbel", " lack",
    "knabbermix", "katzen", "hunde", "für tiere", " napf", "tierfutter", "vogelfutter",
    # Coffee APPLIANCES keep their non-food path: a Kaffeevollautomat is not coffee. Without
    # these the "coffee" rescue above would drag every machine into the Coffee aisle.
    "vollautomat", "maschine", "barista", "mahlwerk", "milchaufschäumer", "kocher",
]


# --------------------------------------------------------------------------------------
# The classifier.
#
# `classify()` and `explain()` must never disagree about which rule won, so there is exactly
# ONE walk of the tables — `_layers()`, a generator yielding one LayerTrace per layer, in
# order — plus one selector, `_winner()`. Short-circuiting is a property of the CONSUMER,
# not of a second code path: `classify` abandons the generator at the first decided layer
# (so the layers after it never execute, exactly as the old inline cascade), while `explain`
# pulls all of them to report what the *losing* layers would have said. Reordering a layer
# means moving one `yield`, and both consumers move with it.
# --------------------------------------------------------------------------------------

# Closed vocabularies for LayerTrace.where / .reason (tests assert on these strings).
_WHERE_RAW = "name_brand_raw"  # layer 0: the raw name+brand — not lowered, not padded
_WHERE_TEXT = "name_text"  # the padded name+brand blob (`_haystack`)
_WHERE_CAPTION = "caption"  # the padded flyer caption (`unit`)
_WHERE_PATH = "path"  # the source taxonomy path
_WHERE_BRAND = "brand_field"  # the bare, UNPADDED brand column

_NO_PATH = "no_category_path"
_PATH_IS_FOOD = "path_is_food_root"
_NO_UNIT = "no_unit"
_RESCUE_VETO_HIT = "rescue_veto"
_NO_RESCUE_TOKEN = "no_rescue_token"
_FALLBACK = "fallback"

LayerStatus = Literal["decided", "skipped", "no_match"]


@dataclass(frozen=True, slots=True)
class LayerTrace:
    """One layer's verdict. `status == "decided"` iff `slug` is set — see the constructors.

    A layer identifies its rule by `table` + `index`, never by `slug` alone: slugs repeat
    within the ordered tables (`_FORM_OVERRIDES` holds "alcoholic" three times), so the slug
    does not name an editable rule while `_FORM_OVERRIDES[2]` does.
    """

    layer: str  # "0", "1", "2", "2b", "3", "4", "5", "6", "7" — the module docstring's numbering
    name: str  # "vegan", "nonfood_path", "form_overrides", …
    status: LayerStatus
    slug: str | None = None  # what it decided — or WOULD have, when it isn't the winner
    table: str | None = None  # which rule table matched
    index: int | None = None  # position in it; None for the `_PATH_MAP` dict lookup
    matched: str | None = None  # the exact token / brand key / path node / regex match
    where: str | None = None  # which haystack it matched against
    reason: str | None = None  # why it was skipped, or which branch of layer 1 ran
    blocked_slug: str | None = None  # layer 1 only: the rescue a `_RESCUE_VETO` word killed

    @classmethod
    def decided(cls, layer: str, name: str, slug: str, **kw: object) -> LayerTrace:
        return cls(layer, name, "decided", slug, **kw)  # type: ignore[arg-type]

    @classmethod
    def skipped(cls, layer: str, name: str, reason: str) -> LayerTrace:
        return cls(layer, name, "skipped", reason=reason)

    @classmethod
    def missed(cls, layer: str, name: str, where: str | None = None) -> LayerTrace:
        return cls(layer, name, "no_match", where=where)


@dataclass(frozen=True, slots=True)
class TraceInputs:
    """What the classifier actually saw — including the two things the API otherwise hides.

    `category_path` is stored but deliberately absent from `OfferOut`, and `text`/`caption`
    are the REAL space-padded haystacks — which is what answers "why didn't my token match?"
    (the space guards in keys like "rama " / " lamm" are invisible from the product name).
    """

    name: str
    brand: str | None
    category_path: List[str] | None
    unit: str | None
    text: str
    caption: str | None


@dataclass(frozen=True, slots=True)
class ClassifyTrace:
    category: str
    inputs: TraceInputs
    layers: tuple[LayerTrace, ...]

    @property
    def winner(self) -> LayerTrace:
        return _winner(self.layers)


def _haystack(name: str, brand: str | None) -> str:
    """The space-padded name+brand blob that layers 1/2/4/5/6 match against.

    The padding is load-bearing: hand-written keys emulate word boundaries with it ("rama "
    vs Ramazzotti, " lamm" vs F-lamm-kuchen, " eis " vs Fleisch/Reis). NOTE layer 1 used to
    build its own byte-identical copy — sharing this is a no-op today, but it means changing
    the padding here now moves layer 1 too.
    """
    return f" {name.lower()} {(brand or '').lower()} "


def _first_token_hit(
    table: Iterable[tuple[str, List[str]]], haystack: str
) -> Optional[tuple[int, str, str]]:
    """First (index, slug, token) whose token is a substring — the entry `any()` stopped on."""
    for index, (slug, tokens) in enumerate(table):
        for token in tokens:
            if token in haystack:
                return index, slug, token
    return None


def _first_brand_hit(brand_text: str, text: str) -> Optional[tuple[int, str, str, str]]:
    """First BRAND_CATEGORY key found in the brand column, else in the name+brand blob.

    The two `if`s are `brand_key in brand_text or brand_key in text` with attribution kept.
    `brand_text` is deliberately NOT padded (unlike `text`), so space-guarded keys like
    "lorenz " / "tuc " can only ever fire off the blob — don't "fix" that asymmetry.
    """
    for index, (brand_key, slug) in enumerate(BRAND_CATEGORY.items()):
        if brand_key in brand_text:
            return index, slug, brand_key, _WHERE_BRAND
        if brand_key in text:
            return index, slug, brand_key, _WHERE_TEXT
    return None


def _token_layer(
    layer: str,
    name: str,
    table_name: str,
    table: Iterable[tuple[str, List[str]]],
    haystack: str,
    where: str,
) -> LayerTrace:
    """The shared body of the four token-table layers (2, 2b, 5, 6)."""
    hit = _first_token_hit(table, haystack)
    if hit is None:
        return LayerTrace.missed(layer, name, where)
    index, slug, token = hit
    return LayerTrace.decided(
        layer, name, slug, table=table_name, index=index, matched=token, where=where
    )


def _path_nonfood(category_path: List[str]) -> bool:
    """True if the source taxonomy files this outside the food root (-> household)."""
    return bool(category_path) and category_path[0].strip().lower() != FOOD_ROOT


def _path_node_hit(category_path: List[str]) -> Optional[tuple[str, str]]:
    """Most-specific known food taxonomy node -> (node as written, slug); the leaf is often a brand."""
    for node in reversed(category_path):
        slug = _PATH_MAP.get(node.strip().lower())
        if slug:
            return node, slug
    return None


def _layers(
    name: str,
    brand: str | None = None,
    category_path: Optional[List[str]] = None,
    unit: str | None = None,
) -> Iterator[LayerTrace]:
    """Yield every layer's verdict in order, evaluating each only when it is pulled."""
    path = category_path or []
    # 0. Explicitly-vegan products are their own category (the user's choice: vegan is a
    #    section, so a vegan cheese moves out of Cheese). First, so it also rescues vegan
    #    *food* the source mis-files under a non-food path (REWE plant-based → "household").
    vegan_hit = vegan_match(name, brand)
    yield (
        LayerTrace.decided("0", "vegan", "vegan", matched=vegan_hit, where=_WHERE_RAW)
        if vegan_hit
        else LayerTrace.missed("0", "vegan", _WHERE_RAW)
    )
    text = _haystack(name, brand)
    # 1. A non-food source path is authoritative ("Sektkühler" is household, not a drink) — UNLESS a
    #    high-confidence food noun rescues it (the source dumps produce/fish under pet/garden/promo
    #    nodes). Gated on the non-food path so a food-path item (Erdbeer-Joghurt -> dairy) is untouched.
    if not path:
        yield LayerTrace.skipped("1", "nonfood_path", _NO_PATH)
    elif not _path_nonfood(path):
        yield LayerTrace.skipped("1", "nonfood_path", _PATH_IS_FOOD)
    else:
        # Split the two outcomes the old `_food_rescue` collapsed into a bare None: a veto word
        # killing a rescue and no rescue token at all both produced "household", indistinguishably.
        veto = next((v for v in _RESCUE_VETO if v in text), None)
        rescue = _first_token_hit(_FOOD_RESCUE.items(), text)
        if veto is not None:  # the veto still wins, exactly as before
            yield LayerTrace.decided(
                "1", "nonfood_path", "household", table="_RESCUE_VETO", matched=veto,
                where=_WHERE_TEXT, reason=_RESCUE_VETO_HIT,
                blocked_slug=rescue[1] if rescue else None,
            )
        elif rescue is not None:
            yield LayerTrace.decided(
                "1", "nonfood_path", rescue[1], table="_FOOD_RESCUE",
                index=rescue[0], matched=rescue[2], where=_WHERE_TEXT,
            )
        else:
            yield LayerTrace.decided("1", "nonfood_path", "household", reason=_NO_RESCUE_TOKEN)
    # 2. Definitive form words beat a *mis-filed food* path (Bananenchips under Obst, etc).
    yield _token_layer("2", "form_overrides", "_FORM_OVERRIDES", _FORM_OVERRIDES, text, _WHERE_TEXT)
    # 2b. What the CAPTION says it is. Beats the path below, because the path is frequently
    #     mis-filed (a cheese under "Gemüse > Kohl", a pastry under "Obst > Rosinen") while the
    #     caption carries the product's own designation.
    if unit:  # NOT `is not None` — an empty caption stays skipped
        yield _token_layer(
            "2b", "caption_signals", "_CAPTION_SIGNALS", _CAPTION_SIGNALS,
            f" {unit.lower()} ", _WHERE_CAPTION,
        )
    else:
        yield LayerTrace.skipped("2b", "caption_signals", _NO_UNIT)
    # 3. The food taxonomy node (an *intermediate* node; the leaf is often a brand).
    if not path:
        yield LayerTrace.skipped("3", "path_node", _NO_PATH)
    else:
        node_hit = _path_node_hit(path)
        yield (
            LayerTrace.decided(
                "3", "path_node", node_hit[1], table="_PATH_MAP",
                matched=node_hit[0], where=_WHERE_PATH,
            )
            if node_hit
            else LayerTrace.missed("3", "path_node", _WHERE_PATH)
        )
    # 4. Unambiguous brand (a brand beats a flavour word: Häagen-Dazs Chocolate is frozen).
    brand_hit = _first_brand_hit((brand or "").lower(), text)
    yield (
        LayerTrace.decided(
            "4", "brand_map", brand_hit[1], table="BRAND_CATEGORY",
            index=brand_hit[0], matched=brand_hit[2], where=brand_hit[3],
        )
        if brand_hit
        else LayerTrace.missed("4", "brand_map")
    )
    # 5. Flavour/priority overrides, then 6. German-keyword rules.
    yield _token_layer("5", "overrides", "_OVERRIDES", _OVERRIDES, text, _WHERE_TEXT)
    yield _token_layer("6", "rules", "_RULES", _RULES, text, _WHERE_TEXT)
    yield LayerTrace.decided("7", "fallback", "other", reason=_FALLBACK)


def _winner(layers: Iterable[LayerTrace]) -> LayerTrace:
    """The first layer that decided. Layer 7 always decides, so this always finds one."""
    for step in layers:
        if step.status == "decided":
            return step
    raise AssertionError("the fallback layer always decides")  # pragma: no cover


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
    # LAZY on purpose: `_winner` returns at the first decided layer and abandons the
    # generator, so the layers after it never run — the same short-circuit as before. Do NOT
    # simplify this to `explain(...).category`: that evaluates every layer (~3x the work) on
    # a path that runs once per scraped offer.
    return _winner(_layers(name, brand, category_path, unit)).slug or "other"


def explain(
    name: str,
    brand: str | None = None,
    category_path: Optional[List[str]] = None,
    unit: str | None = None,
) -> ClassifyTrace:
    """`classify` plus the full trace: every layer's verdict, in order.

    Eager, so the layers *after* the winner are evaluated too — a later "decided" entry is
    the counterfactual ("layer 3 would have said fish"), which is what tells you where a fix
    belongs. Shares `_layers`/`_winner` with `classify`, so the two cannot disagree on the
    winner. Note this reaches layers `classify` short-circuits past, so it sees inputs
    `classify` never touches — callers must validate `category_path` is a list of str.
    """
    layers = tuple(_layers(name, brand, category_path, unit))
    return ClassifyTrace(
        category=_winner(layers).slug or "other",
        inputs=TraceInputs(
            name=name,
            brand=brand,
            category_path=list(category_path) if category_path else None,
            unit=unit,
            text=_haystack(name, brand),
            caption=f" {unit.lower()} " if unit else None,
        ),
        layers=layers,
    )


def label(slug: str) -> str:
    return CATEGORIES.get(slug, "Other")
