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
    # --- Drugstore vertical (Rossmann; dm later) -------------------------------------
    # Appended, because insertion order IS the chip order and the food chips must not move.
    # `/api/categories` omits any slug with no offers, so a grocery PLZ simply never renders
    # these — no per-vertical category list is needed. They are NOT drugstore-only by
    # construction, though: a grocery chain's Nivea deo legitimately lands in `body`.
    "hair": "Hair Care",
    "face": "Face & Skin",
    "body": "Body & Shower",
    "dental": "Dental",
    "makeup": "Make-up",
    "fragrance": "Fragrance",
    "baby": "Baby & Kids",
    "health": "Health & Vitamins",
    "cleaning": "Cleaning",
    "laundry": "Laundry",
    "pet": "Pet",
}

#: The drugstore-vertical slugs, i.e. the ones layer 1 may rescue a non-food path into.
DRUGSTORE_CATEGORIES = frozenset(
    ("hair", "face", "body", "dental", "makeup", "fragrance",
     "baby", "health", "cleaning", "laundry", "pet")
)

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
    # The source's own leaf often names the SPECIES while the parent names only the cut, and
    # the leaf→root scan drops that information when the leaf isn't mapped: a
    # `… > Steak > Schweinerückensteak` fell through to `Steak` -> beef (an ALDI pork loin
    # steak served as Beef, caught from its photo), and `… > Braten > Rinderbraten` fell
    # through to `Fleischzubereitungen` -> pork (an Irish BEEF roast served as Pork).
    "schweinerückensteak": "pork", "rinderbraten": "beef",
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
    # --- Drugstore compounds that a FOOD token would otherwise swallow -----------------------
    # German compounding puts a food word inside a toiletry: a Mundwasser contains "wasser"
    # (soft_drinks), a Zahnpasta contains "pasta" (pantry), a Körper-/Sonnenmilch contains
    # "milch" (dairy). The drugstore aisles are spliced in near the END of this table (see the
    # note by `_DRUGSTORE_RULES`), so without these guards those food tokens win first — which
    # the shadowing ratchet correctly refused to let through.
    #
    # These only ever matter for a PATHLESS product: every one of these currently in the corpus
    # is already right, decided at layer 1 by its non-food path. That is exactly why the guard
    # belongs here rather than being "fixed later" — the failure is invisible until a chain
    # ships one of these without a path.
    ("dental", ["zahnpasta", "mundwasser"]),
    ("face", ["mizellenwasser", "gesichtswasser", "reinigungswasser"]),
    ("body", ["körpermilch", "sonnenmilch"]),
    ("baby", ["muttermilch"]),
    ("health", ["hustenbonbon"]),                 # a cough sweet, not a `bonbon`
    ("cleaning", ["scheuermilch",                 # scouring cream, not `milch`
                  "essigreiniger"]),              # a cleaner, not `essig` (pantry)
    ("laundry", ["wasserenthärter"]),             # a water softener, not `wasser`
    # --- 2026-07-31 image audit -------------------------------------------------------------
    # Found by reading contact sheets of every served product photo, which is the only thing
    # that settles a product whose name, brand, path AND caption all read plausibly for the
    # wrong category. These sit at the FRONT of the table, and the two nut entries are ordered:
    # a Pistazien/Erdnuss *creme* is a spread (pantry), so it has to be matched before the
    # nut-kernel entry claims it for snacks.
    ("pantry", ["pistaziencreme", "nusscreme"]),
    ("snacks", ["nuss-variation", "mandelkerne", "pistazien"]),
    # "Sweet Corner" is a gummy-sweets brand whose product names are fruit words — its
    # "Apfelringe/Saure Würmer" and "Süße Kirschen" (a bag of gummy cherries, confirmed from
    # the photo) were being served in Fruits. "zetti" was dropped by an earlier audit for
    # clashing with Mazzetti; "knusperflocken" is the collision-free half of it.
    ("sweets", ["sweet corner", "knusperflocken"]),
    # funny-frisch crisps: three sat in `other`, and "Ringli/Paprika-Ecken" plus "Jumpys
    # Paprika" were in VEGETABLES, claimed by the paprika keyword.
    ("snacks", ["funny-frisch"]),
    ("fruits", ["datteln"]),
    ("pantry", ["würzöl", "suppentopf", "grießbrei"]),
    ("alcoholic", ["aperitivo"]),
    ("butter", ["die extrazarte"]),
    ("dairy", ["der große bauer"]),
    # --- end image-audit block --------------------------------------------------------------
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
                "wedges", "burrito", "piccolini",
                # "la mia" is Dr. Oetker's pizza line (the name alone reads as nothing);
                # "block burger" and "cheeseburger" arrive tiefgefroren.
                "la mia", "cheese-nuggets", "cheeseburger", "block burger"]),
    ("fish", ["fisch", "lachs", "thunfisch", "garnele", "forelle", "hering", "sardin", "sardelle",
              "scampi", "matjes", "meeresfrüchte", "octopus", "tentakel", "kalmar", "calamares", "prawn",
              # The German spelling and the Spanish name; "octopus" was already here but the
              # flyers write "Oktopus-Arme" and a bare "Pulpo".
              "oktopus", "pulpo"]),
    ("poultry", ["hähnchen", "haehnchen", "huhn", "hühner", "pute", "puten", "geflügel", "chicken",
                 "corned turkey", "knusperdino", "wachtel",
                 "entenbrust"]),  # Knusperdinos = Hähnchenbrust nuggets; duck breast reads as nothing
    # "gulasch"/"steak" are intentionally NOT here — they appear in Schweinegulasch
    # / Schweinesteak (pork); beef relies on "rind" and beef-specific cuts.
    # "angus" stays UNPADDED on purpose. It does fire inside "Lavendel angustifolia", but a
    # leading-space guard breaks the real "Black-Angus-Chipolata" (hyphen, not space) and the plant
    # is already caught by its non-food path. Verified: guarding it costs a beef row and saves none.
    ("beef", ["rind", "rinder", "tafelspitz", "angus", "t-bone", "rumpsteak", "rib eye", "hüftsteak",
              "burger patties", "smash burger", "kalb", "bavette", "chuck-eye", "chuck eye",
              "teres major",  # a beef shoulder cut ("Black Premium Teres Major")
              # "Osso Buco" and "Hamburger Pattys" name the dish/format, never the animal — the
              # species is only in the caption ("vom Kalb", "vom Rind"). Note the existing
              # "burger patties" is the English spelling; the flyer writes "Pattys".
              "osso buco", "hamburger pattys"]),
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
              "tyrolini", "sucuk", "salametti", "pancetta", "spanferkel", "die thüringer",
              # 2026-08-09: aspic cold cuts. "herta finesse" was REJECTED alongside these — the
              # range spans pork AND poultry ("Herta Finesse Hähnchenbrust"), and the bare
              # "Herta Finesse" the flyer prints carries no variant, so there is nothing to
              # tell them apart. It stays in `other`, which is the honest answer.
              "sülzkotelett", "aspikaufschnitt"]),
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
                "harzer",  # Harzer (sour-milk cheese), e.g. "Blankenburg Harzer Kräuterhexe"
                # More cheese names carrying no "käse": "Prima Donna" (Dutch), "Holländer"
                # (Gouda/Edam style), "Weißer Grieche" (feta). The Président entry has to be the
                # FULL "président carré", and both shorter forms were tried and rejected against
                # the corpus: bare "carré" is Lidl's FIN CARRÉ chocolate (cheese runs before
                # sweets, so it would take it), and bare "président" is a WINE — "Corsaire
                # Réserve du Président, Frankreich trocken 0,75-l-Fl.". The wine was sitting in
                # `other`, so it read as a rescue rather than a conflict; only looking at what
                # actually moved caught it.
                "prima donna", "holländer", "weißer grieche", "président carré"]),
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
    # ORDER: `tortellini` must precede the bakery block — "Tortellini" CONTAINS "torte", so a
    # brandless, pathless Tortellini resolved to BAKERY and the `tortellini` entry further down
    # in the pantry block could never fire. The real-world rows are saved earlier (a `Nudeln`
    # path node, or the `barilla` brand), which is why this stayed invisible.
    ("pantry", ["tortellini"]),
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
                "focaccia",
                # 2026-08-08 "other" audit. Both are photo-confirmed in-store bakery goods.
                # `nuss-tasche`, NOT `pekannuss`: a bare nut word claims the nut itself. Today's
                # "Alesto Pekannusskerne" happens to survive — `alesto` is in the brand map, which
                # is layer 4 and outranks these rules — but an UNBRANDED pack of pecans has no
                # such protection and would be served as a pastry. Pinned both ways.
                # `caprese-snack` in full, NOT a bare `caprese`: a Caprese SALAD is vegetables.
                "nuss-tasche", "caprese-snack",
    # 2026-08-09: "Börekstange" is a filled savoury pastry (same call as the Apfeltasche above);
    # "grillino" is ALDI's Fladenbrot-Sticks; "brandt" is the Zwieback maker (single-category);
    # "knusperrollen" and "bienenstich" name the pastry itself.
    # "knusperrollen" left this tuple on 2026-08-11: the photo showed CROQUETTES ("Versch.
    # Sorten, Gekühlt 8er-Pack"), which is a ready meal, not a pastry. See _FORM_OVERRIDES.
    "börekstange", "bienenstich", "grillino", "brandt"]),
    ("vegetables", ["tomate", "gurke", "salat", "kartoffel", "zwiebel", "paprika", "möhre", "moehre", "karotte",
                    "brokkoli", "blumenkohl", "spinat", "zucchini", "champignon", "pilz", "knoblauch", "lauch",
                    "sellerie", "kürbis", "rucola", "spargel", "kohlrabi", "coleslaw", "kresse",
                    # Green beans, spelled out rather than a bare "bohnen": that would also claim
                    # Kidneybohnen (a pantry pulse, cf. "kichererbsen"), coffee "Ganze Bohnen", and
                    # "Bio-Cracker mit Ackerbohnen" — vegetables runs before snacks/pantry.
                    "buschbohnen", "brechbohnen", "prinzessbohnen", "stangenbohnen", "grüne bohnen",
                    # Mushrooms the source leaves in Other (the "pilz"/"champignon" words don't reach them).
                    "pfifferling", "portobello",
                    # 2026-08-08 "other" audit: loose cabbage the source ships with no path at all.
                    # Named cabbages, NOT a bare `kohl` — that fires inside Holz*kohl*e (charcoal),
                    # which household would otherwise lose to vegetables (household runs last).
                    "spitzkohl", "chinakohl",
                    # Florette is a bagged-salad house; its "Sommergenuss" says nothing else.
                    # The unrelated cheese "Fromager d'Affinois Florette" arrives on a `Florette`
                    # brand-leaf path and is saved by the CHEESE CAPTIONS at layer 2b (`fett i. tr`
                    # wins; `weichkäse` would too). That is four layers above this one and it is
                    # the only thing standing between this keyword and a goat cheese in the
                    # vegetable chip, so it is pinned by a test.
                    "florette",
    # Suppengrün is a bundle of vegetables. The pantry tuple's `"suppe "` is space-guarded
    # precisely so it cannot claim this word; nothing else could reach it, so it sat in `other`.
    "suppengrün"]),
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
                "chokis", "hitschies", "nippon",
                # 2026-08-09. `oreo` is safe HERE despite Oreo also being a Stieleis, but NOT
                # for the reason this comment first claimed: the ice cream is caught by
                # `stieleis` in `_FORM_OVERRIDES` at LAYER 2, four layers above this table —
                # verified with explain(), which is the only way to be sure. The within-table
                # order of ice_cream vs sweets never gets a turn. So the thing protecting the
                # Stieleis is that layer-2 entry; delete it and the ice cream becomes a biscuit.
                # `paula snack` is padded because a bare "paula" is also Paulaner —
                # a rejection older than this audit, and re-measured as PRECAUTIONARY: every
                # Paulaner row is held by its `… > Bier > Biermarken` path, so the padding buys
                # independence from that path rather than fixing a live collision.
                "balisto", "oreo", "tic tac", "kinder country", "prinzen rolle", "hitschler",
                "riesenmäuse", "paula snack", "mandelblätter"]),
    # NOTE: "knusper" removed — it's a coating adjective, not a snack noun; it mis-caught cat food
    # (Knuspermenü), chicken nuggets (Knusperdinos) and bread rolls (Knusperjungs), and matched 0
    # real snacks in the live feed. Specific "knusper*" products are pinned above (poultry/bakery).
    ("snacks", ["chips", "cracker", "nüsse", "nuesse", "erdnuss", "popcorn", "salzstange", "flips", "tortilla",
                "studentenfutter", "alesto", "trockenfrüchte", "knabber", "bake rolls", "snackmix",
                "walnusskern",
                # 2026-08-09. `cashew-kerne` is hyphen-specific rather than a bare `cashew` as a
                # PRECAUTION, not a proven save: the nut butter it would read wrongly ("Maribel
                # Bio Cashewmus") is held by its `… > Fruchtmus > Mandelmus` path at layer 3
                # today, so the narrow form costs nothing and stops depending on that.
                # `lyttos` was rejected outright and that one IS load-bearing: ALDI's Greek
                # range spans olives, oil, yoghurt, cheese, pastry and meat across 27 products,
                # and 19 of them carry no usable path, so nothing above layer 6 would save them.
                "pringles", "doritos", "cheez-it", "mandeln", "nuss-frucht", "cashew-kerne"]),
    ("alcoholic", [" bier", "lagerbier", " pils", "wein", "vodka", "champagner", "pilsener", "sangria",
                   "doppelkorn", "goldkrone", "weinbrand", "licor", "san miguel", "holsten", "moët", "moet",
                   "absolut", "korol", "cimarosa", "sauvignon", "primitivo",
                   "oberbräu", "sarti"]),  # a Hell (beer) and the Sarti Rosa aperitivo
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
                "rondo ",
                # Tchibo's ground-coffee line. The BRAND `tchibo` stays rejected (it also sells
                # clothing and a Snack-Piekser); only the coffee line name is safe.
                "feine milde"]),
    ("soft_drinks", ["wasser", "cola", "limo ", "saft", " tee", "energy", "schorle", " spezi ",
                     "fanta", "sprite", "nektar", "pepsi", "solevita", "aloe vera", "smoothie",
                     # 2026-07-28 audit: drinks the house brands leave in Other. "iso light" is
                     # space/word-guarded (vs Isomalt/isotonisch); "gemüsesaft"/"gemüsesäfte"
                     # because the plural "-säfte" isn't caught by the bare "saft".
                     "rotbäckchen", "iso light", "activedrink", "gemüsesaft", "gemüsesäfte",
                    "dr pepper", "lemonaid"]),
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
                "suppe ", "eintopf", "eintöpf", "lasagne-blätter", "lasagneblätter", "gigli ",
                # 2026-08-08 "other" audit. Preserved produce is pantry by the standing convention
                # (jarred/canned leaves the fresh chips), so pickled baby corn belongs here.
                # `bio kräuter` is deliberately the two-word form: a bare `kräuter` spans 13
                # categories in the stored set (Kräuter*likör*, Bresso Feine Kräuter, Kräuter-
                # baguette, Kräuterbutter) and is unguardable. Culinary herbs sit with the
                # spices — "Petersilie" already resolves to pantry.
                "maiskölbchen", "bio kräuter",
    # 2026-08-09: syrups, a honey speciality, a canned pulse and fresh pasta, all of which the
    # flyers publish under a brand-leaf path that carries no category.
    "ahornsirup", "gelée royale", "bihophar", "weiße bohnen", "eierspätzle"]),
    ("household", [
    # NB: `shampoo`, `duschgel`, `zahnbürste`, `rasierer`, `windel`,
    # `weichspüler`, `spülmittel`, `spülmaschinen` and `waschmittel` were REMOVED here on
    # 2026-08-09. They predate the drugstore aisles, which are now spliced in above this
    # tuple and own them — so the copies were dead code, and the shadowing ratchet said so.
"toilettenpapier", "küchenrolle", "reiniger",
                   "müllbeutel", "oleander", "pflanze", "blume", "kleid", "jacke", "schuhe",
                   "garten", "werkzeug", "kissen", "bettdecke", "matratze", "wäschest", "haushaltshelfer",
                   "küchenhelfer", "rätselbuch", "autozubehör", "grillhelfer", "grillzubehör", "schreibwaren",
                   "geschenkpapier", "reinigung", "e-bike", "e-scooter", "ventilator", "staubsauger", "klimagerät",
                   "luftkühler", "bügeleisen", "bügelstation", "fritteuse",
                   "haartrockner", "batterien", "kosmetik", "sonnenschutz", "pavillon", "fahrradträger",
                   # "chrysanthem" (not the plural) also catches the singular "Chrysantheme".
                   "fahrradanhänger", "wanduhr", "kühltasche", "chrysanthem", "lavendel", "palme", "kreuzfahrt", "hotel",
                   "holzkohle", "grillkohle", "brikett", "grillmatte", "haushaltstuch", "müllbeutel", "papierbeutel",
                   "hortensie", "floristen", "blumenstrauß", "keramikgrill", "hundespielzeug",
                   # `plüsch` widened from `plüschtier`: the flyers also sell a bare "Pokémon Plüsch".
                   "plüsch",
                   "spielzeug", "prospekthülle", "auto laden",
                   # --- 2026-08-08 "other" audit: NON-FOOD that was rendering in the food list ---
                   # `other` is NOT gated by the app's Non-food toggle (only `household` is), so a
                   # toy, a book, a deck chair and a mobile plan were all being served among the
                   # groceries. This tuple runs LAST, so every token here can only ever catch a
                   # product that would otherwise fall through to "other" — zero regression by
                   # construction, the same argument as the drugstore step inside layer 1.
                   # "Lidl Connect" needs a rule at all because the source files the SIM under
                   # `Lebensmittel und Getränke > ... > LIDL Connect Classic` — a FOOD root, so
                   # layer 1's non-food branch can never see it.
                   "frischhaltedose", "lidl connect", "kreativspiel", "spinner",
                   "lernblock", "leselernbuch", "liegestuhl",
    # 2026-08-09 audit of the served `other` bucket. Only `household` is hidden by the app's
    # Non-food toggle, so anything non-food that falls through to `other` renders between the
    # yoghurt and the bread. `kaktus` rather than the caption's "Potcover": a `topfcover` token
    # already existed for exactly this class and the source spelled it without the T, so the
    # species word is the handle that does not depend on how they wrote the pot. It also leaves
    # the already-correct plain "Kaktus" where it is.
    "jogginganzug", "gugelhupfform", "kaktus",
    # 2026-08-09 photo sweep: a children's wooden hammer game and a kids' T-shirt were sitting
    # in `other`, i.e. rendering in the food list. `t-shirt` also correctly no-ops on the 42
    # shirts already in household.
    "hammerspiel", "t-shirt",
     # 2026-08-17 photo sweep. A whole BACK-TO-SCHOOL range (EDEKA/E center's Gut&Günstig)
     # plus toys, houseplants and hardware were rendering between the yoghurt and the bread.
     # Every one of them falls to layer 7 today — no rule matches at all — because the source
     # files them under `Lebensmittel und Getränke > Marken > Marken Lebensmittel > Gut &
     # Günstig`, a FOOD root, so layer 1's non-food branch never sees them.
     "collegeblock", "bleistift", "buntstift", "geometriedreieck", "lineal", "radiergummi",
     "schnellhefter", "niveus papier", "frischebox", "trinkflasche",
     # Toys and games, spelled in FULL. A bare `sand` matches three SANDWICHES sitting in
     # `other` (Milbona Sandwich Scheiben, Gut&Günstig Sandwich, Mucci Stracciatella-Sandwich)
     # and would move them to household — which the app hides behind its Non-food toggle, so
     # the food would not merely be mis-chipped, it would vanish. A bare `buch` happens to be
     # harmless this week (its only extra hit is a picture book, correctly household), but the
     # full word does not depend on that staying true.
     "kinetic sand", "stressball", "kartenspiel", "gedächtnisspiel", "aktivitätsbuch",
     # Houseplants named after the plant, and hardware.
     "zinkschale", "lilien", "mauerpfeffer", "drehplatte", "wandleuchte", "airfreshener",
     # A streaming subscription sold at the till — the same class as the mobile-phone plan the
     # 2026-08-08 audit found.
     #
     # `sansibar` was SIMULATED AND REJECTED even though it reads clean: no product leaves a
     # real category, because the row it breaks — SANSIBAR DELUXE Castillo de Albai Gran
     # Reserva Rioja, a WINE on a brand-leaf path — is already sitting in `other`, so a
     # conflict count scores moving it as a free win. It is only visible by reading what MOVED.
     # `südafrika` was rejected too: one travel advert, against a word that is a produce ORIGIN.
     "rtl+"]),
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
    "oro di parma": "pantry",  # canned/passata tomatoes only
    # Stockmeyer is single-category pork cold cuts (Salami, Sonntags-Frühstück). NOT Block House —
    # the steakhouse brand also sells garlic BREAD ("BLOCK HOUSE Brot XXL Knoblauch" → bakery), so
    # its two burgers stay in Other rather than risk that (pinned by test_classify_expanded_names).
    "stockmeyer": "pork",
    "valensina": "soft_drinks", "lipton": "soft_drinks", "volvic": "soft_drinks",
    "schogetten": "sweets", "berggold": "sweets", "häagen-dazs": "ice_cream",
    # REWE flyer brands (paths are often brand-only -> no taxonomy node to use)
    "mirée": "cheese", "miree": "cheese", "salakis": "cheese", "leerdammer": "cheese",
    "bergader": "cheese", "rotkäppchen": "alcoholic",
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
    # 2026-08-08 "other" audit: single-category brands whose products carry no category word at
    # all in the name the source stores ("Ya'ummi Classic Samurai", "Remia Yildriz", "Hellmann's
    # Chili", "Zörbiger Überrübe"). Each was verified against every stored row of that brand:
    # nothing outside the mapped category, so none of these is a brand CONTAINER.
    # The caption would be the obvious alternative for the three sauces, but a `saucen` caption
    # signal was measured and REJECTED — it also matches "Chicken Nuggets mit ... Saucen", where
    # the sauce is an ACCOMPANIMENT, not the product (designation-not-ingredient, as ever).
    "hellmann": "pantry", "remia": "pantry", "zörbiger": "pantry",
    # Both apostrophes: the feed ships the straight one today, but its siblings use the curly.
    "ya'ummi": "pantry", "ya’ummi": "pantry",
    "capico": "sweets", "frikoni": "dairy",
}

