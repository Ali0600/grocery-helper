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
  exclude: ['lauchzwiebel', 'blumenzwiebel', 'zwiebelmettwurst', 'röstzwiebel', 'baguette', 'ciabatta'],
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
  exclude: ['mehlschwitze', 'semmelmehl'],
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
  exclude: ['zuckermais', 'zuckermelone', 'puderzucker', 'zuckerwatte', 'zuckerzusatz', 'cola', 'zero'],
});
const eggs = (qty: string): RecipeIngredient => ({
  label: 'Eggs',
  keywords: ['eier'],
  qty,
  staple: true,
  exclude: ['eierlikör', 'eiersalat', 'eierkuchen', 'eierkocher', 'eiernudeln'],
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
  exclude: ['sauce', 'fix', 'pastasauce', 'carbonara', 'instantnudel', 'nudel snack', 'alfredo', 'dampfnudeln', 'bolognese', 'eishörnchen', 'cup', 'terrine', 'magic asia', 'pesto'],
});
const saltPepper: RecipeIngredient = { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true };
const salt: RecipeIngredient = { label: 'Salt', keywords: ['speisesalz', 'meersalz'], staple: true };

const POTATO_EXCLUDE = ['süßkartoffel', 'rösti', 'chips', 'salat', 'puffer', 'reibekuchen'];
const LEMON_EXCLUDE = ['saft', 'limo', 'tee', 'kuchen', 'eis'];

