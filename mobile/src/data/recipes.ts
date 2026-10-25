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
  exclude: ['wurst', 'baguette', 'butter', 'creme', 'sauce', 'garnelen', 'pizzabrot', 'naan'],
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
  exclude: ['buttermilch', 'erdnussbutter', 'peanut butter', 'butterkäse', 'butterkeks', 'knoblauchbutter', 'kräuterbutter', 'butterfly', 'fassbutter', 'brotaufstrich', 'croissant', 'baguette', 'kuchen', 'rama', 'butterschmalz', 'plätzchen', 'blätterteig', 'butter chicken'],
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
  exclude: ['milchreis', 'milchschnitte', 'kokosnussmilch', 'buttermilch', 'kondensmilch', 'kaffee-milch', 'müllermilch', 'schoko'],
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

// 'marzipan': Lidl's "Marzipankartoffeln" are sweets filed under vegetables.
const POTATO_EXCLUDE = ['süßkartoffel', 'rösti', 'chips', 'salat', 'puffer', 'reibekuchen', 'marzipan', 'bratkartoffel', 'auflauf', 'brot', 'knödel', 'klöße', 'püree'];
const LEMON_EXCLUDE = ['saft', 'limo', 'tee', 'kuchen', 'eis'];
const ROCKET: RecipeIngredient = { label: 'Rocket', keywords: ['rucola'], qty: '1 bag', exclude: ['pesto', 'pizza'] };
const SHIITAKE: RecipeIngredient = { label: 'Shiitake mushrooms', keywords: ['shiitake'], qty: '150 g', exclude: ['suppe', 'sauce', 'nudel'] };
const PAK_CHOI: RecipeIngredient = { label: 'Pak choi', keywords: ['pak-choi', 'pak choi'], qty: '300 g' };
const WOK_SAUCE: RecipeIngredient = { label: 'Wok sauce', keywords: ['wok-sauce', 'wok sauce'], qty: '4 tbsp' };
const SHEEP_CHEESE: RecipeIngredient = { label: 'Greek white cheese', keywords: ['hirtenkäse'], qty: '200 g', exclude: ['back-', 'saganaki', 'cremig'] };
const CUCUMBER: RecipeIngredient = { label: 'Cucumber', keywords: ['salatgurke'], qty: '1', exclude: ['eingelegt'] };
const BUTTERNUT: RecipeIngredient = { label: 'Butternut squash', keywords: ['butternut'], qty: '1 (about 1 kg)', exclude: ['suppe', 'creme'] };
// 'pitahaya' contains 'pita'; a dragon fruit is not a flatbread.
const PITA_EXCLUDE = ['pitahaya', 'chips'];