# Definitive *form* words (and single-category product brands): a product literally called a
# limonade / saft / joghurt / chips — or a Froop / Müllermilch / Vilsa — IS that category, so
# these beat even a mis-filed food taxonomy path (the source files "Bananenchips" under Obst,
# the flavoured water "Vilsa H2 Obst …" under Obst). Only words that pin the category by form
# or an unambiguous brand, never a mere flavour — so a frozen "…Schoko" brand isn't dragged
# here. Space-guarded where a fruit word is a superstring ("nektar " vs "Nektarine").
_FORM_OVERRIDES: list[tuple[str, list[str]]] = [
    # --- 2026-08-03 photo audit + four convention calls --------------------------------------
    # GUARDS FIRST — layer 2 is first-hit-wins and each of these protects a token below it.
    # `oreo`/`nutella` name ice cream as well as biscuits/spread; `müsliriegel` is a BAR while
    # `müsli` is cereal; a `joghurt` with a muesli topping is still a yoghurt.
    ("ice_cream", ["nutella eis", "nutella ice", "nuii", "oreo eis", "oreo ice", "sandwich-eis"]),
    ("sweets", ["müsliriegel", "müsli riegel"]),
    # THE COUNTER SANDWICH IS ONE CLASS. A filled roll sold by the Stück was landing in five
    # different categories depending on which filling word won — `seelachs` -> fish,
    # `fleischkäse` -> pork, `chicken` -> poultry, `mozzarella` -> cheese. It has to sit here,
    # above those tokens: appended at the end of this table it was dead code for every product
    # it was written for. Deliberately NOT a bare `brötchen`, which is a plain bread roll
    # (bakery); each token names a FILLED roll, extending the existing `fischbrötchen` call.
    ("ready_meals", ["im brötchen", "schnitzel-brötchen", "panini"]),
    # A salad dressing is not a yoghurt — this guard must stay ABOVE `joghurt`, which is a
    # substring of it (2026-08-09: appended below, the shadowing ratchet correctly failed it).
    ("pantry", ["joghurt dressing"]),
    ("dairy", ["joghurt"]),
    # The CUT-vs-SPECIES class again, this week as Rouladen/Braten/Gulasch: the source files
    # Irish BEEF roulades under a pork node, and a Kalbsschnitzel is veal (= beef here).
    ("beef", ["rinder-roulade", "rinderroulade", "rinder-braten", "rinder-gulasch",
              "kalbs-schnitzel", "kalbsschnitzel", "burger-patty"]),
    ("other_meat", ["lamm-spieß"]),
    ("vegan", ["billie green", "vegetarian butcher", "vivera"]),
    ("pantry", ["paniermehl", "knorr fix", "air fryer hähnchen", "nesquik", "tortenmehl",
                "müsli", "kaffeebecher", "müslischale"]),
    # CONVENTION (user, 2026-08-03): a deli SALAD is heat-and-eat-adjacent prepared food ->
    # ready_meals. This narrows last week's "spreads and deli salads stay pantry": the SPREADS
    # still do (Brotaufstrich, nut creams), the salads no longer.
    ("ready_meals", ["hühnerfrikassee", "prepmymeal", "eiersalat", "nudelsalat",
                     "kartoffelsalat", "weisskrautsalat", "fleischsalat", "soljanka",
                     # A deli salad sold by drained weight. Without it the layer-6 `salat`
                     # keyword makes it a vegetable, and the preserved redirect then files it
                     # as pantry — one class landing in two chips depending on the filling.
                     "selleriesalat",
                     "gärtnerinnen traum"]),  # a counter deli salad, named like a dish
    ("frozen", ["baniza", "teigröllchen"]),
    # CONVENTION (user): a milk-cream snack cake is a SWEET — Milchschnitte joins Maxi King,
    # which fixes a live split where one family sat in two categories.
    ("sweets", ["milchschnitte", "mikado", "loacker", "napolitanke", "kalter hund"]),
    # " lassi" keeps its LEADING SPACE: bare `lassi` is a substring of "Classic"/"Classico"/
    # "Klassik" and dragged Dallmayr, Red Bull and Langnese into dairy when first simulated.
    ("dairy", ["cremefine", "cremfine", " lassi", "lassi mango"]),
    ("alcoholic", ["whiskey", "whisky"]),
    ("fish", ["thunfisch filet"]),
    ("coffee", ["caffè latte", "caffe latte", "der herzhafte"]),
    # `0.0%` and the named 0.0 brands only. A bare `alkoholfrei` is a DOCUMENTED rejection —
    # ~30 real beers carry "oder alkoholfrei" as a variant note and would empty the beer aisle.
    ("soft_drinks", ["0.0%", "wonderleaf", "yfood"]),   # yfood = the meal-drink brand
    # CONVENTION (user): sports-FORMAT nutrition (bars, powders, shakes) -> health; an ordinary
    # food that happens to be high-protein keeps its own category (protein bread stays bakery).
    ("health", ["proteinpulver", "protein-pulver", "eaa "]),
    ("cheese", ["lauchterrine", "radieschentopf"]),
    ("pork", ["gurkensülze", "paprikapastete"]),
    # Living plants sold in a pot. These reach layer 2 only when the source ships them WITHOUT
    # its garden path (it ships the basil both ways) — with the path, layer 1's veto decides.
    # `basilikum` alone is unusable: it is in Zottarella Basilikum and Patros Tomate & Basilikum,
    # both cheese.
    ("household", ["topfcover", "basilikum im topf"]),
    ("snacks", ["tortillas"]),
    # --- end photo-audit block ------------------------------------------------------------------
    # --- 2026-08-03 new-week audit: the `other` bucket (92 products on arrival) --------------
    # GUARD FIRST: `macadamia` below would otherwise claim a Nuii Stieleis for snacks.
    ("ice_cream", ["ice cream", "stieleis", "eis am stiel"]),
    ("pet", ["ergänzungsfuttermittel", "kaurollchen"]),
    ("cheese", ["ziegenrolle", "kiri", "cheese tiger"]),
    ("pork", ["stickado", "doktorskaja", "stielkotelett", "sulzspezialität"]),
    ("fish", ["feinmarinaden", "mowi"]),                       # Mowi is a salmon brand
    ("pantry", ["buchweizen", "jodsalz", "couscous", "fruchtaufstrich", "spekulatiuscreme",
                # (`soljanka` removed 2026-08-04: an earlier ready_meals entry already carries
                # it, so this copy could never fire. Dead, not wrong — a canned Soljanka is a
                # ready meal by the standing convention.)
                "beanz", "würzpulver", "letscho", "cereals", "cini-minis"]),
    ("frozen", ["grid fries", "blinis", "ristorante", "margherita", "junge erbsen",
                "lasagne bolognese"]),
    # Filled dumplings, heat-and-eat. `teigtaschen` is the generic the flyers use where
    # `pelmeni`/`vareniki` are the named kinds; it follows the same call as Maultaschen and so
    # deliberately does NOT go to `frozen`, even though every one of them is tiefgefroren —
    # the freezer is a shelf, not a category. "street food" is Ben's Original's rice pouches.
    ("ready_meals", ["pelmeni", "vareniki", "döner-box", "teigtaschen", "street food"]),
    ("bakery", ["mini-eclairs", "kleingebäck", "napoleonky"]),
    ("sweets", ["prinzenrolle", "eszet", "maltesers", "pick up", "sallos", "happz",
                "kalter hund", "corny", "honey nuggets"]),
    ("snacks", ["super mix", "macadamia", "vanilla-cashew"]),
    ("soft_drinks", ["cold tea", "rabenhorst"]),
    ("alcoholic", ["kosmonaut", "vieille ferme"]),
    ("fruits", ["zwetsch"]),                                    # Zwetschen / the typo'd Zwetschlen
    ("vegetables", ["pakchoi", "pak choi"]),
    ("dairy", ["high protein pudding", "früchte trio"]),
    ("fragrance", ["eau de parfum"]),
    # --- end new-week block -------------------------------------------------------------------
    # --- 2026-07-31 image audit, batch 4 (pantry / drinks / produce sheets) ------------------
    ("bakery", ["mohnhappen", "dinkelinge"]),          # a yeast pastry and spelt rolls
    ("vegetables", ["petersilie"]),                    # a fresh bunch, sold je Bund
    # Rotkäppchen is the SEKT brand, so its chilled soft-cheese minis were served as Alcoholic.
    ("cheese", ["petrella", "rotkäppchen mini"]),
    ("vegan", ["falafel-bällchen", "pistazien-drink"]),
    # Drinking yoghurt is DAIRY (user's call, 2026-07-31, reversing PR #105's placement of
    # MILSANI Activedrink in soft_drinks). The sibling forms are listed with it so the
    # convention is consistent rather than a single-product patch — `kefir` moved a second
    # product (QUARKI Kefir mild) the same way.
    ("dairy", ["yofrutta", "milchreis", "activedrink", "trinkjoghurt", "joghurtdrink",
               "drinkjoghurt", "kefir"]),
    ("ice_cream", ["gelato", "stieleis",
                   # Mars/Snickers/Bounty ICE CREAM bars, which the brand's confectionery
                   # keywords were claiming as `sweets` (photo: snowflake packs, 5 Stück).
                   "eisriegel"]),
    # Clausthaler is an alcohol-free-ONLY brand, so the name alone settles it. Carlsberg 0.0
    # and Peroni 0.0 are in the same flyer and are deliberately NOT here: both brands also
    # sell real beer, and the "0.0" appears only on the PHOTO, never in the stored name — so
    # there is no text signal to key on and `other`/alcoholic is the honest answer.
    ("soft_drinks", ["clausthaler"]),
    # A micellar water is facial cleanser; `wasser` was sending it to soft_drinks.
    ("face", ["mizellenwasser"]),
    ("pet", ["lieblings-sticks"]),  # "Ergänzungsfuttermittel für ausgewachsene Hunde"
    ("pantry", ["tomatenmark"]),                       # tomato paste is not fresh produce
    ("frozen", ["edamame", "bistro baguette"]),        # both packs state tiefgefroren
    ("alcoholic", ["berliner perle"]),                 # a Helles that was in soft_drinks
    ("soft_drinks", ["fassbrause"]),                   # alkoholfrei, was in alcoholic
    # REJECTED here, and pinned: `nutella` drags Nutella ICE CREAM and Nutella Biscuits into
    # pantry along with the jar, and `yogurette` would take the CHOCOLATE BAR with the
    # Stieleis version. Neither exception is nameable the way `bananen-kirsch` was, so the
    # broad token is dropped rather than guarded.
    # --- end batch 4 --------------------------------------------------------------------------
    # --- 2026-07-31 image audit, batch 3 (household + drugstore sheets) ----------------------
    # Drugstore products stranded in `household`/`other`. None of these is a food word, so
    # they are safe at layer 2.
    ("dental", ["blend-a-dent", "listerine", "mundspülung", "zahnpasta", "colgate"]),
    ("laundry", ["persil"]),
    ("cleaning", ["allzwecktücher", "wc frisch", "wc-spüler"]),
    ("body", ["bodycream", "carefree"]),
    ("hair", ["strong power"]),
    ("household", ["guthabenkarte", "toilettenpapier", "taschentücher", "zewa"]),
    # A canned Eintopf is heat-and-eat, which is what `ready_meals` means (user's convention:
    # only heat-and-eat meals -> ready_meals; spreads and deli salads stay pantry).
    ("ready_meals", ["eintopf", "eintöpfe"]),
    # A cake MIX is an ingredient, not a baked good. The spread tokens are deliberately NARROW:
    # a blanket `brotaufstrich` is a documented REJECTED signal, and re-simulating it here
    # confirmed it still drags Rama (margarine) out of butter and the Brunch spread out of
    # cheese, so the specific products are named instead.
    ("pantry", ["backmischung", "popp brot", "abendbrotaufstrich", "nougat-brotaufstrich"]),
    # --- end batch 3 --------------------------------------------------------------------------
    # --- 2026-07-31 image audit, batch 2 (meat / dairy / cheese sheets) ---------------------
    # These are GUARDS and must stay at the top: layer 2 is first-hit-wins, and each one
    # protects a token further down that would otherwise claim the product.
    ("bakery", ["schweinsöhrchen", "schweineohr"]),   # a palmier pastry, not pork
    ("poultry", ["geflügelfleischkäse"]),             # before the pork `fleischkäse`
    ("pantry", ["geflügelfond", "rinderfond", "gemüsefond", "kalbsfond"]),  # stock, not meat
    ("household", ["daunendecke", "daunenbett"]),     # a DUVET, filed under a `Geflügel` node
    # `bananen` was rejected outright by the previous audit because it dragged a
    # "Bananen-Kirsch-Getränk" out of soft_drinks. The drink is named, so a guard ABOVE the
    # fruit token expresses what the flat table could not.
    ("soft_drinks", ["bananen-kirsch", "bananensaft"]),
    ("snacks", ["bananenchips"]),                     # a crisp, not fruit
    ("fruits", ["bananen"]),                          # one chain files loose bananas under Milch
    ("frozen", ["die ofenfrische"]),                  # a frozen pizza the `salami` keyword took
    ("ready_meals", ["kohlroulade"]),
    ("sweets", ["sahne-toffee", "dinkelchen"]),       # toffees under a Butter node; choc biscuits
    ("pantry", ["spaghetti mit tomatensauce", "rote grütze"]),  # a pasta kit; compote in jars
    ("bakery", ["tigersnack"]),                       # a topped bread roll, not mozzarella
    ("beef", ["rindfleischspieß"]),                   # the house brand map said pork
    # --- end batch 2 -------------------------------------------------------------------------
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
    # 2026-07-31: pet food goes to the `pet` CHIP, not household. `pet` is served in the
    # grocery vertical too (measured: 5 offers), and this guard predates that category — so a
    # Coshida sat behind the Non-food toggle while other pet products reached the chip, i.e.
    # the rule disagreed with itself. `topfpflanze` is a genuine houseplant and stays
    # household, and bare `dental` stays there because human dental care is its own chip and
    # must never become pet — the dog chew is named explicitly instead.
    ("pet", ["hello my cat", "dental-stick",
             "trockennahrung", "nassnahrung", "nassfutter", "trockenfutter", "hundefutter",
             "hundenahrung", "tierfutter", "tiernahrung", "vogelfutter", "katzenstreu",
             "hygienestreu", "katzensticks", "lieblingsmenü", "beef stick",
             "kausnack", "kaurollen", "kauknochen", "kaustange", "coshida", "sheba"]),
    ("household", ["dental", "topfpflanze"]),
    # Breaded chicken drumsticks the source dumps into Knabberzeug>Sticks (a snacks node); no
    # ice-cream "Drumstick" is in the feed, so this is unambiguous poultry.
    ("poultry", ["drumstick"]),
    # --- 2026-08-11: Lidl's "Sol & Mar" Spanish range, adjudicated in the 08-09 photo sweep.
    # Each arrives on a path that answers first, so only layer 2 can reach them; every call
    # below is confirmed by the flyer caption, not by the name alone.
    #   Paella          "Andalusischer Style. Tiefgefroren."   -> frozen
    #   Knusperrollen   "Versch. Sorten, Gekühlt 8er-Pack"     -> croquettes, ready_meals
    #   Kartoffel-Omelette "Versch. Sorten, Gekühlt je 500 g"  -> a tortilla, ready_meals
    #   Tapas de Chorizo — "chorizo" is already a pork token; the `Tapas` PATH node beats it.
    # The mixed "Tapas Selektion"/"Tapasplatte" are deliberately NOT moved: the sweep read
    # them as cured meats, but the name does not say so and I could not re-verify the photo.
    ("frozen", ["sol & mar paella"]),
    ("ready_meals", ["knusperrollen", "omelette"]),
    ("pork", ["tapas de chorizo"]),
    # Two in-store breads the source files under a `Backzutaten` node (a BAKING INGREDIENT).
    # Never a bare "kruste": Krustenbraten, Krustensteaks and Krustenschinken are all pork.
    ("bakery", ["weizenkruste", "vollkornkruste", "dinkelcrusty", "dinkel-schiffchen"]),
    ("dairy", ["joghurt", "jogurt", "froop", "skyr", "müllermilch", "fruchtzwerge", "fruchtquark"]),
    # Freeze-dried fruit is a shelf-stable SNACK, not frozen food — "gefrier" alone reads
    # "Gefriergetrocknete Himbeeren" as tiefkühl.
    # Mövenpick spans ice cream AND coffee AND, here, a tub called "Chocolate Chips" that the
    # snacks token below reads as crisps — its path leaf is literally "Eis". A multi-category
    # brand needs its other categories pinned at layer 2, the only layer above the brand map.
    ("ice_cream", ["mövenpick chocolate chips"]),
    # ...and in the other direction: "Mövenpick Erdbeere" is a FEINJOGHURT, which the
    # brand map (mövenpick -> ice_cream, layer 4) would otherwise serve as ice cream.
    ("dairy", ["mövenpick erdbeere"]),
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
    # Non-food and non-produce the source files under an Obst/Gemüse node, so only layer 2 can
    # move them. Each was verified against the whole DB (13 rows, 7 products, every move strictly
    # more correct, 0 regressions). The path really does say this:
    #   "Power Force Duft-Müllbeutel"  (scented BIN BAGS)   -> "Obst > Melone", because the bags
    #                                  are watermelon-scented                    -> was `fruits`
    #   "Bresso Feine Kräuter"         (herb CREAM CHEESE)  -> "Gemüse > Kohl > Kraut"
    #   "Couronne Feigen-Walnuss" / "Mestemacher Greek Flatbread" (BREADS)       -> Obst / Gemüse
    #   "SKANDINAVIC'S Remoulade"      (a cold SAUCE)                            -> was `vegetables`
    # This matters beyond tidiness: produce is sub-grouped for the deals list and the Basket's
    # suggestions, so a bin bag left in Fruits becomes a recommendable "fruit".
    ("household", ["müllbeutel", "frischhaltebeutel", "gefrierbeutel"]),
    ("bakery", ["flatbread", "couronne"]),
    ("pantry", ["remoulade"]),
    ("cheese", ["bresso"]),
    # --- 2026-07-29 IMAGE audit: the picture showed something the path insisted otherwise ---
    # A Kolbász is Hungarian salami (the source filed it under a `Paprika` node because the
    # sausage is paprika-spiced); a Bulette is a fried meatball (filed under `Feingebäck`).
    # Only layer 2 beats a path, which is why these aren't plain keywords.
    ("pork", ["kolbasz", "kolbász", "bulette", "frikadelle"]),
    # "Tillman's Toasty" is breaded CHICKEN — the `toast` bakery keyword swallowed it. The
    # image is unambiguous; `toast` itself must keep matching Toastbrot, so guard the product.
    ("poultry", ["toasty"]),
    # A rucksack the source filed under `Schaumwein > Sekt`, so it was served as Alcoholic.
    # No food is called a Rucksack, so this is safe at layer 2.
    ("household", ["rucksack"]),
    # Preserved produce leaves the FRESH-produce chip (user's convention call, 2026-07-29):
    # jarred/canned -> pantry, frozen -> frozen. A jar of Gewürzgurken beside loose cucumbers
    # also makes the €/kg sort meaningless. Layer 2 because "canned" is a definitive FORM and
    # has to beat the produce path/brand that currently wins (Bonduelle -> vegetables).
    ("pantry", ["gewürzgurke", "essiggurke", "cornichon", "sauerkraut", "passata",
                "passierte tomaten", "ananas in stücken", "goldmais"]),
    # More IMAGE-audit finds. "Metten Roastbeef" is a beef roast the source files under
    # `Fleischzubereitungen` (-> pork), and the `mett` group name made it look right.
    ("beef", ["roastbeef", "roast beef"]),
    # Cheese-NAMED sausages: a Käsewiener/Käsebeißer/Käsekrainer is a cheese-filled sausage,
    # not a cheese. One came via the `käse` keyword, the other via a `Käse` PATH node, so
    # this has to sit at layer 2 to catch both.
    ("pork", ["käsewiener", "käsebeisser", "käsebeißer", "käsekrainer", "käsegriller"]),
    # --- Image audit, final sweep. All of these need layer 2 because a BRAND at layer 4 was
    # winning: `mövenpick` -> ice_cream and `baileys` -> alcoholic. ---
    # Mövenpick is the documented multi-category brand (ice cream AND coffee). Its coffees were
    # relying on the `ganze bohnen`/`iced coffee` rescue, which does not fire for "Der
    # Himmlische", plain "Kaffee" or "Kaffeekapseln" -- all three were served as ICE CREAM.
    ("coffee", ["kaffeekapsel", "kaffeepad", "der himmlische", "mövenpick kaffee"]),
    # "Baileys Muffins" are muffins, not a liqueur — this entry exists to beat the `baileys`
    # brand at layer 4. The SLUG became `sweets` on 2026-08-03 with the packaged-cake convention
    # (see the block at the bottom of this table); the token stays HERE because appending a
    # second `muffin` lower down is dead code — this one wins, and the full-corpus diff showed
    # exactly that: not one muffin moved until the slug was changed in place.
    ("sweets", ["muffin"]),
    # German "Lachs" is a LOIN CUT as well as salmon: "Greußener Lachsfleisch mit
    # Edelschimmel" is cured PORK. Same trap as the documented `lachsschinken`.
    ("pork", ["lachsfleisch"]),
    ("fish", ["garnelensalat", "thunfisch-salat"]),
    # Ready-to-drink premixes at 10% Vol., served as Soft Drinks.
    ("alcoholic", ["jack daniel", "gin tonic", "mixgetränk"]),
    # --- Final sweep. ORDER IS LOAD-BEARING here (first hit wins): these two guards must
    # precede the tokens below that would otherwise swallow them. ---
    ("alcoholic", ["edelbrand", "obstgeist", "obstbrand"]),  # guards `mirabelle`: a Mirabellen
    #   Edelbrand is a fruit BRANDY, not fruit.
    # ORDER: `fischbrötchen` must precede `matjes`, or "Fischbrötchen Rauchmatjes" is claimed by
    # the guard below and the same product sits in two chips. See the ready_meals note at the
    # bottom of this table for why a filled roll is a ready meal.
    ("ready_meals", ["fischbrötchen"]),
    ("fish", ["matjes"]),  # guards `senf`: a "Matjes Honig-Senf" is herring, not mustard.
    # The source files regional Thüringen FOOD under `Wasser > Wassermarken > Thüringer
    # Waldquell` -- a mineral-WATER brand node -- so mustard, Leberwurst, Rostbratwurst, ham
    # and fresh Mirabellen were all served as Soft Drinks. Removing the `wassermarken` node
    # does not help: the scan falls through to the parent `Wasser`, which also maps to
    # soft_drinks. Only layer 2 beats a path.
    # (`protein-pulver` and `high-protein-pulver` removed 2026-08-04: the health entry higher up
    # carries `protein-pulver`, and it is a SUBSTRING of the "high-" form, so both copies here
    # were unreachable. Dead, not wrong — sports-format nutrition is `health` by convention, and
    # `high-protein-sahne` stays because no earlier token is a substring of it.)
    ("pantry", ["senf", "high-protein-sahne"]),
    ("pork", ["leberwurst", "rostbratwurst", "holzfällerscheibe", "filetpastete",
              "fleischpastete", "leberpastete", "schwarzwälder schinken"]),
    ("fruits", ["mirabelle"]),
    # A "Viba Fruchtschnitte" is a fruit BAR; the source filed it under `Kaffee >
    # Kaffeevariationen > Cafe au lait`.
    ("sweets", ["fruchtschnitte"]),
    # --- 2026-07-31 audit: a path node that names a CUT or a FORM, not a product kind ----
    # Reported: "Schweine-Nackensteaks" served as Beef. The source files it under
    # `Fleisch > Fleischzubereitungen > Steak`, and `_PATH_MAP["steak"] = beef` (L3) beats
    # the `schwein`/`nackensteak` keywords (L6). But a steak is a CUT — pork, turkey and
    # salmon all come as steaks — so the species has to win, and L2 is the only layer above
    # the path. Removing the `steak` node instead would drop "Scotland Hills Cowboy Steak"
    # onto its parent `Fleischzubereitungen` -> pork, trading one wrong answer for another.
    # These sit AFTER the pet guard above, so a Meerschweinchen food stays household.
    ("pork", ["schwein", "schinkensteak"]),
    # `puten` where the existing L2 entry has only the hyphenated `puten-`: the source's
    # `Hackfleisch > Putenhackfleisch` leaf isn't mapped, so it inherits pork from
    # `Fleischzubereitungen` two levels up.
    ("poultry", ["puten"]),
    # A BRAND under a mis-filed parent. `Alpenmilch` isn't in _PATH_MAP — its parent milk
    # node is — so deleting a node can't fix it (cf. the Thüringer Waldquell case), and the
    # brand map is L4, below the path. Milka is chocolate; the trailing space keeps Milkana
    # (a cheese) out, exactly as the L4 entry does.
    ("sweets", ["milka "]),
    # Zespri (kiwi) sat under a beverage brand node and served as a soft drink.
    ("fruits", ["zespri"]),
    # `Knabberzeug > Sticks` is a FORM node: coffee sticks, cheese sticks and ice sticks all
    # hang off it. Dropping the node is a no-op (its parent answers `snacks` identically —
    # measured), so the non-snack kinds are named here instead.
    ("coffee", ["nescafé", "nescafe", "kaffeestick"]),
    ("ice_cream", ["raketeneis", "icestick"]),
    # --- Conventions the user set on 2026-08-03. Appended, not inserted: everything above keeps
    # --- priority, and each block names the sibling that must NOT move.
    #
    # BREADED cheese is a freezer/convenience product, not cheese you buy to eat as cheese. It was
    # split across two chips — Mozzarella-Sticks served as `cheese` at Lidl and as `snacks` at
    # Alpenhain — so this also settles a self-disagreement. Layer 2 because the source files these
    # under a Käse path, which would otherwise win at L3. Plain baked cheese is NOT breaded and
    # stays put: Rougette Ofenkäse, Halloumi Grillkäse, Patros Grill & Ofen, Galbani Mozzarella.
    # Both spellings are needed — the source ships "Mozzarella-Sticks" and "Mozzarella Sticks".
    ("frozen", ["backkäse", "back-camembert", "mozzarella-stick", "mozzarella stick"]),
    # (`fischbrötchen` -> ready_meals lives higher up, above the `matjes` guard it collides with:
    # a filled roll from the counter is one serving you eat as it is, like the deli salads. It
    # beats the source's `Fisch > Fischzubereitung` path, while the fillings on their own stay
    # fish — Rauchmatjes, Matjesfilet, Backfisch, Seelachsschnitzel.)
    #
    # Industrially packaged, individually-portioned cake is confectionery; cake sold as cake stays
    # in Bakery. Only the FORMATS are named, because "shelf-stable" has no signal in the feed: the
    # fresh ones say "Gekühlt" and the packaged ones say nothing, and absence of a word is not
    # evidence. A bare `kuchen`/`torte` token was simulated and REJECTED — it drags Flammkuchen
    # (savoury), Frischkuchen and Schichttorte ("Gekühlt"), Zupfstreuselkuchen and Kuchenglück
    # (fresh from the in-store bakery) out of Bakery with them. Baklava already resolves to sweets.
    # The guard above the block is load-bearing: `MEIN BESTES Filled-Pizza-Donut` is a savoury
    # cheese-filled pizza snack, and layer 2 outranks the `Hartkäse` path node that gets it right.
    # (`muffin` is NOT repeated here — an existing entry higher up already carries it and wins;
    # its slug was changed in place instead. A duplicate token below the first hit is dead code.)
    ("cheese", ["pizza-donut"]),
    ("sweets", ["donut", "kuchenriegel", "mini-kuchen"]),

    # --- 2026-08-09 photo sweep -------------------------------------------------------------
    # Every one of these resolves at layer 4 or 6 today, so layer 2 is the only place that can
    # correct them. Appending is safe precisely because none of them matches an existing layer-2
    # entry — if one did, this block would be dead code below the first hit.
    #
    # THE COUNTER SANDWICH IS ONE CLASS, currently scattered across five categories: a
    # Seelachsschnitzel-Brötchen reads `fish`, a Fleischkäse im Brötchen `pork`, a
    # Curry-Chicken-Panini `poultry`, and two filled rolls `cheese`. They are all a filled roll
    # sold by the Stück — the same call the app already makes for `fischbrötchen`.
    # Lyttos names every meat product after its cream-cheese filling ("Bifteki-Frischkäse"),
    # which put three trays of minced-meat patties in the Cheese chip.
    ("pork", ["bifteki"]),
    # Species named in the product, contradicted by a pork keyword winning first. Veal is
    # already `beef` elsewhere ("Kalbs-Hinterhaxe", "Osso Buco vom Kalb"), so this was a
    # self-disagreement, not a judgement call.
    ("beef", ["rindsbratwurst", "kalbsvorderhaxe", "rindersteak"]),
    ("coffee", ["hochland kaffee"]),   # instant coffee taken by the `hochland` CHEESE brand
    ("bakery", ["käsekuchen"]),        # a Rührkuchen; the quark is an ingredient
    ("snacks", ["bacon-snack"]),       # puffed corn snack, bacon is the FLAVOUR
    ("fruits", ["quetschie"]),         # 100% fruit puree pouch, filed as dairy
    ("frozen", ["knusper-minis"]),     # breaded cheese bites — the app's breaded-cheese rule
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
    # --- 2026-08-03: products whose only usable signal is the CAPTION ------------------------
    # These names say nothing ("3 Glocken Genuss Pur", "Proviant", "Protein") while the caption
    # states the designation. REJECTED here and worth stating: `eingelegt` (it catches pickled
    # HERRING, which is fish) and `pizzateig` (it drags a frozen Pizza-Burger into bakery) —
    # both are forms that span categories, so neither is guardable the way a brand is.
    # GUARD above `gewürzgurken`: a caption signal must be a DESIGNATION, not an INGREDIENT,
    # and "Heringsfilethappen mit Gewürzgurken" is herring WITH gherkins — it was being served
    # as pantry until this entry went in front.
    ("fish", ["heringsfilet", "brathering", "räuchmatjes"]),
    # --- 2026-08-09 -------------------------------------------------------------------------
    # All three are DESIGNATIONS, which is the standing bar for this table. `100% saft` also
    # corrects a product the name layer had actively mis-filed: "Tabaluga Pausen-Drink
    # Mehrfrucht-Karotte" was served in **Vegetables**, because `karotte` fires at layer 6 and
    # only a signal above it can win. REJECTED the same day: `gemahlen` for coffee — it is an
    # INGREDIENT note, and it takes "Erdnussflips mit 33% gemahlenen Erdnüssen" (snacks).
    ("snacks", ["kartoffelchips"]),
    ("alcoholic", ["aperitivo"]),
    ("soft_drinks", ["100% saft"]),
    # `ausformungen` ("versch. Ausformungen") is the flyers' own word for PASTA SHAPES: 21 of the
    # 22 stored offers carrying it are already pantry (Barilla, Delverde, 3 Glocken, GUT&GÜNSTIG
    # Teigwaren). The 22nd is "EDEKA Genussmomente", whose name says nothing at all — the source
    # drops the "Teigwaren" line from the title, so the caption is the only handle.
    ("pantry", ["teigwaren", "gewürzgurken", "ausformungen"]),
    ("pork", ["salamispezialität"]),
    ("cheese", ["käsescheiben", "körnigem frischkäse"]),
    ("bakery", ["weizenkleingebäck"]),
    ("soft_drinks", ["fruchtsaftgetränk", "erfrischungsgetränke"]),
    ("sweets", ["umhüllt von milchschokolade"]),
    # --- end caption block --------------------------------------------------------------------
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
    # --- 2026-07-29 audit: the caption is the ONLY place these state what they are. Most sat
    # in `other` (nothing claimed them); two were products earlier audits deliberately DROPPED
    # because a *name* keyword would have clashed — the caption has no such problem:
    #   "Mars"              -> a bare `mars` name rule collides with Paulaner
    #   "Block House Burger"-> Block House stayed off the brand map (it also sells garlic bread)
    ("sweets", ["schokoladenriegel", "kaubonbon", "biskuitrolle"]),
    ("beef", ["aus rindfleisch"]),  # NOT "aus Schweine- und Rindfleisch" — that stays pork
    ("other_meat", ["vom merino-lamm", "vom lamm"]),
    ("fish", ["seelachsfilet", "capelinrogen"]),
    ("bakery", ["brot in scheiben", "roggenmischbrot"]),
    ("pantry", ["gewürzmischung"]),
    # A Skyr is a dairy product whatever fruit the NAME leads with ("Milsani Erdbeere" was
    # served under Fruits; the picture is a rack of yogurt pots).
    ("dairy", ["skyr high protein", "skyr, "]),
    # Only coffee is called Bohnenkaffee. Needed as a CAPTION signal because "Mövenpick
    # Kaffee"'s name alone loses to the brand map. A "% vol" caption signal was tried here and
    # REJECTED: it is a substring of "20% Vollmilch-Schokolade", which turned a chocolate
    # brioche into alcohol.
    ("coffee", ["bohnenkaffee"]),
    # Frozen PRODUCE -> frozen (the other half of the preserved-produce rule above). These are
    # produce designations, not generic freezer words: only fruit and veg is described as
    # "erntefrisch" (harvest-fresh) or sold "ungezuckert". A bare "tiefgefroren" caption signal
    # was simulated and REJECTED — it emptied ice_cream, fish and poultry into frozen (84 rows:
    # Fischstäbchen, Chicken Nuggets, every Eis). The freezer is not a category.
    ("frozen", ["erntefrisch tiefgefroren", "tiefgefroren, ungezuckert",
                "tiefgefroren, junge sojabohnen"]),
    # REJECTED, and pinned by a test: a bare "brotaufstrich" caption. It reads like a
    # designation but is a USE, not an identity — it moved POPP Fleischsalat and Bauern Gut
    # Eiersalat out of pork and the Brunch cheese spread out of cheese. Same class as the
    # already-rejected "gebäck". A spread's category comes from what it is MADE of.
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
                "ketchup", "kartoffelsalat", "kartoffel-salat",
                # Found by the 2026-07-29 IMAGE audit — each was served under a produce chip
                # while the picture showed a jar or a bottle. The prefix is the produce word,
                # the compound is the product: an Apfelmus is apple SAUCE, a Salatcreme is
                # mayonnaise. Same shape as `apfelessig` directly above.
                "apfelmus", "apfelkompott", "salatcreme", "salatmayonnaise", "knoblauch-sauce",
                "knoblauchsauce"]),
    # An Apfeltasche is a PASTRY, an Orangette is a chocolate stick — both were in Fruits,
    # both obvious from the image and invisible in the name's prefix.
    ("bakery", ["apfeltasche", "apfelstrudel"]),
    ("sweets", ["orangette"]),
    # A Reis-/Mais-/Dinkel-/Linsenwaffel is a savoury crispbread cake, not a sweet waffle —
    # the picture is a stack of pale discs, and the captions read "gesalzen"/"ungesalzen".
    # `waffel` must keep meaning sweets for Manner Waffeln and Karamellwaffeln, so the fix is
    # the specific compound at layer 5, one step ahead of the keyword.
    ("snacks", ["reiswaffel", "maiswaffel", "dinkelwaffel", "linsenwaffel", "knäckebrot"]),
    # --- The "other" bucket, adjudicated against its product photos (2026-07-29). Nothing
    # here moves from a real category: every one of these was unclaimed by any layer. ---
    ("pantry", ["natron", "cerealien", "ajvar", "konfitüre"]),
    ("sweets", ["baklava", "cantuccini", "cereola", "götterspeise", "delice"]),
    ("dairy", ["crème brûlée", "creme brulee", "mousse"]),
    ("fish", ["räucherling"]),
    # "hotties" is Milram's grilling CHEESE. Deliberately NOT the bare "grilltaler": the photo
    # of "Grillmeister Brat- und Grilltaler" is a MEAT patty (Grillmeister is Lidl's grill-meat
    # brand, "Gekühlt 280 g"), so that token would have made a burger into cheese.
    ("cheese", ["hotties"]),
    ("bakery", ["crofranz", "sandwich american", "goldstücke"]),
    ("household", ["hygienestreu", "katzenstreu"]),
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
    "fruits": ["sweet ananas", "nektarine", "plattpfirsich", "aprikose", "brombeere", "himbeere", "erdbeere",
               "pflaume", "wassermelone", "honigmelone", "kirsche", "heidelbeere", "blaubeere",
               # 2026-08-09 photo sweep: fresh fruit found in `household`, filed by the source
               # under `Tierbedarf > Marken für Tiere` and `Marken > REWE Beste Wahl`.
               "zwetschge", "grapefruit", "snack äpfel", "snack-äpfel",
               "stachelbeere", "johannisbeere", " mango", "papaya", "weintraube",
               "tafeltraube", "mandarin-orange",
                 "obstsalat", "kokosnuss stücke"],
    "vegetables": ["frische minze", "speisekartoffeln", "regional paprika", "rispentomate", "romatomate", "cherrytomate", "kulturchampignon", "champignon",
                   "zucchini", "rucola", "feldsalat", "wildkräuter salat",
                   "sonnenmais",
                 "eisbergsalat"],  # canned sweetcorn under `R > REWE > REWE Bio`
    "frozen": ["burek"],
    "fish": ["backfisch", "seelachs", "deutsche see", "lachsfilet", "pangasius", "räucher-garnele",
             "heringsstipp", "tiger-garnele",
            # A bag of raw prawns filed under `Tierbedarf und Tierfutter > Marken für Tiere`.
            "garnelen", "viktoriabarsch"],
    # "putensteak"/"puten-ministeak": grill meat filed under the `Saison und Events > … >
    # Grillsaison` root. Layer 1 decides on a non-food path and never falls through, so a
    # rescue token is the only thing that can reach it — without one a turkey steak lands in
    # household, i.e. invisible behind the Non-food toggle.
    "poultry": ["hähnchenflügel", "goldgriller", "bruzzlkracher", "maishähnchen", "geflügelsalat", "geflügel-fleischsalat", "hähnchen-grillplatte",
                "knusperdino", "putensteak", "puten-ministeak", "hähnchenschenkel",
                 "pollofino", "hähnchengyros"],
    "snacks": ["sonnenblumenkerne", "nic nac", "linsenwaffel", "jumbo erdnüsse", "erdnusskerne", "erdnuss-flip", "cashew", "walnusskern", "reiswaffel",
                 "chipsfrisch", "riffle-chips", "fruit snack"],
    "bakery": ["burger-buns", "laugen-burger", "fertigteig", "croissant", "nusshappen", "meggle brot", "vitalgebäck", "roggenmischbrot", "vollkornbrot", "mehrkornbrot", "kernbrot",
               # bake-off rolls and Greek breadsticks, both under non-food nodes
               "dinkelkrusti", "kritsinia"],
    "pantry": ["haferflocken", "baba ganoush", "hummus", "guacamole", "tomatenketchup", "agavendicksaft", "quinoa",
              # Greek orzo, canned giant beans and a grill sauce, all under non-food nodes.
              "kritharaki", "riesenbohnen", "schlemmersauce",
                 "passierte tomaten", "sweet chili", "röstzwiebeln"],
    "beef": ["ochsen-bäckchen", "ochsenbäckchen"],
    # Pork the source files under a non-food "Grillfleisch"/promo node → household ("Hausmarke
    # Schweine-Nackensteaks"). `nackensteak` is already a pork keyword, but the path wins first, so
    # the rescue re-claims it. Specific enough that only pork carries them.
    # "ASIA GREEN GARDEN Spare Ribs" is filed under `Textilreinigung > Waschmittel` — the
    # unrelated-domain mis-file. Its caption says "Koteletrippe vom Schwein", but layer 1
    # reads only name+brand, so the noun has to be here.
    "pork": ["nackensteak", "schweinenacken", "schweine-nacken", "grillnackensteak", "spare ribs", "spareribs",
             # 2026-08-09 photo sweep. Raw pork and fried meatballs reaching `household`
             # through non-food paths — a Samsung node, `Produkte > Aktionen`, `R > REWE`.
             "grillkotelett", "schälrippe", "frikadellen",
                 "rostbrätl", "hackfleisch gemischt", "gemischtes hackfleisch", "schweinefilet"],
    # 2026-07-29: the source sometimes attaches a path from an ENTIRELY UNRELATED domain --
    # a Zott Monte under "Hautpflege > Creme", Capri-Sun syrup under "Reinigungsmittel >
    # Spülmittel". Layer 1 always decides on a non-food path, so a rescue noun is the ONLY
    # way back for these; the same product arrives with a correct path from another chain,
    # which is how the self-disagreement check found them.
    # `cremefine` is a COOKING CREAM. The source hangs it off `Hautpflege > Creme`, and the
    # drugstore veto deliberately keeps it out of Body & Shower — but that left it in
    # `household`, i.e. hidden from the user entirely. Rescuing it to dairy answers both.
    "dairy": ["monte mega", "fruchtjoghurt", "cremefine", "creme zum kochen"],
    "soft_drinks": ["ingwer shot", "capri sun", "capri-sun", "fruchtsäfte", "eistee"],
    "alcoholic": ["frische-fass", " weine"],  # LEADING SPACE: bare "weine" is a substring of "Schweine-"
    # (a Schweinebraten under a pet path classified as ALCOHOLIC before this guard).
    # Grated cheese the source mis-files under a PET-brand node ("Milsani Reibekäse XXL" under
    # "Marken für Tiere"). Real cheese, not pet food, so it's a rescue — the pet guard's tokens
    # don't match "reibekäse", and no pet product carries the word.
    "cheese": ["pfannenkäse", "grill & ofen", "grillkäse", "babybel", "reibekäse", "reibekase",
               # A grated pizza cheese and a Landfrischkäse terrine, both under Tierbedarf.
               "pizzakäse", "lauchterrine"],
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
    "sweets": ["nutella", "amicelli", "fruchtkaramell", "hafer cookies", "buttergebäck"],
    # `straußensteak` in FULL, and the corpus is emphatic about why: every other stored
    # product containing "strauß" is a flower BOUQUET — Blumenstrauß, Rosenstrauß,
    # Sommerblumenstrauß, eleven of them, all correctly household. A bare token would
    # move the lot into the meat chip to rescue one pack of ostrich steaks.
    "other_meat": ["straußensteak"],
    "coffee": ["feine milde", "senseo", "kaffeepad", "kaffee", "café pads", "cafe pads", "caffè crema", "ganze bohnen"],
}

