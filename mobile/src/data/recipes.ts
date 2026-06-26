// AI-authored recipes — generated OFFLINE by Claude Code from the current grocery.db
// deals + the always-have staples, then bundled into the app and shipped via OTA. There is
// NO runtime LLM/API call: the Recipes screen renders this file and matches each ingredient
// to the user's loaded offers client-side (see ../recipes.ts). Regenerate weekly when the
// flyers refresh (see docs/recipes.md). Each ingredient's `keywords` are German name stems
// matched as substrings of offer names (same signal as the Basket); `staple: true` marks a
// pantry item assumed on hand. Quantities are written for `servings`; the app scales them.

import { RecipesData } from '../types';

export const RECIPES: RecipesData = {
  generatedFor: '10115',
  generatedAt: '2026-06-26',
  recipes: [
    {
      id: 'zucchini-tomato-pasta',
      title: 'Zucchini & Tomato Spaghetti',
      summary: 'A quick weeknight pasta built around on-sale zucchini and tomatoes.',
      servings: 2,
      timeMinutes: 20,
      tags: ['vegetarian', 'italian', 'dinner'],
      ingredients: [
        { label: 'Spaghetti', keywords: ['spaghetti', 'combino'], qty: '250 g' },
        { label: 'Zucchini', keywords: ['zucchini'], qty: '1' },
        { label: 'Tomatoes', keywords: ['tomate'], qty: '300 g', exclude: ['ketchup', 'mark', 'passiert', 'sauce', 'sugo', 'getrocknet'] },
        { label: 'Gouda or Emmentaler (grated)', keywords: ['gouda', 'emmentaler'], qty: '50 g' },
        { label: 'Garlic', keywords: ['knoblauch'], qty: '2 cloves', staple: true },
        { label: 'Olive oil', keywords: ['olivenöl', 'olivenoel'], qty: '2 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['salz', 'pfeffer'], staple: true },
      ],
      steps: [
        'Boil the spaghetti in salted water until al dente.',
        'Dice the zucchini and tomatoes; sauté in olive oil with the garlic for ~6 min.',
        'Toss the drained pasta with the vegetables; season and top with grated cheese.',
      ],
    },
    {
      id: 'caprese-avocado',
      title: 'Tomato, Mozzarella & Avocado Salad',
      summary: 'A no-cook lunch using on-sale mozzarella, tomatoes and avocado.',
      servings: 2,
      timeMinutes: 10,
      tags: ['vegetarian', 'italian', 'lunch'],
      ingredients: [
        { label: 'Mozzarella', keywords: ['mozzarella'], qty: '1 ball' },
        { label: 'Tomatoes', keywords: ['tomate'], qty: '300 g', exclude: ['ketchup', 'mark', 'passiert', 'sauce', 'sugo', 'getrocknet'] },
        { label: 'Avocado', keywords: ['avocado'], qty: '1' },
        { label: 'Olive oil', keywords: ['olivenöl', 'olivenoel'], qty: '1 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['salz', 'pfeffer'], staple: true },
      ],
      steps: [
        'Slice the tomatoes, mozzarella and avocado.',
        'Arrange on a plate, drizzle with olive oil and season.',
      ],
    },
    {
      id: 'chicken-schnitzel-feldsalat',
      title: 'Chicken Minute Schnitzel with Feldsalat',
      summary: 'Pan-fried chicken schnitzel with a fresh on-sale lamb’s-lettuce side.',
      servings: 2,
      timeMinutes: 20,
      tags: ['meat', 'german', 'dinner'],
      ingredients: [
        { label: 'Chicken minute schnitzel', keywords: ['minutenschnitzel', 'minutenchnitzel', 'hähnchen', 'hahnchen'], qty: '400 g', exclude: ['döner', 'nuggets', 'wings'] },
        { label: 'Feldsalat (lamb’s lettuce)', keywords: ['feldsalat'], qty: '150 g' },
        { label: 'Lemon', keywords: ['zitrone', 'limette'], qty: '½', staple: true },
        { label: 'Oil', keywords: ['öl', 'oel'], qty: '2 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['salz', 'pfeffer'], staple: true },
      ],
      steps: [
        'Season the schnitzel and pan-fry in oil 3–4 min per side.',
        'Dress the feldsalat with a squeeze of lemon, oil, salt and pepper.',
        'Serve the schnitzel with the salad and a lemon wedge.',
      ],
    },
    {
      id: 'melon-mango-grapefruit-salad',
      title: 'Melon, Mango & Grapefruit Salad',
      summary: 'A vegan, gluten-free fruit bowl made entirely from on-sale fruit.',
      servings: 2,
      timeMinutes: 10,
      tags: ['vegan', 'vegetarian', 'gluten-free', 'snack'],
      ingredients: [
        { label: 'Watermelon', keywords: ['wassermelone', 'melone'], qty: '¼' },
        { label: 'Mango', keywords: ['mango'], qty: '1', exclude: ['sorbet', 'chutney', 'saft'] },
        { label: 'Grapefruit', keywords: ['grapefruit'], qty: '1' },
        { label: 'Banana', keywords: ['banane'], qty: '1' },
      ],
      steps: [
        'Cube the melon and mango; segment the grapefruit; slice the banana.',
        'Toss together and chill before serving.',
      ],
    },
    {
      id: 'quark-banana-bowl',
      title: 'Quark & Banana Breakfast Bowl',
      summary: 'A high-protein breakfast on on-sale quark, topped with banana.',
      servings: 2,
      timeMinutes: 5,
      tags: ['vegetarian', 'breakfast'],
      ingredients: [
        { label: 'Quark', keywords: ['speisequark', 'quark'], qty: '500 g', exclude: ['riegel', 'kräuter', 'sour'] },
        { label: 'Banana', keywords: ['banane'], qty: '2' },
        { label: 'Honey', keywords: ['honig'], qty: '2 tbsp', staple: true },
        { label: 'Oats', keywords: ['haferflocken', 'müsli', 'muesli'], qty: '4 tbsp', staple: true },
      ],
      steps: [
        'Spoon the quark into two bowls.',
        'Top with sliced banana, a drizzle of honey and a sprinkle of oats.',
      ],
    },
    {
      id: 'seelachs-zucchini',
      title: 'Pan-fried Seelachs with Zucchini',
      summary: 'A light pescatarian dinner using on-sale seelachs fillet and zucchini.',
      servings: 2,
      timeMinutes: 25,
      tags: ['pescatarian', 'dinner'],
      ingredients: [
        { label: 'Seelachs fillet', keywords: ['seelachs', 'saibling'], qty: '300 g' },
        { label: 'Zucchini', keywords: ['zucchini'], qty: '1' },
        { label: 'Butter', keywords: ['butter'], qty: '20 g', exclude: ['margarine', 'erdnuss'] },
        { label: 'Lemon', keywords: ['zitrone', 'limette'], qty: '½', staple: true },
        { label: 'Salt & pepper', keywords: ['salz', 'pfeffer'], staple: true },
      ],
      steps: [
        'Slice and sauté the zucchini in half the butter until tender; set aside.',
        'Season the fish and fry in the rest of the butter 3 min per side.',
        'Finish with a squeeze of lemon and serve over the zucchini.',
      ],
    },
    {
      id: 'beef-hueftsteak-romana',
      title: 'Beef Hüftsteak with Romana Salad',
      summary: 'On-sale rump steak seared and served with crisp romana lettuce.',
      servings: 2,
      timeMinutes: 20,
      tags: ['meat', 'german', 'dinner'],
      ingredients: [
        { label: 'Beef rump steak', keywords: ['hüftsteak', 'hueftsteak', 'rinder-hüft', 'hüftspieß'], qty: '2' },
        { label: 'Mini romana salad', keywords: ['romana', 'salat-mix', 'salat mix'], qty: '1' },
        { label: 'Olive oil', keywords: ['olivenöl', 'olivenoel'], qty: '1 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['salz', 'pfeffer'], staple: true },
      ],
      steps: [
        'Bring the steaks to room temperature; season well.',
        'Sear in a hot pan ~2–3 min per side; rest 5 min.',
        'Serve sliced over romana dressed with oil, salt and pepper.',
      ],
    },
    {
      id: 'buttermilch-pancakes',
      title: 'Buttermilk Pancakes',
      summary: 'Fluffy pancakes from on-sale buttermilk and pantry staples.',
      servings: 2,
      timeMinutes: 25,
      tags: ['vegetarian', 'breakfast'],
      ingredients: [
        { label: 'Buttermilk', keywords: ['buttermilch'], qty: '250 ml' },
        { label: 'Butter', keywords: ['butter'], qty: '20 g', exclude: ['margarine', 'erdnuss'] },
        { label: 'Flour', keywords: ['mehl'], qty: '200 g', staple: true },
        { label: 'Egg', keywords: ['eier', 'freilandei'], qty: '1', staple: true },
        { label: 'Sugar', keywords: ['zucker'], qty: '1 tbsp', staple: true },
      ],
      steps: [
        'Whisk flour, sugar, egg and buttermilk into a smooth batter.',
        'Fry small pancakes in a little butter until golden on both sides.',
      ],
    },
    {
      id: 'aubergine-tomato-bake',
      title: 'Aubergine & Tomato Bake',
      summary: 'A comforting vegetarian bake using on-sale aubergine and tomatoes.',
      servings: 2,
      timeMinutes: 40,
      tags: ['vegetarian', 'italian', 'dinner'],
      ingredients: [
        { label: 'Aubergine', keywords: ['aubergine'], qty: '1' },
        { label: 'Tomatoes', keywords: ['tomate'], qty: '400 g', exclude: ['ketchup', 'mark', 'passiert', 'sauce', 'sugo', 'getrocknet'] },
        { label: 'Gouda or Emmentaler (grated)', keywords: ['gouda', 'emmentaler'], qty: '80 g' },
        { label: 'Onion', keywords: ['zwiebel'], qty: '1', staple: true },
        { label: 'Garlic', keywords: ['knoblauch'], qty: '2 cloves', staple: true },
        { label: 'Olive oil', keywords: ['olivenöl', 'olivenoel'], qty: '2 tbsp', staple: true },
      ],
      steps: [
        'Slice the aubergine and brush with oil; layer with tomato and onion in a dish.',
        'Top with grated cheese and bake at 200°C for ~25 min until golden.',
      ],
    },
    {
      id: 'chicken-doener-bowl',
      title: 'Chicken Döner Rice Bowl',
      summary: 'On-sale chicken döner over rice with a quick quark-garlic sauce.',
      servings: 2,
      timeMinutes: 20,
      tags: ['meat', 'german', 'dinner'],
      ingredients: [
        { label: 'Chicken döner', keywords: ['döner', 'doener'], qty: '300 g' },
        { label: 'Salad mix', keywords: ['salat-mix', 'salat mix', 'romana'], qty: '150 g' },
        { label: 'Tomatoes', keywords: ['tomate'], qty: '2', exclude: ['ketchup', 'mark', 'passiert', 'sauce', 'sugo', 'getrocknet'] },
        { label: 'Quark', keywords: ['speisequark', 'quark'], qty: '150 g', exclude: ['riegel'] },
        { label: 'Rice', keywords: ['reis'], qty: '150 g', staple: true },
        { label: 'Garlic', keywords: ['knoblauch'], qty: '1 clove', staple: true },
      ],
      steps: [
        'Cook the rice. Pan-heat the döner meat until crisp at the edges.',
        'Stir the grated garlic into the quark with a little salt.',
        'Build bowls: rice, döner, salad, tomato; spoon over the quark-garlic sauce.',
      ],
    },
    {
      id: 'corn-coleslaw-baguette',
      title: 'Corn & Coleslaw Baguette',
      summary: 'A fast vegetarian lunch from on-sale coleslaw, sweetcorn and baguette.',
      servings: 2,
      timeMinutes: 10,
      tags: ['vegetarian', 'lunch'],
      ingredients: [
        { label: 'Coleslaw', keywords: ['coleslaw'], qty: '200 g' },
        { label: 'Sweetcorn', keywords: ['mais', 'goldmais'], qty: '1 tin' },
        { label: 'Baguette', keywords: ['baguette', 'ciabatta'], qty: '1' },
        { label: 'Gouda or Emmentaler', keywords: ['gouda', 'emmentaler'], qty: '40 g' },
      ],
      steps: [
        'Drain the corn and stir it through the coleslaw.',
        'Halve and lightly toast the baguette; fill with the corn-slaw and sliced cheese.',
      ],
    },
  ],
};
