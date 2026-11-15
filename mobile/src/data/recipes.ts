// AI-authored recipes — generated OFFLINE by Claude Code from the current grocery.db
// deals + the always-have staples, then bundled into the app and shipped via OTA. There is
// NO runtime LLM/API call: the Recipes screen renders this file and matches each ingredient
// to the user's loaded offers client-side (see ../recipes.ts). Regenerate weekly when the
// flyers refresh (see docs/recipes.md). Each ingredient's `keywords` are German name stems
// matched as substrings of offer names (same signal as the Basket); `staple: true` marks a
// pantry item assumed on hand. Quantities are written for `servings`; the app scales them.
//
// Each recipe is authored for ONE chain, or for exactly TWO (the "Shop at" scope) — every
// non-staple ingredient comes from that chain's own candidate list. A recipe carries no store
// field on purpose: the app re-derives the stores from the live match each session, so a tag
// written here would be a claim about one week's flyer that quietly goes stale.
//
// Watch the STAPLE keywords: they are matched as substrings like any other, so bare 'salz'
// hits salted peanuts, 'pfeffer' hits Pfeffer-Salami, 'butter' hits a Buttercroissant and
// 'honig' hits a Walnuss-Honig-Brot. A false staple match is not cosmetic — it inflates the
// on-sale count the ranking uses. Seasoning is never worth pricing at all, so it is
// deliberately narrowed to standalone products and reads as "have".

import { RecipesData, RecipeIngredient } from '../types';

// Shared staple lines — identical in every recipe, so they are written once.
const onion = (qty: string, label = 'Onion'): RecipeIngredient => ({
  label,
  keywords: ['zwiebel'],
  qty,
  staple: true,
  exclude: ['lauchzwiebel', 'blumenzwiebel', 'zwiebelmettwurst', 'röstzwiebel', 'baguette', 'ciabatta', 'zwiebelbrot', 'schinkenzwiebelmett', 'zwiebelbällchen', 'schmalz'],
});
const garlic = (qty: string): RecipeIngredient => ({
  label: 'Garlic',
  keywords: ['knoblauch'],
  qty,
  staple: true,
  exclude: ['wurst', 'salami', 'baguette', 'butter', 'creme', 'sauce', 'garnelen', 'pizzabrot', 'naan'],
});
const oil = (qty: string, label = 'Oil'): RecipeIngredient => ({
  label,
  keywords: ['olivenöl', 'speiseöl', 'rapsöl', 'sonnenblumenöl'],
  qty,
  staple: true,
  exclude: ['grissini', 'antipasti', 'tischset', 'kürbiscreme'],
});
const butter = (qty: string): RecipeIngredient => ({
  label: 'Butter',
  keywords: ['butter'],
  qty,
  staple: true,
  exclude: ['buttermilch', 'erdnussbutter', 'peanut butter', 'butterkäse', 'butterkeks', 'knoblauchbutter', 'kräuterbutter', 'butterfly', 'fassbutter', 'brotaufstrich', 'croissant', 'baguette', 'kuchen', 'rama', 'butterschmalz', 'plätzchen', 'blätterteig', 'butter chicken', 'zopf', 'gebäck'],
});
const flour = (qty: string): RecipeIngredient => ({
  label: 'Flour',
  keywords: ['weizenmehl', 'dinkelmehl', 'mehl'],
  qty,
  staple: true,
  exclude: ['mehlschwitze', 'semmelmehl', 'eierkuchenmehl', 'eierkuchen-mehl', 'paniermehl'],
});
const milk = (qty: string): RecipeIngredient => ({
  label: 'Milk',
  keywords: ['haltbare milch', 'frische milch', 'vollmilch', 'landmilch', 'weidemilch'],
  qty,
  staple: true,
  exclude: ['milchreis', 'milchschnitte', 'kokosnussmilch', 'buttermilch', 'kondensmilch', 'kaffee-milch', 'müllermilch', 'schoko', 'baumkuchen'],
});
const sugar = (qty: string): RecipeIngredient => ({
  label: 'Sugar',
  keywords: ['zucker'],
  qty,
  staple: true,
  exclude: ['zuckermais', 'zuckermelone', 'puderzucker', 'zuckerwatte', 'zuckerzusatz', 'cola', 'zero', 'zuckerfrei', 'zuckerdekor', 'zuckerstangen', 'zuckerglasur'],
});
const eggs = (qty: string): RecipeIngredient => ({
  label: 'Eggs',
  keywords: ['eier'],
  qty,
  staple: true,
  exclude: ['eierlikör', 'eiersalat', 'eierkuchen', 'eierkocher', 'eiernudeln', 'dessert-ei', 'puddingdessert', 'tagliatelle', 'spätzle'],
});
const rice = (qty: string): RecipeIngredient => ({
  label: 'Rice',
  keywords: ['basmati', 'jasminreis', 'langkornreis', 'express-reis', 'expressreis'],
  qty,
  staple: true,
  exclude: ['milchreis', 'waffel', 'snack', 'drink'],
});
const pasta = (qty: string, label = 'Pasta'): RecipeIngredient => ({
  label,
  keywords: ['spaghetti', 'teigwaren', 'nudeln', 'pasta'],
  qty,
  staple: true,
  exclude: ['sauce', 'fix', 'pastasauce', 'carbonara', 'instantnudel', 'instant-nudel', 'nudel snack', 'alfredo', 'dampfnudeln', 'bolognese', 'eishörnchen', 'cup', 'terrine', 'magic asia', 'pesto', 'pasta pot', 'bowl', 'glasnudeln', 'bratnudeln', 'nudelsuppe', 'wok-nudeln', 'mie-nudeln', 'konjak', 'gebratene', 'spaghetteria', 'asia'],
});
const carrots = (qty: string): RecipeIngredient => ({
  label: 'Carrots',
  keywords: ['speisemöhren', 'möhren', 'karotten'],
  qty,
  staple: true,
  exclude: ['saft', 'kuchen', 'brei', 'krüstchen'],
});
const saltPepper: RecipeIngredient = { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true };
const salt: RecipeIngredient = { label: 'Salt', keywords: ['speisesalz', 'meersalz'], staple: true };