export const RECIPES: RecipesData = {
  generatedFor: '10115',
  generatedAt: '2026-10-04',
  recipes: [
    // ---- single store: ALDI ----
    {
      id: 'aldi-rinderrouladen-gewuerzgurken-kartoffeln',
      title: 'Beef Rouladen with Pickles, Carrots & Potatoes',
      summary: 'Thin beef slices rolled around pickle and onion, browned and braised until tender, the gravy finished with cream, potatoes and glazed carrots alongside.',
      servings: 4,
      timeMinutes: 120,
      tags: ['meat', 'german', 'dinner'],
      ingredients: [
        { label: 'Beef rouladen', keywords: ['rinderrouladen'], qty: '4 slices' },
        { label: 'Gherkins', keywords: ['gewürzgurken'], qty: '4' },
        { label: 'Carrots', keywords: ['speisemöhren', 'möhren'], qty: '500 g', exclude: ['saft', 'kuchen', 'brei', 'krüstchen'] },
        { label: 'Potatoes', keywords: ['kartoffeln'], qty: '1 kg', exclude: POTATO_EXCLUDE },
        { label: 'Cooking cream', keywords: ['cremfine', 'cremefine'], qty: '100 ml' },
        onion('2', 'Onions'),
        flour('1 tbsp'),
        oil('3 tbsp'),
        saltPepper,
      ],
      steps: [
        'Season each slice, lay a quartered gherkin and a few onion strips across one end, roll it up tightly and pin it with a toothpick.',
        'Brown the rolls all over in hot oil, lift them out, soften the remaining onion in the pot, dust with flour, then return the meat with water to come halfway up and braise covered for 90 minutes, adding the carrots in chunks for the last 30.',
        'Boil the potatoes meanwhile; lift out the meat and carrots, stir the cream into the gravy, let it bubble until it coats a spoon and season it hard before serving.',
      ],
    },
    {
      id: 'aldi-ofenpasta-sanmarzano-bueffelmozzarella',
      title: 'Baked Pasta with San Marzano Tomatoes, Buffalo Mozzarella & Olives',
      summary: 'Pasta folded through a quick San Marzano sauce with olives, torn buffalo mozzarella melted over the top and a hard crust of grated Gran Moravia.',
      servings: 4,
      timeMinutes: 40,
      tags: ['vegetarian', 'italian', 'lunch'],
      ingredients: [
        { label: 'San Marzano tomatoes', keywords: ['san-marzano'], qty: '800 g' },
        { label: 'Buffalo mozzarella', keywords: ['büffelmozzarella', 'mozzarella'], qty: '250 g', exclude: ['stange', 'sticks', 'pizza'] },
        { label: 'Hard cheese', keywords: ['gran moravia', 'grana padano'], qty: '60 g' },
        { label: 'Olives', keywords: ['oliven'], qty: '100 g', exclude: ['brötchen', 'brot'] },
        pasta('400 g', 'Short pasta'),
        garlic('3 cloves'),
        oil('3 tbsp', 'Olive oil'),
        sugar('1 pinch'),
        saltPepper,
      ],
      steps: [
        'Warm the sliced garlic in the oil, crush in the tomatoes with a pinch of sugar and salt, and simmer 15 minutes until thick; stir in the halved olives.',
        'Boil the pasta 2 minutes short of the packet time, drain, and fold it through the sauce in a baking dish.',
        'Tear the mozzarella over, grate the hard cheese on top, and bake at 220 °C for 12–15 minutes until it bubbles and browns at the edges.',
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
      id: 'edeka-lachs-rahmporree-kartoffeln',
      title: 'Salmon on Creamy Leeks with Potatoes',
      summary: 'Salmon fillets steamed on a bed of buttery leeks stirred through with soured cream, boiled potatoes to catch the sauce.',
      servings: 2,
      timeMinutes: 35,
      tags: ['pescatarian', 'german', 'dinner'],
      ingredients: [
        { label: 'Salmon fillets', keywords: ['lachsfilet'], qty: '2', exclude: ['räucher', 'schinken', 'vegan', 'aufschnitt', 'gebraten'] },
        { label: 'Leeks', keywords: ['porree'], qty: '2' },
        { label: 'Potatoes', keywords: ['kartoffeln'], qty: '600 g', exclude: POTATO_EXCLUDE },
        { label: 'Soured cream (Schmand)', keywords: ['schmand'], qty: '200 g' },
        butter('2 tbsp'),
        saltPepper,
      ],
      steps: [
        'Boil the potatoes in salted water. Slice the leeks into rings, wash them well, and sweat them in the butter with a pinch of salt for 10 minutes until soft.',
        'Stir in the Schmand, lay the seasoned salmon on top, cover and cook on low heat for 8–10 minutes until the fish just flakes.',
        'Grind plenty of pepper over and serve the salmon on the leeks with the potatoes.',
      ],
    },
    {
      id: 'edeka-bircher-himbeeren-mango',
      title: 'Bircher Oats with Raspberries, Mango & Yoghurt',
      summary: 'Oats soaked overnight in milk and yoghurt, topped in the morning with raspberries and diced mango.',
      servings: 2,
      timeMinutes: 10,
      tags: ['vegetarian', 'swiss', 'breakfast'],
      ingredients: [
        { label: 'Rolled oats', keywords: ['haferflocken'], qty: '100 g' },
        { label: 'Yoghurt', keywords: ['joghurt'], qty: '250 g', exclude: ['frucht', 'drink', 'dessert', 'schoko'] },
        { label: 'Raspberries', keywords: ['himbeeren'], qty: '125 g', exclude: ['eis', 'joghurt', 'sirup'] },
        { label: 'Mango', keywords: ['mango'], qty: '1', exclude: ['curry', 'sauce', 'saft', 'chutney', 'lufterfrischer'] },
        milk('150 ml'),
        sugar('1 tbsp'),
      ],
      steps: [
        'Stir the oats with the milk, half the yoghurt and the sugar, cover and leave in the fridge overnight.',
        'In the morning loosen it with the rest of the yoghurt; peel and dice the mango.',
        'Spoon into bowls and pile the raspberries and mango on top, crushing a few berries so they bleed into the oats.',
      ],
    },

    // ---- single store: E center ----
    {
      id: 'edekacenter-chili-sin-carne-kidney-mais',
      title: 'Chili sin Carne with Kidney Beans & Sweetcorn',
      summary: 'Kidney beans and sweetcorn simmered in a garlicky passata base with plenty of onion, served over rice.',
      servings: 4,
      timeMinutes: 40,
      tags: ['vegan', 'mexican', 'dinner'],
      ingredients: [
        { label: 'Kidney beans', keywords: ['kidneybohnen', 'kidney'], qty: '2 tins' },
        { label: 'Passata', keywords: ['tomaten passiert', 'passierte'], qty: '500 g', exclude: ['ketchup'] },
        { label: 'Sweetcorn', keywords: ['sonnenmais', 'goldmais'], qty: '1 tin' },
        rice('300 g'),
        onion('2', 'Onions'),
        garlic('4 cloves'),
        oil('3 tbsp'),
        sugar('1 tsp'),
        saltPepper,
      ],
      steps: [
        'Soften the diced onions in the oil for 10 minutes, add the chopped garlic and plenty of black pepper and cook one minute more.',
        'Pour in the passata with the sugar and salt, add the drained beans and simmer 20 minutes uncovered until thick enough to hold a spoon line.',
        'Cook the rice; stir the drained sweetcorn into the chili for the last 5 minutes and serve it over the rice.',
      ],
    },
    {
      id: 'edekacenter-rumpsteak-pilze-brokkoli',
      title: 'Rump Steak with Garlic Mushrooms, Broccoli & Crushed Potatoes',
      summary: 'Rump steak seared hard and rested, brown mushrooms fried in the same pan with garlic butter, broccoli and crushed potatoes on the side.',
      servings: 2,
      timeMinutes: 35,
      tags: ['meat', 'french', 'dinner'],
      ingredients: [
        { label: 'Rump steak', keywords: ['rumpsteak'], qty: '2 steaks' },
        { label: 'Brown mushrooms', keywords: ['champignons'], qty: '250 g', exclude: ['creme', 'suppe', 'sauce'] },
        { label: 'Broccoli', keywords: ['brokkoli'], qty: '1 head' },
        { label: 'Potatoes', keywords: ['speisekartoffeln'], qty: '600 g', exclude: POTATO_EXCLUDE },
        butter('3 tbsp'),
        garlic('3 cloves'),
        oil('1 tbsp'),
        saltPepper,
      ],
      steps: [
        'Boil the potatoes until tender, drain, and crush them roughly with a spoon of butter and salt; boil the broccoli florets for 4 minutes.',
        'Salt the steaks and sear them in a smoking oiled pan, 2–3 minutes a side for medium-rare, then rest them on a warm plate.',
        'In the same pan fry the halved mushrooms until browned, add the rest of the butter and the sliced garlic for a minute, and spoon it all over the sliced steak.',
      ],
    },

    // ---- single store: Lidl ----
    {
      id: 'lidl-ratatouille-baguette',
      title: 'Ratatouille with Crusty Baguette',
      summary: 'Aubergine, zucchini and peppers browned in batches and stewed slowly in tomato and garlic, with warm baguette to mop it up.',
      servings: 4,
      timeMinutes: 60,
      tags: ['vegan', 'french', 'dinner'],
      ingredients: [
        { label: 'Aubergines', keywords: ['auberginen', 'aubergine'], qty: '2' },
        { label: 'Zucchini', keywords: ['zucchini'], qty: '2', exclude: ['saaten', 'chips'] },
        {
          label: 'Peppers',
          keywords: ['paprika'],
          qty: '3',
          exclude: ['salami', 'mortadella', 'lyoner', 'pastete', 'chips', 'gewürz', 'pulver', 'wurst', 'snack'],
        },
        { label: 'Tomatoes (tinned)', keywords: ['oro di parma', 'passierte', 'gehackte tomaten'], qty: '400 g', exclude: ['ketchup'] },
        { label: 'Baguette', keywords: ['bauernbaguette', 'baguette'], qty: '1', exclude: ['laugen', 'knoblauch', 'kräuter', 'walnuss'] },
        onion('2', 'Red onions'),
        garlic('4 cloves'),
        oil('6 tbsp', 'Olive oil'),
        saltPepper,
      ],
      steps: [
        'Cut the aubergines, zucchini and peppers into bite-size chunks and brown each vegetable separately in hot oil — crowding the pan steams them grey.',
        'Soften the sliced onions and garlic in the same pot, add the tomatoes, then return all the vegetables, salt well and simmer covered on low for 30 minutes.',
        'Uncover for the last 10 minutes so it thickens, season with lots of pepper and serve warm with the baguette.',
      ],
    },
    {
      id: 'lidl-schweinefilet-pfifferlinge-rahm',
      title: 'Pork Tenderloin with Chanterelle Cream & Tagliatelle',
      summary: 'Pork tenderloin medallions seared and rested, chanterelles fried with onion and finished with cream, ribbon pasta and a lamb\'s lettuce salad.',
      servings: 4,
      timeMinutes: 35,
      tags: ['meat', 'german', 'dinner'],
      ingredients: [
        { label: 'Pork tenderloin', keywords: ['schweinefilet'], qty: '600 g' },
        { label: 'Chanterelles', keywords: ['pfifferlinge'], qty: '250 g' },
        { label: 'Whipping cream', keywords: ['schlagsahne'], qty: '200 ml' },
        { label: "Lamb's lettuce", keywords: ['feldsalat'], qty: '150 g' },
        pasta('400 g', 'Tagliatelle'),
        onion('1'),
        butter('2 tbsp'),
        oil('3 tbsp'),
        saltPepper,
      ],
      steps: [
        'Cut the tenderloin into thick medallions, season, and sear in hot oil for 3 minutes a side; rest them on a warm plate while you make the sauce.',
        'Fry the cleaned chanterelles in the butter with the diced onion until their liquid has gone and they squeak, pour in the cream and the resting juices and let it bubble until it coats a spoon.',
        'Boil the pasta, toss it through the sauce, lay the pork on top, and dress the lettuce with oil and salt to serve alongside.',
      ],
    },

    // ---- single store: Penny ----
    {
      id: 'penny-spaghettikuerbis-pesto-grana',
      title: 'Roast Spaghetti Squash with Pesto & Grana Padano',
      summary: 'A spaghetti squash roasted until its flesh pulls into strands, tossed with pesto and grated Grana Padano, lamb\'s lettuce on the side.',
      servings: 2,
      timeMinutes: 55,
      tags: ['vegetarian', 'italian', 'lunch'],
      ingredients: [
        { label: 'Spaghetti squash', keywords: ['spaghettikürbis'], qty: '1' },
        { label: 'Pesto', keywords: ['pesto'], qty: '1 jar' },
        { label: 'Grana Padano', keywords: ['grana padano'], qty: '50 g' },
        { label: "Lamb's lettuce", keywords: ['feldsalat'], qty: '100 g' },
        oil('2 tbsp', 'Olive oil'),
        saltPepper,
      ],
      steps: [
        'Halve the squash lengthwise, scoop out the seeds, rub the cut sides with oil and salt and roast face-down at 200 °C for 40 minutes.',
        'Scrape the flesh out with a fork so it falls into strands, and toss it straight away with the pesto and most of the grated cheese.',
        'Pile it back into the shells, finish with the remaining cheese and black pepper, and serve with the lettuce dressed in oil and salt.',
      ],
    },
    {
      id: 'penny-haehnchenschenkel-hokkaido-zaziki',
      title: 'Lemon Chicken Drumsticks with Roast Hokkaido, Carrots & Tzatziki',
      summary: 'Drumsticks roasted on one tray with wedges of hokkaido and carrots, everything sharpened with lemon and garlic, cold tzatziki to dip.',
      servings: 4,
      timeMinutes: 55,
      tags: ['meat', 'greek', 'dinner'],
      ingredients: [
        { label: 'Chicken drumsticks', keywords: ['hähnchen-unterschenkel', 'unterschenkel'], qty: '1 kg', exclude: ['wiener'] },
        { label: 'Hokkaido squash', keywords: ['hokkaido'], qty: '1' },
        { label: 'Carrots', keywords: ['möhren'], qty: '500 g', exclude: ['saft', 'kuchen', 'brei', 'krüstchen'] },
        { label: 'Tzatziki', keywords: ['zaziki', 'tzatziki'], qty: '250 g' },
        { label: 'Lemons', keywords: ['zitronen'], qty: '2', exclude: LEMON_EXCLUDE },
        garlic('4 cloves'),
        oil('4 tbsp'),
        saltPepper,
      ],
      steps: [
        'Cut the squash (skin on) into wedges and the carrots into thick batons, toss with half the oil, the crushed garlic and salt, and spread them on a tray.',
        'Rub the drumsticks with the rest of the oil, the zest and juice of one lemon and plenty of salt, sit them on top of the vegetables and roast at 210 °C for 40 minutes, turning once.',
        'Serve with the second lemon in wedges and the tzatziki to dip.',
      ],
    },

    // ---- single store: REWE ----
    {
      id: 'rewe-zander-selleriepueree-radieschen',
      title: 'Pan-Fried Zander on Celeriac Mash with Radish Salad',
      summary: 'Pike-perch fillets fried skin-side down until crisp, served on a buttery celeriac and potato mash with a sharp salted radish salad.',
      servings: 2,
      timeMinutes: 40,
      tags: ['pescatarian', 'german', 'dinner'],
      ingredients: [
        { label: 'Zander fillets', keywords: ['zander'], qty: '2' },
        { label: 'Celeriac', keywords: ['knollensellerie', 'sellerie'], qty: '1 small' },
        { label: 'Potatoes', keywords: ['speisekartoffeln'], qty: '400 g', exclude: POTATO_EXCLUDE },
        { label: 'Radishes', keywords: ['radieschen'], qty: '1 bunch' },
        butter('3 tbsp'),
        milk('100 ml'),
        flour('1 tbsp'),
        oil('2 tbsp'),
        saltPepper,
      ],
      steps: [
        'Peel and dice the celeriac and potatoes and boil them together in salted water for 20 minutes, then mash with the warm milk and two spoons of butter.',
        'Slice the radishes thinly and toss them with a little oil and salt so they soften slightly.',
        'Pat the fish dry, dust the skin with flour, and fry skin-side down in oil and the last of the butter for 4 minutes until crisp, then 1 minute on the flesh; serve on the mash with the radishes.',
      ],
    },
    {
      id: 'rewe-butternut-ziegenkaese-pflaumen',
      title: 'Roast Butternut with Goat Cheese, Plums & Ciabatta',
      summary: 'Butternut squash roasted until caramelised, dark plums blistered on the same tray for the last ten minutes, crumbled goat cheese over and ciabatta alongside.',
      servings: 2,
      timeMinutes: 45,
      tags: ['vegetarian', 'french', 'lunch'],
      ingredients: [
        { label: 'Butternut squash', keywords: ['butternut'], qty: '1' },
        { label: 'Goat cheese', keywords: ['ziegenkäse'], qty: '150 g' },
        { label: 'Dark plums', keywords: ['pflaumen'], qty: '6', exclude: ['mus', 'kuchen', 'saft'] },
        { label: 'Ciabatta', keywords: ['ciabatta'], qty: '1 loaf' },
        oil('3 tbsp', 'Olive oil'),
        sugar('1 tsp'),
        saltPepper,
      ],
      steps: [
        'Peel the squash, cut it into chunks, toss with oil and salt, and roast at 200 °C for 25 minutes.',
        'Add the halved, stoned plums sprinkled with the sugar and roast another 10 minutes until they slump and bleed into the squash.',
        'Crumble the goat cheese over while it is hot, grind pepper on top, and serve with warm torn ciabatta.',
      ],
    },

    // ---- two stores ----
    {
      id: 'lidl-penny-quarkkeulchen-zwetschgen',
      title: 'Quark Pancakes (Quarkkeulchen) with Stewed Plums',
      summary: 'Saxon quark pancakes, soft inside and crisp-edged from the butter, served with plums stewed briefly with sugar until they collapse.',
      servings: 4,
      timeMinutes: 35,
      tags: ['vegetarian', 'german', 'breakfast'],
      ingredients: [
        { label: 'Quark', keywords: ['speisequark'], qty: '500 g' },
        { label: 'Plums', keywords: ['zwetschgen'], qty: '500 g', exclude: ['mus', 'kuchen', 'likör', 'saft'] },
        flour('150 g'),
        eggs('2'),
        sugar('5 tbsp'),
        butter('3 tbsp'),
        salt,
      ],
      steps: [
        'Halve and stone the plums and stew them with three spoons of sugar and a splash of water for 8 minutes, just until they collapse.',
        'Beat the quark with the eggs, the rest of the sugar, a pinch of salt and the flour into a thick, sticky dough; shape it into 12 small patties with floured hands.',
        'Fry them in butter over medium heat for 3 minutes a side until deep golden, and serve hot with the warm plums.',
      ],
    },
    {
      id: 'aldi-edeka-garnelen-mango-salat',
      title: 'Prawn, Mango & Cucumber Salad with Lemon-Garlic Dressing',
      summary: 'Prawns flashed in a hot pan, tossed while warm with mango, cucumber, cherry tomatoes and romaine in a sweet-sharp lemon and garlic dressing.',
      servings: 2,
      timeMinutes: 20,
      tags: ['pescatarian', 'asian', 'lunch'],
      ingredients: [
        { label: 'Prawns', keywords: ['garnelen'], qty: '250 g', exclude: ['dillcreme', 'spieß', 'salat', 'knusper'] },
        { label: 'Mango', keywords: ['mango'], qty: '1', exclude: ['curry', 'sauce', 'saft', 'chutney', 'lufterfrischer'] },
        { label: 'Cucumber', keywords: ['salatgurke'], qty: '1' },
        { label: 'Cherry tomatoes', keywords: ['cherryrispentomaten', 'rispentomaten'], qty: '250 g' },
        { label: 'Mini romaine', keywords: ['romanasalat'], qty: '2' },
        { label: 'Lemons', keywords: ['zitronen'], qty: '2', exclude: LEMON_EXCLUDE },
        garlic('2 cloves'),
        oil('3 tbsp'),
        sugar('2 tsp'),
        saltPepper,
      ],
      steps: [
        'Whisk the juice of both lemons with the grated garlic, sugar, a big pinch of salt and two spoons of oil until the sugar dissolves.',
        'Dice the mango, slice the cucumber, halve the tomatoes and tear the romaine into a wide bowl.',
        'Fry the prawns in the last spoon of oil over high heat for about 90 seconds a side until pink, tip them hot onto the salad and pour the dressing over.',
      ],
    },
    {
      id: 'rewe-edekacenter-miesmuscheln-sahne-baguette',
      title: 'Mussels in Garlic Cream with Celeriac & Baguette',
      summary: 'Mussels steamed open over a soft base of onion, celeriac and garlic, the liquor finished with cream, baguette for the broth.',
      servings: 2,
      timeMinutes: 30,
      tags: ['pescatarian', 'belgian', 'dinner'],
      ingredients: [
        { label: 'Mussels', keywords: ['miesmuscheln'], qty: '1 kg' },
        { label: 'Whipping cream', keywords: ['schlagsahne'], qty: '150 ml' },
        { label: 'Celeriac', keywords: ['knollensellerie', 'sellerie'], qty: '¼' },
        { label: 'Baguette', keywords: ['baguette'], qty: '1', exclude: ['laugen', 'knoblauch', 'kräuter', 'walnuss'] },
        onion('1'),
        garlic('4 cloves'),
        butter('2 tbsp'),
        saltPepper,
      ],
      steps: [
        'Scrub the mussels and throw away any that stay open when tapped. Sweat the diced onion, finely diced celeriac and sliced garlic in the butter in a wide pot for 8 minutes.',
        'Turn the heat to high, tip in the mussels with a splash of water, cover tightly and shake the pot; after 4–5 minutes they should all be open.',
        'Lift the mussels into bowls, boil the cream into the liquor for a minute, season with pepper (it rarely needs salt), pour it over and serve with the baguette.',
      ],
    },
    {
      id: 'lidl-rewe-haehnchen-wraps-mais',
      title: 'Chicken, Pepper & Sweetcorn Wraps with Soured Cream',
      summary: 'Strips of chicken breast fried with peppers, rolled in wraps with sweetcorn, crunchy cucumber and radishes and a spoon of soured cream.',
      servings: 4,
      timeMinutes: 25,
      tags: ['meat', 'mexican', 'lunch'],
      ingredients: [
        { label: 'Wraps', keywords: ['wraps'], qty: '8' },
        { label: 'Chicken breast', keywords: ['hähnchen-brustfilet', 'hähnchen-innenbrustfilet'], qty: '500 g', exclude: ['finesse', 'aufschnitt', 'wurst'] },
        {
          label: 'Peppers',
          keywords: ['paprika'],
          qty: '2',
          exclude: ['salami', 'mortadella', 'lyoner', 'pastete', 'chips', 'gewürz', 'pulver', 'wurst', 'snack'],
        },
        { label: 'Sweetcorn', keywords: ['goldmais', 'sonnenmais'], qty: '1 tin' },
        { label: 'Cucumber', keywords: ['bauerngurken', 'salatgurke'], qty: '1' },
        { label: 'Radishes', keywords: ['radieschen'], qty: '1 bunch' },
        { label: 'Soured cream', keywords: ['saure sahne'], qty: '200 g' },
        garlic('2 cloves'),
        oil('2 tbsp'),
        saltPepper,
      ],
      steps: [
        'Cut the chicken and peppers into strips and fry them over high heat in the oil with the crushed garlic and salt for 6–8 minutes, until the chicken is cooked through and browned at the edges.',
        'Slice the cucumber and radishes into thin batons and drain the sweetcorn; warm the wraps in a dry pan for 20 seconds a side.',
        'Spread each wrap with soured cream, fill with the chicken, peppers, corn and crunchy vegetables, grind pepper over and roll tightly.',
      ],
    },
    {
      id: 'aldi-penny-couscous-salat-hummus',
      title: 'Lemon Couscous Salad with Olives, Tomatoes & Hummus',
      summary: 'Couscous soaked in lemon and oil, tossed with cherry tomatoes, cucumber, olives and salad leaves, a thick spoon of hummus on each plate.',
      servings: 4,
      timeMinutes: 20,
      tags: ['vegan', 'lebanese', 'lunch'],
      ingredients: [
        { label: 'Couscous', keywords: ['couscous'], qty: '250 g' },
        { label: 'Cherry tomatoes', keywords: ['cherryrispentomaten', 'rispentomaten'], qty: '250 g' },
        { label: 'Cucumber', keywords: ['bio-gurke', 'salatgurke'], qty: '1' },
        { label: 'Olives', keywords: ['kalamata', 'oliven'], qty: '100 g', exclude: ['brötchen', 'brot'] },
        { label: 'Salad leaves', keywords: ['pflücksalat'], qty: '1 bag' },
        { label: 'Hummus', keywords: ['hummus'], qty: '200 g' },
        { label: 'Lemons', keywords: ['zitronen'], qty: '2', exclude: LEMON_EXCLUDE },
        onion('½', 'Red onion'),
        oil('5 tbsp', 'Olive oil'),
        saltPepper,
      ],
      steps: [
        'Pour 300 ml of boiling salted water over the couscous with a spoon of oil, cover for 5 minutes, then fork it loose.',
        'Whisk the juice of both lemons with the remaining oil and salt and pour it over the warm couscous so it soaks in.',
        'Fold in the halved tomatoes, diced cucumber, olives, finely sliced onion and the leaves, and serve with a big spoon of hummus on each plate.',
      ],
    },
  ],
};
