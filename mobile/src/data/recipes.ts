// AI-authored recipes — generated OFFLINE by Claude Code from the current grocery.db
// deals + the always-have staples, then bundled into the app and shipped via OTA. There is
// NO runtime LLM/API call: the Recipes screen renders this file and matches each ingredient
// to the user's loaded offers client-side (see ../recipes.ts). Regenerate weekly when the
// flyers refresh (see docs/recipes.md). Each ingredient's `keywords` are German name stems
// matched as substrings of offer names (same signal as the Basket); `staple: true` marks a
// pantry item assumed on hand. Quantities are written for `servings`; the app scales them.

import { RecipesData } from '../types';

export const RECIPES: RecipesData = {
  generatedFor: '10713',
  generatedAt: '2026-06-29',
  recipes: [
    {
      id: 'spring-onion-cheese-omelette',
      title: 'Spring Onion & Cheese Omelette',
      summary: 'A fast breakfast built on on-sale spring onions and Gouda or Emmentaler.',
      servings: 2,
      timeMinutes: 12,
      tags: ['vegetarian', 'german', 'breakfast'],
      ingredients: [
        { label: 'Eggs', keywords: ['eier'], qty: '4', staple: true },
        { label: 'Spring onions', keywords: ['lauchzwiebel'], qty: '1 bunch' },
        { label: 'Gouda or Emmentaler', keywords: ['gouda', 'emmentaler'], qty: '60 g' },
        { label: 'Butter', keywords: ['butter'], qty: '1 tbsp', staple: true, exclude: ['buttermilch', 'erdnuss'] },
        { label: 'Salt & pepper', keywords: ['salz', 'pfeffer'], staple: true },
      ],
      steps: [
        'Whisk the eggs with salt and pepper; slice the spring onions.',
        'Melt the butter in a pan, pour in the eggs and scatter the spring onions on top.',
        'When almost set, add the grated cheese, fold over and serve.',
      ],
    },
    {
      id: 'salmon-cucumber-salad',
      title: 'Pan-fried Salmon with Cucumber Salad',
      summary: 'On-sale salmon fillet with a crisp cucumber-and-yogurt salad.',
      servings: 2,
      timeMinutes: 20,
      tags: ['pescatarian', 'nordic', 'dinner'],
      ingredients: [
        { label: 'Salmon fillet', keywords: ['lachsfilet', 'lachs'], qty: '2 fillets', exclude: ['vegan', 'schinken', 'aufschnitt', 'art', 'garnele'] },
        { label: 'Cucumber', keywords: ['gurke'], qty: '1' },
        { label: 'Yogurt', keywords: ['joghurt'], qty: '150 g', exclude: ['riegel', 'drink'] },
        { label: 'Dill', keywords: ['dill'], qty: '2 tbsp', staple: true },
        { label: 'Olive oil', keywords: ['olivenöl', 'olivenoel'], qty: '1 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['salz', 'pfeffer'], staple: true },
      ],
      steps: [
        'Pan-fry the salmon skin-side down in oil for ~4 min, flip and cook 2 min more.',
        'Thinly slice the cucumber; mix with the yogurt, dill, salt and pepper.',
        'Serve the salmon over the cucumber salad.',
      ],
    },
    {
      id: 'chicken-kohlrabi-slaw',
      title: 'Pan-fried Chicken with Kohlrabi Slaw',
      summary: 'On-sale chicken with a fresh, crunchy kohlrabi slaw.',
      servings: 2,
      timeMinutes: 25,
      tags: ['meat', 'german', 'dinner'],
      ingredients: [
        { label: 'Chicken', keywords: ['hähnchen'], qty: '400 g', exclude: ['wurst', 'aufschnitt', 'pastete', 'döner', 'mini', 'pelmeni'] },
        { label: 'Kohlrabi', keywords: ['kohlrabi'], qty: '1' },
        { label: 'Yogurt', keywords: ['joghurt'], qty: '100 g', exclude: ['riegel', 'drink'] },
        { label: 'Oil', keywords: ['öl', 'oel'], qty: '2 tbsp', staple: true, exclude: ['knoblauch'] },
        { label: 'Salt & pepper', keywords: ['salz', 'pfeffer'], staple: true },
      ],
      steps: [
        'Season the chicken and pan-fry in oil until golden and cooked through.',
        'Julienne the kohlrabi and toss with the yogurt, salt and pepper.',
        'Slice the chicken and serve over the slaw.',
      ],
    },
    {
      id: 'rinderrouladen',
      title: 'Beef Roulades (Rinderrouladen)',
      summary: 'A German classic from on-sale beef roulades, mustard and pickles.',
      servings: 2,
      timeMinutes: 90,
      tags: ['meat', 'german', 'dinner'],
      ingredients: [
        { label: 'Beef roulades', keywords: ['rouladen'], qty: '2' },
        { label: 'Mustard', keywords: ['senf'], qty: '2 tbsp' },
        { label: 'Pickled cucumber', keywords: ['gurke'], qty: '1' },
        { label: 'Onion', keywords: ['zwiebel'], qty: '1', staple: true },
        { label: 'Oil', keywords: ['öl', 'oel'], qty: '2 tbsp', staple: true, exclude: ['knoblauch'] },
        { label: 'Salt & pepper', keywords: ['salz', 'pfeffer'], staple: true },
      ],
      steps: [
        'Spread each beef slice with mustard, salt and pepper; lay on pickle and onion strips.',
        'Roll up, fix with toothpicks and sear in oil on all sides.',
        'Add a splash of water, cover and braise gently for ~75 min until tender.',
      ],
    },
    {
      id: 'watermelon-cucumber-salad',
      title: 'Watermelon, Cucumber & Mint Salad',
      summary: 'A no-cook summer salad from on-sale watermelon and cucumber.',
      servings: 2,
      timeMinutes: 10,
      tags: ['vegan', 'mediterranean', 'lunch'],
      ingredients: [
        { label: 'Watermelon', keywords: ['wassermelone', 'melone'], qty: '400 g' },
        { label: 'Cucumber', keywords: ['gurke'], qty: '1' },
        { label: 'Spring onions', keywords: ['lauchzwiebel'], qty: '2' },
        { label: 'Mint', keywords: ['minze'], qty: '1 handful', staple: true },
        { label: 'Olive oil', keywords: ['olivenöl', 'olivenoel'], qty: '1 tbsp', staple: true },
        { label: 'Salt', keywords: ['salz'], staple: true },
      ],
      steps: [
        'Cube the watermelon and cucumber; thinly slice the spring onions.',
        'Toss with torn mint, olive oil and a pinch of salt. Serve cold.',
      ],
    },
    {
      id: 'yogurt-cherry-bowl',
      title: 'Yogurt Bowl with Cherries & Banana',
      summary: 'A 5-minute breakfast using on-sale yogurt, cherries and banana.',
      servings: 2,
      timeMinutes: 5,
      tags: ['vegetarian', 'american', 'breakfast'],
      ingredients: [
        { label: 'Yogurt', keywords: ['joghurt'], qty: '300 g', exclude: ['riegel', 'drink'] },
        { label: 'Cherries', keywords: ['kirsch'], qty: '150 g' },
        { label: 'Banana', keywords: ['banane'], qty: '1' },
        { label: 'Honey or sugar', keywords: ['honig', 'zucker'], qty: '1 tbsp', staple: true },
      ],
      steps: [
        'Spoon the yogurt into bowls.',
        'Top with pitted cherries and sliced banana; drizzle with honey.',
      ],
    },
    {
      id: 'avocado-toast-radish',
      title: 'Avocado Toast with Radishes',
      summary: 'On-sale avocado and radishes on toasted baguette.',
      servings: 2,
      timeMinutes: 10,
      tags: ['vegan', 'american', 'lunch'],
      ingredients: [
        { label: 'Baguette or rolls', keywords: ['baguette', 'brötchen'], qty: '4 slices', exclude: ['donut', 'aufstrich'] },
        { label: 'Avocado', keywords: ['avocado'], qty: '1' },
        { label: 'Radishes', keywords: ['radieschen'], qty: '4' },
        { label: 'Spring onions', keywords: ['lauchzwiebel'], qty: '1' },
        { label: 'Olive oil', keywords: ['olivenöl', 'olivenoel'], qty: '1 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['salz', 'pfeffer'], staple: true },
      ],
      steps: [
        'Toast the baguette slices.',
        'Mash the avocado with salt, pepper and olive oil; spread on the toast.',
        'Top with thinly sliced radishes and spring onions.',
      ],
    },
    {
      id: 'baked-seelachs-quark-dip',
      title: 'Baked Seelachs with Quark-Cucumber Dip',
      summary: 'On-sale seelachs fillet baked, with a cool quark and cucumber dip.',
      servings: 2,
      timeMinutes: 25,
      tags: ['pescatarian', 'german', 'dinner'],
      ingredients: [
        { label: 'Seelachs fillet', keywords: ['seelachs'], qty: '2 fillets' },
        { label: 'Quark', keywords: ['quark'], qty: '200 g', exclude: ['riegel'] },
        { label: 'Cucumber', keywords: ['gurke'], qty: '1/2' },
        { label: 'Dill', keywords: ['dill'], qty: '2 tbsp', staple: true },
        { label: 'Oil', keywords: ['öl', 'oel'], qty: '1 tbsp', staple: true, exclude: ['knoblauch'] },
        { label: 'Salt & pepper', keywords: ['salz', 'pfeffer'], staple: true },
      ],
      steps: [
        'Season the fillets, brush with oil and bake at 200°C for ~15 min.',
        'Grate the cucumber, squeeze out water and stir into the quark with dill, salt and pepper.',
        'Serve the fish with the dip.',
      ],
    },
    {
      id: 'pork-schnitzel-broetchen',
      title: 'Pork Schnitzel Brötchen',
      summary: 'A hearty sandwich from on-sale pork schnitzel and fresh rolls.',
      servings: 2,
      timeMinutes: 20,
      tags: ['meat', 'german', 'lunch'],
      ingredients: [
        { label: 'Pork schnitzel', keywords: ['schnitzel'], qty: '2', exclude: ['hähnchen', 'vegan', 'cordon'] },
        { label: 'Rolls', keywords: ['brötchen', 'laugenbrötchen'], qty: '2' },
        { label: 'Lettuce', keywords: ['romana', 'kopfsalat', 'blattsalat'], qty: '4 leaves' },
        { label: 'Mustard', keywords: ['senf'], qty: '1 tbsp' },
        { label: 'Oil', keywords: ['öl', 'oel'], qty: '2 tbsp', staple: true, exclude: ['knoblauch'] },
        { label: 'Salt & pepper', keywords: ['salz', 'pfeffer'], staple: true },
      ],
      steps: [
        'Season and pan-fry the schnitzel in oil until golden on both sides.',
        'Halve the rolls and spread with mustard.',
        'Fill with the schnitzel and lettuce.',
      ],
    },
    {
      id: 'kiwi-banana-buttermilk-smoothie',
      title: 'Kiwi-Banana Buttermilk Smoothie',
      summary: 'A tangy smoothie from on-sale kiwi, banana and buttermilk.',
      servings: 2,
      timeMinutes: 5,
      tags: ['vegetarian', 'american', 'breakfast'],
      ingredients: [
        { label: 'Kiwi', keywords: ['kiwi'], qty: '2' },
        { label: 'Banana', keywords: ['banane'], qty: '1' },
        { label: 'Buttermilk', keywords: ['buttermilch'], qty: '300 ml' },
        { label: 'Honey or sugar', keywords: ['honig', 'zucker'], qty: '1 tbsp', staple: true },
      ],
      steps: [
        'Peel the kiwi and banana.',
        'Blend with the buttermilk and honey until smooth.',
      ],
    },
  ],
};