# The caption words that mean "this produce is preserved, not fresh" — a drained weight or a
# jar/tin. Read by `_redirect` AFTER the layer walk, so it reaches a product however it was
# classified.
#
# It used to be consulted only inside layer 1's food rescue, on the stated grounds that "the
# layer-2 form words handle the same convention for food-path products". They do not: those
# entries name SPECIFIC preserved products (gewürzgurke, passata), they never implement the
# caption rule. So the convention held only for the non-food-path minority, and a jar of
# Schwarzwurzeln sat in the Vegetables chip because its path was perfectly ordinary.
_PRESERVED_CAPTION: tuple[str, ...] = ("abtropfgewicht", "-glas", " glas", "konserve", " dose")
_FRESH_PRODUCE: frozenset[str] = frozenset({"fruits", "vegetables"})


def _preserved_caption(unit: str) -> Optional[str]:
    """The preserved-form word in this caption, if any (returned so the trace can name it)."""
    low = unit.lower()
    return next((t for t in _PRESERVED_CAPTION if t in low), None)


# If any of these appear in the name, the food noun is a coincidence and the non-food path stands:
# a garden plant, a garment, cookware/DIY material, or pet food — the things that legitimately live
# under the non-food roots and happen to share a word with a produce/meat noun ("Mango" the fashion
# brand, "Kirschholz" furniture, "Tomatenpflanze", "Good Boy … Knabbermix" cat treats).
_RESCUE_VETO: list[str] = [
    "pflanze", "hyazinth", "röschen", "strauch", "saatgut", " samen", "topfrose", "kunstblume",
    "schleierkraut", " beet", "kübel", "blumen", "baumschule",
    # dm sells GARDEN SEED PACKETS named after the plant — "Saaten, Zucchini (Zuboda)",
    # "Saaten, Rucola (Wilde Rauke)" — and `zucchini`/`rucola`/`feldsalat` are all
    # `_FOOD_RESCUE` tokens, so without a veto the app offers you a seed packet under
    # Fruits & Veg. The token is the BRAND, not a bare "saaten": that is a substring of
    # "Meisterbrot mit Saaten" and "Kerne-Saaten-Granola" — both pathless today, so the
    # veto would not reach them, but the bakery rescue above exists precisely to pull
    # breads out of a non-food path, and "saaten" would then veto the rescue it needs.
    "stadt land blüht",
    # A LIVING PLANT sold in a pot, named after the fruit it will one day bear. "Heidelbeere im
    # Topfcover" (a 50 cm blueberry bush) was served in the FRUITS chip: `heidelbeere` is a rescue
    # token, the path is `Heimwerken und Garten > … > Beerensträucher`, and layer 1 decides and
    # never falls through — so the `topfcover` -> household entry in `_FORM_OVERRIDES` could not
    # reach it. That L2 entry still earns its place (the same product also ships pathless), but the
    # veto is what fixes the real row. `im topf` was rejected as the token: German food marketing
    # uses it too ("Gulasch im Topf"), and this needs no width.
    "topfcover",
    # A ceramic MUG, rescued into Coffee by the bare `kaffee` token (`GUT&GÜNSTIG Kaffeebecher`,
    # `Kaffeebecher aus Steingut`). A bare `becher` is NOT usable — it is inside Becherovka (a
    # liqueur), Knorr Snackbecher and Jacobs Instant-Becherportionen, which is real coffee.
    "kaffeebecher",
    " hose", "shirt", "jacke", "socken", "kleid", "pulli", "pullover", "jeans", "leggings",
    " holz", "möbel", " lack",
    "knabbermix", "katzen", "hunde", "für tiere", " napf", "tierfutter", "vogelfutter",
    # Coffee APPLIANCES keep their non-food path: a Kaffeevollautomat is not coffee. Without
    # these the "coffee" rescue above would drag every machine into the Coffee aisle.
    "vollautomat", "maschine", "barista", "mahlwerk", "milchaufschäumer", "kocher",
]

