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
so there's no DB column or migration — exactly like `unit_price_cents`. Only the
categories where a same-product comparison is useful are mapped; everything else
returns `(None, None)` and stays ungrouped (the app shows it as a flat list).
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
