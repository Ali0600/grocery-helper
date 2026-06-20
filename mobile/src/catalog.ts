// A curated, bilingual grocery catalog that powers the Basket's quick-add + matching.
//
// Each item carries English + German labels (so typing "strawberry" OR "erdbeere"
// finds it) and a list of **German name keywords** matched as substrings against the
// (German) offer names — the same signal the backend's `product_group.py` uses, ported
// to the client and extended with common staples. `exclude` guards the documented
// substring traps so one item doesn't steal another's offers (e.g. the leek keyword
// "lauch" is a substring of "Knoblauch"). Deterministic, no LLM — extend the lists to
// tune matching, exactly like the backend keyword maps.

export type CatalogItem = {
  key: string; // stable id (used as the BasketItem key + de-dupe)
  en: string; // English label — app chrome is English; drives search + display
  de: string; // German label — matches the product cards
  keywords: string[]; // German name stems, matched as substrings of the offer name
  category?: string; // category slug hint (matches backend `categories.py` slugs)
  exclude?: string[]; // substring-trap guards: skip an offer if its name contains one
};

// Shown as default suggestions when the search box is empty (most common staples).
export const POPULAR_KEYS: string[] = [
  'milk',
  'eggs',
  'bread',
  'banana',
  'apple',
  'potato',
  'tomato',
  'chicken',
  'yogurt',
  'cheese',
  'butter',
  'coffee',
];