# --------------------------------------------------------------------------------------
# Drugstore resolution — runs INSIDE the layer-1 non-food branch, after the food rescue and
# before the fall to `household`.
#
# Why here, and why this is 0-regression BY CONSTRUCTION: layer 1 is authoritative, so a
# non-food path already ends at `household` unless `_FOOD_RESCUE` saves it. This step can
# therefore only fire where the answer is CURRENTLY `household` — every move is
# `household -> <drugstore slug>`, and no existing food categorisation can change. That's a
# proof, not a measurement (the full-DB diff still ran: 258 moved, 0 out of a food category).
#
# It is deliberately NOT gated to drugstore chains. A Nivea deo at Lidl is still body care,
# and the grocery `household` chip shrinking is the point rather than a side effect.
# --------------------------------------------------------------------------------------

# Source taxonomy node (lowercased) -> slug. Scanned leaf->root, most specific first, like
# `_PATH_MAP`. Only nodes that NAME a product kind: Rossmann's level-2 is `Marken`/`Produkte`
# (pure brand containers, the documented ALDI shape), so the signal lives at level 3+.
_DRUGSTORE_PATH_MAP: dict[str, str] = {
    "zahnpflege": "dental", "zahnbürste": "dental", "zahncreme": "dental",
    "mundhygiene": "dental", "mundpflege": "dental",
    "parfümerie": "fragrance", "düfte": "fragrance", "eau de parfum": "fragrance",
    "eau de toilette": "fragrance",
    "haarpflege": "hair", "haarstyling": "hair", "haarfarben": "hair", "shampoo": "hair",
    "haarkur": "hair", "coloration": "hair",
    "gesichtspflege": "face", "gesichtsreinigung": "face",
    "gesichtsmaske": "face", "augenpflege": "face", "lippenpflege": "face",
    # The lookup is an EXACT match per node, so a qualified leaf misses the plain one it reads
    # like: dm files men's skincare under its own "Gesichtspflege für Männer", which shares no
    # key with "gesichtspflege" above and was blobbing into household. "Serum & Kur" is dm's
    # face-serum leaf (its Nagelserum and Scalp Serum sit under other leaves, so this cannot
    # reach them).
    "gesichtspflege für männer": "face", "serum & kur": "face",
    "babyflaschen & kinderflaschen": "baby",
    "körperpflege": "body", "körperreinigung": "body", "duschbad": "body", "deodorant": "body",
    "rasur": "body", "intimpflege": "body", "fußpflege": "body", "handpflege": "body",
    "sonnenschutz": "body", "hygieneartikel": "body",
    # Hair REMOVAL is shaving, i.e. body care — not hair care. `Gillette Fusion5` sits under
    # `Körperpflege > Haarentfernung` and reads as `hair` to anyone matching on "haar".
    "haarentfernung": "body",
    "make-up": "makeup", "dekorative kosmetik": "makeup", "nagellack": "makeup",
    "lippenstift": "makeup", "wimperntusche": "makeup",
    "babypflege": "baby", "windeln": "baby", "kinderpflege": "baby", "wickeln": "baby",
    "nahrungsergänzungsmittel": "health", "arzneimittel": "health", "erste hilfe": "health",
    "vitamine": "health", "haut-gesundheit": "health",
    # NOT `Textilreinigung`: it spans detergents AND drying hardware — a `LEIFHEIT
    # Wäscheschirm` and even a `WORKZONE Konstruktionsschnur` sit under
    # `Textilreinigung > Textiltrocknung > Wäscheleine`. Only the detergent nodes.
    "waschmittel": "laundry", "weichspüler": "laundry", "waschpulver": "laundry",
    "reinigungsmittel": "cleaning", "spülmittel": "cleaning", "putzmittel": "cleaning",
    "reinigen": "cleaning", "wc-reiniger": "cleaning",
    "tierfutter": "pet", "katzenfutter": "pet", "hundefutter": "pet", "tierbedarf": "pet",

    # ---- dm's own taxonomy (2026-07-30) ---------------------------------------------
    # dm sends a single, flat category leaf per product (100% coverage), and it is a far
    # better signal than the product NAME: dm's cosmetics names are full of shade words
    # that collide with tokens tuned for grocery flyers — a CATRICE blush in shade "Coral
    # Cutie" was reaching `_DRUGSTORE_RULES` "coral", the Henkel DETERGENT brand, and
    # being served as Laundry. The path map is consulted before those tokens, so mapping
    # the leaf fixes that class outright.
    # Every entry below was simulated over all stored offers before being kept.
    "blush": "makeup", "lipgloss": "makeup", "lipliner": "makeup", "highlighter": "makeup",
    "puder & mattierung": "makeup", "contouring": "makeup", "abdeckstift": "makeup",
    "lidschatten & paletten": "makeup", "make-up pinsel": "makeup", "make-up primer": "makeup",
    "nagelpflege": "makeup", "nageldesign": "makeup", "nagelfolien": "makeup",
    "kunstnägel": "makeup", "top coat & base coat": "makeup",
    "haarkur & haarmaske": "hair", "kindershampoo": "hair",
    "gesichtswasser": "face", "tagescreme": "face", "nachtcreme": "face",
    # Lip CARE, matching the `lippenpflege` -> face entry above.
    "lippenöl": "face",
    "körperöl": "body", "bodylotion & hautcreme": "body", "body spray": "body",
    "after shave & rasurpflege": "body", "sonnencreme": "body", "sonnenspray": "body",
    "elektrorasierer": "body", "feuchttücher & co.": "body",
    "babyöl & babycreme": "baby", "babyshampoo, badezusätze & co.": "baby",
    "immunsystem unterstützen": "health", "magen & verdauung": "health",
    "mineralstoffe": "health", "halsschmerzen & schluckbeschwerden": "health",
    "schlafen & nerven": "health", "wundheilung": "health", "schwangerschaftstests": "health",
    "bodenreiniger": "cleaning", "spezialreiniger": "cleaning",
    "waschzusatz": "laundry",
    "snacks für katzen": "pet",
    # NB: `Saaten & Körner` (dm's garden seed packets) is deliberately NOT here. Mapping it
    # would be DEAD CODE: `_FOOD_RESCUE` runs before this step, so "Saaten, Zucchini" is
    # already rescued to Vegetables and never reaches the path map. The fix has to be a
    # `_RESCUE_VETO` token, which is where it lives.
    # Food leaves. The drugstore step may return a FOOD slug — `_food_rescue` already does
    # from the same branch — and it must here, or dm's tea and sweets stay buried in
    # household, which is the one thing layer 1 can never fall through from.
    "tee": "soft_drinks", "herzhafte brotaufstriche": "pantry",
    "bonbons & fruchtgummi": "sweets",
}
# DELIBERATELY NOT MAPPED, each caught by the full-DB diff rather than by reading:
#   `Marken Parfum`, `Marken für Tiere`, `Marken Baby`  — BRAND CONTAINERS, the documented
#     trap. `Marken Parfum > Axe` made Axe DUSCHGEL a fragrance, and `Marken für Tiere`
#     made an `EDEKA Herzstücke Feine Pastete` and a `REWE to go Salatschale` cat food.
#   `Hautpflege` — spans face AND body ("NIVEA Pflegedusche" is a shower gel), and it is one
#     of the nodes the source attaches to unrelated products (an `AMICELLI Milchcreme`,
#     a chocolate wafer, sits under `Hautpflege > Creme`). Too broad to be trusted.
#   `Babynahrung` — a FOOD node. `Huel Trinkmahlzeit Banana` is an adult meal drink the
#     source filed there; baby food belongs in the food categories, not a drugstore aisle.
#   `Beautyhelfer` (dm) — a CONTAINER node again: it holds refill travel bottles (household)
#     AND a CATRICE eyeliner tool that already resolves to makeup on its own. Mapping it to
#     `body` DEMOTED a correct row, which is why only nodes naming a product KIND are safe.
#   `Selbstbräuner & Bräunungsbeschleuniger` (dm) — spans face drops and body lotions.
#   `Lipbalm` (dm) — mapping it would move 8 already-categorised rows body -> face for no
#     reduction in the household blob, and would then disagree with the `lippenbalsam` rule
#     that files pathless lip balms as body. The face/body split on lip care is pre-existing;
#     resolving it means moving Rossmann and grocery rows too, so it needs its own diff.