export const RECIPES: RecipesData = {
  generatedFor: '10115',
  generatedAt: '2026-10-25',
  recipes: [
    // ---- single store: ALDI ----
    {
      id: 'aldi-haehnchen-pak-choi-shiitake-wok',
      title: 'Chicken, Pak Choi & Shiitake Stir-Fry',
      summary: 'Strips of chicken breast seared hard in a wok with shiitake, tenderstem broccoli and pak choi, glazed in wok sauce and spooned over rice.',
      servings: 3,
      timeMinutes: 25,
      tags: ['meat', 'chinese', 'dinner'],
      ingredients: [
        {
          label: 'Chicken breast',
          keywords: ['hähnchenbrustfilet', 'hähnchen-brustfilet', 'hähnchen-innenfilet'],
          qty: '450 g',
          exclude: ['nuggets', 'schnitzel', 'wurst', 'salami', 'aufschnitt', 'roulade', 'cordon', 'dulano', 'wiltmann', 'metten', 'müller & müller'],
        },
        SHIITAKE,
        PAK_CHOI,
        { label: 'Tenderstem broccoli', keywords: ['stangenbrokkoli', 'bimi'], qty: '200 g' },
        WOK_SAUCE,
        rice('200 g'),
        garlic('3 cloves'),
        oil('2 tbsp'),
      ],
      steps: [
        'Cook the rice. Cut the chicken into thin strips, halve the pak choi lengthways and slice the shiitake.',
        'Sear the chicken in very hot oil for 4 minutes until browned, then add the garlic, shiitake and broccoli and stir-fry 3 minutes.',
        'Add the pak choi and a splash of water, cover for 1 minute until just wilted, then toss everything in the wok sauce and serve over the rice.',
      ],
    },
    {
      id: 'aldi-lachs-knoblauchspinat-kartoffeln',
      title: 'Salmon with Garlic Spinach & Butter Potatoes',
      summary: 'Crisp-skinned salmon fillets on a bed of garlicky wilted spinach, with boiled potatoes tossed in brown butter.',
      servings: 2,
      timeMinutes: 30,
      tags: ['pescatarian', 'german', 'dinner'],
      ingredients: [
        { label: 'Salmon fillet', keywords: ['lachsfilet'], qty: '2 portions', exclude: ['vegan', 'schinken', 'aufschnitt', 'räucher', 'garnelen', 'spieß', 'stremel'] },
        { label: 'Spinach', keywords: ['spinat'], qty: '300 g', exclude: ['rahm', 'auflauf', 'börek', 'taschen', 'pasta', 'knorr'] },
        { label: 'Potatoes', keywords: ['speisekartoffeln', 'kartoffeln'], qty: '600 g', exclude: POTATO_EXCLUDE },
        butter('3 tbsp'),
        garlic('2 cloves'),
        oil('1 tbsp'),
        saltPepper,
      ],
      steps: [
        'Boil the potatoes in salted water for about 20 minutes; drain, then toss them in 2 tbsp butter cooked until it smells nutty.',
        'Season the salmon and fry it skin-side down in the oil for 5 minutes, flip and give it 2 more.',
        'In the same pan melt the last of the butter with the sliced garlic, add the spinach and stir until just wilted; serve the salmon on top with the potatoes.',
      ],
    },

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
      id: 'edeka-haehnchen-butternut-kokoscurry',
      title: 'Chicken & Butternut Coconut Curry',
      summary: 'Cubes of butternut and chicken simmered in coconut milk with red pepper and broccoli until the squash melts into the sauce.',
      servings: 4,
      timeMinutes: 40,
      tags: ['meat', 'thai', 'dinner'],
      ingredients: [
        {
          label: 'Chicken breast',
          keywords: ['hähnchen-brustfilet', 'hähnchenbrustfilet'],
          qty: '500 g',
          exclude: ['nuggets', 'schnitzel', 'wurst', 'salami', 'aufschnitt', 'roulade', 'cordon', 'dulano', 'wiltmann', 'metten', 'müller & müller'],
        },
        BUTTERNUT,
        { label: 'Coconut milk', keywords: ['kokosnussmilch', 'kokosmilch'], qty: '400 ml', exclude: ['drink', 'reis'] },
        { label: 'Red pepper', keywords: ['paprika'], qty: '1', exclude: ['gefüllt', 'chips', 'paprikarand', 'pastete', 'salami', 'wurst', 'gewürz', 'edelsüß', 'pulver'] },
        { label: 'Broccoli', keywords: ['brokkoli'], qty: '1 head', exclude: ['stangenbrokkoli', 'bimi', 'auflauf'] },
        rice('250 g'),
        onion('1'),
        garlic('3 cloves'),
        oil('2 tbsp'),
        saltPepper,
      ],
      steps: [
        'Cook the rice. Soften the onion and garlic in the oil, add the peeled, cubed butternut and the sliced pepper and fry 5 minutes.',
        'Pour in the coconut milk with 200 ml water and simmer 15 minutes until the squash is tender.',
        'Add the chicken in strips and the broccoli florets and simmer 8 more minutes until cooked through; season and serve over the rice.',
      ],
    },
    {
      id: 'edeka-griechischer-joghurt-himbeeren-granatapfel',
      title: 'Greek Yoghurt Bowl with Raspberries, Pomegranate & Toasted Pumpkin Seeds',
      summary: 'Thick Greek-style yoghurt topped with fresh raspberries, pomegranate seeds and pumpkin seeds toasted with a little sugar until they crackle.',
      servings: 2,
      timeMinutes: 10,
      tags: ['vegetarian', 'greek', 'breakfast'],
      ingredients: [
        { label: 'Greek-style yoghurt', keywords: ['griechischer art', 'griechisch'], qty: '400 g', exclude: ['frischkäse', 'hirtenkäse', 'dressing'] },
        { label: 'Raspberries', keywords: ['himbeeren'], qty: '125 g', exclude: ['joghurt', 'pudding', 'eis', 'marmelade', 'konfitüre', 'kaugummi', 'tee', 'sirup'] },
        { label: 'Pomegranate seeds', keywords: ['granatapfel'], qty: '1 tub', exclude: ['saft', 'tee', 'shot'] },
        { label: 'Pumpkin seeds', keywords: ['kürbiskerne'], qty: '3 tbsp', exclude: ['brot', 'brötchen', 'öl', 'pesto'] },
        sugar('1 tbsp'),
      ],
      steps: [
        'Toast the pumpkin seeds in a dry pan until they start to pop, sprinkle over the sugar and stir until it just melts and coats them; tip onto a plate to cool.',
        'Spoon the yoghurt into bowls.',
        'Top with the raspberries, pomegranate seeds and the crunchy pumpkin seeds.',
      ],
    },

    // ---- single store: E center ----
    {
      id: 'edeka-center-burger-laugenbuns-gouda',
      title: 'Cheeseburgers on Pretzel Buns with Cornichons',
      summary: 'Seared beef patties melted under young Gouda, stacked in toasted pretzel buns with vine tomatoes, red onion and sliced cornichons.',
      servings: 4,
      timeMinutes: 20,
      tags: ['meat', 'american', 'dinner'],
      ingredients: [
        { label: 'Beef burger patties', keywords: ['pattys', 'burger patties'], qty: '4', exclude: ['chicken', 'crispy', 'vegan', 'vegetarisch', 'veggie'] },
        { label: 'Pretzel burger buns', keywords: ['burger-buns', 'burger buns'], qty: '4' },
        { label: 'Young Gouda', keywords: ['gouda'], qty: '4 slices', exclude: ['valess', 'schnitzel', 'vegan'] },
        { label: 'Vine tomatoes', keywords: ['rispentomaten'], qty: '2' },
        { label: 'Cornichons', keywords: ['cornichons'], qty: '6' },
        onion('1', 'Red onion'),
        oil('1 tbsp'),
        saltPepper,
      ],
      steps: [
        'Halve and toast the buns cut-side down in a dry pan; slice the tomatoes, onion and cornichons.',
        'Season the patties and sear them in the oil for 3 minutes a side, laying a slice of Gouda on each for the last minute under a lid.',
        'Build the burgers: bun, tomato, patty with its melted cheese, onion and cornichons, then the lid.',
      ],
    },
    {
      id: 'edeka-center-garnelen-avocado-papaya-bowl',
      title: 'Prawn Poke Bowl with Avocado & Papaya',
      summary: 'Warm rice topped with garlicky seared prawns, ripe avocado, sweet papaya and crunchy cucumber.',
      servings: 2,
      timeMinutes: 25,
      tags: ['pescatarian', 'hawaiian', 'lunch'],
      ingredients: [
        { label: 'Prawn tails', keywords: ['garnelenschwänze', 'garnelen'], qty: '250 g', exclude: ['salat', 'aioli', 'spieß', 'tempura', 'surimi', 'chips', 'cracker'] },
        { label: 'Avocado', keywords: ['avocado'], qty: '1', exclude: ['creme', 'öl', 'dip'] },
        { label: 'Papaya', keywords: ['papaya'], qty: '½', exclude: ['lipgloss', 'getrocknet'] },
        CUCUMBER,
        rice('150 g'),
        garlic('2 cloves'),
        oil('2 tbsp'),
        saltPepper,
      ],
      steps: [
        'Cook the rice and season it lightly with salt.',
        'Fry the prawns with the sliced garlic in the oil for 2 minutes a side until pink.',
        'Divide the rice between bowls and arrange the prawns, sliced avocado, cubed papaya and cucumber on top.',
      ],
    },

    // ---- single store: Lidl ----
    {
      id: 'lidl-porridge-birne-banane-honig',
      title: 'Porridge with Pear, Banana & Honey',
      summary: 'Creamy oats cooked in milk with diced pear stirred through, topped with sliced banana and a drizzle of honey.',
      servings: 2,
      timeMinutes: 10,
      tags: ['vegetarian', 'british', 'breakfast'],
      ingredients: [
        { label: 'Rolled oats', keywords: ['haferflocken'], qty: '100 g', exclude: ['riegel', 'cookies', 'keks'] },
        { label: 'Pear', keywords: ['birnen'], qty: '1', exclude: ['saft', 'nashi', 'schnaps', 'helene'] },
        { label: 'Banana', keywords: ['bananen'], qty: '1', exclude: ['chips', 'kirsch', 'saft', 'milch', 'quetschie'] },
        { label: 'Honey', keywords: ['blütenhonig', 'honig'], qty: '2 tbsp', exclude: ['brot', 'brötchen', 'senf', 'putenbrust', 'tee', 'pops', 'loops', 'bratapfel', 'melone', 'pomelo'] },
        milk('500 ml'),
        salt,
      ],
      steps: [
        'Bring the oats, milk and a pinch of salt to a simmer, stirring.',
        'Add the diced pear and cook 4–5 minutes, stirring often, until thick and creamy.',
        'Spoon into bowls, top with the sliced banana and drizzle with honey.',
      ],
    },
    {
      id: 'lidl-wirsing-pasta-creme-fraiche-hirtenkaese',
      title: 'Savoy Cabbage Pasta with Shallots, Crème Fraîche & Feta',
      summary: 'Shredded savoy cabbage and shallots softened in butter until sweet, folded through pasta with crème fraîche and finished with salty white cheese.',
      servings: 3,
      timeMinutes: 25,
      tags: ['vegetarian', 'german', 'dinner'],
      ingredients: [
        { label: 'Savoy cabbage', keywords: ['wirsing'], qty: '½ head' },
        { label: 'Shallots', keywords: ['schalotten'], qty: '3' },
        { label: 'Crème fraîche', keywords: ['crème fraîche', 'creme fraiche'], qty: '150 g' },
        SHEEP_CHEESE,
        pasta('300 g'),
        butter('2 tbsp'),
        saltPepper,
      ],
      steps: [
        'Boil the pasta in well-salted water. Shred the cabbage finely and slice the shallots.',
        'Soften the shallots in the butter, add the cabbage and a splash of water and cook covered for 8 minutes, stirring now and then, until tender and sweet.',
        'Stir in the crème fraîche, toss through the drained pasta with a little of its water, season with pepper and crumble the cheese over.',
      ],
    },

    // ---- single store: Penny ----
    {
      id: 'penny-hokkaido-linsen-dal',
      title: 'Hokkaido & Lentil Dal with Chickpeas',
      summary: 'Lentils and cubed Hokkaido simmered down with carrot, garlic and onion until thick and golden, sharpened with lemon and served over rice.',
      servings: 4,
      timeMinutes: 40,
      tags: ['vegan', 'indian', 'dinner'],
      ingredients: [
        { label: 'Hokkaido pumpkin', keywords: ['hokkaido'], qty: '½ (about 500 g)' },
        { label: 'Lentils', keywords: ['linsen'], qty: '250 g', exclude: ['chips', 'waffel', 'snack', 'suppe', 'eintopf'] },
        { label: 'Chickpeas', keywords: ['kichererbsen'], qty: '1 jar', exclude: ['chips', 'snack', 'hummus'] },
        { label: 'Lemon', keywords: ['zitronen'], qty: '1', exclude: LEMON_EXCLUDE },
        carrots('2'),
        rice('250 g'),
        onion('1'),
        garlic('3 cloves'),
        oil('3 tbsp'),
        salt,
      ],
      steps: [
        'Soften the onion, garlic and diced carrots in the oil for 5 minutes, then add the seeded, cubed pumpkin (skin on).',
        'Add the rinsed lentils and 1 litre of water and simmer 25 minutes, stirring, until the lentils collapse; meanwhile cook the rice.',
        'Stir in the drained chickpeas to warm through, season with salt and the lemon juice, and serve over the rice.',
      ],
    },
    {
      id: 'penny-gyros-pita-knoblauchjoghurt',
      title: 'Gyros Pitas with Garlic Yoghurt & Pointed Cabbage Slaw',
      summary: 'Crisp-fried gyros piled into warm pita boats with a quick garlic yoghurt and a crunchy slaw of pointed cabbage and red onion.',
      servings: 3,
      timeMinutes: 20,
      tags: ['meat', 'greek', 'dinner'],
      ingredients: [
        { label: 'Gyros', keywords: ['gyros'], qty: '400 g', exclude: ['gewürz', 'würzer', 'vegan', 'fix', 'chips'] },
        { label: 'Pita boats', keywords: ['pita'], qty: '1 pack', exclude: PITA_EXCLUDE },
        { label: 'Natural yoghurt', keywords: ['naturjoghurt'], qty: '250 g' },
        { label: 'Pointed cabbage', keywords: ['spitzkohl'], qty: '¼ head' },
        onion('1', 'Red onion'),
        garlic('2 cloves'),
        oil('2 tbsp'),
        saltPepper,
      ],
      steps: [
        'Stir the crushed garlic and a pinch of salt into the yoghurt. Shred the cabbage finely and toss it with the sliced onion, 1 tbsp oil and salt.',
        'Fry the gyros in the remaining oil over high heat until crisp at the edges; warm the pitas in the oven or a dry pan.',
        'Fill the pitas with slaw and gyros and spoon the garlic yoghurt over.',
      ],
    },

    // ---- single store: REWE ----
    {
      id: 'rewe-rinderrouladen-weisskohl',
      title: 'Beef Rouladen with Braised White Cabbage',
      summary: 'Classic German beef rolls filled with onion and carrot, slowly braised in their own gravy, with buttery white cabbage on the side.',
      servings: 4,
      timeMinutes: 120,
      tags: ['meat', 'german', 'dinner'],
      ingredients: [
        { label: 'Beef rouladen', keywords: ['rinder-rouladen', 'rinderroulade'], qty: '4' },
        { label: 'White cabbage', keywords: ['weisskohl', 'weißkohl'], qty: '500 g', exclude: ['salat'] },
        carrots('2'),
        onion('2', 'Onions'),
        flour('1 tbsp'),
        butter('2 tbsp'),
        oil('2 tbsp'),
        saltPepper,
      ],
      steps: [
        'Season the rouladen, lay strips of carrot and onion on each, roll them up tightly and secure with toothpicks or string.',
        'Brown them all over in the oil, add the rest of the chopped onion and carrot and 500 ml water, cover and braise gently for 90 minutes; thicken the gravy with the flour stirred into a little cold water.',
        'For the last 15 minutes, braise the cabbage in the butter with a splash of water and salt until tender, and serve alongside the rouladen and their gravy.',
      ],
    },
    {
      id: 'rewe-butternut-zucchini-gratin',
      title: 'Butternut & Zucchini Gratin with Parmesan',
      summary: 'Thin slices of butternut and zucchini baked in a garlicky béchamel under mozzarella and grated Parmigiano until bubbling and golden.',
      servings: 4,
      timeMinutes: 60,
      tags: ['vegetarian', 'french', 'dinner'],
      ingredients: [
        BUTTERNUT,
        { label: 'Zucchini', keywords: ['zucchini'], qty: '2', exclude: ['saaten'] },
        { label: 'Mozzarella', keywords: ['mozzarella'], qty: '125 g', exclude: ['sticks', 'caprese', 'snack', 'vegan'] },
        { label: 'Grated Parmigiano', keywords: ['parmigiano', 'parmesan'], qty: '60 g' },
        milk('500 ml'),
        butter('3 tbsp'),
        flour('3 tbsp'),
        garlic('2 cloves'),
        saltPepper,
      ],
      steps: [
        'Heat the oven to 200 °C. Melt the butter, stir in the flour for a minute, then whisk in the milk and garlic and simmer until thick; season well.',
        'Peel the butternut and slice it and the zucchini thinly; layer them in a buttered dish, spooning sauce between the layers.',
        'Top with torn mozzarella and the Parmigiano and bake 40 minutes until the squash is tender and the top is golden.',
      ],
    },

    // ---- two stores ----
    {
      id: 'aldi-lidl-gefuellte-spitzpaprika',
      title: 'Pointed Peppers Stuffed with Beef, Rice & White Cheese',
      summary: 'Sweet pointed peppers filled with spiced minced beef and rice, baked until soft and served with crumbled white cheese and rocket.',
      servings: 4,
      timeMinutes: 50,
      tags: ['meat', 'turkish', 'dinner'],
      ingredients: [
        { label: 'Minced beef', keywords: ['rinderhack', 'rinder-hack'], qty: '400 g', exclude: ['vegan', 'burger'] },
        { label: 'Pointed peppers', keywords: ['spitzpaprika'], qty: '6' },
        SHEEP_CHEESE,
        ROCKET,
        rice('100 g'),
        onion('1'),
        garlic('2 cloves'),
        oil('2 tbsp', 'Olive oil'),
        saltPepper,
      ],
      steps: [
        'Heat the oven to 200 °C. Cook the rice for 10 minutes (it finishes in the oven) and drain.',
        'Fry the beef with the onion and garlic in the oil until browned, mix with the rice and season well; slit the peppers lengthways, scrape out the seeds and fill them.',
        'Bake 25 minutes until the peppers are soft and blistered, then crumble the cheese over and serve with the rocket.',
      ],
    },
    {
      id: 'edeka-rewe-raeucherlachs-broetchen',
      title: 'Smoked Salmon & Cream Cheese Rolls',
      summary: 'Fresh breakfast rolls spread thick with cream cheese and topped with smoked salmon, red onion and cracked black pepper.',
      servings: 2,
      timeMinutes: 10,
      tags: ['pescatarian', 'scandinavian', 'breakfast'],
      ingredients: [
        { label: 'Smoked salmon', keywords: ['räucherla'], qty: '100 g', exclude: ['vegan', 'schinken', 'aufschnitt', 'stremel'] },
        { label: 'Cream cheese', keywords: ['philadelphia', 'frischkäse'], qty: '100 g', exclude: ['röllchen', 'griechisch', 'hähnchen'] },
        { label: 'Breakfast rolls', keywords: ['weizenbrötchen', 'landbrötchen', 'baguette brötchen'], qty: '4' },
        onion('½', 'Red onion'),
        saltPepper,
      ],
      steps: [
        'Warm the rolls briefly in the oven so they crisp up, then split them.',
        'Spread each half generously with cream cheese.',
        'Lay the smoked salmon on top, scatter over very thinly sliced red onion and finish with black pepper.',
      ],
    },
    {
      id: 'penny-edeka-center-putenschnitzel-gurkensalat',
      title: 'Panko Turkey Schnitzel with Creamy Cucumber Salad',
      summary: 'Turkey escalopes in a shatteringly crisp panko crust, with a cool sour-cream cucumber salad and a crusty roll on the side.',
      servings: 3,
      timeMinutes: 30,
      tags: ['meat', 'austrian', 'lunch'],
      ingredients: [
        { label: 'Turkey escalopes', keywords: ['puten-schnitzel', 'putenschnitzel'], qty: '3', exclude: ['paniert', 'vegan'] },
        { label: 'Panko breadcrumbs', keywords: ['panko'], qty: '100 g' },
        CUCUMBER,
        { label: 'Sour cream', keywords: ['saure sahne'], qty: '200 g' },
        { label: 'Baguette rolls', keywords: ['baguette-brötchen', 'baguette brötchen'], qty: '3' },
        eggs('2'),
        flour('3 tbsp'),
        oil('6 tbsp', 'Frying oil'),
        sugar('1 pinch'),
        saltPepper,
      ],
      steps: [
        'Slice the cucumber very thinly, salt it for 10 minutes, squeeze it dry and stir it into the sour cream with a pinch of sugar and pepper.',
        'Pound the escalopes thin, season them, then dip each in flour, beaten egg and panko.',
        'Fry in hot oil for 2–3 minutes a side until deep golden; drain briefly and serve with the cucumber salad and warm rolls.',
      ],
    },
    {
      id: 'lidl-rewe-suesskartoffel-mango-salat',
      title: 'Roast Sweet Potato, Mango & Date Salad',
      summary: 'Warm roasted sweet potato tossed with rocket, ripe mango and chopped dates in a simple olive-oil dressing — sweet, peppery and filling.',
      servings: 2,
      timeMinutes: 35,
      tags: ['vegan', 'middle-eastern', 'lunch'],
      ingredients: [
        { label: 'Sweet potatoes', keywords: ['süßkartoffel'], qty: '600 g', exclude: ['chips', 'pommes'] },
        { label: 'Mango', keywords: ['mango'], qty: '1', exclude: ['saft', 'lassi', 'smoothie', 'joghurt', 'duft', 'lufterfrischer', 'maracuja', 'chutney', 'eis', 'getrocknet'] },
        { label: 'Dates', keywords: ['datteln'], qty: '6', exclude: ['schinken', 'speck', 'creme'] },
        ROCKET,
        onion('½', 'Red onion'),
        oil('4 tbsp', 'Olive oil'),
        saltPepper,
      ],
      steps: [
        'Heat the oven to 220 °C. Cube the sweet potatoes, toss with 2 tbsp oil and salt and roast 25 minutes until caramelised at the edges.',
        'Whisk the remaining oil with salt and pepper; dice the mango, chop the dates and slice the onion very thinly.',
        'Toss the rocket, mango, dates and onion with the dressing and pile the warm sweet potato on top.',
      ],
    },
    {
      id: 'aldi-rewe-shiitake-chinakohl-nudelsuppe',
      title: 'Shiitake & Chinese Cabbage Noodle Soup with Soft Egg',
      summary: 'A quick, savoury noodle broth with shiitake, pak choi, Chinese cabbage and carrot, seasoned with wok sauce and crowned with a jammy egg.',
      servings: 2,
      timeMinutes: 25,
      tags: ['vegetarian', 'japanese', 'lunch'],
      ingredients: [
        SHIITAKE,
        PAK_CHOI,
        { label: 'Chinese cabbage', keywords: ['chinakohl'], qty: '¼ head' },
        { label: 'Mie noodles', keywords: ['mie-nudeln', 'wok-nudeln'], qty: '125 g', exclude: ['instant', 'suppe', 'cup'] },
        WOK_SAUCE,
        eggs('2'),
        carrots('1'),
        garlic('2 cloves'),
        oil('1 tbsp'),
      ],
      steps: [
        'Boil the eggs for 6½ minutes, cool them in cold water and peel.',
        'Soften the garlic, sliced shiitake and carrot ribbons in the oil, add 800 ml water and the wok sauce and simmer 5 minutes.',
        'Add the noodles, shredded Chinese cabbage and halved pak choi and cook 3–4 minutes until the noodles are tender; ladle into bowls and top with the halved eggs.',
      ],
    },
  ],
};
