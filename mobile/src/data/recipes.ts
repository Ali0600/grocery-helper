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
// hits salted peanuts, 'pfeffer' hits Pfeffer-Salami, 'butter' hits a Schweinefleisch-Spieß
// "Butterfly" and 'zucker' hits a Zero-sugar cola. A false staple match is not cosmetic — it
// inflates the on-sale count the ranking uses. Seasoning is never worth pricing at all, so it
// is deliberately narrowed to standalone products and reads as "have".

import { RecipesData } from '../types';

export const RECIPES: RecipesData = {
  generatedFor: '10115',
  generatedAt: '2026-07-30',
  recipes: [
    // ---- single store: ALDI ----
    {
      id: 'aldi-suess-sauer-tofu-spiesse',
      title: 'Sweet & Sour Tofu Skewers with Rice',
      summary: 'Grill tofu, peppers and mushrooms threaded onto skewers and glazed with sweet-and-sour sauce.',
      servings: 2,
      timeMinutes: 25,
      tags: ['vegan', 'asian', 'dinner'],
      ingredients: [
        { label: 'Grilling tofu', keywords: ['grilltofu', 'tofu'], qty: '360 g' },
        {
          label: 'Red pepper',
          keywords: ['paprika'],
          qty: '2',
          exclude: ['chips', 'salami', 'gewürz', 'pulver', 'edelsüß', 'snack', 'kolbasz'],
        },
        {
          label: 'Mushrooms',
          keywords: ['champignon'],
          qty: '250 g',
          exclude: ['käserei', 'baguette', 'suppe', 'creme'],
        },
        { label: 'Sweet & sour sauce', keywords: ['süß-sauer', 'süßsauer'], qty: '4 tbsp' },
        {
          label: 'Rice',
          keywords: ['basmati', 'reis'],
          qty: '150 g',
          staple: true,
          exclude: ['milchreis', 'reiswaffel', 'preis'],
        },
        {
          label: 'Garlic',
          keywords: ['knoblauch'],
          qty: '2 cloves',
          staple: true,
          exclude: ['wurst', 'baguette', 'butter', 'creme'],
        },
        { label: 'Oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '2 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Cook the rice. Cube the tofu and peppers, halve the mushrooms.',
        'Thread everything onto skewers, brush with oil and crushed garlic, and grill or pan-fry 10 minutes, turning.',
        'Brush with the sweet-and-sour sauce for the last 2 minutes and serve over the rice.',
      ],
    },
    {
      id: 'aldi-fruehkartoffel-pilzpfanne',
      title: 'New Potato, Mushroom & Leek Pan',
      summary: 'New potatoes crisped in the pan with mushrooms, leek and zucchini — one pan, no oven.',
      servings: 2,
      timeMinutes: 30,
      tags: ['vegan', 'german', 'lunch'],
      ingredients: [
        { label: 'New potatoes', keywords: ['speisefrühkartoffel', 'frühkartoffel'], qty: '600 g' },
        {
          label: 'Mushrooms',
          keywords: ['champignon'],
          qty: '250 g',
          exclude: ['käserei', 'baguette', 'suppe', 'creme'],
        },
        { label: 'Leek', keywords: ['porree'], qty: '1' },
        { label: 'Zucchini', keywords: ['zucchini'], qty: '1' },
        {
          label: 'Garlic',
          keywords: ['knoblauch'],
          qty: '2 cloves',
          staple: true,
          exclude: ['wurst', 'baguette', 'butter', 'creme'],
        },
        { label: 'Oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '3 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Boil the potatoes in their skins 15 minutes, drain, and halve them.',
        'Fry the potatoes cut-side down in hot oil until golden, then add the quartered mushrooms.',
        'Stir in the sliced leek, zucchini and garlic, cook 5 more minutes, and season well.',
      ],
    },

    // ---- single store: dm (clearance only — one cookable item, so both recipes lean on staples) ----
    {
      id: 'dm-kuerbiscreme-pasta',
      title: 'Pumpkin Cream Pasta',
      summary: 'A jar of pumpkin-and-olive-oil cream loosened with pasta water into a five-minute sauce.',
      servings: 2,
      timeMinutes: 15,
      tags: ['vegetarian', 'italian', 'lunch'],
      ingredients: [
        { label: 'Pumpkin cream', keywords: ['kürbiscreme'], qty: '180 g' },
        {
          label: 'Pasta',
          keywords: ['spaghetti', 'nudel', 'pasta', 'teigwaren'],
          qty: '250 g',
          staple: true,
          exclude: ['sauce', 'fix', 'instantnudel'],
        },
        {
          label: 'Garlic',
          keywords: ['knoblauch'],
          qty: '1 clove',
          staple: true,
          exclude: ['wurst', 'baguette', 'butter', 'creme'],
        },
        { label: 'Olive oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '1 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Boil the pasta in well-salted water, reserving a cup of the water before draining.',
        'Warm the pumpkin cream with the sliced garlic and oil in a wide pan.',
        'Toss the pasta through, loosening with pasta water until glossy, and season.',
      ],
    },
    {
      id: 'dm-kuerbiscreme-ruehrei',
      title: 'Pumpkin Cream Scrambled Eggs',
      summary: 'Soft scrambled eggs rippled with pumpkin cream and sweet fried onion.',
      servings: 2,
      timeMinutes: 10,
      tags: ['vegetarian', 'german', 'breakfast'],
      ingredients: [
        { label: 'Pumpkin cream', keywords: ['kürbiscreme'], qty: '3 tbsp' },
        { label: 'Eggs', keywords: ['eier'], qty: '4', staple: true, exclude: ['eierlikör', 'eiersalat', 'eierkuchen', 'eierkocher'] },
        {
          label: 'Onion',
          keywords: ['zwiebel'],
          qty: '1',
          staple: true,
          exclude: ['lauchzwiebel', 'zwiebelmettwurst', 'röstzwiebel'],
        },
        {
          label: 'Butter',
          keywords: ['butter'],
          qty: '1 tbsp',
          staple: true,
          exclude: ['buttermilch', 'erdnussbutter', 'butterkäse', 'butterkeks', 'knoblauchbutter', 'butterfly', 'fassbutter'],
        },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Soften the finely diced onion in the butter until sweet and just colouring.',
        'Beat the eggs, season, and scramble gently over low heat until barely set.',
        'Ripple the pumpkin cream through off the heat and serve immediately.',
      ],
    },

    // ---- single store: EDEKA ----
    {
      id: 'edeka-kabeljau-bohnen-pfifferlinge',
      title: 'Cod Loin with Green Beans & Chanterelles',
      summary: 'Thick cod loin basted in butter, with chanterelles and crisp bush beans.',
      servings: 2,
      timeMinutes: 30,
      tags: ['pescatarian', 'french', 'dinner'],
      ingredients: [
        { label: 'Cod loin', keywords: ['kabeljau'], qty: '2 pieces' },
        { label: 'Green beans', keywords: ['buschbohne'], qty: '300 g' },
        { label: 'Chanterelles', keywords: ['pfifferling'], qty: '200 g' },
        {
          label: 'Butter',
          keywords: ['butter'],
          qty: '2 tbsp',
          staple: true,
          exclude: ['buttermilch', 'erdnussbutter', 'butterkäse', 'butterkeks', 'knoblauchbutter', 'butterfly', 'fassbutter'],
        },
        {
          label: 'Garlic',
          keywords: ['knoblauch'],
          qty: '1 clove',
          staple: true,
          exclude: ['wurst', 'baguette', 'butter', 'creme'],
        },
        { label: 'Olive oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '1 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Blanch the trimmed beans 4 minutes, then refresh under cold water.',
        'Fry the chanterelles hard in oil until dry and golden, add the garlic and beans, and keep warm.',
        'Season the cod, fry 3 minutes a side in foaming butter, spooning it over, and serve on the beans.',
      ],
    },
    {
      id: 'edeka-simit-frischkaese-fruehstueck',
      title: 'Simit with Cream Cheese, Tomato & Radish',
      summary: 'Sesame-crusted simit split and piled with cream cheese, vine tomato and peppery radish.',
      servings: 2,
      timeMinutes: 10,
      tags: ['vegetarian', 'turkish', 'breakfast'],
      ingredients: [
        { label: 'Simit', keywords: ['simit'], qty: '2' },
        {
          label: 'Cream cheese',
          keywords: ['frischkäse'],
          qty: '150 g',
          exclude: ['hähnchen', 'röllchen', 'torte', 'kuchen'],
        },
        {
          label: 'Vine tomatoes',
          keywords: ['rispentomate'],
          qty: '250 g',
          exclude: ['ketchup', 'tomatenmark', 'passata', 'sauce'],
        },
        { label: 'Radishes', keywords: ['radieschen'], qty: '1 bunch' },
        { label: 'Olive oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '1 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Warm the simit briefly in a dry pan and split them open.',
        'Spread thickly with the cream cheese.',
        'Top with sliced tomato and radish, drizzle with oil, and season.',
      ],
    },

    // ---- single store: E center ----
    {
      id: 'edekacenter-putensteak-portobello',
      title: 'Turkey Steaks with Portobello & Kohlrabi Slaw',
      summary: 'Turkey steaks and meaty portobello caps seared in butter, with a crunchy kohlrabi-radish slaw.',
      servings: 2,
      timeMinutes: 25,
      tags: ['meat', 'german', 'dinner'],
      ingredients: [
        { label: 'Turkey steak', keywords: ['putenbruststeak', 'putenschnitzel', 'putenbrust'], qty: '2' },
        { label: 'Portobello mushrooms', keywords: ['portobello'], qty: '4' },
        { label: 'Kohlrabi', keywords: ['kohlrabi'], qty: '1' },
        { label: 'Radishes', keywords: ['radieschen'], qty: '1 bunch' },
        {
          label: 'Butter',
          keywords: ['butter'],
          qty: '2 tbsp',
          staple: true,
          exclude: ['buttermilch', 'erdnussbutter', 'butterkäse', 'butterkeks', 'knoblauchbutter', 'butterfly', 'fassbutter'],
        },
        { label: 'Oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '1 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Cut the kohlrabi and radishes into matchsticks, salt lightly, and set aside to crisp.',
        'Sear the portobello caps in butter until browned, then lift out and keep warm.',
        'Season the turkey and fry 3–4 minutes a side in the same pan; serve with the mushrooms and slaw.',
      ],
    },
    {
      id: 'edekacenter-gorgonzola-gnocchi',
      title: 'Gorgonzola Gnocchi with Grilled Peppers',
      summary: 'Pan-fried gnocchi in a quick gorgonzola cream, with charred peppers and spring onion.',
      servings: 2,
      timeMinutes: 20,
      tags: ['vegetarian', 'italian', 'lunch'],
      ingredients: [
        { label: 'Gnocchi', keywords: ['gnocchi'], qty: '500 g' },
        { label: 'Gorgonzola', keywords: ['gorgonzola'], qty: '120 g' },
        {
          label: 'Peppers',
          keywords: ['grillpaprika', 'paprika'],
          qty: '2',
          exclude: ['chips', 'salami', 'gewürz', 'pulver', 'edelsüß', 'snack', 'kolbasz'],
        },
        { label: 'Spring onions', keywords: ['lauchzwiebel'], qty: '3' },
        { label: 'Milk', keywords: ['vollmilch'], qty: '100 ml', staple: true },
        {
          label: 'Butter',
          keywords: ['butter'],
          qty: '1 tbsp',
          staple: true,
          exclude: ['buttermilch', 'erdnussbutter', 'butterkäse', 'butterkeks', 'knoblauchbutter', 'butterfly', 'fassbutter'],
        },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Char the sliced peppers in a dry hot pan, then set aside.',
        'Fry the gnocchi in butter until golden on both sides.',
        'Melt the gorgonzola with the milk into a sauce, fold in the gnocchi and peppers, and scatter with spring onion.',
      ],
    },

    // ---- single store: Lidl ----
    {
      id: 'lidl-burrata-romatomaten-pesto',
      title: 'Burrata & Roma Tomato Salad with Pesto',
      summary: 'Torn stracciatella di burrata over ripe Roma tomatoes, spooned with pesto and parsley.',
      servings: 2,
      timeMinutes: 10,
      tags: ['vegetarian', 'italian', 'lunch'],
      ingredients: [
        { label: 'Stracciatella di burrata', keywords: ['burrata', 'stracciatella'], qty: '140 g' },
        {
          label: 'Roma tomatoes',
          keywords: ['romatom', 'cherrystrauchtomate'],
          qty: '500 g',
          exclude: ['ketchup', 'tomatenmark', 'passata', 'sauce', 'soße'],
        },
        { label: 'Pesto', keywords: ['pesto'], qty: '3 tbsp' },
        { label: 'Parsley', keywords: ['petersilie'], qty: '½ bunch' },
        { label: 'Olive oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '2 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Slice the tomatoes thickly, salt them, and let them sit 5 minutes.',
        'Arrange on a plate and tear the burrata over the top.',
        'Spoon over the pesto, scatter with chopped parsley, and finish with oil and pepper.',
      ],
    },
    {
      id: 'lidl-putenschnitzel-mais-spitzkohl',
      title: 'Turkey Escalopes with Sweetcorn & Pointed Cabbage',
      summary: 'Quick turkey escalopes with buttered corn and pointed cabbage braised in sour cream.',
      servings: 2,
      timeMinutes: 25,
      tags: ['meat', 'german', 'dinner'],
      ingredients: [
        { label: 'Turkey escalopes', keywords: ['puten-brust', 'putenbrust', 'putenschnitzel'], qty: '2' },
        { label: 'Sweetcorn', keywords: ['zuckermais'], qty: '2 cobs' },
        { label: 'Pointed cabbage', keywords: ['spitzkohl'], qty: '½' },
        { label: 'Sour cream', keywords: ['saure sahne', 'schmand'], qty: '150 g' },
        {
          label: 'Butter',
          keywords: ['butter'],
          qty: '2 tbsp',
          staple: true,
          exclude: ['buttermilch', 'erdnussbutter', 'butterkäse', 'butterkeks', 'knoblauchbutter', 'butterfly', 'fassbutter'],
        },
        { label: 'Oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '1 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Boil the corn 8 minutes, then roll the cobs in butter and salt.',
        'Shred the cabbage and braise it in a little butter and water for 8 minutes; stir in the sour cream.',
        'Season the escalopes and fry 2–3 minutes a side in hot oil, then serve with the cabbage and corn.',
      ],
    },

    // ---- single store: REWE ----
    {
      id: 'rewe-haehnchen-zucchini-passata',
      title: 'Chicken with Zucchini & Passata Pasta',
      summary: 'Chicken breast simmered in passata with zucchini, tossed through pasta and finished with rucola.',
      servings: 2,
      timeMinutes: 30,
      tags: ['meat', 'italian', 'dinner'],
      ingredients: [
        {
          label: 'Chicken breast',
          keywords: ['hähnchen-brustfilet', 'hähnchenbrustfilet', 'hähnchenbrust'],
          qty: '400 g',
          exclude: ['salami', 'pelmeni', 'fond', 'pastete', 'salat'],
        },
        { label: 'Zucchini', keywords: ['zucchini'], qty: '2' },
        { label: 'Passata', keywords: ['passata'], qty: '700 g' },
        { label: 'Rucola', keywords: ['rucola'], qty: '60 g' },
        {
          label: 'Pasta',
          keywords: ['spaghetti', 'nudel', 'pasta', 'teigwaren'],
          qty: '250 g',
          staple: true,
          exclude: ['sauce', 'fix', 'instantnudel'],
        },
        {
          label: 'Onion',
          keywords: ['zwiebel'],
          qty: '1',
          staple: true,
          exclude: ['lauchzwiebel', 'zwiebelmettwurst', 'röstzwiebel'],
        },
        {
          label: 'Garlic',
          keywords: ['knoblauch'],
          qty: '2 cloves',
          staple: true,
          exclude: ['wurst', 'baguette', 'butter', 'creme'],
        },
        { label: 'Olive oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '2 tbsp', staple: true },
      ],
      steps: [
        'Brown the sliced chicken in oil with the onion and garlic.',
        'Add the diced zucchini and the passata, and simmer 15 minutes until thick.',
        'Cook the pasta, toss it through the sauce, and pile the rucola on top.',
      ],
    },
    {
      id: 'rewe-griechischer-joghurt-pfirsich',
      title: 'Greek-style Yogurt with Peaches & Blueberries',
      summary: 'Thick Greek-style yogurt under sliced yellow peaches and a handful of blueberries.',
      servings: 2,
      timeMinutes: 5,
      tags: ['vegetarian', 'greek', 'breakfast'],
      ingredients: [
        {
          label: 'Greek-style yogurt',
          keywords: ['joghurt nach griechischer', 'griechischer art', 'joghurt'],
          qty: '400 g',
          exclude: ['getränk', 'drink', 'eis'],
        },
        {
          label: 'Peaches',
          keywords: ['pfirsich'],
          qty: '2',
          exclude: ['joghurt', 'maracuja', 'saft', 'nektar', 'tee', 'konfitüre', 'eis'],
        },
        {
          label: 'Blueberries',
          keywords: ['heidelbeere'],
          qty: '150 g',
          exclude: ['joghurt', 'froop', 'quark', 'muffin', 'saft'],
        },
        {
          label: 'Honey or sugar',
          keywords: ['honig', 'zucker'],
          qty: '1 tbsp',
          staple: true,
          exclude: ['pepsi', 'cola', 'zero', 'zuckermais', 'zuckerapri', 'zuckerwatte', 'puderzucker'],
        },
      ],
      steps: [
        'Stir the yogurt smooth and divide between two bowls.',
        'Stone and slice the peaches, and scatter them with the blueberries on top.',
        'Drizzle with honey and serve.',
      ],
    },

    // ---- two stores ----
    {
      id: 'lidl-rewe-raeucherlachs-stullen',
      title: 'Smoked Salmon Open Sandwiches with Rucola',
      summary: 'Crusty bread under crème fraîche, smoked salmon, cherry tomatoes and rucola — bread and salmon at one shop, the leaves at the other.',
      servings: 2,
      timeMinutes: 10,
      tags: ['pescatarian', 'nordic', 'lunch'],
      ingredients: [
        { label: 'Smoked salmon', keywords: ['räucherlachs'], qty: '200 g', exclude: ['schinken', 'vegan'] },
        { label: 'Crusty bread', keywords: ['sonnencrusti'], qty: '1 loaf' },
        { label: 'Crème fraîche', keywords: ['creme fraîche', 'crème fraîche', 'saure sahne', 'schmand'], qty: '150 g' },
        { label: 'Rucola', keywords: ['rucola'], qty: '60 g' },
        {
          label: 'Cherry tomatoes',
          keywords: ['romatom', 'cherrytomate'],
          qty: '200 g',
          exclude: ['ketchup', 'tomatenmark', 'passata', 'sauce', 'soße'],
        },
        { label: 'Olive oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '1 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Slice and lightly toast the bread.',
        'Spread each slice with crème fraîche and drape over the smoked salmon.',
        'Top with halved tomatoes and rucola, drizzle with oil, and grind over plenty of pepper.',
      ],
    },
    {
      id: 'aldi-edeka-feta-paprika-ofen',
      title: 'Feta-baked Peppers with Vine Tomatoes',
      summary: 'Peppers and vine tomatoes roasted around a block of feta until it collapses into a sauce.',
      servings: 2,
      timeMinutes: 35,
      tags: ['vegetarian', 'mediterranean', 'dinner'],
      ingredients: [
        { label: 'Feta', keywords: ['feta', 'schafkäse'], qty: '200 g' },
        {
          label: 'Red peppers',
          keywords: ['paprika'],
          qty: '3',
          exclude: ['chips', 'salami', 'gewürz', 'pulver', 'edelsüß', 'snack', 'kolbasz'],
        },
        {
          label: 'Vine tomatoes',
          keywords: ['rispentomate'],
          qty: '400 g',
          exclude: ['ketchup', 'tomatenmark', 'passata', 'sauce'],
        },
        { label: 'Spring onions', keywords: ['lauchzwiebel'], qty: '3' },
        {
          label: 'Garlic',
          keywords: ['knoblauch'],
          qty: '3 cloves',
          staple: true,
          exclude: ['wurst', 'baguette', 'butter', 'creme'],
        },
        { label: 'Olive oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '3 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Heat the oven to 200 °C. Put the feta in the middle of a baking dish.',
        'Pack the sliced peppers, tomatoes and whole garlic cloves around it, douse in oil, and season.',
        'Bake 25 minutes, mash the softened feta and garlic through the vegetables, and scatter with spring onion.',
      ],
    },
    {
      id: 'edekacenter-lidl-haehnchenspiesse-mais',
      title: 'Chicken Skewers with Corn & Cabbage Slaw',
      summary: 'Barbecue-glazed chicken skewers with charred corn and a sour-cream slaw — skewers at one shop, the vegetables at the other.',
      servings: 2,
      timeMinutes: 25,
      tags: ['meat', 'american', 'dinner'],
      ingredients: [
        { label: 'Chicken skewers', keywords: ['hähnchenspieß', 'hähnchen-spieß'], qty: '4' },
        { label: 'Sweetcorn', keywords: ['zuckermais'], qty: '2 cobs' },
        { label: 'Pointed cabbage', keywords: ['spitzkohl'], qty: '½' },
        { label: 'Barbecue sauce', keywords: ['grillsauce'], qty: '4 tbsp' },
        { label: 'Sour cream', keywords: ['saure sahne', 'schmand'], qty: '150 g' },
        { label: 'Oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '1 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Shred the cabbage finely, salt it, and dress with the sour cream and plenty of pepper.',
        'Grill or pan-fry the corn until charred in patches, then the skewers, 10–12 minutes turning.',
        'Brush the skewers with barbecue sauce for the last 2 minutes and serve with the corn and slaw.',
      ],
    },
    {
      id: 'rewe-aldi-kotelett-pflaumen',
      title: 'Pork Chops with Plums & New Potatoes',
      summary: 'Pork chops rested under caramelised plums, with new potatoes and celery — chops at one shop, the rest at the other.',
      servings: 2,
      timeMinutes: 35,
      tags: ['meat', 'austrian', 'dinner'],
      ingredients: [
        { label: 'Pork chops', keywords: ['stielkotelett', 'kotelett'], qty: '2' },
        { label: 'Plums', keywords: ['pflaume'], qty: '300 g', exclude: ['konfitüre', 'saft', 'joghurt', 'mus'] },
        { label: 'New potatoes', keywords: ['speisefrühkartoffel', 'frühkartoffel'], qty: '500 g' },
        { label: 'Celery', keywords: ['staudensellerie'], qty: '2 sticks' },
        {
          label: 'Onion',
          keywords: ['zwiebel'],
          qty: '1',
          staple: true,
          exclude: ['lauchzwiebel', 'zwiebelmettwurst', 'röstzwiebel'],
        },
        {
          label: 'Butter',
          keywords: ['butter'],
          qty: '2 tbsp',
          staple: true,
          exclude: ['buttermilch', 'erdnussbutter', 'butterkäse', 'butterkeks', 'knoblauchbutter', 'butterfly', 'fassbutter'],
        },
        {
          label: 'Sugar',
          keywords: ['honig', 'zucker'],
          qty: '1 tsp',
          staple: true,
          exclude: ['pepsi', 'cola', 'zero', 'zuckermais', 'zuckerapri', 'zuckerwatte', 'puderzucker'],
        },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Boil the potatoes in their skins until tender, about 20 minutes.',
        'Season the chops and fry 4 minutes a side in butter, then rest them on a warm plate.',
        'Cook the halved plums, sliced celery, onion and sugar in the same pan 5 minutes, and spoon over the chops.',
      ],
    },
    {
      id: 'dm-lidl-kuerbiscreme-ziegenkaese-toast',
      title: 'Pumpkin Cream & Goat’s Cheese Toast',
      summary: 'Fig-and-walnut bread toasted under pumpkin cream and melting goat’s cheese — the cream from one shop, the bread and cheese from the other.',
      servings: 2,
      timeMinutes: 15,
      tags: ['vegetarian', 'french', 'lunch'],
      ingredients: [
        { label: 'Pumpkin cream', keywords: ['kürbiscreme'], qty: '150 g' },
        { label: 'Goat’s cheese', keywords: ['ziegenkäse'], qty: '150 g' },
        { label: 'Fig & walnut bread', keywords: ['couronne'], qty: '4 slices' },
        { label: 'Parsley', keywords: ['petersilie'], qty: '½ bunch' },
        { label: 'Olive oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '1 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Toast the bread slices on one side under a hot grill.',
        'Turn them, spread with the pumpkin cream, and lay slices of goat’s cheese on top.',
        'Grill until the cheese blisters, then finish with parsley, oil and pepper.',
      ],
    },
  ],
};