# Products the drugstore step must NOT touch, checked BEFORE the path map (which would
# otherwise decide them first). These are food the source hangs off a body-care node —
# a cooking cream and a chocolate wafer under `Körperpflege > Creme`. They stay `household`,
# the honest "we can't tell" bucket, rather than becoming a confidently wrong Body & Shower.
# Not `_FOOD_RESCUE` entries because that would need a per-product food category; this just
# declines to guess. Add here when the diff shows a food product entering a drugstore aisle.
# Paper goods ride along here for the same reason, one step further: the source files them under
# `Körperpflege`, so the path map was serving toilet roll and tissues as BODY CARE. They were also
# SPLIT — 23 rows household vs 22 body for `toilettenpapier` alone — so leaving them alone was not
# a stable answer either. Declining to guess lands them in `household`, which is where the other
# half already sat and what the (unreachable, layer-2) `_FORM_OVERRIDES` entry always intended.
# `feuchttücher` is deliberately NOT here: those genuinely split body vs baby, which is a real
# question rather than a filing error.
_DRUGSTORE_VETO: list[str] = [
    "cremefine", "amicelli",
    "toilettenpapier", "taschentücher", "küchenrolle",
]

# name/brand tokens, for the products whose path dead-ends at a brand container. Ordered,
# first hit wins — so a token that is a substring of another kind's word must come after the
# guard for it. Every entry was simulated over the full DB before being kept.
_DRUGSTORE_RULES: list[tuple[str, list[str]]] = [
    # Guards FIRST — each protects a token further down.
    # "Mundharmonika" is a HARMONICA; without this it is dental via `mund`.
    ("household", ["mundharmonika", "mundstück"]),
    # ORDER: `mundspülung` must precede the bare `spülung` below. It is listed again in the
    # dental block, but that block sits AFTER the hair rule and this table is first-hit-wins —
    # so `spülung` was claiming every Mundspülung and five Listerine/meridol mouthwashes were
    # served in the HAIR aisle. (The `mundspülung` entry in `_FORM_OVERRIDES` cannot help: that
    # is layer 2, and layer 1 decides a non-food path without falling through.)
    ("dental", ["mundspülung", "mundwasser"]),
    # ORDER, same shape: `babyshampoo` CONTAINS "shampoo" and `feuchttücher baby` contains
    # `feuchttücher`, so the baby block further down could never claim either — a baby shampoo
    # resolved to hair and baby wipes to body care. Nothing in the corpus exercises these yet,
    # which is exactly why they sat unreachable.
    # `babydream` is named explicitly rather than left to luck: the haystack is name+brand, so
    # "Feuchttücher" + brand "Babydream" happens to contain `feuchttücher baby` across the join.
    # That lands the right answer (Babydream is Rossmann's BABY line) for the wrong reason.
    ("baby", ["babyshampoo", "feuchttücher baby", "babybad", "babydream"]),
    # A Kinder-Spülbecken is a toy sink and a Spülmaschinen-tab is cleaning, but neither is
    # a Spülmittel; and "Spülung" (conditioner) is hair, not washing-up.
    ("hair", ["spülung", "haarspülung"]),
    ("dental", [
        "zahnpasta", "zahncreme", "zahnbürste", "zahnseide", "mundspülung", "mundwasser",
        "oral-b", "meridol", "elmex", "odol", "sensodyne", "parodontax", "prokudent",
        "gebissreiniger", "interdental",
    ]),
    ("hair", [
        "shampoo", "haarkur", "haarfarbe", "haarspray", "haargel", "haarschaum", "haaröl",
        "conditioner", "schauma", "guhl", "syoss", "gliss kur", "wella", "schwarzkopf",
        "alpecin", "nivea men shampoo", "haarbürste", "trockenshampoo",
    ]),
    ("face", [
        "gesichtscreme", "gesichtspflege", "gesichtsmaske", "gesichtsreinigung", "tagespflege",
        "nachtpflege", "tagescreme", "nachtcreme", "augencreme", "gesichtsserum", "daycream",
        "nightcream", "reinigungsschaum", "mizellenwasser", "revitalift", "hyaluron",
        "anti-age", "gesichtswasser",
    ]),
    ("makeup", [
        "lippenstift", "mascara", "nagellack", "make-up", "lidschatten", "kajal", "eyeliner",
        "concealer", "foundation", "rouge", "wimperntusche", "nagelöl", "primer",
    ]),
    ("fragrance", [
        "eau de parfum", "eau de toilette", "eau de cologne", "parfum", "duftset", "bodyspray",
        "body mist", "aftershave", "after shave",
    ]),
    ("body", [
        "duschgel", "duschbad", "duschcreme", "deospray", "deoroller", "deostick", "deo ",
        "bodylotion", "body lotion", "körperlotion", "körpermilch", "handcreme", "fußcreme",
        "seife", "rasierer", "rasierklinge", "rasierschaum", "rasiergel", "wilkinson",
        "gillette", "sonnencreme", "sonnenmilch", "sonnenspray", "lippenbalsam", "labello",
        "wattestäbchen", "wattepads", "damenbinde", "tampon", "slipeinlage", "facelle",
        "feuchttücher", "intimwaschlotion", "badezusatz", "schaumbad", "bartöl",
    ]),
    ("baby", [
        "windel", "babypflege", "babycreme", "babyöl", "babyshampoo", "babydream", "pampers",
        "milupa", "hipp ", "babynahrung", "schnuller", "muttermilch", "mullwindel",
        "feuchttücher baby", "babybad",
    ]),
    ("health", [
        # NOT a bare `vitamin`: it is an INGREDIENT claim all over cosmetics — it made
        # "Garnier Skin Active 2in1 Vitamin C", a face serum, a supplement.
        "nahrungsergänzung", "vitamintabletten", "vitaminpräparat", "magnesium", "kalzium",
        "elektrolyte", "laktase", "pflaster", "wundsalbe", "erkältung", "halstabletten",
        "nasenspray", "taxofit", "altapharma", "abtei", "doppelherz", "hustenbonbon",
        "desinfektion", "fieberthermometer", "warzen",
    ]),
    ("laundry", [
        "waschmittel", "weichspüler", "waschpulver", "colorwaschmittel", "vollwaschmittel",
        "perwoll", "persil", "lenor", "vernel", "coral", "ariel", "fleckenentferner",
        "wäscheparfüm", "hygienespüler",
    ]),
    ("cleaning", [
        "spülmittel", "spülmaschinen", "geschirrspül", "allzweckreiniger", "badreiniger",
        # NOT `müllbeutel`: bin bags were deliberately routed to `household` by an earlier
        # audit (the scented ones the source files under `Obst > Melone`), and claiming them
        # for Cleaning would silently reverse that decision.
        "wc-reiniger", "glasreiniger", "scheuermilch", "putztuch", "domol",
        "finish ", "calgonit", "sagrotan", "frosch ", "meister proper", "somat",
    ]),
    ("pet", [
        "katzenfutter", "hundefutter", "katzennassfutter", "hundetrockennahrung", "katzenstreu",
        "perfect fit", "sheba", "whiskas", "felix katze", "pedigree", "purina", "kauknochen",
    ]),
    # --- 2026-08-03 photo audit: drugstore products stranded in the grocery `household` chip.
    # APPENDED on purpose — the existing, more specific rules above must keep priority. Putting
    # these first made a Cien Kids "2in1 Shampoo & Duschgel" resolve to body instead of hair.
    ("fragrance", ["eau de parfum", "eau de toilette", "body splash", "after shave", "aftershave"]),
    ("hair", ["coloration", "intensiv-color", "creme color", "nutrisse", "garnier olia", "palette intensiv"]),
    ("face", ["anti-falten", "tuchmaske", "hydro boost", "gesichtsserum", "reinigungstücher"]),
    ("body", ["dusche", "duschgel", "sonnenfluid", "sonnenmilch", "badekugel", "schaumbad",
              "hidrofugal"]),
    ("health", ["heilerde", "nahrungsergänzung", "trink gel", "mumijo", "kontaktlinsen",
                "all-in-one lösung"]),
    ("baby", ["wundschutzcreme", "babytücher", "pampers", "magic cup", "action cup", "babydream"]),
    ("cleaning", ["wc-frisch", "wc frisch", "bodentücher", "geschirr-reiniger",
                  "hygiene-reiniger", "klorix"]),
    ("laundry", ["calgon", "vanish", "wasserenthärter"]),
    ("pet", ["katzentoilette", "kratzbaum", "kratzmöbel", "katzenkratz", "hundesnack",
             "beneful", "vitakraft", "winston katze", "katzenkorb",
             # 2026-08-09 photo sweep: dog/cat food still blobbing into `household`.
             "cesar hund", "winston hund", "gourmet gold", "gourmet revelations",
             "lieblings-sticks"]),
    # 2026-08-11: the ~50 drugstore products the 08-09 sweep left sitting in `household`.
    # They all arrive on a `Drogerie und Haushalt` path, so they already REACHED layer 1 —
    # they fell through for want of a token, which is the opposite half of the problem PR #155
    # fixed. Appended, so every more-specific rule above keeps priority.
    #
    # Brands that span aisles are deliberately absent (garnier -> hair/face/body, isana ->
    # face/body/health, cien -> makeup/tools, lacura -> body/makeup); the product-type word is
    # used instead. Single-aisle brands are safe: Colgate, Elvital, Pantene, Taft, Tetesept.
    ("dental", ["haftcreme", "blend-a-dent", "colgate"]),
    ("hair", ["schaumfestiger", "lockenstab", "fructis", "elvital", "pantene", "taft "]),
    ("face", ["feuchtigkeitscreme", "augenpads", "reinigungsöl", "reinigungswasser",
              "mizellen", "beauty-roller"]),
    # Feminine hygiene resolves to `body` here, and that is the EXISTING answer, not a new
    # call: all 9 stored Slipeinlagen rows (Always/Facelle/Carefree) already classify body.
    # These tokens make the household strays agree with them rather than inventing a third
    # answer. "skin food" is the same shape — one Weleda row said body, another household.
    ("body", ["enthaarungscreme", "bodycream", "selbstbräun", "après", "sonnenschutzfluid",
              "ambre solaire", "sunozon", "sun ozon", "isana pace", "hornhautentferner",
              "skin food", " binden", "carefree", "intimpflege", "tena "]),
    # NOT a bare "insektenschutz": LIVARNO's Dachfenster-Insektenschutz and Alu-Insektenschutz-
    # Tür are window and door SCREENS, i.e. household hardware. Only what goes on skin is here.
    ("health", ["tetesept", "tiger balm", "zeckito", "insektenschutzspray", "autan",
                "mückenschutz"]),
    # "raid essentials", never a bare "raid " — that sits inside "HydRAID Hydration Helper",
    # a drink.
    ("cleaning", ["domestos", "drano", "wc ente", "essigreiniger", "raid essentials"]),
]

