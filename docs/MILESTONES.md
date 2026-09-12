# Milestones

What shipped, one line each, oldest first. Unchecked boxes are still planned. The *why* behind the choices is in [DECISIONS.md](DECISIONS.md).

- [x] Backend pipeline: scrape → normalize → categorize → discount % → store
- [x] API: offers, categories, stores, basket optimizer
- [x] Live Lidl scraper (Lidl Plus store + offers endpoints; PLZ → nearest store)
- [x] Weekly Aktionsprospekt via Bonial/meinprospekt — ~430 structured flyer
      offers alongside the coupons, each tagged `coupon`/`flyer` in the app
- [x] React Native app: live deals by category, ranked by % off, with per-offer
      flyer images + tap-to-view (links to Lidl's full weekly Prospekt)
- [x] Set your postal code in-app — resolves the nearest Lidl and persists it
- [x] In-app search bar + Coupon/Prospekt source badges
- [x] REWE as a second chain (meinprospekt "Dein Markt" flyer, publisher
      `DE-1062`), with a per-offer store badge (Lidl/REWE) in the app
- [x] EDEKA as a third chain (meinprospekt flyer, publisher `DE-220164`) — ~300
      Berlin offers, an Edeka badge, and three-way per-product price comparison
- [x] Nearby-stores directory ("Stores"): nearest Lidl/REWE/Edeka/Aldi/Netto/
      Penny/Kaufland with addresses (OpenStreetMap), add non-active chains to a
      saved "My stores" list — groundwork for onboarding more chains; a "Change"
      picker lists every branch of a chain near the PLZ so you can pick the one
      actually near you (not just nearest the PLZ centroid)
- [x] Per-unit price (€/kg, €/l) shown on every offer that has one, plus REWE
      loyalty-card bonus badges ("1,00 € Bonus") — both pulled from data we
      already fetched but had been discarding
- [x] EDEKA app-coupon prices — a yellow "App 2,99 €" badge surfacing the
      app-exclusive price (`SPECIAL_PRICE` + "App-Preis"), ~24 EDEKA offers/PLZ
- [x] "Cheapest €/kg" sort — ranks the current view by normalized per-unit price
      (e.g. find the best-value beef per kg, independent of pack size)
- [x] Group similar products inside a category — pick Fruits/Beef/etc. and offers
      cluster by product (Avocado, Pfirsich, …) under a header so competing prices
      sit together (e.g. Avocado: REWE 0,88 € vs Lidl 1,99 €)
- [x] Filter by store (All / Lidl / REWE / EDEKA) — a session lens that narrows the
      whole list (and search) to one chain, with the brand colour on the active pill
- [x] **Basket** — a shopping list you build from common items (bilingual quick-add:
      type "Strawberry" or "Erdbeere"); each item shows its cheapest current deal plus
      a store-by-store shopping plan with the savings vs. one store (matched
      per-product against the live deals, client-side). The plan **lists each item under
      its store** with the product you'd actually pick up, so it reads as a shopping list —
      and it **follows the "Only show" store lens**: narrow the deals to Lidl and Aldi and
      the plan is built from those two, while what you can *add* stays the full week.
      An **"In this week's flyers"**
      section lists every product sub-category actually on offer — grouped by aisle, so
      Kohlrabi or Pfifferling can be added even though no curated catalogue lists them.
      Adding from there and swiping a deal card produce the same basket entry
- [x] CI/CD pipeline (GitHub Actions) — test / lint / typecheck / Docker-build gates,
      gated Render deploy (deploy hook), EAS Update OTA, and a weekly scrape cron
- [x] Offline deals cache — instant open from an on-device cache + stale-while-revalidate
      refresh (no cold-start spinner; works offline), with a weekly-expiry "may be
      expired" banner and a "Deals as of <time>" stamp
- [x] Category-accuracy pass — mine more of the Bonial `categoryPaths` taxonomy + a
      product-image audit (uncategorized "Other" 11% → 1%; Fruits confirmed against images)
- [x] In-app OTA update prompt — alerts "Reload to update?" when an EAS Update is ready
- [x] Hide/show stores — persisted multi-select store visibility, applied to the deals
      list, basket optimizer, and recipe pricing alike
- [x] Swipe-to-basket — swipe a deal left to add its product sub-category (the same
      entry the basket's "+" adds), with haptic feedback (native build 1.1.0)
- [x] E center as a fourth chain (own meinprospekt publisher `DE-3443181`) — EDEKA's
      hypermarket flyer as a separate store
- [x] Compare Stores — a per-product price face-off across selected stores, cheapest
      highlighted, tap-through to the deal
- [x] Security & ops hardening — header-based admin auth on destructive endpoints,
      scrape throttling, Berlin-timezone validity, supply-chain-pinned CI, non-root
      container
- [x] Grocery / Drugstore sections — a home screen with large buttons, with every
      fetch, cache and chip scoped to the chosen one (which is also what keeps each
      section clear of the API's 2,000-offer ceiling)
- [x] Drinks as a third section — soft drinks, beer, wine and spirits out of the food
      list, carved from the grocery chains by *category* rather than by chain, which
      also took grocery from 1,926 of the 2,000-offer cap down to 1,689
- [x] Rossmann as the drugstore chain, plus 11 drugstore categories (hair, face, body,
      dental, fragrance, baby, health, cleaning, laundry, pet, make-up) so its offers
      stop collapsing into "Household & Non-food"
- [x] dm as the second drugstore chain — sourced from its **Ausverkauf (clearance) API**
      rather than a flyer, since its meinprospekt brochure serves no offers. Every item
      carries a struck-through original price (median 48% off), the best discount
      coverage of any chain in the app
- [ ] dm's full catalog (~21k products at everyday prices, no validity window) — still a
      different data model from the deals pipeline; likely belongs in the price-history
      collector rather than here
- [x] Weekly price history on History rows, read from the companion
      `grocery-price-history` collector and tiered by how much evidence exists
- [ ] Production monitoring/alerting (uptime + scraper health) on a persistent DB
- [ ] "Store scorecard" compare view — per-store summary (deal count, avg discount,
      which categories each store wins)
