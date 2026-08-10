"""Group offers by the product they are *within* a category.

Inside a category (e.g. Fruits) the same product is scattered across chains and
sources, so comparing prices means hunting. This derives a coarse product key from
the offer **name** — e.g. "Avocado" / "Aprikosen, lose" -> avocado / aprikose — so
the app can cluster competing offers (Avocado: REWE 0,88 € vs Lidl 1,99 €) under a
header.

Why the name and not the stored `category_path`: the path's leaf is unreliable for
this ("Aprikosen" -> "Steinobst", "Mix Tafeltrauben" -> "kernlos" (an attribute
node), coupons have no path at all). The product noun is in the name, and the
classifier already enumerates those nouns.

Deterministic, no LLM. Computed in the serializer (`OfferOut.group`/`group_label`),
so there's no DB column or migration — exactly like `unit_price_cents`.

**Every category is mapped, except the `other` fallback**, and
`test_every_category_has_sub_groups` ratchets that so a new category cannot ship
ungrouped by accident. A name that matches no keyword still returns `(None, None)`
and falls into the list's trailing "More" bucket, which is the honest answer.

Two rules bind anyone adding a map here:

* **Order is part of the mapping.** Matching is a raw `token in name.lower()`
  substring test, first hit wins, so a specific product must precede a generic one
  whose keyword it contains — German compounds make that the common case
  ("Buttermilch" before "Milch", "Schaumwein" before "Wein").
* **A label the mobile catalog already covers must be spelled the catalog's way.**
  `basketResolve.subGroupItem` matches a group label against `GROCERY_CATALOG` by
  exact equality and a hit wins, because catalog entries carry `exclude` guards a
  synthesized `grp:` item has not. So "Nudeln" (not "Pasta"), "Müsli" (not
  "Müsli & Cerealien"), "Bier", "Reis", "Mehl", "Zucker", "Speiseöl", "Butter",
  "Schokolade" — a label that misses puts one product in the Basket twice.
  Pinned by `test_a_group_label_the_catalog_already_covers_is_spelled_its_way`.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

# slug -> [(German label, [name keywords])], scanned in order so a SPECIFIC product
# wins before a GENERIC one whose keyword it contains as a substring (German
# compounds): "Seelachs" before "Lachs", "Buttermilch" before "Milch", "Knoblauch"
# before "Lauch", specific berries before the generic "Beere". Keywords are matched
# as substrings of the lowercased name (singular stems also catch plurals:
# "aprikose" in "Aprikosen", "kirsche" in "Kirschen").
#
# For beverages (soft_drinks) a brand spans types (Volvic -> water/tea/juice, Granini ->
# juice/limo), so a brand's keyword sits in its PRIMARY type, ordered AFTER the type-word
# groups that catch its other lines (so "Volvic Tee" -> Tee before "volvic" -> Wasser).
# snacks reuse this: the "alesto" nut-brand keyword comes AFTER Studentenfutter's specific
# words, so "Alesto Trail Mix" -> Studentenfutter, "Alesto Cashewkerne" -> Nüsse.
_GROUPS: Dict[str, List[Tuple[str, List[str]]]] = {
    "fruits": [
        ("Avocado", ["avocado"]),
        ("Apfel", ["apfel", "äpfel"]),
        ("Banane", ["banane"]),
        ("Erdbeere", ["erdbeer"]),
        ("Heidelbeere", ["heidelbeer", "blaubeer"]),
        ("Himbeere", ["himbeer"]),
        ("Brombeere", ["brombeer"]),
        ("Johannisbeere", ["johannisbeer"]),
        ("Traube", ["traube"]),
        ("Orange", ["orange"]),
        ("Mandarine", ["mandarine"]),
        ("Clementine", ["clementine"]),
        ("Zitrone", ["zitrone"]),
        ("Limette", ["limette"]),
        ("Birne", ["birne"]),
        ("Kiwi", ["kiwi"]),
        ("Mango", ["mango"]),
        ("Ananas", ["ananas"]),
        # "Piel de Sapo" is a melon cultivar the flyer names without the word "Melone".
        ("Melone", ["melone", "piel de sapo"]),
        ("Pfirsich", ["pfirsich"]),
        ("Nektarine", ["nektarine"]),
        ("Aprikose", ["aprikose"]),
        ("Pflaume", ["pflaume", "zwetschge"]),
        ("Kirsche", ["kirsche"]),
        ("Physalis", ["physalis"]),
        ("Grapefruit", ["grapefruit", "pampelmuse"]),
        ("Beere", ["beere"]),  # generic, must stay after the specific berries
    ],
    "vegetables": [
        # "romatom": the feed ships a typo'd "Romatomen" (for Romatomaten) — a source
        # defect, not a product. Harmless if they ever fix it.
        ("Tomate", ["tomate", "romatom"]),
        ("Gurke", ["gurke"]),
        ("Kartoffel", ["kartoffel"]),
        ("Zwiebel", ["zwiebel"]),
        ("Paprika", ["paprika"]),
        ("Peperoni", ["peperoni"]),
        ("Möhre", ["möhre", "karotte", "mohrrübe"]),
        ("Radieschen", ["radieschen"]),
        ("Brokkoli", ["brokkoli", "broccoli"]),
        ("Blumenkohl", ["blumenkohl"]),  # before the generic Kohl
        ("Kohlrabi", ["kohlrabi"]),  # before the generic Kohl ("kohl" ⊂ "kohlrabi")
        # the flyer hyphenates it ("Mini-Pak-Choi"), so the spaced form alone misses.
        ("Pak Choi", ["pak choi", "pak-choi", "pakchoi"]),
        ("Spinat", ["spinat"]),
        ("Zucchini", ["zucchini"]),
        ("Aubergine", ["aubergine"]),
        ("Pilz", ["pilz", "champignon", "seitling", "pfifferling", "portobello", "shiitake"]),
        ("Knoblauch", ["knoblauch"]),  # before Lauch ("lauch" ⊂ "knoblauch")
        ("Lauch", ["lauch", "porree"]),
        ("Sellerie", ["sellerie"]),
        ("Kürbis", ["kürbis"]),
        ("Spargel", ["spargel"]),
        ("Mais", ["mais"]),
        ("Bohne", ["bohne"]),  # Busch-/Prinzess-/Brech-/Stangenbohnen
        ("Edamame", ["edamame"]),
        ("Erbse", ["erbse"]),
        ("Kresse", ["kresse"]),
        ("Ingwer", ["ingwer"]),
        ("Chicorée", ["chicor"]),  # covers Chicorée / Chicoree
        ("Rucola", ["rucola"]),
        ("Salat", ["salat", "lollo"]),  # generic, after Rucola ("lollo": Lollo Bionda)
        ("Kohl", ["kohl"]),  # generic, MUST stay after Blumenkohl + Kohlrabi
        ("Gemüse", ["gemüse"]),  # generic veg mixes, last of all
    ],
    "beef": [
        ("Hackfleisch", ["hack"]),
        ("Filet", ["filet"]),
        ("Steak", ["steak", "rib eye", "ribeye", "entrecôte", "entrecote"]),
        ("Gulasch", ["gulasch"]),
        ("Braten", ["braten", "tafelspitz", "schmorbraten"]),
        ("Roulade", ["roulade"]),
        ("Burger", ["burger", "patties", "frikadelle", "bulette"]),
    ],
    "poultry": [
        ("Hähnchenbrust", ["hähnchenbrust", "hühnerbrust", "putenbrust"]),
        ("Schenkel", ["schenkel", "keule", "unterkeule"]),
        ("Hähnchen", ["hähnchen", "haehnchen", "huhn", "hühner", "poulet"]),
        ("Pute", ["pute"]),
        ("Ente", ["ente"]),
    ],
    "pork": [
        ("Mett", ["mett", "hackepeter"]),
        ("Schnitzel", ["schnitzel"]),
        ("Gulasch", ["gulasch"]),
        ("Braten", ["braten"]),
        ("Kotelett", ["kotelett", "nackensteak", "nacken"]),
        ("Bratwurst", ["bratwurst", "rostbratwurst"]),  # before Wurst
        ("Salami", ["salami"]),
        ("Schinken", ["schinken"]),
        ("Bacon", ["bacon", "frühstücksspeck", "speck"]),
        ("Wurst", ["wurst", "würstchen", "lyoner", "fleischwurst"]),  # generic
    ],
    "fish": [
        ("Seelachs", ["seelachs"]),  # before Lachs ("lachs" ⊂ "seelachs")
        ("Lachs", ["lachs"]),
        ("Thunfisch", ["thunfisch"]),
        ("Forelle", ["forelle"]),
        ("Garnele", ["garnele", "shrimp", "scampi"]),
        ("Hering", ["hering", "matjes"]),
        ("Kabeljau", ["kabeljau", "dorsch"]),
        ("Pangasius", ["pangasius"]),
        ("Sardine", ["sardine", "sardelle"]),
        ("Makrele", ["makrele"]),
        ("Fischstäbchen", ["fischstäbchen", "stäbchen"]),
    ],
    "cheese": [
        ("Frischkäse", ["frischkäse"]),  # before the generic Käse
        ("Gouda", ["gouda"]),
        ("Mozzarella", ["mozzarella"]),
        ("Feta", ["feta"]),
        ("Camembert", ["camembert"]),
        ("Parmesan", ["parmesan", "grana"]),
        ("Emmentaler", ["emmentaler"]),
        ("Edamer", ["edamer"]),
        ("Brie", ["brie"]),
        ("Ziegenkäse", ["ziegenkäse"]),
        ("Käse", ["käse"]),  # generic
    ],
    "dairy": [
        ("Buttermilch", ["buttermilch"]),  # before Milch
        ("Milch", ["milch"]),
        ("Joghurt", ["joghurt", "jogurt"]),
        ("Quark", ["quark"]),
        ("Sahne", ["sahne"]),
        ("Skyr", ["skyr"]),
        ("Pudding", ["pudding"]),
        ("Schmand", ["schmand", "crème fraîche", "creme fraiche"]),
        ("Kefir", ["kefir"]),
    ],
    "bakery": [
        ("Brötchen", ["brötchen", "broetchen", "semmel", "schrippe"]),
        ("Baguette", ["baguette"]),
        ("Croissant", ["croissant"]),
        ("Toast", ["toast"]),
        ("Brezel", ["brezel", "laugen"]),
        ("Kuchen", ["kuchen", "torte"]),
        ("Donut", ["donut"]),
        ("Muffin", ["muffin"]),
        ("Brot", ["brot"]),  # generic, after the specific baked goods
    ],
    # Coffee groups by FORM, not by brand: capsules, pads, beans and a chilled iced coffee are
    # not substitutes for each other, so "which of these is cheapest" is only a fair question
    # within a form. Brands are matched too because the word "Kaffee" is often absent from the
    # name ("Jacobs Gold", "Dallmayr Prodomo") — but only single-category ones. NOT "tchibo"
    # (sells clothing) or "melitta" (also filters and machines); both are safe here in a way
    # they are not in categories.py, since this map only runs on offers already IN coffee, but
    # they earn nothing either — every stored row of theirs is caught by a form word first.
    # Specific before generic: Kapseln/Pads/Instant precede the catch-all Gemahlen.
    "coffee": [
        ("Eiskaffee", ["iced coffee", "eiskaffee", "latte macchiato", "cold brew"]),
        ("Kapseln", ["kapsel", "dolce gusto", "capsa", "nespresso", "tassimo"]),
        ("Pads", ["pad", "senseo"]),
        ("Instant", ["instant", "3in1", "löslich", "nescafé", "nescafe"]),
        ("Ganze Bohnen", ["ganze bohne", "bohnen", "bohne"]),
        # Everything else is ground/filter coffee — the default form.
        ("Gemahlen", ["kaffee", "caffè", "caffe", "espresso", "lungo", " crema", "röstkaffee",
                      "gemahlen", "filterkaffee", "jacobs", "dallmayr", "lavazza", "prodomo",
                      # Röstfein's ground lines; safe because this map only runs inside coffee.
                      "rondo", "aromatico"]),
    ],
    "soft_drinks": [
        # before Wasser/Saft so "Volvic Tee" -> Tee. "tea" catches the English iced teas
        # (Fuze Tea / Ice Tea / Bubble Tea — every "tea" name in the feed is a tea); eistee /
        # " tee" / teekanne the German -tee spellings.
        ("Tee", ["tea", "eistee", " tee", "teekanne", "teegetränk", "früchtetee", "kombucha"]),
        ("Energy", ["energy", "energydrink", "red bull", "rockstar", "28 black",
                    "effect energy", "powerade"]),
        ("Schorle", ["schorle"]),  # before Saft/Wasser (it's neither)
        ("Smoothie", ["smoothie"]),
        # before Limonade so "Coca-Cola Erfrischungsgetränk" -> Cola; the LEADING SPACE in
        # " spezi" avoids the "Spülmaschinen-Spezialsalz" substring trap.
        ("Cola", ["cola", "pepsi", " spezi", "schwip schwap", "mezzo mix"]),
        # before Saft so "Granini Die Limo" -> Limonade (not the "granini" juice keyword).
        ("Limonade", ["limonade", "lemonade", "limo", "brause", "fruchtinade",
                      "erfrischungsgetränk", "almdudler", "sinalco", "fanta", "sprite",
                      "mio mio", "tonic", "paloma"]),
        ("Saft", ["saft", "säfte", "nektar", "direktsaft", "muttersaft", "fruchtgetränk",
                  "mehrfrucht", "hohes c", "valensina", "capri-sun", "capri sun", "granini",
                  "innocent", "true fruits", "becker", "albi", "trinkgenuss", "juicy",
                  "multivitamin", "ace", "vitamin shot", "tymbark"]),
        # generic/last: earlier groups already claimed each brand's tea/juice/schorle lines,
        # so "Volvic naturelle" / "Gerolsteiner" / "Spreequell" fall through to water here.
        ("Wasser", ["wasser", "naturell", "gerolsteiner", "evian", "volvic", "spreequell",
                    "sprechquell", "sanpellegrino", "adelholzener", "aquintell", "near water",
                    "active o2", "vitamin-water", "vitamin water", "kokoswasser",
                    "kokosnusswasser"]),
    ],
    # Grouped by DRINK TYPE. Two thirds of these names are a bare brand ("Jägermeister",
    # "Aperol", "Heineken") with no type word at all, so each type carries its brands after
    # its type words — the convention soft_drinks already uses for Volvic. A brand keyword is
    # far safer here than in categories.py: this map only runs inside `alcoholic`, so a token
    # is never tested against a name from another aisle.
    "alcoholic": [
        # FIRST, ahead of every spirit brand below: a 0,33 l can of "Jack Daniel's Cola" or
        # "Three Sixty Dosen" is not a substitute for the bottle, so "which is cheapest" is
        # only a fair question against other RTDs — the same form-not-brand argument the
        # coffee map makes for capsules vs beans.
        ("Mixgetränke", ["dosen", "mixgetränk", "premixed", "longdrink", "mixery", "cocktail",
                         "hard seltzer", "ready to drink", "ready to serve", "mixed with",
                         "& cola", "coca-cola", "caipirinha", "pina colada", "batida",
                         "sex on the beach", "bellini", "smirnoff ice"]),
        # Bier before Spirituosen, so "Salitos Tequila Beer" is a beer and not a tequila.
        # "altbier"/"pale ale" are spelled out because a bare "alt" sits inside "Single MALT"
        # and a bare "ale" inside dozens of words; " beer" is space-guarded against
        # "BEERenauslese", which is a wine.
        ("Bier", ["pils", "bier", " beer", "weizen", "weissbier", "weißbier", "helles",
                  " hell", "lager", "radler", "märzen", "bockbier", "kölsch", "altbier",
                  "stout", "pale ale", "bräu", "malz", "veltins", "krombacher", "jever",
                  "warsteiner", "beck's", "becks", "heineken", "corona", "paulaner",
                  "franziskaner", "holsten", "flensburger", "sternburg", "erdinger",
                  "bitburger", "hasseröder", "wernesgrüner", "köstritzer", "radeberger",
                  "störtebeker", "oettinger", "tyskie", "staropramen", "budweiser", " bud",
                  "spaten", "mönchshof", "lübzer", "perlenbacher", "carlsberg", "desperados",
                  # No "karlsberg": the brand's only products here are the Mixery (caught as
                  # a Mixgetränk above) and a vodka RTD, which belongs in Wodka.
                  "schöfferhofer", "guinness", "feldschlö", "berliner kindl",
                  "chiemseer", "weihenstephan", "weltenburger", "augustiner", "clausthaler",
                  "gösser", "altenburger", "oberdorfer", "peroni", "astra", "maisel",
                  "kapuziner", "schultheiss", "neuzeller", "san miguel", "lemke",
                  "märkischer landmann", "klostergold", "büble", "salitos"]),
        # Sekt BEFORE Wein: "Schaumwein" contains "wein", as does "Perlwein".
        ("Sekt & Champagner", ["sekt", "champagner", "champagne", "prosecco", "secco", "cava",
                               "spumante", "schaumwein", "perlwein", "crémant", "cremant",
                               "brut", "asti", "rotkäppchen", "söhnlein", "mumm", "mionetto",
                               "moet", "moët", "roederer", "feuillatte", "metternich",
                               "freixenet", "geldermann", "wackerbarth", "henkell", "faber",
                               "arestel", "heidsieck", "bissinger", "senneval", "dargent",
                               "pommery", "ruinart", "mm extra"]),
        # Aperitif before Likör, or the "bitter" token below claims "Aperol Aperitif Bitter".
        ("Aperitif", ["aperitif", "aperitivo", "spritz", "sprizz", "hugo", "vermouth",
                      "wermut", "martini", "campari", "aperol", "lillet", "sangria",
                      "l'aperitivo"]),
        # Likör before Whisky: "FIREBALL Likör mit Whiskygeschmack" and "IRISH MIST Honig
        # Whiskey Liqueur" are liqueurs that merely name a whisky flavour, and "whisky" fires
        # inside both. Designation, not ingredient — the same rule categories.py uses.
        ("Likör", ["likör", "liqueur", "licor", "limes", "limoncello", "curacao", "curaçao",
                   "eierlikör", "bitter", "jägermeister", "jäger-meister", "baileys",
                   "bailey's", "kleiner klopfer", "fireball", "frangelico", "amaretto",
                   "sarti", "kahlua", "kahlúa", "malibu", "ramazzotti", "berentzen",
                   "kuemmerling", "krupnik", "gorzka", "schierker", "bumbu", "kraken",
                   "underberg", "triple sec", "unicum", "becherovka",
                   # "amaro di ..." spelled out: a bare "amaro" is inside "AMAROne", a wine.
                   "amaro di"]),
        ("Whisky", ["whisky", "whiskey", "bourbon", "scotch", "single malt", "jameson",
                    "jack daniel", "ballantine", "laphroaig", "macallen", "macallan",
                    "jim beam", "glenfarclas", "chivas", "johnnie walker", "tullamore",
                    "grant's", "famous grouse", "kilbeggan", "bowmore", "dalwhinnie",
                    "lagavulin", "glenlivet", "ardmore", "ben bracken", "maker's mark",
                    "monkey shoulder", "singleton", "bulleit", "paddy", "label 5"]),
        ("Wodka", ["vodka", "wodka", "wódka", "smirnoff", "absolut", "gorbatschow",
                   "three sixty", "grasovka", "five lakes", "poliakov", "russian standard",
                   "9 mile", "moskovskaya", "zubrowka", "zoladkowa", "kleiner feigling"]),
        # "gin" is a substring of "OriGINal" and "VirGIN", which is why neither token is bare:
        # " gin" catches "Roku Gin"/"Dry Gin" and "gin " catches "Gin Sul"/"GIN NOSTRUM",
        # while "Havana Club Original" and "HEINEKEN Original" match neither.
        ("Gin", [" gin", "gin ", "gordon", "hendrick", "bombay", "tanqueray", "beefeater",
                 "finsbury", "monkey 47", "malfy"]),
        # " rum" / "rum " for the same reason ("Trumpf", "Strumpf", "Rumford" all carry it).
        ("Rum", [" rum", "rum ", "havana club", "bacardi", "don papa", "botucal",
                 "captain morgan", "ron centenario", "ron zacapa", "pott rum", "cachaça",
                 "cachaca", "pitú", "pitu"]),
        ("Spirituosen", ["weinbrand", "edelbrand", "obstbrand", "obstgeist", "brandy",
                         "cognac", "grappa", "korn", "schnaps", "schnäpse", "brennerei",
                         "tequila", "mezcal", "raki", "rakı", "ouzo", "pastis", "obstler",
                         "metaxa", "nordhäuser", "sierra", "wilthener", "goldkrone",
                         "fernet", "sambuca", "aquavit", "absinth", "chantré", "chantre",
                         "osborne", "veterano", "vecchia romagna", "akropolis", "cellini",
                         "alpenschnaps"]),
        # BEFORE Wein: "Apfelwein" and "Fruchtwein" both contain "wein".
        ("Cider & Fruchtwein", ["cider", "cidre", "apfelwein", "fruchtwein", "somersby"]),
        # Generic/last, so every varietal, appellation and dryness word above has had its turn.
        # "wein" is deliberately bare — the compounds it catches (Rotwein, Weißwein, Landwein,
        # Glühwein) are all wine, and Sekt/Spirituosen already took Schaumwein and Weinbrand.
        ("Wein", ["wein", "riesling", "chardonnay", "sauvignon", "primitivo", "merlot",
                  "burgunder", "grigio", "dornfelder", "tempranillo", "cabernet", "rioja",
                  "lugana", "vinho", "veltliner", "zweigelt", "montepulciano", "chianti",
                  "valpolicella", "shiraz", "syrah", "malbec", "gewürztraminer", "scheurebe",
                  "silvaner", "trollinger", "falanghina", "fendant", "amarone", "vermentino",
                  "ribolla", "muskat", "mädchentraube", "winzer", "kellerei", "weingut",
                  " doc", "d.o.c", " aoc", " aop", " igp", " igt", " qba", "trocken",
                  "lieblich", "halbtrocken", "rosé", "rosato", "blanc", "bianco", " port",
                  "cimarosa", "blanchet", "mederano", "mederaño", "grand sud", "doppio passo",
                  "mucho mas", "erben", "weinfreunde", "barefoot", "faustino", "lungarotti",
                  "frank’n", "frank'n", "donauherbst", "donaurherbst"]),
    ],
    "snacks": [
        # Chips first: catches puffed/fried savory snacks (incl. Erdnussflips / Nic Nac's via
        # "flips"/"nic nac") before the nut keywords would grab them as raw nuts.
        ("Chips", ["chips", "chipsfrisch", "crunchips", "kesselchips", "riffels", "cross cut",
                   "pringles", "tortilla", "nachos", "kartoffelsticks", "kartoffelchips",
                   "flips", "nic nac"]),
        # before Nüsse so "Alesto Studentenfutter/Trail Mix" hit these words, not "alesto".
        ("Studentenfutter", ["studentenfutter", "trail mix", "soft-frücht", "trockenfrücht",
                             "feigen", "datteln", " samen"]),
        # Alesto = Lidl's nut brand; the brand keyword is last (after Studentenfutter).
        ("Nüsse", ["erdnuss", "erdnüsse", "mandel", "cashew", "walnuss", "pekannuss",
                   "haselnuss", "pistazie", "nussmix", "nuss", "nüsse", "alesto"]),
        ("Cracker", ["cracker", "salzgebäck", "saltlett", "brezli", "brezel", "tuc", "wasa",
                     "risbelli", "knäcke"]),
    ],
    # The dry-goods shelf, grouped by the product you'd actually put on a list. Several labels
    # are FIXED by mobile's GROCERY_CATALOG rather than free: `basketResolve.subGroupItem`
    # matches a group label against the catalog by exact equality, and a hit wins because
    # catalog entries carry `exclude` guards a synthesized `grp:` item has not. So "Nudeln"
    # (not Pasta), "Reis", "Mehl", "Zucker", "Müsli" and "Speiseöl" are spelled the catalog's
    # way — a compound like "Müsli & Cerealien" normalises to a string the catalog cannot
    # match and would put the same product in the Basket twice.
    "pantry": [
        # Oils first: "olivenöl" contains "oliven", which Konserven claims further down. Never
        # a bare "öl" — it is inside "KÖLLn" (the muesli brand two lines below).
        ("Speiseöl", ["olivenöl", "sonnenblumenöl", "rapsöl", "keimöl", "leinöl", "kokosöl",
                      "kokosnussöl", "würzöl", "speiseöl", "distelöl", "sesamöl", "bratöl",
                      "walnussöl", "arganöl", "pflanzenöl", "salatöl", "kürbiskernöl",
                      "ölspray", "rapso"]),
        ("Essig", ["essig", "balsamico", "aceto"]),
        # Ketchup before Gewürze, or "Curry Gewürzketchup" lands in spices.
        ("Ketchup", ["ketchup"]),
        ("Senf", ["senf"]),
        # Dressing before Sauce ("Salatsauce" is a dressing) and before Konserven ("Aioli").
        ("Mayonnaise & Dressing", ["mayonnaise", "mayo", "dressing", "salatcreme", "miracel",
                                   "remoulade", "aioli", "salatkrönung", "salat krönung",
                                   "vinaigrette"]),
        ("Pesto", ["pesto"]),
        ("Sauce", ["sauce", "saucen", "soße", "sossen", "soßen", "ajvar", "sriracha",
                   "tomatenmark", "passata", "chutney", "salsa"]),
        # Konfitüre before Reis ("PREISelbeere") and before Zucker ("ohne ZuckerZusatz" is a
        # jam label, not a bag of sugar).
        ("Konfitüre", ["konfitüre", "marmelade", "fruchtaufstrich", "gelee", "preiselbeer",
                       "apfelmus", "fruchtquetsch", "quetschbeutel", "schwartau"]),
        ("Honig", ["honig", "agavendicksaft", "ahornsirup", "zuckerrübensirup", "goldsaft"]),
        # "creme"/"crema" are safe here only because Mayonnaise & Dressing already took
        # "SalatCreme" and Sauce took the cooking sauces.
        ("Nussmus & Creme", ["nusspli", "erdnussbutter", "erdnussmus", "cashewmus",
                             "nuss-nougat", "nougatcreme", "schokocreme", "nutella", "tahini",
                             "mandelmus", "brotaufstrich", "brotaufrich", "creme", "crema"]),
        # Fix/Instant before Nudeln and Sauce: a "Knorr Fix Spaghetti Bolognese" is a sachet,
        # not pasta, "Nudel-Schinken Gratin" is a packet meal, and "Asia Noodles" is a cup.
        ("Fix & Instant", ["fix-produkte", "fix spaghetti", "fix ", "5 minuten terrine",
                           "terrine", "snackbecher", "instantnudeln", "instant-nudeln",
                           "pasta pot", "gratin", "noodles", "snackbar", "bechergericht"]),
        ("Nudeln", ["nudel", "spaghetti", "pasta", "teigwaren", "penne", "fusilli", "gnocchi",
                    # "tortell" covers TortellINI and TortellONI — "tortelli" matches neither.
                    "maccheroni", "tortell", "tagliatelle", "ravioli", "lasagne", "spätzle",
                    "couscous", "rigatoni", "spirelli", "gigli", "pierogi", "wareniki",
                    "collezione"]),
        ("Reis", ["reis", "risotto"]),
        ("Müsli", ["müsli", "muesli", "cerealien", "haferflocken", "porridge", "cornflakes",
                   "crunchy", "granola", "dinkelpops", "knusperm", "kölln"]),
        # Feinkost before Konserven ("Gewürzgurken" and "Antipasti" are deli, not tinned veg)
        # and before Gewürze, or the "curry" token there claims a "Hummus Dattel-Curry".
        # The bare "salat" is safe only in this position: Speiseöl already took "SalatÖl",
        # and Mayonnaise & Dressing took "SalatCreme"/"SalatKrönung"/"Salat-Dressing".
        ("Feinkost-Salate", ["kartoffelsalat", "antipasti", "hummus", "meerrettich",
                             "gewürzgurken", "feinkost", "krautsalat", "oliven-mix",
                             "tapas", "salat", "flusskrebssalat", "guacamole", "allioli",
                             "aspik"]),
        ("Tofu & Fleischersatz", ["tofu", "tempeh", "seitan", "falafel", "veggie",
                                  "vegetarian butcher", "lupinen"]),
        # Before Zucker, so "Bio-ZUCKERmais" is sweetcorn and not a bag of sugar. "tomaten"
        # is safe this late: Ketchup, Sauce and Feinkost already took Tomatenketchup,
        # Tomatensoße/-mark and the deli tomato salads.
        ("Konserven", ["kichererbsen", "oliven", "zuckermais", "mais", "bohnen", "beanz",
                       "linsen", "erbsen", "sauerkraut", "rotkohl", "in stücken",
                       "champignons", "pilze in", "gurken", "cornichons", "tomaten",
                       "anchovis"]),
        ("Eintopf & Suppe", ["eintopf", "eintöpfe", "suppe", "ravioli-topf", "linsentopf"]),
        # "hefe" is NOT bare — it is inside Hefezopf, Hefe-Röllchen and Hefeweizen, none of
        # which is a baking ingredient.
        ("Backzutaten", ["backpulver", "natron", "trockenhefe", "backhefe", "hefewürfel",
                         "vanillin", "backmischung", "puddingpulver", "speisestärke",
                         "kuvertüre", "götterspeise", "gelatine", "paniermehl", "streusel",
                         "streudekor", "pinienkerne"]),
        ("Mehl", ["mehl"]),
        ("Zucker", ["zucker"]),
        # Fresh herbs land in this chip too, so they group here rather than nowhere. No bare
        # "kräuter": it is inside "Kräuterröpfe", a bread the classifier files here by mistake.
        ("Gewürze", ["gewürz", "spices", "pfeffer", "salz", "paprikapulver", "oregano",
                     "curry", "zimt", "muskat", "brühe", "bouillon", "hefeflocken",
                     "petersilie", "dill", "koriander", "schnittlauch", "basilikum"]),
    ],
}

_UMLAUT = str.maketrans({"ä": "a", "ö": "o", "ü": "u", "ß": "ss", "é": "e", "è": "e", "ê": "e"})


_DRUGSTORE_GROUPS: Dict[str, List[Tuple[str, List[str]]]] = {
    # Drugstore aisles group by PRODUCT TYPE, which is usually the head noun of the name
    # ("Blush Stick …", "Deospray", "Zahncreme"). Same first-hit-wins rule as above, so the
    # ordering comments below are part of the mapping, not decoration.
    "body": [
        # Rasur FIRST: "Gillette Satin Care Rasiergel" would otherwise be caught by nothing,
        # but "King C. Gillette Bartshampoo" must not fall through to a hair-ish word, and
        # "Bade- & Duschgel" must not be claimed by `gel`.
        ("Rasur", ["rasier", "rasur", "systemklingen", "after shave", "aftershave",
                   "bartöl", "bartshampoo", "bartschneider", "gillette", "wilkinson"]),
        # Sonnenschutz before Bodylotion — "Sonnenmilch"/"Sonnencreme" contain neither, but
        # "After Sun Lotion" would otherwise land in Bodylotion via `lotion`.
        ("Sonnenschutz", ["sonnenspray", "sonnencreme", "sonnenmilch", "sonnenschutz",
                          "after sun", "aftersun", "sunspray"]),
        # A bare `deo` is safe HERE in a way it never is in the food maps: `_GROUPS` is keyed by
        # category, so this token is only ever tested against body-care names. "Fa Deo" ends the
        # string, so a trailing-space form would have missed it.
        ("Deo", ["deo", "bodyspray", "körperspray", "roll-on", "hidrofugal"]),
        ("Duschgel", ["duschgel", "duschbad", "duschcreme", "duschöl", "dusche",
                      "schaumbad", "badezusatz", "pflegebad"]),
        ("Bodylotion", ["bodylotion", "body lotion", "körpermilch", "körperlotion",
                        "körperbutter", "körperöl", "körpercreme", "hautmilch"]),
        ("Damenhygiene", ["slipeinlage", "einlagen", "periodenslip", "tampon",
                          "monatshygiene", "intimwasch", "blasenschwäche"]),
        ("Seife", ["seife", "seifenkissen"]),
        ("Fußpflege", ["fußpflege", "fusswohl", "fußmaske", "hornhaut", "bimsstein"]),
        ("Lippenpflege", ["lippenbalsam", "lippenbalm", "lippenpflege", "lippenöl"]),
        ("Handpflege", ["handcreme", "handlotion"]),
        ("Feuchttücher", ["feuchttücher", "reinigungstücher", "pflegetücher"]),
        ("Watte", ["wattepads", "wattestäbchen", "watte"]),
        # Deliberately NOT a bare `creme`: `body` still holds four mis-filed FOODS whose names
        # end in it (a cooking cream, a goat-cheese spread, a chocolate, a herb butter). They
        # stay ungrouped, which is the honest answer for a product in the wrong aisle.
        ("Hautcreme", ["softcreme", "hautcreme", "pflegecreme", "24h creme", "körpercreme"]),
    ],
    "face": [
        ("Lippenpflege", ["lippenbalsam", "lippenbalm", "lippenmaske", "lippenöl",
                          "lippenpflege", "lip "]),
        ("Gesichtsmaske", ["gesichtsmaske", "tuchmaske"]),
        # Reinigung before Gesichtscreme: "Reinigungscreme" ends in `creme`.
        ("Gesichtsreinigung", ["mizellenwasser", "gesichtsreinigung", "reinigungsgel",
                               "waschgel", "gesichtswasser", "peeling"]),
        ("Serum", ["serum", "booster"]),
        ("Gesichtscreme", ["tagespflege", "nachtcreme", "tagescreme", "gesichtscreme",
                           "anti-falten", "feuchtigkeitscreme", "augencreme"]),
    ],
    "hair": [
        # Coloration before Shampoo: "Coloration" lines carry brand words only, but a
        # "Color-Shampoo" must read as Shampoo, so the specific colour words come first.
        ("Coloration", ["coloration", "haarfarbe", "intensiv-color", "creme color",
                        "nutrisse", "olia", "palette intensiv", "glossing"]),
        # Trockenshampoo before Shampoo (it contains it) — a dry shampoo is its own product.
        ("Trockenshampoo", ["trockenshampoo"]),
        ("Shampoo", ["shampoo"]),
        ("Spülung", ["spülung", "conditioner"]),
        ("Haarpflege", ["haarkur", "haaröl", "haarmaske", "haarserum", "tonic"]),
        ("Styling", ["haarspray", "haargel", "haarschaum", "haarwachs", "styling"]),
        ("Haarbürste", ["haarbürste", "bürste"]),
    ],
    "dental": [
        # Aufsteckzahnbürste + elektrisch before the plain brush: they are a different
        # purchase entirely (heads vs a manual brush), and both contain "zahnbürste".
        ("Aufsteckbürsten", ["aufsteckzahnbürste", "aufsteckbürste", "ersatzbürste"]),
        ("Elektrische Zahnbürste", ["elektrische zahnbürste", "schallzahnbürste", "sonicare"]),
        ("Zahnbürste", ["zahnbürste", "interdental", "zahnseide", "zahnstocher"]),
        ("Zahncreme", ["zahncreme", "zahnpasta", "zahngel"]),
        ("Mundspülung", ["mundspülung", "mundwasser", "mundpflege"]),
        ("Haftcreme", ["haftcreme", "gebissreiniger", "prothesen"]),
    ],
    "makeup": [
        # Every one of these is the head noun of the name, so no generic fallback is needed.
        ("Nagellack", ["nagellack", "nail", "nagel"]),
        ("Concealer", ["concealer", "abdeckstift"]),
        ("Foundation", ["foundation", "make-up fluid", "bb cream", "cc cream"]),
        ("Puder", ["puder", "powder", "kompaktpuder"]),
        # Blush before Highlighter: "Blush & Highlighter" reads as a blush product.
        ("Blush", ["blush", "rouge"]),
        ("Highlighter", ["highlighter", "illuminator"]),
        ("Eyeliner", ["eyeliner", "kajal", "eye pencil"]),
        ("Mascara", ["mascara", "wimperntusche"]),
        ("Lidschatten", ["lidschatten", "eyeshadow"]),
        ("Augenbrauen", ["augenbrauen", "brow"]),
        # Lipgloss/Lippenstift before a bare `lip`, which would swallow both.
        ("Lipgloss", ["lipgloss", "lip gloss", "lipglow", "lip oil"]),
        ("Lippenstift", ["lippenstift", "lipstick", "lip liner", "lippenkonturenstift"]),
        ("Primer", ["primer", "fixing spray", "setting spray"]),
    ],
    "fragrance": [
        # Concentration is the axis a shopper compares on, and it is always spelled out.
        ("Eau de Parfum", ["eau de parfum", "eau de parfüm"]),
        ("Eau de Toilette", ["eau de toilette"]),
        ("Body Mist", ["body mist", "perfume mist", "körperspray"]),
        ("Deo", ["deospray", "deo stick", "deo roll"]),
    ],
    "laundry": [
        # Feinwaschmittel/Colorwaschmittel/Vollwaschmittel all contain "waschmittel", so the
        # specific kinds must come first — they are genuinely different purchases.
        ("Feinwaschmittel", ["feinwaschmittel", "wollwaschmittel", "perwoll"]),
        ("Colorwaschmittel", ["colorwaschmittel", "color-waschmittel", "coral"]),
        ("Vollwaschmittel", ["vollwaschmittel"]),
        ("Waschmittel", ["waschmittel", "waschpulver", "waschgel", "persil", "ariel"]),
        ("Weichspüler", ["weichspüler", "vernel", "lenor", "softlan"]),
        ("Wäscheparfüm", ["wäscheparfüm", "wäscheduft"]),
        ("Fleckenentferner", ["fleckenentferner", "vanish", "gallseife"]),
        ("Hygienespüler", ["hygienespüler", "waschmaschinenreiniger", "calgon"]),
    ],
    "cleaning": [
        # Spülmaschine before Spülmittel: "Geschirrspülmittel" is hand-washing, "Spülmaschinen-
        # tabs" are not, and both contain "spül".
        ("Spülmaschine", ["spülmaschine", "geschirr-reiniger", "geschirrspüler",
                          "somat", "finish ", "calgonit"]),
        ("Spülmittel", ["spülmittel", "geschirrspülmittel", "pril", "fairy"]),
        ("Putztücher", ["putztuch", "putztücher", "bodentücher", "allzwecktücher",
                        "geschirrtücher", "reinigungstücher", "schwamm", "topfreiniger"]),
        ("Raumduft", ["raumduft", "lufterfrischer", "duftstecker", "textilerfrischer",
                      "duftstempel"]),
        ("Entkalker", ["entkalker", "kalkreiniger", "kalk ", "wasserenthärter", "calgon"]),
        # A GENERIC `reiniger` last. In the food maps that would be reckless; here it is only
        # ever tested against cleaning-category names, and the specific kinds above have already
        # claimed the ones that matter. It is what catches the spelling zoo the source ships:
        # "WC-Reiniger", "WC Reiniger", "Glas- oder Bad-Reiniger", "Kraftreiniger".
        ("Reiniger", ["reiniger", "wc frisch", "wc-gel", "meister proper", "sagrotan",
                      "klorix", "der general", "cillit", "scheuermilch"]),
    ],
    "baby": [
        ("Windeln", ["windel", "pampers", "pants"]),
        ("Feuchttücher", ["feuchttücher", "pflegetücher", "reinigungstücher"]),
        ("Babypflege", ["wundschutz", "babycreme", "pflegeöl", "babyöl", "badezusatz",
                        "pflegebad", "baby shampoo", "waschschaum"]),
        ("Babynahrung", ["babynahrung", "folgemilch", "anfangsmilch", "quetschbeutel",
                         "früchteriegel", "brei"]),
        ("Stillzubehör", ["stilleinlagen", "stillkissen", "milchpumpe"]),
    ],
    "health": [
        # Sportnahrung FIRST: a "High-Protein-Pulver Iced Matcha Latte" carries a flavour word,
        # and `protein` must not be read as a plain supplement — this is the sports-FORMAT
        # convention (protein powders and bars are health, ordinary high-protein food is not).
        ("Sportnahrung", ["proteinpulver", "protein-pulver", "protein pulver", "whey",
                          "kreatin", "eaa ", "bcaa"]),
        ("Kontaktlinsen", ["kontaktlinsen", "monatslinsen", "linsen"]),
        ("Vitamine", ["vitamin", "multivitamin", "magnesium", "kalzium", "zink", "eisen",
                      "omega-3", "folsäure", "biotin"]),
        ("Nahrungsergänzung", ["kollagen", "elektrolyte", "melatonin", "probiotik",
                               "bitterstoffe", "heilerde", "kapseln", "tabletten",
                               "tropfen", "granulat", "blocker", "ginkgo", "laktase",
                               "sticks", "trink gel"]),
        ("Pflaster", ["pflaster", "wundpflaster", "wärmepflaster", "patch", "verband"]),
        ("Selbsttest", ["selbsttest", "schnelltest", "teststreifen"]),
        ("Erkältung", ["erkältung", "halstabletten", "nasenspray", "hustensaft"]),
    ],
    "pet": [
        # Katzenstreu before the Katze food words — litter is not food, and it contains "katze".
        ("Katzenstreu", ["katzenstreu", "streu", "cat's best"]),
        # Zubehör before the food words too: a "CACHET Kratzbaum" is furniture, and a
        # "Cachet & Romeo Haustierbett" must not read as cat food via a brand token.
        # `katzentoilette` and `katzenkratz` MUST be here rather than left to fall through: they
        # contain "katze", so the Katzenfutter group below was serving a litter box and a cat toy
        # as cat FOOD. Caught by auditing what each group actually swallowed, not by reading.
        ("Tierzubehör", ["kratzbaum", "kratzmöbel", "kratzspielzeug", "katzentoilette",
                         "haustierbett", "vogelfutterhaus", "trinkzubehör", "napf",
                         "transportbox", "hundeleine", "spielzeug"]),
        # Snacks before the food brands — a "GUT&GÜNSTIG Lieblings-Kaurollchen" is a treat, and
        # "Good Boy Bunter Hähnchen Knabbermix" would otherwise fall through entirely.
        ("Tiersnacks", ["leckerli", "kausnack", "kaurollchen", "kaustange", "kauknochen",
                        "hundesnack", "katzensnack", "knabbersnack", "knabbermix",
                        "dental-stick", "vitakraft"]),
        ("Katzenfutter", ["katzennahrung", "katzenfutter", "katzennassnahrung", "katze",
                          "sheba", "whiskas", "felix", "kitekat", "coshida", "my cat"]),
        ("Hundefutter", ["hundenahrung", "hundefutter", "hundetrockennahrung", "hund",
                         "pedigree", "beneful", "frolic", "4 paws"]),
        # Generic last: the brands that sell both (Animonda, Purina, Winston) and the products
        # named only by their FORM. Safe for the same reason as `reiniger` above — this list is
        # only ever tested against pet-category names.
        ("Tiernahrung", ["animonda", "purina", "winston", "nassnahrung", "trockennahrung",
                         "alleinfuttermittel", "pastete", "häppchen", "gelee", "futter"]),
    ],
}
# Snapshot the grocery keys BEFORE the merge, so the collision test below can be derived
# rather than hand-listed — a literal set stops covering every category added after it.
_GROCERY_GROUP_KEYS = frozenset(_GROUPS)
# A repeated slug here would SILENTLY replace a grocery map — no error, just a category that
# quietly stops grouping the way it did. Pinned by
# `test_the_drugstore_maps_do_not_overwrite_a_grocery_one`.
_GROUPS.update(_DRUGSTORE_GROUPS)


def _slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", label.lower().translate(_UMLAUT)).strip("-")


def product_group(
    name: str, brand: Optional[str] = None, category: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """(group_key, group_label) for an offer, or (None, None) if it doesn't group.

    Only categories in `_GROUPS` are grouped; within one, the first keyword hit
    wins (specific before generic), so the order in `_GROUPS` is significant.
    """
    groups = _GROUPS.get(category or "")
    if not groups:
        return None, None
    text = (name or "").lower()
    for group_label, keywords in groups:
        if any(kw in text for kw in keywords):
            return _slug(group_label), group_label
    return None, None
