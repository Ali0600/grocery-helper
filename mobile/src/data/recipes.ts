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
  exclude: ['lauchzwiebel', 'blumenzwiebel', 'zwiebelmettwurst', 'röstzwiebel', 'baguette', 'ciabatta', 'zwiebelbrot', 'schinkenzwiebelmett'],
});
const garlic = (qty: string): RecipeIngredient => ({
  label: 'Garlic',
  keywords: ['knoblauch'],
  qty,
  staple: true,
  exclude: ['wurst', 'baguette', 'butter', 'creme', 'sauce', 'garnelen', 'pizzabrot'],
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
  exclude: ['buttermilch', 'erdnussbutter', 'peanut butter', 'butterkäse', 'butterkeks', 'knoblauchbutter', 'kräuterbutter', 'butterfly', 'fassbutter', 'brotaufstrich', 'croissant', 'baguette', 'kuchen', 'rama'],
});
const flour = (qty: string): RecipeIngredient => ({
  label: 'Flour',
  keywords: ['weizenmehl', 'dinkelmehl', 'mehl'],
  qty,
  staple: true,
  exclude: ['mehlschwitze', 'semmelmehl', 'eierkuchenmehl'],
});
const milk = (qty: string): RecipeIngredient => ({
  label: 'Milk',
  keywords: ['haltbare milch', 'frische milch', 'vollmilch', 'landmilch'],
  qty,
  staple: true,
  exclude: ['milchreis', 'milchschnitte', 'kokosnussmilch', 'buttermilch', 'kondensmilch', 'kaffee-milch', 'müllermilch'],
});
const sugar = (qty: string): RecipeIngredient => ({
  label: 'Sugar',
  keywords: ['zucker'],
  qty,
  staple: true,
  exclude: ['zuckermais', 'zuckermelone', 'puderzucker', 'zuckerwatte', 'zuckerzusatz', 'cola', 'zero', 'zuckerfrei'],
});
const eggs = (qty: string): RecipeIngredient => ({
  label: 'Eggs',
  keywords: ['eier'],
  qty,
  staple: true,
  exclude: ['eierlikör', 'eiersalat', 'eierkuchen', 'eierkocher', 'eiernudeln', 'dessert-ei', 'puddingdessert', 'tagliatelle'],
});
const rice = (qty: string): RecipeIngredient => ({
  label: 'Rice',
  keywords: ['basmati', 'jasminreis', 'langkornreis', 'express-reis'],
  qty,
  staple: true,
  exclude: ['milchreis', 'waffel', 'snack'],
});
const pasta = (qty: string, label = 'Pasta'): RecipeIngredient => ({
  label,
  keywords: ['spaghetti', 'teigwaren', 'nudeln', 'pasta'],
  qty,
  staple: true,
  exclude: ['sauce', 'fix', 'pastasauce', 'carbonara', 'instantnudel', 'nudel snack', 'alfredo', 'dampfnudeln', 'bolognese', 'eishörnchen', 'cup', 'terrine', 'magic asia', 'pesto', 'pasta pot', 'bowl', 'glasnudeln', 'bratnudeln', 'nudelsuppe'],
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

// 'marzipan': Penny's "Marzipankartoffeln" are sweets filed under vegetables.
const POTATO_EXCLUDE = ['süßkartoffel', 'rösti', 'chips', 'salat', 'puffer', 'reibekuchen', 'marzipan', 'bratkartoffel', 'auflauf', 'brot'];
const LEMON_EXCLUDE = ['saft', 'limo', 'tee', 'kuchen', 'eis'];
const ROCKET: RecipeIngredient = { label: 'Rocket', keywords: ['rucola'], qty: '1 bag', exclude: ['pesto', 'pizza'] };

export const RECIPES: RecipesData = {
  generatedFor: '10115',
  generatedAt: '2026-10-11',
  recipes: [
    // ---- single store: ALDI ----
    {
      id: 'aldi-frikadellen-apfelrotkohl-kartoffeln',
      title: 'Beef Frikadellen with Apple Red Cabbage & Potatoes',
      summary: 'Juicy pan-fried beef patties with plenty of onion, a pot of apple red cabbage and buttery boiled potatoes — Sunday lunch on a weeknight.',
      servings: 4,
      timeMinutes: 45,
      tags: ['meat', 'german', 'dinner'],
      ingredients: [
        { label: 'Minced beef', keywords: ['rinderhack', 'rinder-hack'], qty: '600 g', exclude: ['vegan', 'burger'] },
        { label: 'Apple red cabbage', keywords: ['rotkohl'], qty: '1 jar' },
        { label: 'Potatoes', keywords: ['kartoffeln'], qty: '1 kg', exclude: POTATO_EXCLUDE },
        onion('2', 'Onions'),
        eggs('1'),
        flour('2 tbsp'),
        butter('2 tbsp'),
        oil('3 tbsp'),
        saltPepper,
      ],
      steps: [
        'Grate one onion into the beef with the egg, flour, salt and plenty of pepper; mix well with wet hands and shape eight flat patties.',
        'Boil the potatoes in salted water for 20 minutes; meanwhile warm the red cabbage with the second onion, diced and softened in butter.',
        'Fry the patties in hot oil for 4–5 minutes a side until deeply browned; toss the drained potatoes in the pan juices and serve together.',
      ],
    },
    {
      id: 'aldi-hokkaido-aubergine-hirtenkaese',
      title: 'Roast Hokkaido, Aubergine & Mushrooms with Greek White Cheese',
      summary: 'Wedges of unpeeled Hokkaido and aubergine roasted with garlic until caramelised, mushrooms thrown in at the end and salty white cheese crumbled over hot.',
      servings: 3,
      timeMinutes: 45,
      tags: ['vegetarian', 'greek', 'dinner'],
      ingredients: [
        { label: 'Hokkaido pumpkin', keywords: ['hokkaido'], qty: '1 small' },
        { label: 'Aubergine', keywords: ['aubergine'], qty: '1', exclude: ['creme', 'paste', 'deko'] },
        { label: 'Mushrooms', keywords: ['champignons'], qty: '250 g', exclude: ['creme', 'suppe', 'sauce'] },
        { label: 'Greek white cheese', keywords: ['hirtenkäse'], qty: '200 g' },
        garlic('4 cloves'),
        onion('1', 'Red onion'),
        oil('4 tbsp', 'Olive oil'),
        saltPepper,
      ],
      steps: [
        'Heat the oven to 220 °C. Seed the pumpkin and cut it into wedges (no need to peel), cube the aubergine and cut the onion into eighths.',
        'Toss everything with the oil, crushed garlic, salt and pepper on a tray and roast for 25 minutes; add the halved mushrooms and roast 10 more.',
        'Crumble the cheese over while the vegetables are still hot and serve with the tray juices spooned on top.',
      ],
    },

    // ---- single store: dm (clearance only — one cookable line each, so both lean on staples) ----
    {
      id: 'dm-kuerbiscreme-risotto',
      title: 'Pumpkin Cream Risotto with Garlic Oil',
      summary: 'A plain risotto made glossy at the end with a jar of pumpkin-and-olive-oil cream, finished with crisp garlic slices and their oil.',
      servings: 2,
      timeMinutes: 35,
      tags: ['vegan', 'italian', 'dinner'],
      ingredients: [
        { label: 'Pumpkin cream', keywords: ['kürbiscreme'], qty: '180 g' },
        {
          label: 'Risotto rice',
          keywords: ['risotto', 'arborio', 'rundkornreis'],
          qty: '200 g',
          staple: true,
          exclude: ['milchreis', 'fertig'],
        },
        onion('1'),
        garlic('4 cloves'),
        oil('4 tbsp', 'Olive oil'),
        saltPepper,
      ],
      steps: [
        'Slice the garlic thinly and warm it in the oil from cold, lifting it out when pale gold; keep the oil.',
        'Soften the diced onion in half the oil, stir in the rice until it turns translucent at the edges, then add hot salted water a ladle at a time, stirring, for about 18 minutes.',
        'Off the heat, beat in the pumpkin cream until the rice flows like lava, season, and serve with the garlic chips and the rest of the oil spooned over.',
      ],
    },
    {
      id: 'dm-pfannkuchen-fruechtetee-sirup',
      title: 'Pancakes with Cranberry-Strawberry Tea Syrup',
      summary: 'Thick German pancakes cooked in butter, with a ruby syrup of berry fruit tea boiled down with sugar poured over at the table.',
      servings: 4,
      timeMinutes: 30,
      tags: ['vegetarian', 'german', 'breakfast'],
      ingredients: [
        { label: 'Berry fruit tea', keywords: ['früchtetee'], qty: '3 tbsp loose' },
        flour('250 g'),
        milk('400 ml'),
        eggs('3'),
        sugar('6 tbsp'),
        butter('3 tbsp'),
        salt,
      ],
      steps: [
        'Steep the tea in 250 ml of boiling water for 10 minutes, strain it hard, and boil it with four spoons of sugar until it thickens to a syrup.',
        'Whisk the flour, milk, eggs, the rest of the sugar and a pinch of salt into a smooth batter and let it rest 10 minutes.',
        'Fry ladlefuls in butter over medium heat, 2 minutes a side, until golden and puffed; stack them and pour the syrup over.',
      ],
    },

    // ---- single store: EDEKA ----
    {
      id: 'edeka-pasta-blattspinat-champignons-feta',
      title: 'Creamy Pasta with Spinach, Mushrooms & Feta',
      summary: 'Browned mushrooms and wilted spinach in a quick cream sauce, tossed through pasta and finished with crumbled feta for salt and tang.',
      servings: 3,
      timeMinutes: 25,
      tags: ['vegetarian', 'mediterranean', 'lunch'],
      ingredients: [
        { label: 'Leaf spinach', keywords: ['blattspinat'], qty: '200 g', exclude: ['auflauf', 'rahm', 'börek'] },
        { label: 'Mushrooms', keywords: ['champignons'], qty: '250 g', exclude: ['creme', 'suppe', 'sauce'] },
        { label: 'Whipping cream', keywords: ['schlagsahne'], qty: '200 ml' },
        { label: 'Feta', keywords: ['feta'], qty: '150 g' },
        pasta('300 g'),
        garlic('2 cloves'),
        oil('2 tbsp'),
        saltPepper,
      ],
      steps: [
        'Boil the pasta in well-salted water. Meanwhile brown the sliced mushrooms hard in the oil, then add the sliced garlic for a minute.',
        'Pour in the cream, let it bubble for 2 minutes, then stir in the spinach a handful at a time until wilted.',
        'Toss the drained pasta through the sauce with a splash of its cooking water, season with pepper and crumble the feta over.',
      ],
    },
    {
      id: 'edeka-seelachs-gurkenjoghurt-reis',
      title: 'Butter-Fried Pollock with Cucumber Yoghurt & Rice',
      summary: 'Pollock fillets fried golden in butter, served on rice with a cool, garlicky cucumber yoghurt — a light weeknight fish plate.',
      servings: 2,
      timeMinutes: 25,
      tags: ['pescatarian', 'scandinavian', 'dinner'],
      ingredients: [
        { label: 'Pollock fillet', keywords: ['seelachs'], qty: '300 g', exclude: ['schnitzel', 'paniert', 'salat'] },
        { label: 'Cucumber', keywords: ['salatgurke'], qty: '1' },
        { label: 'Natural yoghurt', keywords: ['naturjoghurt'], qty: '250 g' },
        rice('150 g'),
        butter('2 tbsp'),
        flour('2 tbsp'),
        garlic('1 clove'),
        saltPepper,
      ],
      steps: [
        'Cook the rice. Coarsely grate the cucumber, squeeze it dry, and stir it into the yoghurt with the crushed garlic and a pinch of salt.',
        'Pat the fish dry, season it and dust it lightly in flour.',
        'Fry in foaming butter for 3 minutes a side until golden and just flaking; serve on the rice with the cucumber yoghurt alongside.',
      ],
    },

    // ---- single store: E center ----
    {
      id: 'edeka-center-hokkaido-ingwer-suppe',
      title: 'Hokkaido & Ginger Soup with Soy',
      summary: 'A velvety pumpkin and carrot soup with a good hit of fresh ginger, seasoned with soy sauce instead of salt for depth.',
      servings: 4,
      timeMinutes: 40,
      tags: ['vegan', 'asian', 'lunch'],
      ingredients: [
        { label: 'Hokkaido pumpkin', keywords: ['hokkaido'], qty: '1 (about 1 kg)' },
        { label: 'Fresh ginger', keywords: ['ingwer'], qty: '1 thumb', exclude: ['shot', 'tee', 'getränk', 'keks', 'bonbon', 'kaugummi'] },
        { label: 'Soy sauce', keywords: ['sojasauce', 'sojasoße'], qty: '3 tbsp' },
        carrots('2'),
        onion('1'),
        garlic('2 cloves'),
        oil('2 tbsp'),
      ],
      steps: [
        'Soften the chopped onion, garlic and grated ginger in the oil for 5 minutes.',
        'Add the seeded, cubed pumpkin (skin on) and sliced carrots, cover with about 1 litre of water and simmer 20 minutes until soft.',
        'Blend until smooth, season with the soy sauce, and thin with a little water if it is too thick to pour.',
      ],
    },
    {
      id: 'edeka-center-haehnchenkeulen-tomaten-rucola',
      title: 'Roast Chicken Legs with Vine Tomatoes & Rocket',
      summary: 'Crisp-skinned chicken legs roasted over vine tomatoes and onions that collapse into a sauce, piled with peppery rocket to serve.',
      servings: 4,
      timeMinutes: 60,
      tags: ['meat', 'italian', 'dinner'],
      ingredients: [
        { label: 'Chicken legs', keywords: ['hähnchenkeule'], qty: '4' },
        { label: 'Vine tomatoes', keywords: ['rispentomaten'], qty: '500 g' },
        ROCKET,
        onion('2', 'Red onions'),
        garlic('6 cloves'),
        oil('3 tbsp', 'Olive oil'),
        saltPepper,
      ],
      steps: [
        'Heat the oven to 210 °C. Scatter the tomatoes on their vines, onion wedges and whole garlic cloves in a roasting dish with half the oil.',
        'Rub the chicken legs with the rest of the oil, salt and pepper and sit them skin-up on top.',
        'Roast 45–50 minutes until the skin is crisp and the juices run clear; squash the tomatoes into the pan juices and serve with the rocket on top.',
      ],
    },

    // ---- single store: Lidl ----
    {
      id: 'lidl-kichererbsen-chorizo-spinat',
      title: 'Chickpea & Chorizo Stew with Spinach',
      summary: 'Spanish-style stew: chorizo fried until it bleeds its paprika oil, then chickpeas, sweet green peppers and a pile of spinach simmered in it.',
      servings: 3,
      timeMinutes: 30,
      tags: ['meat', 'spanish', 'dinner'],
      ingredients: [
        { label: 'Chorizo', keywords: ['chorizo'], qty: '200 g' },
        { label: 'Chickpeas', keywords: ['kichererbsen'], qty: '1 jar' },
        { label: 'Pointed green pepper', keywords: ['spitzpaprika'], qty: '2' },
        { label: 'Spinach', keywords: ['spinat'], qty: '200 g', exclude: ['rahm', 'auflauf', 'börek', 'blatt-spinat'] },
        onion('1'),
        garlic('2 cloves'),
        oil('1 tbsp', 'Olive oil'),
        saltPepper,
      ],
      steps: [
        'Fry the sliced chorizo in the oil until it crisps and releases its red fat, then add the onion, garlic and sliced peppers and soften for 5 minutes.',
        'Add the drained chickpeas and a cup of water and simmer 10 minutes, crushing a few chickpeas to thicken the broth.',
        'Stir in the spinach until it wilts, season and serve with bread.',
      ],
    },
    {
      id: 'lidl-knoblauchgarnelen-zucchini-zitrone',
      title: 'Garlic Prawns with Zucchini, Lemon & Rice',
      summary: 'Prawns flashed in garlicky olive oil with ribbons of zucchini, sharpened with lemon zest and juice and spooned over rice.',
      servings: 2,
      timeMinutes: 25,
      tags: ['pescatarian', 'mediterranean', 'dinner'],
      ingredients: [
        { label: 'Prawns', keywords: ['garnelen'], qty: '250 g', exclude: ['tempura', 'salat'] },
        { label: 'Zucchini', keywords: ['zucchini'], qty: '2', exclude: ['saaten'] },
        { label: 'Lemon', keywords: ['zitronen'], qty: '1', exclude: LEMON_EXCLUDE },
        rice('150 g'),
        garlic('4 cloves'),
        oil('4 tbsp', 'Olive oil'),
        saltPepper,
      ],
      steps: [
        'Cook the rice. Shave the zucchini into ribbons with a peeler and fry them in half the oil for 3 minutes; set aside.',
        'Warm the sliced garlic in the rest of the oil, add the prawns and cook 2 minutes a side until pink.',
        'Return the zucchini, add the lemon zest and juice, season, and spoon everything with its oil over the rice.',
      ],
    },

    // ---- single store: Penny ----
    {
      id: 'penny-haehnchen-kokos-curry-aubergine',
      title: 'Chicken & Aubergine Coconut Curry',
      summary: 'Strips of chicken and soft aubergine simmered in coconut milk with cherry tomatoes, garlic and plenty of black pepper, served over rice.',
      servings: 3,
      timeMinutes: 35,
      tags: ['meat', 'thai', 'dinner'],
      ingredients: [
        { label: 'Chicken strips', keywords: ['hähnchen-geschnetzeltes', 'hähnchengeschnetzeltes'], qty: '400 g' },
        { label: 'Coconut milk', keywords: ['kokosmilch'], qty: '400 ml', exclude: ['drink'] },
        { label: 'Aubergine', keywords: ['aubergine'], qty: '1', exclude: ['creme', 'paste', 'deko'] },
        { label: 'Cherry tomatoes', keywords: ['romatomaten', 'cherrytomaten', 'cocktailtomaten'], qty: '250 g' },
        rice('200 g'),
        onion('1'),
        garlic('3 cloves'),
        oil('2 tbsp'),
        saltPepper,
      ],
      steps: [
        'Cook the rice. Fry the cubed aubergine in the oil until golden on several sides, then add the onion and garlic and soften.',
        'Add the chicken and cook until it loses its pink, then pour in the coconut milk and the halved tomatoes.',
        'Simmer 12 minutes until the chicken is cooked and the sauce has thickened; season generously with salt and black pepper and serve over the rice.',
      ],
    },
    {
      id: 'penny-knaeckebrot-avocado-huettenkaese',
      title: 'Crispbread with Avocado, Cottage Cheese & Tomatoes',
      summary: 'Rye crispbread loaded with smashed avocado, a spoon of cottage cheese and halved cherry tomatoes — a five-minute breakfast.',
      servings: 2,
      timeMinutes: 10,
      tags: ['vegetarian', 'scandinavian', 'breakfast'],
      ingredients: [
        { label: 'Rye crispbread', keywords: ['knäckebr'], qty: '6 slices' },
        { label: 'Avocado', keywords: ['avocado'], qty: '1', exclude: ['creme', 'öl', 'dip'] },
        { label: 'Cottage cheese', keywords: ['körniger frischkäse'], qty: '200 g' },
        { label: 'Cherry tomatoes', keywords: ['romatomaten', 'cherrytomaten', 'cocktailtomaten'], qty: '150 g' },
        saltPepper,
      ],
      steps: [
        'Mash the avocado roughly with a fork and season it with salt and pepper.',
        'Spread it on the crispbread, top with a spoon of cottage cheese and the halved tomatoes.',
        'Finish with more black pepper and eat straight away, before the crispbread softens.',
      ],
    },

    // ---- single store: REWE ----
    {
      id: 'rewe-lachssteak-suesskartoffel-bohnen',
      title: 'Salmon Steaks with Sweet Potato & Green Beans',
      summary: 'Pan-roasted salmon steaks with crisp sweet potato wedges and buttery green beans, a herb quark on the side.',
      servings: 2,
      timeMinutes: 40,
      tags: ['pescatarian', 'international', 'dinner'],
      ingredients: [
        { label: 'Salmon steaks', keywords: ['lachs-steak', 'lachssteak'], qty: '2', exclude: ['vegan', 'kasseler'] },
        { label: 'Sweet potatoes', keywords: ['süßkartoffel'], qty: '500 g', exclude: ['chips', 'pommes'] },
        { label: 'Green beans', keywords: ['prinzessbohnen', 'grüne bohnen'], qty: '250 g', exclude: ['salat'] },
        { label: 'Herb quark', keywords: ['gewürzquark', 'kräuterquark'], qty: '1 tub' },
        oil('3 tbsp'),
        butter('1 tbsp'),
        saltPepper,
      ],
      steps: [
        'Heat the oven to 220 °C. Cut the sweet potatoes into wedges, toss with 2 tbsp oil and salt, and roast 30 minutes, turning once.',
        'Blanch the beans 4 minutes in salted water, drain, and toss with the butter.',
        'Season the salmon and fry it in the remaining oil for 3–4 minutes a side; serve with the wedges, beans and a spoon of herb quark.',
      ],
    },
    {
      id: 'rewe-rote-bete-kohlrabi-grapefruit-salat',
      title: 'Beetroot, Kohlrabi & Grapefruit Salad',
      summary: 'Crunchy matchsticks of kohlrabi and beetroot tossed with grapefruit segments and rocket in a sharp citrus dressing.',
      servings: 2,
      timeMinutes: 20,
      tags: ['vegan', 'european', 'lunch'],
      ingredients: [
        { label: 'Cooked beetroot', keywords: ['rote bete'], qty: '300 g', exclude: ['saft', 'chips'] },
        { label: 'Kohlrabi', keywords: ['kohlrabi'], qty: '1' },
        { label: 'Grapefruit', keywords: ['grapefruit'], qty: '1', exclude: ['saft', 'limo'] },
        ROCKET,
        oil('3 tbsp', 'Olive oil'),
        sugar('1 pinch'),
        saltPepper,
      ],
      steps: [
        'Peel the kohlrabi and cut it and the beetroot into thin matchsticks.',
        'Segment the grapefruit over a bowl to catch the juice, then whisk the juice with the oil, a pinch of sugar, salt and pepper.',
        'Toss the vegetables and segments in the dressing and fold through the rocket just before serving.',
      ],
    },

    // ---- two stores ----
    {
      id: 'aldi-lidl-bacon-pilze-spinat-fruehstueck',
      title: 'Bacon, Mushroom & Spinach Breakfast Skillet',
      summary: 'Crisp bacon, browned mushrooms and wilted spinach with eggs cracked into the pan and wholegrain rolls to mop it up.',
      servings: 2,
      timeMinutes: 20,
      tags: ['meat', 'british', 'breakfast'],
      ingredients: [
        { label: 'Bacon', keywords: ['bacon'], qty: '150 g' },
        { label: 'Mushrooms', keywords: ['champignons'], qty: '250 g', exclude: ['creme', 'suppe', 'sauce'] },
        { label: 'Spinach', keywords: ['spinat'], qty: '150 g', exclude: ['rahm', 'auflauf', 'börek', 'blatt-spinat'] },
        { label: 'Wholegrain rolls', keywords: ['krusti'], qty: '2' },
        eggs('4'),
        butter('1 tbsp'),
        saltPepper,
      ],
      steps: [
        'Fry the bacon in a large pan until crisp and lift it out, leaving the fat behind.',
        'Brown the sliced mushrooms in the bacon fat with the butter, then stir in the spinach until it just wilts.',
        'Make four hollows, crack in the eggs, cover and cook 3–4 minutes until the whites set; return the bacon and serve with the warmed rolls.',
      ],
    },
    {
      id: 'edeka-rewe-kaesespaetzle',
      title: 'Käsespätzle with Crispy Onions & Chives',
      summary: 'Alpine cheese noodles layered with mountain cheese and Emmental until stringy, under a heap of slow-fried onions and fresh chives.',
      servings: 3,
      timeMinutes: 35,
      tags: ['vegetarian', 'german', 'lunch'],
      ingredients: [
        { label: 'Spätzle', keywords: ['spätzle'], qty: '500 g' },
        { label: 'Mountain cheese', keywords: ['bergkäse'], qty: '150 g' },
        { label: 'Emmental', keywords: ['emmentaler'], qty: '150 g' },
        { label: 'Chives', keywords: ['schnittlauch'], qty: '1 bunch' },
        onion('3', 'Onions'),
        butter('3 tbsp'),
        saltPepper,
      ],
      steps: [
        'Slice the onions into thin rings and fry them slowly in 2 tbsp butter for 15–20 minutes until deep golden and crisp at the edges.',
        'Heat the spätzle through in boiling salted water and drain, keeping a splash of the water.',
        'Layer the spätzle with both grated cheeses in a hot buttered pan, stirring until stringy (add a little cooking water if dry); pile the onions and chives on top and season with pepper.',
      ],
    },
    {
      id: 'penny-edeka-center-matjes-hausfrauenart',
      title: 'Matjes Herring "Hausfrauen Art" with New Potatoes',
      summary: 'Mild matjes fillets in a creamy yoghurt sauce with apple, cucumber and onion, served with buttered baby potatoes.',
      servings: 2,
      timeMinutes: 30,
      tags: ['pescatarian', 'german', 'dinner'],
      ingredients: [
        { label: 'Matjes fillets', keywords: ['matjes'], qty: '4', exclude: ['honig', 'senf', 'salat', 'heringstopf'] },
        { label: 'Baby potatoes', keywords: ['kartoffeln'], qty: '600 g', exclude: POTATO_EXCLUDE },
        { label: 'Apple', keywords: ['äpfel'], qty: '1', exclude: ['rotkohl', 'saft', 'mus', 'tasche', 'chips', 'kuchen', 'strudel', 'essig', 'schorle'] },
        { label: 'Cucumber', keywords: ['salatgurke'], qty: '½' },
        { label: 'Natural yoghurt', keywords: ['naturjoghurt'], qty: '250 g' },
        onion('1', 'Red onion'),
        butter('1 tbsp'),
        sugar('1 pinch'),
        saltPepper,
      ],
      steps: [
        'Boil the potatoes in their skins for about 20 minutes and toss them in the butter.',
        'Stir the yoghurt with a pinch of sugar, salt and pepper, then fold in the diced apple, cucumber and finely sliced onion.',
        'Cut the matjes into bite-size pieces, fold them into the sauce, let it stand 10 minutes and serve with the warm potatoes.',
      ],
    },
    {
      id: 'lidl-rewe-suesskartoffel-kichererbsen-bowl',
      title: 'Roast Sweet Potato & Crispy Chickpea Bowl with Hummus',
      summary: 'Roasted sweet potato and chickpeas crisped in the oven, on rocket with a big spoon of hummus and a lemon-oil dressing.',
      servings: 2,
      timeMinutes: 35,
      tags: ['vegan', 'middle-eastern', 'lunch'],
      ingredients: [
        { label: 'Sweet potatoes', keywords: ['süßkartoffel'], qty: '500 g', exclude: ['chips', 'pommes'] },
        { label: 'Chickpeas', keywords: ['kichererbsen'], qty: '1 jar' },
        { label: 'Hummus', keywords: ['hummus'], qty: '150 g' },
        { label: 'Lemon', keywords: ['zitronen'], qty: '1', exclude: LEMON_EXCLUDE },
        ROCKET,
        oil('4 tbsp', 'Olive oil'),
        saltPepper,
      ],
      steps: [
        'Heat the oven to 220 °C. Cube the sweet potatoes, pat the drained chickpeas dry, toss both with 2 tbsp oil and salt and roast 25 minutes until crisp.',
        'Whisk the rest of the oil with the lemon juice, salt and pepper.',
        'Pile the rocket into bowls, top with the hot sweet potato and chickpeas, add a spoon of hummus and pour the dressing over.',
      ],
    },
    {
      id: 'aldi-edeka-french-toast-zwetschgen',
      title: 'French Toast with Spiced Plum Compote',
      summary: 'Thick toast soaked in sweet egg custard and fried in butter, with a quick compote of fresh plums bubbled down with sugar.',
      servings: 2,
      timeMinutes: 25,
      tags: ['vegetarian', 'french', 'breakfast'],
      ingredients: [
        { label: 'Fresh plums', keywords: ['zwetschgen', 'pflaumen'], qty: '400 g', exclude: ['mus', 'kuchen', 'tomaten', 'saft'] },
        { label: 'Toast bread', keywords: ['toastbrot'], qty: '6 slices' },
        eggs('3'),
        milk('150 ml'),
        sugar('4 tbsp'),
        butter('2 tbsp'),
      ],
      steps: [
        'Halve and stone the plums and simmer them with 3 tbsp sugar and a splash of water for 10 minutes until they collapse into a compote.',
        'Whisk the eggs, milk and the remaining sugar; soak each slice of toast for a few seconds on each side.',
        'Fry the slices in butter over medium heat, 2–3 minutes a side, until golden; serve hot with the plum compote spooned over.',
      ],
    },
  ],
};
