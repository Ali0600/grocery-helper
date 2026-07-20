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
        ("Melone", ["melone"]),
        ("Pfirsich", ["pfirsich"]),
        ("Nektarine", ["nektarine"]),
        ("Aprikose", ["aprikose"]),
        ("Pflaume", ["pflaume", "zwetschge"]),
        ("Kirsche", ["kirsche"]),
        ("Physalis", ["physalis"]),
        ("Beere", ["beere"]),  # generic, must stay after the specific berries
    ],
    "vegetables": [
        ("Tomate", ["tomate"]),
        ("Gurke", ["gurke"]),
        ("Kartoffel", ["kartoffel"]),
        ("Zwiebel", ["zwiebel"]),
        ("Paprika", ["paprika"]),
        ("Möhre", ["möhre", "karotte", "mohrrübe"]),
        ("Brokkoli", ["brokkoli", "broccoli"]),
        ("Blumenkohl", ["blumenkohl"]),
        ("Spinat", ["spinat"]),
        ("Zucchini", ["zucchini"]),
        ("Aubergine", ["aubergine"]),
        ("Pilz", ["pilz", "champignon", "seitling"]),
        ("Knoblauch", ["knoblauch"]),  # before Lauch ("lauch" ⊂ "knoblauch")
        ("Lauch", ["lauch", "porree"]),
        ("Sellerie", ["sellerie"]),
        ("Kürbis", ["kürbis"]),
        ("Spargel", ["spargel"]),
        ("Rucola", ["rucola"]),
        ("Salat", ["salat"]),  # generic, after Rucola
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