# `_DRUGSTORE_RULES` above runs INSIDE layer 1, which is only reached by a product carrying a
# NON-FOOD path. That left 226 of its 237 tokens dead for a product with no path at all (or a
# food-root one): a pathless "Formil Feinwaschmittel" matched `waschmittel` in the household
# tuple at layer 6 and stopped there, because no drugstore slug appears in `_RULES`. Measured
# 2026-08-09 — the ratchet test only ever guarded the OTHER direction (31 layer-2 tokens dead
# for a pathed product), so the larger half of the drift was silent.
#
# The fix is data, not a new layer. `_RULES` is already an ordered first-hit-wins list whose
# LAST tuple is `household`, so splicing the aisles in immediately before it gives exactly the
# gate we want: every food tuple has already had its turn, and a drugstore token can only ever
# catch a product that was going to be `household` or `other` anyway. Zero-regression by
# construction — the same argument as appending to the last tuple.
#
# Splicing rather than copying keeps ONE source of truth, so the two placements cannot drift.
_RULES[-1:-1] = [(slug, list(tokens)) for slug, tokens in _DRUGSTORE_RULES if slug != "household"]


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
    # What this entry PREVENTED: the rescue a `_RESCUE_VETO` word killed (layer 1), or the
    # answer a post-layer redirect overrode (layer "R").
    blocked_slug: str | None = None

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
    # A post-layer override, when one fired. NOT a tenth entry in `layers`: that tuple is
    # exactly `LAYER_ORDER` and three tests pin it, so a variable-length list would churn
    # them for a reason unrelated to what they assert. `blocked_slug` names what it overrode.
    redirect: LayerTrace | None = None

    @property
    def winner(self) -> LayerTrace:
        """What produced `category` — the redirect when one fired, else the first decided layer."""
        return self.redirect or _winner(self.layers)


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


