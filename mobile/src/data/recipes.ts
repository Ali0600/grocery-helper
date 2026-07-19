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
  generatedAt: '2026-07-19',
  recipes: [
    // ---- single store: ALDI (thin week — only Rispentomaten + Vollmilch/staple) ----
    {
      id: 'aldi-frische-tomaten-spaghetti',
      title: 'Fresh Tomato Spaghetti',
      summary: 'Vine tomatoes cooked down with garlic and onion into a quick sauce for spaghetti.',
      servings: 2,
      timeMinutes: 20,
      tags: ['vegan', 'italian', 'dinner'],
      ingredients: [
        {
          label: 'Vine tomatoes',
          keywords: ['rispentomate'],
          qty: '500 g',
          exclude: ['ketchup', 'tomatenmark', 'passata', 'sauce'],
        },
        {
          label: 'Spaghetti',
          keywords: ['spaghetti', 'nudel', 'pasta', 'teigwaren'],
          qty: '250 g',
          staple: true,
          exclude: ['sauce', 'fix', 'instantnudel'],
        },
        {
          label: 'Garlic',
          keywords: ['knoblauch'],
          qty: '2 cloves',
          staple: true,
          exclude: ['wurst', 'baguette', 'butter', 'creme'],
        },
        {
          label: 'Onion',
          keywords: ['zwiebel'],
          qty: '1',
          staple: true,
          exclude: ['lauchzwiebel', 'zwiebelmettwurst', 'röstzwiebel'],
        },
        { label: 'Olive oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '2 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Boil the spaghetti in well-salted water until al dente.',
        'Soften the diced onion and garlic in olive oil, then add the chopped tomatoes.',
        'Simmer 10 minutes until saucy, season, and toss with the drained pasta.',
      ],
    },
    {
      id: 'aldi-cremige-tomatensuppe',
      title: 'Creamy Tomato Soup',
      summary: 'Vine tomatoes blended into a smooth soup finished with a splash of milk.',
      servings: 2,
      timeMinutes: 25,
      tags: ['vegetarian', 'german', 'lunch'],
      ingredients: [
        {
          label: 'Vine tomatoes',
          keywords: ['rispentomate'],
          qty: '600 g',
          exclude: ['ketchup', 'tomatenmark', 'passata', 'sauce'],
        },
        { label: 'Milk', keywords: ['vollmilch'], qty: '150 ml', staple: true },
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
        { label: 'Flour', keywords: ['mehl'], qty: '1 tbsp', staple: true, exclude: ['mehrkorn'] },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Sweat the diced onion in the butter, stir in the flour and cook a minute.',
        'Add the chopped tomatoes and 300 ml water; simmer 15 minutes, then blend smooth.',
        'Stir in the milk, season, and warm through without boiling.',
      ],
    },

    // ---- single store: EDEKA ----
    {
      id: 'edeka-kirsch-himbeer-joghurt',
      title: 'Cherry & Raspberry Greek Yogurt Bowl',
      summary: 'Thick Greek-style yogurt under a pile of cherries, raspberries and toasted pumpkin seeds.',
      servings: 2,
      timeMinutes: 5,
      tags: ['vegetarian', 'greek', 'breakfast'],
      ingredients: [
        { label: 'Greek yogurt', keywords: ['griechischer sahnejoghurt', 'sahnejoghurt', 'joghurt'], qty: '400 g' },
        { label: 'Cherries', keywords: ['kirschen'], qty: '200 g', exclude: ['kirsch-vanille', 'tomaten', 'sauce'] },
        { label: 'Raspberries', keywords: ['himbeere'], qty: '125 g' },
        { label: 'Pumpkin seeds', keywords: ['kürbiskerne'], qty: '2 tbsp' },
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
        'Stone the cherries and scatter them with the raspberries on top.',
        'Sprinkle over the pumpkin seeds and drizzle with honey.',
      ],
    },
    {
      id: 'edeka-wolfsbarsch-moehren-rucola',
      title: 'Sea Bass with Roasted Carrots & Rucola',
      summary: 'Sea bass fillets crisped in butter, with roasted carrots and a peppery rucola salad.',
      servings: 2,
      timeMinutes: 30,
      tags: ['pescatarian', 'mediterranean', 'dinner'],
      ingredients: [
        { label: 'Sea bass fillet', keywords: ['wolfsbarsch'], qty: '2' },
        { label: 'Carrots', keywords: ['möhre', 'karotte'], qty: '400 g', staple: true },
        { label: 'Rucola', keywords: ['rucola'], qty: '80 g' },
        {
          label: 'Cherry tomatoes',
          keywords: ['mini-rispentomate', 'rispentomate'],
          qty: '200 g',
          exclude: ['ketchup', 'tomatenmark', 'sauce'],
        },
        { label: 'Olive oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '2 tbsp', staple: true },
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
        'Toss the carrot batons in oil and roast at 200 °C for 20 minutes.',
        'Pat the fillets dry, season, and fry skin-side down in butter 3–4 minutes, then flip briefly.',
        'Dress the rucola and halved tomatoes with oil; serve with the fish and carrots.',
      ],
    },

    // ---- single store: E center ----
    {
      id: 'edekacenter-hueftsteak-rucola-baguette',
      title: 'Hip Steak with Rucola Salad & Baguette',
      summary: 'A seared beef hip steak resting on a rucola and tomato salad, with warm baguette.',
      servings: 2,
      timeMinutes: 25,
      tags: ['meat', 'german', 'dinner'],
      ingredients: [
        { label: 'Beef hip steak', keywords: ['hüftsteak'], qty: '2' },
        { label: 'Rucola', keywords: ['rucola'], qty: '100 g' },
        {
          label: 'Vine tomatoes',
          keywords: ['rispentomate'],
          qty: '250 g',
          exclude: ['ketchup', 'tomatenmark', 'sauce'],
        },
        { label: 'Baguette', keywords: ['weizenbaguette', 'baguette'], qty: '1', exclude: ['salami'] },
        { label: 'Olive oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '2 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Bring the steaks to room temperature and season generously; warm the baguette.',
        'Sear 2–3 minutes a side in a smoking-hot pan, then rest 5 minutes.',
        'Toss the rucola and halved tomatoes with olive oil, slice the steak over the top, and serve with bread.',
      ],
    },
    {
      id: 'edekacenter-fladenbrot-gouda-gurkensalat',
      title: 'Fladenbrot with Gouda & Cucumber Salad',
      summary: 'Warm flatbread filled with young Gouda and creamy Almette, with a crisp cucumber-rucola salad.',
      servings: 2,
      timeMinutes: 15,
      tags: ['vegetarian', 'turkish', 'lunch'],
      ingredients: [
        { label: 'Fladenbrot', keywords: ['fladenbrot'], qty: '1' },
        { label: 'Young Gouda', keywords: ['gouda'], qty: '150 g' },
        { label: 'Cream cheese (Almette)', keywords: ['almette'], qty: '100 g' },
        { label: 'Mini cucumbers', keywords: ['minigurken'], qty: '3' },
        { label: 'Rucola', keywords: ['rucola'], qty: '60 g' },
        { label: 'Olive oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '2 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Warm the flatbread and split it open; spread the inside with the cream cheese.',
        'Slice the Gouda and cucumbers, and toss the cucumber with the rucola and a little oil.',
        'Fill the flatbread with the cheese and salad, season, and cut into wedges.',
      ],
    },

    // ---- single store: Lidl ----
    {
      id: 'lidl-haehnchen-bohnen-pfanne',
      title: 'Chicken & Green Bean Stir-fry with Soy',
      summary: 'Chicken breast steaks stir-fried with runner beans and pointed pepper in a garlicky soy glaze.',
      servings: 2,
      timeMinutes: 25,
      tags: ['meat', 'asian', 'dinner'],
      ingredients: [
        { label: 'Chicken breast steaks', keywords: ['hähnchen-bruststeak', 'hähnchen'], qty: '400 g' },
        { label: 'Runner beans', keywords: ['stangenbohnen'], qty: '300 g' },
        { label: 'Pointed pepper', keywords: ['spitzpaprika'], qty: '2' },
        { label: 'Soy sauce', keywords: ['sojasauce', 'sojasoße'], qty: '3 tbsp' },
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
        { label: 'Oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '1 tbsp', staple: true },
      ],
      steps: [
        'Cook the rice. Blanch the trimmed beans 3 minutes, then drain.',
        'Stir-fry the sliced chicken in hot oil until golden; add the pepper, beans and garlic.',
        'Splash in the soy sauce, toss to glaze, and serve over the rice.',
      ],
    },
    {
      id: 'lidl-nektarinen-ananas-joghurt',
      title: 'Nectarine & Pineapple Yogurt Bowl',
      summary: 'Fruit-corner yogurt topped with fresh nectarine and pineapple — five minutes, no cooking.',
      servings: 2,
      timeMinutes: 5,
      tags: ['vegetarian', 'german', 'breakfast'],
      ingredients: [
        { label: 'Yogurt', keywords: ['joghurt mit der ecke', 'joghurt'], qty: '2 pots' },
        { label: 'Nectarines', keywords: ['nektarine'], qty: '2' },
        { label: 'Pineapple', keywords: ['ananas'], qty: '¼' },
        {
          label: 'Honey or sugar',
          keywords: ['honig', 'zucker'],
          qty: '1 tbsp',
          staple: true,
          exclude: ['pepsi', 'cola', 'zero', 'zuckermais', 'zuckerapri', 'zuckerwatte', 'puderzucker'],
        },
      ],
      steps: [
        'Spoon the yogurt into two bowls.',
        'Stone and slice the nectarines, peel and cube the pineapple, and pile them on top.',
        'Drizzle with honey and serve.',
      ],
    },

    // ---- single store: REWE (thin week — Teewurst + Gewürzquark) ----
    {
      id: 'rewe-teewurst-omelett',
      title: 'Teewurst Omelette',
      summary: 'A soft folded omelette with spoonfuls of spreadable Teewurst melting into the eggs.',
      servings: 2,
      timeMinutes: 15,
      tags: ['meat', 'german', 'breakfast'],
      ingredients: [
        { label: 'Teewurst', keywords: ['teewurst'], qty: '100 g', exclude: ['vegan', 'veggie', 'pflanzlich'] },
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
        'Soften the diced onion in the butter.',
        'Beat the eggs with salt and pepper, pour in, and cook gently until just set.',
        'Dot spoonfuls of Teewurst over one half, fold the omelette over, and serve.',
      ],
    },
    {
      id: 'rewe-kraeuterquark-dip',
      title: 'Herbed Quark Dip with Carrot Sticks',
      summary: 'Spiced quark loosened into a herby dip, with carrot and onion crudités.',
      servings: 2,
      timeMinutes: 10,
      tags: ['vegetarian', 'german', 'lunch'],
      ingredients: [
        { label: 'Spiced quark', keywords: ['gewürzquark', 'quark'], qty: '250 g', exclude: ['quarkbrötchen', 'quark-brötchen'] },
        { label: 'Carrots', keywords: ['möhre', 'karotte'], qty: '3', staple: true },
        {
          label: 'Garlic',
          keywords: ['knoblauch'],
          qty: '1 clove',
          staple: true,
          exclude: ['wurst', 'baguette', 'butter', 'creme'],
        },
        {
          label: 'Onion',
          keywords: ['zwiebel'],
          qty: '½',
          staple: true,
          exclude: ['lauchzwiebel', 'zwiebelmettwurst', 'röstzwiebel'],
        },
        { label: 'Olive oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '1 tbsp', staple: true },
      ],
      steps: [
        'Stir the quark with the grated garlic, finely diced onion and a little oil until creamy.',
        'Cut the carrots into sticks.',
        'Season the dip and serve with the carrot sticks.',
      ],
    },

    // ---- two stores ----
    {
      id: 'lidl-edeka-lachs-bohnen-kartoffeln',
      title: 'Salmon with Green Beans & New Potatoes',
      summary: 'Salmon fillets with buttery new potatoes and runner beans — salmon and beans at one shop, potatoes at the other.',
      servings: 2,
      timeMinutes: 30,
      tags: ['pescatarian', 'german', 'dinner'],
      ingredients: [
        { label: 'Salmon', keywords: ['lachsfackel', 'räucherlachs'], qty: '300 g', exclude: ['schinken'] },
        { label: 'Runner beans', keywords: ['stangenbohnen'], qty: '300 g' },
        { label: 'New potatoes', keywords: ['speisefrühkartoffel', 'frühkartoffel'], qty: '500 g' },
        {
          label: 'Butter',
          keywords: ['butter'],
          qty: '2 tbsp',
          staple: true,
          exclude: ['buttermilch', 'erdnussbutter', 'butterkäse', 'butterkeks', 'knoblauchbutter', 'butterfly', 'fassbutter'],
        },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Boil the potatoes in their skins until tender, about 20 minutes.',
        'Blanch the beans 4 minutes, then toss them in butter.',
        'Fry the salmon 3 minutes a side, season, and serve with the potatoes and beans.',
      ],
    },
    {
      id: 'lidl-edekacenter-haehnchen-paprika-fladenbrot',
      title: 'Chicken & Pepper Fladenbrot',
      summary: 'Grilled chicken and charred pointed pepper stuffed into warm flatbread with cream cheese.',
      servings: 2,
      timeMinutes: 25,
      tags: ['meat', 'mediterranean', 'dinner'],
      ingredients: [
        { label: 'Chicken breast steaks', keywords: ['hähnchen-bruststeak', 'hähnchen'], qty: '400 g' },
        { label: 'Pointed pepper', keywords: ['spitzpaprika'], qty: '2' },
        { label: 'Fladenbrot', keywords: ['fladenbrot'], qty: '1' },
        { label: 'Cream cheese (Almette)', keywords: ['almette'], qty: '100 g' },
        { label: 'Olive oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '2 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Grill or pan-fry the chicken until cooked through, then slice.',
        'Char the sliced pepper in the same pan for 3 minutes.',
        'Warm and split the flatbread, spread with cream cheese, and fill with the chicken and pepper.',
      ],
    },
    {
      id: 'edeka-rewe-putensteak-kraeuterquark',
      title: 'Turkey Steak with Herbed Quark & Tomato',
      summary: 'Pan-seared turkey steaks with a cooling spiced-quark sauce and a quick tomato-rucola salad.',
      servings: 2,
      timeMinutes: 25,
      tags: ['meat', 'german', 'dinner'],
      ingredients: [
        { label: 'Turkey steak', keywords: ['putenbruststeak', 'putenbrust'], qty: '2' },
        { label: 'Spiced quark', keywords: ['gewürzquark', 'quark'], qty: '150 g', exclude: ['quarkbrötchen', 'quark-brötchen'] },
        {
          label: 'Cherry tomatoes',
          keywords: ['mini-rispentomate', 'rispentomate'],
          qty: '250 g',
          exclude: ['ketchup', 'tomatenmark', 'sauce'],
        },
        { label: 'Rucola', keywords: ['rucola'], qty: '60 g' },
        { label: 'Olive oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '2 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Season the turkey steaks and fry 3–4 minutes a side until cooked through.',
        'Toss the halved tomatoes and rucola with olive oil, salt and pepper.',
        'Serve the steaks with the salad and a spoonful of the spiced quark alongside.',
      ],
    },
    {
      id: 'aldi-rewe-tomaten-quark-salat',
      title: 'Tomato Salad with Spiced Quark',
      summary: 'Ripe vine tomatoes dressed with a spiced-quark spoon — tomatoes from one shop, quark from the other.',
      servings: 2,
      timeMinutes: 10,
      tags: ['vegetarian', 'german', 'lunch'],
      ingredients: [
        {
          label: 'Vine tomatoes',
          keywords: ['rispentomate'],
          qty: '500 g',
          exclude: ['ketchup', 'tomatenmark', 'passata', 'sauce'],
        },
        { label: 'Spiced quark', keywords: ['gewürzquark', 'quark'], qty: '200 g', exclude: ['quarkbrötchen', 'quark-brötchen'] },
        {
          label: 'Onion',
          keywords: ['zwiebel'],
          qty: '½',
          staple: true,
          exclude: ['lauchzwiebel', 'zwiebelmettwurst', 'röstzwiebel'],
        },
        { label: 'Olive oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '1 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Slice the tomatoes and thinly slice the onion; arrange on a plate.',
        'Loosen the spiced quark with the oil and a splash of water into a spoonable dressing.',
        'Spoon the quark over the tomatoes, season, and rest 5 minutes before serving.',
      ],
    },
    {
      id: 'edeka-edekacenter-seelachs-kartoffeln-rucola',
      title: 'Pan-fried Pollock with New Potatoes & Rucola',
      summary: 'Pollock fillet crisped in butter, with new potatoes and a peppery rucola salad — fish and potatoes from two shops.',
      servings: 2,
      timeMinutes: 30,
      tags: ['pescatarian', 'german', 'dinner'],
      ingredients: [
        { label: 'Pollock fillet', keywords: ['seelachs'], qty: '400 g' },
        { label: 'New potatoes', keywords: ['speisefrühkartoffel', 'frühkartoffel'], qty: '500 g' },
        { label: 'Rucola', keywords: ['rucola'], qty: '80 g' },
        {
          label: 'Butter',
          keywords: ['butter'],
          qty: '2 tbsp',
          staple: true,
          exclude: ['buttermilch', 'erdnussbutter', 'butterkäse', 'butterkeks', 'knoblauchbutter', 'butterfly', 'fassbutter'],
        },
        { label: 'Olive oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '1 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Boil the potatoes in their skins until tender, about 20 minutes; halve them.',
        'Pat the fillets dry, season, and fry in butter 3 minutes a side.',
        'Dress the rucola with olive oil and serve with the fish and potatoes.',
      ],
    },
  ],
};
