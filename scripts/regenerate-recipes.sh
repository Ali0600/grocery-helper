#!/usr/bin/env bash
#
# regenerate-recipes.sh — weekly AI-recipe refresh, fully local (no managed LLM key).
#
# Scrapes this week's deals into the local DB, dumps the cheapest on-sale candidates,
# has Claude Code (headless `claude -p`, your local auth) rewrite
# mobile/src/data/recipes.ts, validates it builds, then commits + pushes to main —
# which the eas-update workflow turns into an OTA after CI passes.
#
#   ./scripts/regenerate-recipes.sh [PLZ]        # run manually
# or on a schedule via scripts/com.groceryhelper.recipes.plist (launchd, Sundays).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLZ="${1:-10115}"
CANDIDATES="$ROOT/.recipe-candidates.json"
RECIPES="mobile/src/data/recipes.ts"

# --- make tools resolvable, especially under launchd's minimal env ---
export PATH="/opt/homebrew/bin:$HOME/.local/bin:$PATH"
# Activate the default node via fnm; fall back to the newest installed version so a node
# upgrade doesn't break the schedule.
if command -v fnm >/dev/null 2>&1; then eval "$(fnm env)"; fnm use default >/dev/null 2>&1 || true; fi
NODE_BIN="$(ls -d "$HOME"/.local/share/fnm/node-versions/*/installation/bin 2>/dev/null | sort -V | tail -1 || true)"
[ -n "$NODE_BIN" ] && export PATH="$NODE_BIN:$PATH"

echo "→ $(date '+%F %T') regenerating recipes for PLZ $PLZ"
cd "$ROOT"

# 1. Start from a clean, current main.
git checkout main
git pull --ff-only

# 2. Refresh local deals, then dump this week's candidates (read-only).
( cd backend && source .venv/bin/activate && python -m app.scripts.scrape --plz "$PLZ" )
( cd backend && source .venv/bin/activate && python -m app.scripts.recipe_seed --plz "$PLZ" ) > "$CANDIDATES"
echo "→ dumped $(wc -c < "$CANDIDATES" | tr -d ' ') bytes of candidates"

# 3. Author recipes.ts via headless Claude Code (local auth — no managed key).
claude -p "$(cat "$ROOT/scripts/recipe-prompt.md")" \
  --permission-mode acceptEdits \
  --allowedTools "Read,Write,Edit"

# 4. Validate — abort (no commit) if it doesn't build.
( cd mobile && npx tsc --noEmit && npm run lint )

# 5. Ship: commit + push only if recipes.ts actually changed (→ CI → OTA).
if git diff --quiet -- "$RECIPES"; then
  echo "→ recipes.ts unchanged — nothing to ship"
  exit 0
fi
git add "$RECIPES"
git commit -m "chore(recipes): weekly regen $(date '+%F')"
git push
echo "→ pushed; eas-update will OTA after CI passes"