// 'marzipan': EDEKA's "Marzipan-kartoffeln" are sweets filed under vegetables;
// 'bratkartoffel': E center's ready-fried potatoes are not raw ones.
const POTATO_EXCLUDE = ['süßkartoffel', 'rösti', 'chips', 'salat', 'puffer', 'reibekuchen', 'marzipan', 'bratkartoffel', 'auflauf', 'brot', 'knödel', 'klöße', 'püree', 'mal anders', 'wedges', 'herzoginkartoffel'];
const POINTED_PEPPER = (qty: string): RecipeIngredient => ({ label: 'Red pointed peppers', keywords: ['spitzpaprika'], qty, exclude: ['gefüllt', 'creme'] });
const CUCUMBER: RecipeIngredient = { label: 'Cucumber', keywords: ['salatgurke'], qty: '1', exclude: ['eingelegt'] };
const SPRING_ONIONS: RecipeIngredient = { label: 'Spring onions', keywords: ['lauchzwiebel'], qty: '1 bunch' };
// 'topf': E center's "Radieschentopf" is a cream cheese, not radishes.
const RADISHES: RecipeIngredient = { label: 'Radishes', keywords: ['radieschen'], qty: '1 bunch', exclude: ['topf', 'frischkäse'] };
const MOUNTAIN_CHEESE = (qty: string): RecipeIngredient => ({ label: 'Mountain cheese (Bergkäse)', keywords: ['bergkäse'], qty, exclude: ['snack'] });
const LEEKS: RecipeIngredient = { label: 'Leeks', keywords: ['porree', 'lauch'], qty: '2', exclude: ['lauchzwiebel', 'suppe', 'käse-lauch'] };
const CIABATTA: RecipeIngredient = { label: 'Ciabatta', keywords: ['ciabatta'], qty: '1 loaf', exclude: ['chips'] };