def _drugstore_hit(
    category_path: List[str], text: str
) -> Optional[tuple[str, Optional[int], str, str, str]]:
    """(table, index, matched, slug, where) for a drugstore aisle, else None.

    The PATH wins over the keywords: a node like `Körperpflege > Hautpflege` is the source's
    own designation, while a name token is our inference. (This is the opposite of the food
    layers, where the path is often mis-filed — here the non-food path has already been
    trusted enough to reach this branch, so its sub-nodes are trustworthy too.)
    """
    if any(v in text for v in _DRUGSTORE_VETO):
        return None  # before the path map, which would otherwise decide first
    for node in reversed(category_path):  # leaf -> root: most specific wins
        slug = _DRUGSTORE_PATH_MAP.get(node.strip().lower())
        if slug:
            return "_DRUGSTORE_PATH_MAP", None, node, slug, _WHERE_PATH
    hit = _first_token_hit(_DRUGSTORE_RULES, text)
    if hit is None:
        return None
    index, slug, matched = hit
    # A guard entry (`("household", [...])`) is returned as-is rather than filtered out: its
    # slug already IS `household`, so the caller's answer is identical either way, and the
    # trace then explains WHY ("_DRUGSTORE_RULES[0] matched 'mundharmonika'") instead of
    # falling through to a bare "no rescue token". A filter here would be a branch no test
    # could ever fail — `_DRUGSTORE_VETO` above is the guard that actually changes an outcome.
    return "_DRUGSTORE_RULES", index, matched, slug, _WHERE_TEXT


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
        drug = _drugstore_hit(path, text)
        # The veto blocks the FOOD rescue only — it exists so a Kaffeevollautomat isn't
        # filed as coffee. It must not also block a drugstore aisle: `maschine` is a veto
        # word and is a substring of "Finish SpülMASCHINEn-caps", which really is Cleaning.
        if rescue is not None and veto is None:
            # Real food buried under a non-food path — checked FIRST so a drugstore node
            # can't claim it (the source files spare ribs under `Waschmittel`).
            # Preserved produce used to be redirected right here. `_redirect` now does it for
            # every layer, so this branch reports what it actually found and the override is
            # recorded separately — two facts instead of one conflated one. Verified
            # redundant, not assumed: blinding `_preserved_caption` (which is exactly what
            # disabled this branch) and re-running the general redirect over the full stored
            # table reproduced the old answers row for row.
            yield LayerTrace.decided(
                "1", "nonfood_path", rescue[1], table="_FOOD_RESCUE",
                index=rescue[0], matched=rescue[2], where=_WHERE_TEXT,
            )
        elif drug is not None:
            # Not food — but a drugstore aisle rather than the undifferentiated "household"
            # bucket? Only reachable where the answer was ALREADY household, so every move
            # here is household -> a drugstore slug and nothing food can shift.
            table, index, matched, slug, where = drug
            yield LayerTrace.decided(
                "1", "nonfood_path", slug, table=table, index=index,
                matched=matched, where=where,
            )
        elif veto is not None:
            yield LayerTrace.decided(
                "1", "nonfood_path", "household", table="_RESCUE_VETO", matched=veto,
                where=_WHERE_TEXT, reason=_RESCUE_VETO_HIT,
                blocked_slug=rescue[1] if rescue else None,
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


def _redirect(won: LayerTrace, unit: str | None) -> Optional[LayerTrace]:
    """Preserved produce leaves the FRESH chips, whichever layer put it there.

    The user's standing convention (jarred/canned -> pantry, frozen -> frozen). Every rule that
    answers `fruits`/`vegetables` matches the NAME or the PATH, and neither can tell a jar from
    loose produce — while the CAPTION states the form outright ("Abtropfgewicht", "580-ml-Glas").

    A post-layer redirect rather than a layer, because a layer cannot reach this: `_winner`
    takes the FIRST decided layer, so anything placed after layers 3/6 is unreachable, and
    anything placed before them would have to re-derive the answer it is correcting.

    Gated on the winning SLUG, and that gate — not the token — is what holds the line:
    `-glas` is not right-bounded and really does fire inside "Bubble-Gum-Glasur", a stored ice
    lolly. Note this outranks every layer including the layer-2 guards; no fruits/vegetables
    entry there carries a preserved caption today, but a future guard meaning "this jarred
    thing really IS a vegetable" would be silently overridden.
    """
    if won.slug not in _FRESH_PRODUCE or not unit:
        return None
    token = _preserved_caption(unit)
    if token is None:
        return None
    return LayerTrace.decided(
        "R", "preserved_redirect", "pantry", table="_PRESERVED_CAPTION",
        matched=token, where=_WHERE_CAPTION, blocked_slug=won.slug,
    )


def _decide(
    layers: Iterable[LayerTrace], unit: str | None
) -> tuple[str, Optional[LayerTrace]]:
    """(final slug, the redirect that produced it or None) — the ONE place the answer forms.

    `classify` and `explain` both come through here, and that shared call is what keeps them
    unable to disagree: once an answer can be overridden after the walk, `_layers` + `_winner`
    alone no longer guarantee it.

    Stays LAZY. `_winner` abandons the generator at the first decided layer, and `_redirect`
    scans no rule table — five substrings against a short caption — so `classify` still costs
    the same table walks it did before.
    """
    won = _winner(layers)
    redirect = _redirect(won, unit)
    return (redirect or won).slug or "other", redirect


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
    return _decide(_layers(name, brand, category_path, unit), unit)[0]


def explain(
    name: str,
    brand: str | None = None,
    category_path: Optional[List[str]] = None,
    unit: str | None = None,
) -> ClassifyTrace:
    """`classify` plus the full trace: every layer's verdict, in order.

    Eager, so the layers *after* the winner are evaluated too — a later "decided" entry is
    the counterfactual ("layer 3 would have said fish"), which is what tells you where a fix
    belongs. Shares `_layers` and `_decide` with `classify`, so the two cannot disagree on the
    answer — `_decide` is the guarantee now that a post-layer redirect can override the walk.
    Note this reaches layers `classify` short-circuits past, so it sees inputs `classify`
    never touches — callers must validate `category_path` is a list of str.
    """
    layers = tuple(_layers(name, brand, category_path, unit))
    category, redirect = _decide(layers, unit)
    return ClassifyTrace(
        category=category,
        inputs=TraceInputs(
            name=name,
            brand=brand,
            category_path=list(category_path) if category_path else None,
            unit=unit,
            text=_haystack(name, brand),
            caption=f" {unit.lower()} " if unit else None,
        ),
        layers=layers,
        redirect=redirect,
    )


def label(slug: str) -> str:
    return CATEGORIES.get(slug, "Other")
