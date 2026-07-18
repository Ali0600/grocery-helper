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
  generatedAt: '2026-07-18',
  recipes: [
    // ---- single store: ALDI ----
    {
      id: 'zucchini-champignon-ricotta-pasta',
      title: 'Zucchini & Mushroom Pasta with Ricotta',
      summary: 'Pan-fried zucchini and brown mushrooms folded through pasta with spoonfuls of ricotta.',
      servings: 2,
      timeMinutes: 25,
      tags: ['vegetarian', 'italian', 'dinner'],
      ingredients: [
        { label: 'Zucchini', keywords: ['zucchini'], qty: '2' },
        { label: 'Brown mushrooms', keywords: ['kulturchampignon', 'champignon'], qty: '250 g' },
        { label: 'Ricotta', keywords: ['ricotta'], qty: '250 g' },
        { label: 'Tomato passata', keywords: ['passata'], qty: '200 ml' },
        { label: 'Pasta', keywords: ['gigli', 'nudel', 'pasta'], qty: '250 g', staple: true, exclude: ['sauce', 'pot', 'fix'] },
        { label: 'Garlic', keywords: ['knoblauch'], qty: '2 cloves', staple: true, exclude: ['wurst', 'baguette', 'butter'] },
        { label: 'Olive oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '2 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Boil the pasta in salted water until al dente.',
        'Fry the sliced zucchini and mushrooms in olive oil over high heat until browned; add the garlic near the end.',
        'Stir in the passata, season, then toss with the drained pasta.',
        'Serve topped with spoonfuls of ricotta.',
      ],
    },
    {
      id: 'aprikosen-nektarinen-milchreis',
      title: 'Apricot & Nectarine Milk Rice',
      summary: 'Ready-made milk rice topped with this week’s stone fruit — five minutes, no cooking.',
      servings: 2,
      timeMinutes: 5,
      tags: ['vegetarian', 'german', 'breakfast'],
      ingredients: [
        { label: 'Milk rice', keywords: ['milchreis'], qty: '400 g' },
        { label: 'Apricots', keywords: ['aprikose'], qty: '3', exclude: ['gebäck', 'blätterteig'] },
        { label: 'Nectarines', keywords: ['nektarine'], qty: '1' },
        {
          label: 'Honey or sugar',
          keywords: ['honig', 'zucker'],
          qty: '1 tbsp',
          staple: true,
          // 'zucker' is a substring of a soft drink's "Zero Zucker" and of real produce
          // (Zuckeraprikosen, Zuckermais) — none of them are the sugar jar.
          exclude: ['pepsi', 'cola', 'zero', 'zuckermais', 'zuckerapri', 'zuckerwatte', 'puderzucker'],
        },
      ],
      steps: [
        'Spoon the milk rice into two bowls.',
        'Stone and slice the apricots and nectarine and pile them on top.',
        'Drizzle with honey and serve.',
      ],
    },

    // ---- single store: Lidl ----
    {
      id: 'tomaten-mozzarella-nudelsalat',
      title: 'Tomato & Buffalo Mozzarella Pasta Salad',
      summary: 'A cold pasta salad with ripe tomatoes, torn buffalo mozzarella and green olives.',
      servings: 2,
      timeMinutes: 20,
      tags: ['vegetarian', 'italian', 'lunch'],
      ingredients: [
        { label: 'Pasta', keywords: ['rigatoni', 'nudel', 'pasta'], qty: '250 g', staple: true, exclude: ['sauce', 'pot', 'fix'] },
        { label: 'Buffalo mozzarella', keywords: ['mozzarella'], qty: '250 g' },
        {
          label: 'Tomatoes',
          keywords: ['tomaten mix', 'softtomaten', 'rispentomate', 'strauchtomate'],
          qty: '400 g',
          exclude: ['ketchup', 'sauce', 'passata'],
        },
        { label: 'Green olives', keywords: ['oliven'], qty: '100 g', exclude: ['olivenöl'] },
        { label: 'Olive oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '3 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Cook the pasta, drain and rinse under cold water.',
        'Quarter the tomatoes, tear the mozzarella, stone the olives.',
        'Toss everything with olive oil, salt and pepper and rest 10 minutes before serving.',
      ],
    },
    {
      id: 'kartoffel-bohnen-salat',
      title: 'Warm Potato & Green Bean Salad',
      summary: 'New potatoes and green beans dressed while still warm, with tomatoes and olives.',
      servings: 2,
      timeMinutes: 30,
      tags: ['vegan', 'german', 'lunch'],
      ingredients: [
        {
          label: 'New potatoes',
          keywords: ['frühkartoffel', 'speisefrühkartoffel', 'kartoffel'],
          qty: '600 g',
          exclude: ['kartoffelbrot', 'kartoffelgericht', 'chips', 'salat'],
        },
        {
          label: 'Green beans',
          keywords: ['buschbohnen', 'brechbohnen'],
          qty: '300 g',
        },
        { label: 'Tomatoes', keywords: ['tomaten mix', 'softtomaten'], qty: '250 g', exclude: ['ketchup', 'sauce'] },
        { label: 'Green olives', keywords: ['oliven'], qty: '80 g', exclude: ['olivenöl'] },
        { label: 'Olive oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '3 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Boil the potatoes in their skins until tender, 20 minutes; halve them while hot.',
        'Blanch the beans 4 minutes, then drain.',
        'Dress the warm potatoes and beans with olive oil, salt and pepper; fold in the tomatoes and olives.',
      ],
    },

    // ---- single store: EDEKA ----
    {
      id: 'kirsch-himbeer-skyr',
      title: 'Cherry & Raspberry Skyr Bowl',
      summary: 'High-protein skyr under a pile of cherries and raspberries.',
      servings: 2,
      timeMinutes: 5,
      tags: ['vegetarian', 'german', 'breakfast'],
      ingredients: [
        { label: 'Skyr', keywords: ['skyr'], qty: '400 g' },
        { label: 'Cherries', keywords: ['kirschen'], qty: '200 g', exclude: ['tomaten', 'sauce'] },
        { label: 'Raspberries', keywords: ['himbeere'], qty: '125 g' },
        {
          label: 'Honey or sugar',
          keywords: ['honig', 'zucker'],
          qty: '1 tbsp',
          staple: true,
          // 'zucker' is a substring of a soft drink's "Zero Zucker" and of real produce
          // (Zuckeraprikosen, Zuckermais) — none of them are the sugar jar.
          exclude: ['pepsi', 'cola', 'zero', 'zuckermais', 'zuckerapri', 'zuckerwatte', 'puderzucker'],
        },
      ],
      steps: [
        'Stir the skyr smooth and divide between two bowls.',
        'Stone the cherries and scatter them with the raspberries on top.',
        'Finish with a drizzle of honey.',
      ],
    },
    {
      id: 'nackensteak-lauchzwiebel-baguette',
      title: 'Pork Neck Steaks with Spring Onions & Herb Baguette',
      summary: 'Marinated neck steaks seared hard, with charred spring onions, sweet pepper and warm baguette.',
      servings: 2,
      timeMinutes: 25,
      tags: ['meat', 'german', 'dinner'],
      ingredients: [
        { label: 'Marinated pork neck steaks', keywords: ['schweinenacken', 'nackensteak'], qty: '2' },
        { label: 'Spring onions', keywords: ['lauchzwiebel'], qty: '1 bunch' },
        { label: 'Pointed pepper', keywords: ['spitzpaprika'], qty: '2' },
        { label: 'Herb baguette', keywords: ['baguette'], qty: '1', exclude: ['salami', 'bistro'] },
        { label: 'Oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '1 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Bake the baguette according to the packet.',
        'Sear the steaks 3–4 minutes a side in a very hot pan, then rest them.',
        'In the same pan, char the halved spring onions and sliced pepper for 3 minutes.',
        'Slice the steaks and serve with the vegetables and bread.',
      ],
    },

    // ---- single store: E center ----
    {
      id: 'halloumi-edamame-spiess',
      title: 'Halloumi Skewers with Edamame & Zaziki',
      summary: 'Grilled halloumi and carrot skewers with warm edamame and a cool zaziki dip.',
      servings: 2,
      timeMinutes: 20,
      tags: ['vegetarian', 'gluten-free', 'mediterranean', 'dinner'],
      ingredients: [
        { label: 'Halloumi', keywords: ['halloumi'], qty: '250 g' },
        { label: 'Edamame', keywords: ['edamame'], qty: '200 g' },
        { label: 'Bunched carrots', keywords: ['bundmöhre', 'möhre'], qty: '1 bunch' },
        { label: 'Zaziki', keywords: ['zaziki'], qty: '150 g' },
        { label: 'Lemon', keywords: ['zitrone'], qty: '1' },
        { label: 'Olive oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '2 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Cube the halloumi and cut the carrots into batons; thread them onto skewers.',
        'Brush with oil and grill or pan-fry 3 minutes a side until the cheese colours.',
        'Warm the edamame in salted water for 4 minutes.',
        'Serve with zaziki and a squeeze of lemon.',
      ],
    },
    {
      id: 'putenbrust-gouda-broetchen',
      title: 'Turkey & Gouda Rolls with Pickles',
      summary: 'Fresh rolls layered with turkey breast, young Gouda and sliced pickles.',
      servings: 2,
      timeMinutes: 10,
      tags: ['meat', 'german', 'lunch'],
      ingredients: [
        { label: 'Turkey breast', keywords: ['putenbrust'], qty: '150 g' },
        { label: 'Gouda', keywords: ['gouda'], qty: '100 g' },
        { label: 'Pickles', keywords: ['einlegegurke', 'gurkendill', 'gewürzgurke'], qty: '4' },
        {
          label: 'Rolls',
          keywords: ['roggenbrötchen', 'dinkelbrötchen', 'kürbiskernbrötchen', 'brötchen'],
          qty: '4',
          exclude: ['fleischkäse', 'schoko', 'nuss-nougat'],
        },
        {
          label: 'Butter',
          keywords: ['butter'],
          qty: '2 tbsp',
          staple: true,
          exclude: ['buttermilch', 'erdnussbutter', 'butterkäse', 'butterkeks', 'knoblauchbutter', 'butterfly'],
        },
      ],
      steps: [
        'Halve the rolls and butter them.',
        'Layer on the turkey breast, sliced Gouda and pickle slices.',
        'Press together and cut in half to serve.',
      ],
    },

    // ---- single store: REWE ----
    {
      id: 'seelachs-spargel-wildkraeuter',
      title: 'Pan-fried Pollock with Asparagus & Wild Herb Salad',
      summary: 'Pollock fillet crisped in butter, with quick-fried asparagus and a peppery herb salad.',
      servings: 2,
      timeMinutes: 25,
      tags: ['pescatarian', 'gluten-free', 'german', 'dinner'],
      ingredients: [
        { label: 'Pollock fillet', keywords: ['seelachs'], qty: '400 g' },
        { label: 'Asparagus', keywords: ['spargel', 'klaistower'], qty: '400 g' },
        { label: 'Wild herb salad', keywords: ['wildkräuter', 'schäfersalat', 'lollo'], qty: '100 g' },
        {
          label: 'Butter',
          keywords: ['butter'],
          qty: '2 tbsp',
          staple: true,
          exclude: ['buttermilch', 'erdnussbutter', 'butterkäse', 'butterkeks', 'knoblauchbutter', 'butterfly'],
        },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Pat the fillets dry, season, and fry in butter 3 minutes a side.',
        'Cut the asparagus into lengths and fry 5 minutes in the same pan.',
        'Serve the fish and asparagus on the herb salad, with the pan butter spooned over.',
      ],
    },
    {
      id: 'rumpsteak-tomatensalat',
      title: 'Rump Steak with Tomato Salad & Baguette',
      summary: 'A seared rump steak resting on a sharp tomato and lollo salad, with warm baguette.',
      servings: 2,
      timeMinutes: 25,
      tags: ['meat', 'german', 'dinner'],
      ingredients: [
        { label: 'Rump steak', keywords: ['rumpsteak'], qty: '2' },
        { label: 'Mini plum tomatoes', keywords: ['rispentomate', 'romatomate'], qty: '300 g' },
        { label: 'Lollo salad', keywords: ['lollo'], qty: '1 head' },
        { label: 'Baguette', keywords: ['baguette'], qty: '1', exclude: ['salami', 'bistro'] },
        { label: 'Olive oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '2 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Bring the steaks to room temperature and season generously.',
        'Sear 2–3 minutes a side in a smoking-hot pan, then rest 5 minutes.',
        'Toss the halved tomatoes and torn lollo with olive oil, salt and pepper.',
        'Slice the steak over the salad and serve with warm baguette.',
      ],
    },

    // ---- two stores ----
    {
      id: 'burrata-wildkraeuter-kirschen',
      title: 'Burrata & Wild Herb Salad with Cherries',
      summary: 'Torn burrata over peppery leaves with asparagus and sweet cherries — a two-shop plate.',
      servings: 2,
      timeMinutes: 15,
      tags: ['vegetarian', 'italian', 'lunch'],
      ingredients: [
        { label: 'Burrata', keywords: ['burrata'], qty: '250 g' },
        { label: 'Wild herb salad', keywords: ['wildkräuter', 'schäfersalat'], qty: '100 g' },
        { label: 'Cherries', keywords: ['kirschen'], qty: '150 g', exclude: ['tomaten', 'sauce'] },
        { label: 'Asparagus', keywords: ['spargel', 'klaistower'], qty: '250 g' },
        { label: 'Olive oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '2 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Blanch the asparagus 3 minutes and cool it under cold water.',
        'Spread the leaves on a platter, add the asparagus and stoned, halved cherries.',
        'Tear the burrata over the top, then oil, salt and pepper.',
      ],
    },
    {
      id: 'haehnchenschnitzel-champignon-ricotta',
      title: 'Chicken Schnitzel with Mushroom Ricotta Sauce',
      summary: 'Crisp chicken schnitzel under a quick mushroom sauce loosened with ricotta and lemon.',
      servings: 2,
      timeMinutes: 30,
      tags: ['meat', 'german', 'dinner'],
      ingredients: [
        { label: 'Chicken schnitzel', keywords: ['hähnchenschnitzel'], qty: '2' },
        { label: 'Brown mushrooms', keywords: ['kulturchampignon', 'champignon'], qty: '250 g' },
        { label: 'Ricotta', keywords: ['ricotta'], qty: '150 g' },
        { label: 'Lemon', keywords: ['zitrone'], qty: '1' },
        {
          label: 'Rice',
          keywords: ['basmati', 'reis'],
          qty: '150 g',
          staple: true,
          exclude: ['milchreis', 'reiswaffel', 'preis'],
        },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Cook the rice.',
        'Fry the schnitzel 4 minutes a side until golden, then keep warm.',
        'Fry the sliced mushrooms hard in the same pan, stir in the ricotta and a squeeze of lemon, and season.',
        'Spoon the sauce over the schnitzel and serve with the rice.',
      ],
    },
    {
      id: 'fladenbrot-halloumi-mais',
      title: 'Fladenbrot with Halloumi, Corn & Zaziki',
      summary: 'Warm flatbread stuffed with grilled halloumi, charred sweetcorn, pepper and zaziki.',
      servings: 2,
      timeMinutes: 25,
      tags: ['vegetarian', 'mediterranean', 'dinner'],
      ingredients: [
        { label: 'Fladenbrot', keywords: ['fladenbrot'], qty: '1' },
        { label: 'Halloumi', keywords: ['halloumi'], qty: '250 g' },
        { label: 'Sweetcorn', keywords: ['zuckermais'], qty: '2 cobs' },
        { label: 'Zaziki', keywords: ['zaziki'], qty: '150 g' },
        { label: 'Pointed pepper', keywords: ['spitzpaprika'], qty: '2' },
        { label: 'Olive oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '2 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Grill the corn and pepper until charred in places, then cut the kernels off the cob.',
        'Fry the sliced halloumi 2 minutes a side.',
        'Warm the flatbread, split it, and fill with the vegetables, halloumi and zaziki.',
      ],
    },
    {
      id: 'raeucherlachs-walnussbrot-dill',
      title: 'Smoked Salmon on Walnut Bread with Dill',
      summary: 'Smoked salmon and cream cheese on walnut bread, showered with fresh dill.',
      servings: 2,
      timeMinutes: 10,
      tags: ['pescatarian', 'german', 'breakfast'],
      ingredients: [
        { label: 'Smoked salmon', keywords: ['räucher-lachs', 'räucherlachs'], qty: '150 g', exclude: ['salat'] },
        { label: 'Cream cheese', keywords: ['philadelphia', 'frischkäse'], qty: '150 g' },
        { label: 'Walnut bread', keywords: ['walnussbrot', 'walnuss-brötchen'], qty: '4 slices', exclude: ['walnussöl'] },
        { label: 'Dill', keywords: ['dill'], qty: '½ bunch', exclude: ['gurkendill', 'dillhappen'] },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Spread the walnut bread thickly with cream cheese.',
        'Drape the smoked salmon over the top.',
        'Finish with plenty of chopped dill and a good grind of pepper.',
      ],
    },
    {
      id: 'schweinespiess-mais-tomatensalat',
      title: 'Pork Skewers with Corn & Tomato Salad',
      summary: 'Pork skewers off the grill pan with buttery sweetcorn and a spring-onion tomato salad.',
      servings: 2,
      timeMinutes: 25,
      tags: ['meat', 'german', 'dinner'],
      ingredients: [
        {
          label: 'Pork skewers',
          keywords: ['schweinefiletspieße', 'schweinefleisch-spieß', 'schweinebauch-spieß', 'schweinenacken'],
          qty: '4',
        },
        { label: 'Sweetcorn', keywords: ['goldmais', 'zuckermais'], qty: '1 tin' },
        { label: 'Tomatoes', keywords: ['rispentomate', 'romatomate'], qty: '300 g' },
        { label: 'Spring onions', keywords: ['lauchzwiebel'], qty: '1 bunch' },
        { label: 'Olive oil', keywords: ['olivenöl', 'speiseöl', 'rapsöl'], exclude: ['grissini', 'antipasti', 'tischset'], qty: '2 tbsp', staple: true },
        { label: 'Salt & pepper', keywords: ['speisesalz', 'meersalz'], staple: true },
      ],
      steps: [
        'Cook the skewers in a hot grill pan, 4 minutes a side, and rest them.',
        'Warm the drained sweetcorn through with a knob of butter or oil.',
        'Toss the quartered tomatoes with sliced spring onions, oil, salt and pepper, and serve alongside.',
      ],
    },
  ],
};