export const RECIPES: RecipesData = {
  generatedFor: '10115',
  generatedAt: '2026-11-15',
  recipes: [
    // ---- single store: dm (clearance only — one cookable line each, so both lean on staples) ----
    {
      id: 'dm-kuerbiscreme-pasta-knoblauch',
      title: 'Pumpkin Cream Pasta with Crispy Garlic',
      summary: 'Pasta tossed in a jar of pumpkin-and-olive-oil cream loosened with its cooking water, topped with golden garlic chips and black pepper.',
      servings: 2,
      timeMinutes: 20,
      tags: ['vegan', 'italian', 'lunch'],
      ingredients: [
        { label: 'Pumpkin cream', keywords: ['kürbiscreme'], qty: '180 g' },
        pasta('250 g'),
        garlic('4 cloves'),
        onion('1'),
        oil('3 tbsp', 'Olive oil'),
        saltPepper,
      ],
      steps: [
        'Boil the pasta in well-salted water. Slice the garlic thinly and warm it in the oil from cold, lifting it out when pale gold.',
        'Soften the finely diced onion in the garlic oil for 5 minutes, then stir in the pumpkin cream.',
        'Toss in the drained pasta with a ladle of its cooking water until glossy, season with plenty of pepper and scatter over the garlic chips.',
      ],
    },
    {
      id: 'dm-kaiserschmarrn-fruechtetee-sirup',
      title: 'Kaiserschmarrn with Berry Tea Syrup',
      summary: 'A fluffy, torn Austrian pancake caramelised with sugar in the pan, served with a ruby cranberry-strawberry tea syrup.',
      servings: 3,
      timeMinutes: 30,
      tags: ['vegetarian', 'austrian', 'breakfast'],
      ingredients: [
        { label: 'Berry fruit tea', keywords: ['früchtetee'], qty: '3 tbsp loose' },
        flour('150 g'),
        milk('250 ml'),
        eggs('4'),
        sugar('6 tbsp'),
        butter('3 tbsp'),
        salt,
      ],
      steps: [
        'Steep the tea in 250 ml of boiling water for 10 minutes, strain it hard and boil it with 4 tbsp sugar until it turns syrupy.',
        'Whisk the flour, milk, egg yolks and a pinch of salt; beat the whites stiff with 1 tbsp sugar and fold them in.',
        'Pour into a hot buttered pan, cook until set underneath, flip in pieces and tear into chunks with two forks; sprinkle with the last sugar, let it caramelise, and serve with the syrup.',
      ],
    },

    // ---- single store: EDEKA ----
    {
      id: 'edeka-knoblauch-haehnchen-brokkoli-spitzpaprika',
      title: 'Garlic Chicken Stir-Fry with Broccoli & Pointed Pepper',
      summary: 'Chicken breast seared in a very hot pan with broccoli florets and sweet red pointed pepper, finished with plenty of garlic and spring onions over rice.',
      servings: 3,
      timeMinutes: 25,
      tags: ['meat', 'asian', 'dinner'],
      ingredients: [
        {
          label: 'Chicken breast',
          keywords: ['hähnchenbrustfilet', 'hähnchen-brustfilet', 'hähnchen-innenfilet'],
          qty: '450 g',
          exclude: ['nuggets', 'schnitzel', 'wurst', 'salami', 'aufschnitt', 'roulade', 'cordon', 'dulano', 'wiltmann', 'metten', 'müller & müller'],
        },
        { label: 'Broccoli', keywords: ['brokkoli', 'broccoli'], qty: '1 head', exclude: ['stangenbrokkoli', 'bimi', 'auflauf', 'schinkensalat'] },
        POINTED_PEPPER('2'),
        SPRING_ONIONS,
        rice('200 g'),
        garlic('4 cloves'),
        oil('2 tbsp'),
        saltPepper,
      ],
      steps: [
        'Cook the rice. Cut the chicken into strips, the broccoli into small florets and the pepper into rings; slice the spring onions.',
        'Sear the chicken in very hot oil for 4 minutes until browned, then add the broccoli with a splash of water and cover for 2 minutes.',
        'Add the pepper and the sliced garlic and stir-fry 2 more minutes; season well, scatter over the spring onions and serve over the rice.',
      ],
    },
    {
      id: 'edeka-joghurt-bircher-granatapfel-clementinen',
      title: 'Bircher Yoghurt Bowl with Clementines & Pomegranate',
      summary: 'Bircher muesli soaked overnight in yoghurt, topped with juicy clementine segments and a scatter of pomegranate seeds.',
      servings: 2,
      timeMinutes: 10,
      tags: ['vegetarian', 'swiss', 'breakfast'],
      ingredients: [
        { label: 'Bircher muesli', keywords: ['bircher'], qty: '120 g' },
        {
          label: 'Plain yoghurt',
          keywords: ['joghurt'],
          qty: '300 g',
          exclude: ['müsli', 'frucht', 'drink', 'dressing', 'pudding', 'ecke', 'knusper', 'vanille', 'pfirsich', 'stracciatella', 'mousse'],
        },
        { label: 'Clementines', keywords: ['clementinen'], qty: '3', exclude: ['saft'] },
        { label: 'Pomegranate seeds', keywords: ['granatapfelkerne', 'granatapfel'], qty: '1 tub', exclude: ['saft', 'tee', 'shot'] },
        milk('100 ml'),
      ],
      steps: [
        'The night before (or at least 20 minutes ahead), stir the muesli into the yoghurt with the milk and leave it in the fridge to soften.',
        'Peel the clementines and pull them into segments.',
        'Spoon the bircher into bowls and top with the clementines and pomegranate seeds.',
      ],
    },

    // ---- single store: E center ----
    {
      id: 'edeka-center-suesskartoffel-champignon-patros-blech',
      title: 'Sweet Potato, Mushroom & White Cheese Traybake',
      summary: 'Wedges of sweet potato roasted with mushrooms, red pointed peppers and onion until caramelised, then finished with crumbled salty white cheese.',
      servings: 3,
      timeMinutes: 45,
      tags: ['vegetarian', 'greek', 'dinner'],
      ingredients: [
        { label: 'Sweet potatoes', keywords: ['süßkartoffel'], qty: '800 g', exclude: ['rösti', 'pommes', 'chips'] },
        { label: 'White mushrooms', keywords: ['champignons'], qty: '250 g', exclude: ['creme', 'suppe', 'sauce', 'cambozola'] },
        POINTED_PEPPER('2'),
        { label: 'Greek-style white cheese', keywords: ['patros'], qty: '200 g' },
        onion('2', 'Red onions'),
        garlic('3 cloves'),
        oil('4 tbsp', 'Olive oil'),
        saltPepper,
      ],
      steps: [
        'Heat the oven to 220 °C. Cut the sweet potatoes into wedges, the onions into eighths and the peppers into strips; halve the mushrooms.',
        'Toss everything with the oil, crushed garlic, salt and pepper on a large tray and roast 30 minutes, turning once, until soft and browned at the edges.',
        'Crumble the cheese over and return to the oven for 5 minutes until it just starts to colour.',
      ],
    },
    {
      id: 'edeka-center-rindergulasch-bratkartoffeln',
      title: 'Beef Goulash with Pointed Pepper & Sour Cream',
      summary: 'Beef braised slowly with onions, tomato paste and sweet pointed peppers into a deep red goulash, topped with smetana and served with crisp fried potatoes.',
      servings: 4,
      timeMinutes: 120,
      tags: ['meat', 'hungarian', 'dinner'],
      ingredients: [
        { label: 'Beef goulash meat', keywords: ['rindergulasch', 'rinder-gulasch'], qty: '500 g', exclude: ['suppe', 'dose', 'eintopf'] },
        POINTED_PEPPER('2'),
        { label: 'Tomato paste', keywords: ['tomatenmark'], qty: '2 tbsp' },
        { label: 'Smetana (sour cream)', keywords: ['smetana'], qty: '150 g' },
        { label: 'Fried potatoes', keywords: ['bratkartoffeln'], qty: '1 pack' },
        onion('3', 'Onions'),
        garlic('2 cloves'),
        carrots('1'),
        flour('1 tbsp'),
        oil('3 tbsp'),
        saltPepper,
      ],
      steps: [
        'Brown the beef in batches in hot oil and set aside. Fry the sliced onions and diced carrot in the same pot for 10 minutes until golden.',
        'Stir in the tomato paste, garlic and flour for a minute, return the beef, add 600 ml water, cover and simmer gently for 90 minutes; add the pepper strips for the last 20.',
        'Fry the potatoes in a hot pan until crisp, season the goulash and serve it with a spoonful of smetana on top.',
      ],
    },

    // ---- single store: Lidl ----
    {
      id: 'lidl-miesmuscheln-tomate-ciabatta',
      title: 'Mussels in Tomato & Garlic with Ciabatta',
      summary: 'A big pot of mussels steamed open in a quick tomato, onion and garlic broth, with torn ciabatta to mop up every drop.',
      servings: 2,
      timeMinutes: 30,
      tags: ['pescatarian', 'french', 'dinner'],
      ingredients: [
        { label: 'Mussels', keywords: ['miesmuscheln'], qty: '1 kg', exclude: ['salat'] },
        { label: 'Roma tomatoes', keywords: ['romatomaten'], qty: '4', exclude: ['getrocknet', 'sauce'] },
        CIABATTA,
        onion('1'),
        garlic('4 cloves'),
        oil('3 tbsp', 'Olive oil'),
        saltPepper,
      ],
      steps: [
        'Scrub the mussels and throw away any that stay open when tapped. Dice the tomatoes.',
        'Soften the onion and garlic in the oil for 5 minutes, add the tomatoes and 100 ml water and simmer 5 minutes.',
        'Tip in the mussels, cover tightly and steam 5–6 minutes, shaking the pot, until they open (discard any that stay shut); serve with the warm ciabatta.',
      ],
    },
    {
      id: 'lidl-couscous-granatapfel-avocado-salat',
      title: 'Couscous Salad with Pomegranate, Avocado & Peppers',
      summary: 'Fluffy couscous tossed with green pepper, cherry vine tomatoes and ripe avocado, sparkling with pomegranate seeds in an olive-oil dressing.',
      servings: 3,
      timeMinutes: 20,
      tags: ['vegan', 'middle-eastern', 'lunch'],
      ingredients: [
        { label: 'Couscous', keywords: ['couscous'], qty: '250 g', exclude: ['salat', 'fertig'] },
        { label: 'Pomegranate', keywords: ['granatapfel'], qty: '1', exclude: ['saft', 'tee', 'shot'] },
        { label: 'Avocado', keywords: ['avocado'], qty: '1', exclude: ['creme', 'öl', 'dip'] },
        { label: 'Green pepper', keywords: ['paprika'], qty: '1', exclude: ['gefüllt', 'chips', 'salami', 'wurst', 'gewürz', 'edelsüß', 'pulver', 'paprikarand'] },
        { label: 'Cherry vine tomatoes', keywords: ['strauchtomaten', 'cocktailtomaten'], qty: '250 g', exclude: ['getrocknet', 'sauce'] },
        onion('½', 'Red onion'),
        oil('4 tbsp', 'Olive oil'),
        saltPepper,
      ],
      steps: [
        'Pour 300 ml boiling salted water over the couscous with 1 tbsp oil, cover for 5 minutes, then fluff it with a fork and let it cool a little.',
        'Halve the tomatoes, dice the pepper and avocado, slice the onion finely and knock the seeds out of the halved pomegranate.',
        'Toss everything with the remaining oil, salt and pepper.',
      ],
    },

    // ---- single store: Penny ----
    {
      id: 'penny-rinderrouladen-rotkohl-kartoffeln',
      title: 'Beef Rouladen with Red Cabbage & Potatoes',
      summary: 'Classic beef rolls filled with onion and carrot, slowly braised in their own gravy, served with sweet-sour red cabbage and boiled potatoes.',
      servings: 4,
      timeMinutes: 120,
      tags: ['meat', 'german', 'dinner'],
      ingredients: [
        { label: 'Beef rouladen', keywords: ['rinder-rouladen', 'rinderroulade'], qty: '4' },
        { label: 'Red cabbage', keywords: ['rotkohl'], qty: '1 jar', exclude: ['salat'] },
        { label: 'Potatoes', keywords: ['kartoffeln'], qty: '800 g', exclude: POTATO_EXCLUDE },
        carrots('2'),
        onion('2', 'Onions'),
        flour('1 tbsp'),
        oil('2 tbsp'),
        saltPepper,
      ],
      steps: [
        'Season the rouladen, lay strips of carrot and onion on each, roll them up tightly and secure with toothpicks or string.',
        'Brown them all over in the oil, add the rest of the chopped onion and carrot and 500 ml water, cover and braise gently for 90 minutes; thicken the gravy with the flour stirred into a little cold water.',
        'For the last 25 minutes boil the potatoes and gently heat the red cabbage, and serve both with the rouladen and their gravy.',
      ],
    },
    {
      id: 'penny-flammkuchen-bergkaese-eisbergsalat',
      title: 'Onion & Mountain Cheese Flammkuchen',
      summary: 'Wafer-thin tarte flambée spread with herb quark, scattered with onion and grated mountain cheese and baked until blistered, with a crisp iceberg salad.',
      servings: 2,
      timeMinutes: 25,
      tags: ['vegetarian', 'french', 'dinner'],
      ingredients: [
        { label: 'Flammkuchen dough', keywords: ['flammkuchenteig'], qty: '1 roll' },
        { label: 'Herb quark', keywords: ['gewürzquark', 'kräuterquark'], qty: '200 g' },
        MOUNTAIN_CHEESE('100 g'),
        { label: 'Iceberg lettuce', keywords: ['eisbergsalat'], qty: '½ head' },
        onion('2'),
        oil('3 tbsp'),
        saltPepper,
      ],
      steps: [
        'Heat the oven as hot as it goes (250 °C). Unroll the dough on its paper and spread it thinly with the quark.',
        'Scatter over the onions sliced into very thin rings and the grated cheese, grind over pepper and bake 10–12 minutes until the edges blister.',
        'Meanwhile tear the lettuce and dress it with the oil and a pinch of salt; serve with the flammkuchen cut into squares.',
      ],
    },

    // ---- single store: REWE ----
    {
      id: 'rewe-aubergine-hummus-ciabatta',
      title: 'Charred Aubergine on Hummus with Cherry Tomatoes',
      summary: 'Thick slices of aubergine fried until silky, piled on a swoosh of hummus with roasted cherry tomatoes, sliced radishes and warm ciabatta.',
      servings: 2,
      timeMinutes: 30,
      tags: ['vegan', 'middle-eastern', 'lunch'],
      ingredients: [
        { label: 'Aubergine', keywords: ['aubergine'], qty: '2', exclude: ['creme', 'dip', 'antipasti'] },
        { label: 'Hummus', keywords: ['hummus'], qty: '200 g', exclude: ['chips', 'snack'] },
        { label: 'Cherry tomatoes', keywords: ['romatomaten', 'rispentomaten'], qty: '250 g', exclude: ['getrocknet', 'sauce'] },
        RADISHES,
        CIABATTA,
        garlic('2 cloves'),
        oil('5 tbsp', 'Olive oil'),
        salt,
      ],
      steps: [
        'Heat the oven to 200 °C. Toss the tomatoes with 1 tbsp oil and salt and roast 15 minutes until they burst; warm the ciabatta for the last 5.',
        'Slice the aubergines 2 cm thick, salt them and fry in the rest of the oil with the sliced garlic until deep golden and soft right through.',
        'Spread the hummus on plates, pile on the aubergine and tomatoes, scatter over the sliced radishes and serve with the ciabatta.',
      ],
    },
    {
      id: 'rewe-schweinekotelett-senf-porree-kartoffeln',
      title: 'Pork Chops with Mustard Leeks & Potatoes',
      summary: 'Pan-fried pork chops on soft, buttery leeks sharpened with East German mustard, with boiled potatoes to soak up the pan juices.',
      servings: 2,
      timeMinutes: 35,
      tags: ['meat', 'german', 'dinner'],
      ingredients: [
        { label: 'Pork chops', keywords: ['stielkotelett', 'schweine-kotelett', 'schweinekotelett'], qty: '2', exclude: ['kalbs'] },
        LEEKS,
        { label: 'Potatoes', keywords: ['speisekartoffeln', 'kartoffeln'], qty: '600 g', exclude: POTATO_EXCLUDE },
        { label: 'Mustard', keywords: ['senf'], qty: '2 tbsp', exclude: ['sauce', 'gurke', 'dressing', 'hering', 'matjes'] },
        butter('2 tbsp'),
        oil('1 tbsp'),
        saltPepper,
      ],
      steps: [
        'Boil the potatoes in salted water for about 20 minutes. Slice the leeks into rings and wash them well.',
        'Season the chops and fry them in the oil for 4–5 minutes a side; rest them on a plate.',
        'Melt the butter in the same pan, soften the leeks for 8 minutes with a splash of water, stir in the mustard and the chop juices, and serve with the chops and potatoes.',
      ],
    },

    // ---- two stores ----
    {
      id: 'edeka-lidl-raeucherlachs-bagels',
      title: 'Smoked Salmon Bagels with Cucumber & Spring Onion',
      summary: 'Toasted bagels spread thick with cream cheese, layered with Scottish smoked salmon, cucumber ribbons and spring onion.',
      servings: 2,
      timeMinutes: 10,
      tags: ['pescatarian', 'american', 'breakfast'],
      ingredients: [
        { label: 'Bagels', keywords: ['bagel'], qty: '2', exclude: ['chips'] },
        { label: 'Smoked salmon', keywords: ['räucherlachs'], qty: '100 g', exclude: ['vegan', 'schinken', 'aufschnitt', 'tatar'] },
        { label: 'Cream cheese', keywords: ['philadelphia', 'frischkäse'], qty: '100 g', exclude: ['walnuss', 'protein', 'kuchen', 'röllchen', 'hähnchen'] },
        CUCUMBER,
        SPRING_ONIONS,
        saltPepper,
      ],
      steps: [
        'Split and toast the bagels.',
        'Spread each half generously with cream cheese and lay on thin cucumber ribbons.',
        'Drape over the smoked salmon, scatter with sliced spring onion and finish with black pepper.',
      ],
    },
    {
      id: 'lidl-rewe-avocado-radieschen-toast-ei',
      title: 'Avocado & Radish Toast with Fried Eggs',
      summary: 'Crusty multigrain toast piled with crushed avocado, crisp sliced radishes and a runny fried egg.',
      servings: 2,
      timeMinutes: 15,
      tags: ['vegetarian', 'australian', 'breakfast'],
      ingredients: [
        { label: 'Avocado', keywords: ['avocado'], qty: '2', exclude: ['creme', 'öl', 'dip'] },
        RADISHES,
        { label: 'Multigrain bread', keywords: ['mehrkornbrot', 'sonnenkernbrot', 'körner-krusti'], qty: '4 slices' },
        eggs('2'),
        oil('1 tbsp'),
        saltPepper,
      ],
      steps: [
        'Toast the bread. Mash the avocado roughly with salt and pepper and slice the radishes thinly.',
        'Fry the eggs in the oil until the whites are set and the yolks still runny.',
        'Spread the avocado on the toast, top with the radishes and an egg each, and grind over more pepper.',
      ],
    },
    {
      id: 'edeka-center-penny-seelachs-selleriepueree',
      title: 'Pollock with Celeriac Mash & Brown Butter',
      summary: 'Golden pan-fried pollock fillets on a silky celeriac-and-potato mash, spooned over with nutty brown butter and spring onions.',
      servings: 3,
      timeMinutes: 40,
      tags: ['pescatarian', 'german', 'dinner'],
      ingredients: [
        { label: 'Pollock fillets', keywords: ['seelachsfilet', 'seelachs-filet'], qty: '450 g', exclude: ['schlemmer', 'panier', 'backfisch'] },
        { label: 'Celeriac', keywords: ['knollensellerie', 'sellerie'], qty: '½ (about 500 g)', exclude: ['salat', 'saft'] },
        { label: 'Potatoes', keywords: ['kartoffeln'], qty: '400 g', exclude: POTATO_EXCLUDE },
        SPRING_ONIONS,
        butter('4 tbsp'),
        milk('100 ml'),
        flour('2 tbsp'),
        oil('1 tbsp'),
        saltPepper,
      ],
      steps: [
        'Peel and cube the celeriac and potatoes and boil them together in salted water for 20 minutes; drain and mash with the warm milk and 1 tbsp butter.',
        'Season the fish, dust it in flour and fry in the oil with 1 tbsp butter for 3 minutes a side.',
        'Brown the remaining butter in a small pan until it smells nutty, then serve the fish on the mash with the butter spooned over and the spring onions scattered on top.',
      ],
    },
    {
      id: 'penny-rewe-haehnchen-geschnetzeltes-spaetzle',
      title: 'Creamy Chicken Geschnetzeltes with Leeks & Spätzle',
      summary: 'Strips of chicken and leek simmered in a quick cream sauce, Zurich-style, served over buttery egg spätzle.',
      servings: 3,
      timeMinutes: 30,
      tags: ['meat', 'swiss', 'dinner'],
      ingredients: [
        { label: 'Chicken strips', keywords: ['hähnchen-geschnetzeltes', 'geschnetzeltes'], qty: '500 g', exclude: ['vegan', 'veggie', 'gyros'] },
        LEEKS,
        { label: 'Cream', keywords: ['schlagsahne', 'kochsahne'], qty: '200 ml', exclude: ['vegan', 'spray'] },
        { label: 'Egg spätzle', keywords: ['spätzle'], qty: '300 g', exclude: ['käsespätzle'] },
        onion('1'),
        butter('2 tbsp'),
        flour('1 tbsp'),
        oil('1 tbsp'),
        saltPepper,
      ],
      steps: [
        'Cook the spätzle as the pack says, drain and toss with 1 tbsp butter.',
        'Sear the chicken in the oil over high heat until golden and set aside; soften the onion and sliced leeks in the remaining butter for 6 minutes.',
        'Dust with the flour, stir in the cream and 100 ml water and simmer 3 minutes, then return the chicken to heat through; season and serve over the spätzle.',
      ],
    },
    {
      id: 'edeka-penny-brotzeit-bergkaese-schinken',
      title: 'German Brotzeit Board with Mountain Cheese & Ham',
      summary: 'A proper German cold lunch: rye rolls with butter, sliced ham and mountain cheese, crunchy Spreewald gherkins and cucumber.',
      servings: 2,
      timeMinutes: 10,
      tags: ['meat', 'german', 'lunch'],
      ingredients: [
        { label: 'Rye rolls', keywords: ['roggenbrötchen'], qty: '4' },
        { label: 'Cooked ham', keywords: ['mühlenschinken', 'kochschinken'], qty: '100 g', exclude: ['vegan', 'vegetarisch', 'veggie'] },
        MOUNTAIN_CHEESE('150 g'),
        { label: 'Spreewald gherkins', keywords: ['spreelinge', 'gewürzgurken'], qty: '1 jar' },
        CUCUMBER,
        butter('2 tbsp'),
        saltPepper,
      ],
      steps: [
        'Warm the rolls briefly in the oven, then split and butter them.',
        'Slice the cheese and cucumber and drain the gherkins.',
        'Lay everything out on a board with the ham and let everyone build their own rolls.',
      ],
    },
  ],
};