export const GROCERY_CATALOG: CatalogItem[] = [
  // ── Fruits ──────────────────────────────────────────────────────────────────
  { key: 'apple', en: 'Apple', de: 'Apfel', category: 'fruits', keywords: ['apfel', 'äpfel'], exclude: ['apfelsaft', 'apfelschorle', 'apfelmus', 'apfelessig', 'apfelwein'] },
  { key: 'banana', en: 'Banana', de: 'Banane', category: 'fruits', keywords: ['banane'] },
  { key: 'strawberry', en: 'Strawberry', de: 'Erdbeere', category: 'fruits', keywords: ['erdbeer'] },
  { key: 'blueberry', en: 'Blueberry', de: 'Heidelbeere', category: 'fruits', keywords: ['heidelbeer', 'blaubeer'] },
  { key: 'raspberry', en: 'Raspberry', de: 'Himbeere', category: 'fruits', keywords: ['himbeer'] },
  { key: 'grape', en: 'Grapes', de: 'Trauben', category: 'fruits', keywords: ['traube', 'trauben'] },
  { key: 'orange', en: 'Orange', de: 'Orange', category: 'fruits', keywords: ['orange'], exclude: ['orangensaft', 'orangenlimonade'] },
  { key: 'mandarin', en: 'Mandarin', de: 'Mandarine', category: 'fruits', keywords: ['mandarine', 'clementine'] },
  { key: 'lemon', en: 'Lemon', de: 'Zitrone', category: 'fruits', keywords: ['zitrone'], exclude: ['zitronensaft', 'limonade'] },
  { key: 'pear', en: 'Pear', de: 'Birne', category: 'fruits', keywords: ['birne'], exclude: ['glühbirne'] },
  { key: 'kiwi', en: 'Kiwi', de: 'Kiwi', category: 'fruits', keywords: ['kiwi'] },
  { key: 'mango', en: 'Mango', de: 'Mango', category: 'fruits', keywords: ['mango'] },
  { key: 'pineapple', en: 'Pineapple', de: 'Ananas', category: 'fruits', keywords: ['ananas'] },
  { key: 'melon', en: 'Melon', de: 'Melone', category: 'fruits', keywords: ['melone'] },
  { key: 'peach', en: 'Peach', de: 'Pfirsich', category: 'fruits', keywords: ['pfirsich', 'nektarine'] },
  { key: 'apricot', en: 'Apricot', de: 'Aprikose', category: 'fruits', keywords: ['aprikose'] },
  { key: 'plum', en: 'Plum', de: 'Pflaume', category: 'fruits', keywords: ['pflaume', 'zwetschge'] },
  { key: 'cherry', en: 'Cherry', de: 'Kirsche', category: 'fruits', keywords: ['kirsche', 'kirschen'] },
  { key: 'avocado', en: 'Avocado', de: 'Avocado', category: 'fruits', keywords: ['avocado'] },

  // ── Vegetables ──────────────────────────────────────────────────────────────
  { key: 'tomato', en: 'Tomato', de: 'Tomate', category: 'vegetables', keywords: ['tomate'], exclude: ['tomatenmark', 'tomatensoße', 'tomatensauce', 'ketchup'] },
  { key: 'cucumber', en: 'Cucumber', de: 'Gurke', category: 'vegetables', keywords: ['gurke'] },
  { key: 'potato', en: 'Potato', de: 'Kartoffel', category: 'vegetables', keywords: ['kartoffel'], exclude: ['kartoffelsalat', 'kartoffelchips', 'kartoffelpüree', 'kartoffelpuffer'] },
  { key: 'onion', en: 'Onion', de: 'Zwiebel', category: 'vegetables', keywords: ['zwiebel'], exclude: ['röstzwiebel'] },
  { key: 'pepper', en: 'Bell pepper', de: 'Paprika', category: 'vegetables', keywords: ['paprika'], exclude: ['paprikapulver', 'paprikagewürz'] },
  { key: 'carrot', en: 'Carrot', de: 'Möhre', category: 'vegetables', keywords: ['möhre', 'karotte', 'mohrrübe'] },
  { key: 'broccoli', en: 'Broccoli', de: 'Brokkoli', category: 'vegetables', keywords: ['brokkoli', 'broccoli'] },
  { key: 'cauliflower', en: 'Cauliflower', de: 'Blumenkohl', category: 'vegetables', keywords: ['blumenkohl'] },
  { key: 'spinach', en: 'Spinach', de: 'Spinat', category: 'vegetables', keywords: ['spinat'] },
  { key: 'zucchini', en: 'Zucchini', de: 'Zucchini', category: 'vegetables', keywords: ['zucchini'] },
  { key: 'mushroom', en: 'Mushrooms', de: 'Champignons', category: 'vegetables', keywords: ['champignon', 'pilz', 'seitling'] },
  { key: 'garlic', en: 'Garlic', de: 'Knoblauch', category: 'vegetables', keywords: ['knoblauch'] },
  { key: 'leek', en: 'Leek', de: 'Lauch', category: 'vegetables', keywords: ['lauch', 'porree'], exclude: ['knoblauch'] },
  { key: 'asparagus', en: 'Asparagus', de: 'Spargel', category: 'vegetables', keywords: ['spargel'] },
  { key: 'lettuce', en: 'Lettuce', de: 'Salat', category: 'vegetables', keywords: ['kopfsalat', 'eisbergsalat', 'blattsalat', 'salatherz', 'feldsalat'] },
  { key: 'rocket', en: 'Rocket', de: 'Rucola', category: 'vegetables', keywords: ['rucola'] },

  // ── Meat & poultry ──────────────────────────────────────────────────────────
  { key: 'mince', en: 'Minced meat', de: 'Hackfleisch', category: 'beef', keywords: ['hack', 'gehacktes'], exclude: ['hackepeter'] },
  { key: 'steak', en: 'Steak', de: 'Steak', category: 'beef', keywords: ['steak', 'rib eye', 'ribeye', 'entrecôte', 'entrecote'] },
  { key: 'chicken-breast', en: 'Chicken breast', de: 'Hähnchenbrust', category: 'poultry', keywords: ['hähnchenbrust', 'hühnerbrust', 'putenbrust'] },
  { key: 'chicken', en: 'Chicken', de: 'Hähnchen', category: 'poultry', keywords: ['hähnchen', 'haehnchen', 'huhn', 'hühner', 'poulet'] },
  { key: 'turkey', en: 'Turkey', de: 'Pute', category: 'poultry', keywords: ['pute', 'puten'] },
  { key: 'schnitzel', en: 'Schnitzel', de: 'Schnitzel', category: 'pork', keywords: ['schnitzel'] },
  { key: 'sausage', en: 'Sausage', de: 'Wurst', category: 'pork', keywords: ['bratwurst', 'würstchen', 'wiener', 'rostbratwurst'] },
  { key: 'salami', en: 'Salami', de: 'Salami', category: 'pork', keywords: ['salami'], exclude: ['pizza'] },
  { key: 'ham', en: 'Ham', de: 'Schinken', category: 'pork', keywords: ['schinken'] },
  { key: 'bacon', en: 'Bacon', de: 'Bacon', category: 'pork', keywords: ['bacon', 'frühstücksspeck', 'speck'] },

  // ── Fish ────────────────────────────────────────────────────────────────────
  { key: 'salmon', en: 'Salmon', de: 'Lachs', category: 'fish', keywords: ['lachs'], exclude: ['seelachs'] },
  { key: 'pollock', en: 'Pollock', de: 'Seelachs', category: 'fish', keywords: ['seelachs'] },
  { key: 'tuna', en: 'Tuna', de: 'Thunfisch', category: 'fish', keywords: ['thunfisch'] },
  { key: 'trout', en: 'Trout', de: 'Forelle', category: 'fish', keywords: ['forelle'] },
  { key: 'shrimp', en: 'Shrimp', de: 'Garnelen', category: 'fish', keywords: ['garnele', 'shrimp', 'scampi'] },
  { key: 'fish-fingers', en: 'Fish fingers', de: 'Fischstäbchen', category: 'fish', keywords: ['fischstäbchen'] },

  // ── Dairy, cheese & eggs ────────────────────────────────────────────────────
  { key: 'milk', en: 'Milk', de: 'Milch', category: 'dairy', keywords: ['milch'], exclude: ['buttermilch', 'kokosmilch', 'mandelmilch', 'hafermilch', 'sojamilch', 'reismilch', 'kondensmilch'] },
  { key: 'yogurt', en: 'Yogurt', de: 'Joghurt', category: 'dairy', keywords: ['joghurt', 'jogurt'] },
  { key: 'quark', en: 'Quark', de: 'Quark', category: 'dairy', keywords: ['quark'] },
  { key: 'cream', en: 'Cream', de: 'Sahne', category: 'dairy', keywords: ['sahne', 'schlagsahne'] },
  { key: 'butter', en: 'Butter', de: 'Butter', category: 'butter', keywords: ['butter'], exclude: ['buttermilch', 'erdnussbutter', 'butterkäse', 'butterkeks', 'knoblauchbutter'] },
  { key: 'eggs', en: 'Eggs', de: 'Eier', category: 'dairy', keywords: ['eier', 'freilandei', 'bodenhaltung'], exclude: ['eierlikör', 'eiernudeln', 'eiersalat', 'eierschecke'] },
  { key: 'cheese', en: 'Cheese', de: 'Käse', category: 'cheese', keywords: ['käse'], exclude: ['käsekuchen', 'käsespätzle'] },
  { key: 'cream-cheese', en: 'Cream cheese', de: 'Frischkäse', category: 'cheese', keywords: ['frischkäse'] },
  { key: 'mozzarella', en: 'Mozzarella', de: 'Mozzarella', category: 'cheese', keywords: ['mozzarella'] },
  { key: 'feta', en: 'Feta', de: 'Feta', category: 'cheese', keywords: ['feta', 'hirtenkäse'] },
  { key: 'gouda', en: 'Gouda', de: 'Gouda', category: 'cheese', keywords: ['gouda'] },

  // ── Bakery ──────────────────────────────────────────────────────────────────
  { key: 'bread', en: 'Bread', de: 'Brot', category: 'bakery', keywords: ['brot'], exclude: ['brotaufstrich', 'knäckebrot', 'brötchen'] },
  { key: 'rolls', en: 'Bread rolls', de: 'Brötchen', category: 'bakery', keywords: ['brötchen', 'broetchen', 'semmel', 'schrippe'] },
  { key: 'toast', en: 'Toast', de: 'Toast', category: 'bakery', keywords: ['toast'] },
  { key: 'croissant', en: 'Croissant', de: 'Croissant', category: 'bakery', keywords: ['croissant'] },

  // ── Pantry & staples ────────────────────────────────────────────────────────
  { key: 'pasta', en: 'Pasta', de: 'Nudeln', category: 'pantry', keywords: ['nudel', 'spaghetti', 'pasta', 'penne', 'fusilli', 'maccheroni'] },
  { key: 'rice', en: 'Rice', de: 'Reis', category: 'pantry', keywords: ['reis'], exclude: ['reismilch', 'reiswaffel', 'preiselbeere', 'preis'] },
  { key: 'flour', en: 'Flour', de: 'Mehl', category: 'pantry', keywords: ['mehl'] },
  { key: 'sugar', en: 'Sugar', de: 'Zucker', category: 'pantry', keywords: ['zucker'], exclude: ['puderzucker', 'zuckerwatte', 'vanillezucker'] },
  { key: 'oil', en: 'Cooking oil', de: 'Öl', category: 'pantry', keywords: ['olivenöl', 'sonnenblumenöl', 'rapsöl', 'speiseöl'] },
  { key: 'coffee', en: 'Coffee', de: 'Kaffee', category: 'beverages', keywords: ['kaffee', 'espresso'] },
  { key: 'tea', en: 'Tea', de: 'Tee', category: 'beverages', keywords: ['tee', 'teebeutel'], exclude: ['teewurst', 'teelicht'] },
  { key: 'cereal', en: 'Cereal', de: 'Müsli', category: 'pantry', keywords: ['müsli', 'cornflakes', 'haferflocken'] },
  { key: 'chocolate', en: 'Chocolate', de: 'Schokolade', category: 'sweets', keywords: ['schokolade', 'schoko', 'tafelschokolade'], exclude: ['schokobrötchen'] },

  // ── Beverages ───────────────────────────────────────────────────────────────
  { key: 'water', en: 'Water', de: 'Wasser', category: 'beverages', keywords: ['mineralwasser', 'tafelwasser', 'wasser'] },
  { key: 'juice', en: 'Juice', de: 'Saft', category: 'beverages', keywords: ['saft', 'fruchtsaft', 'nektar'] },
  { key: 'cola', en: 'Cola', de: 'Cola', category: 'beverages', keywords: ['cola'] },
  { key: 'beer', en: 'Beer', de: 'Bier', category: 'beverages', keywords: ['bier', 'pils', 'radler', 'weizenbier', 'helles'], exclude: ['weizenmehl', 'bierschinken'] },
];
