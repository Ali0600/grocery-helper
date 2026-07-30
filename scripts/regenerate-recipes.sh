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
STATUS="$ROOT/.recipe-regen.status"
LOG="$ROOT/.recipe-regen.log"
ALERT_LABEL="recipe-failure"

# --- make tools resolvable, especially under launchd's minimal env ---
export PATH="/opt/homebrew/bin:$HOME/.local/bin:$PATH"
# Activate the default node via fnm; fall back to the newest installed version so a node
# upgrade doesn't break the schedule.
if command -v fnm >/dev/null 2>&1; then eval "$(fnm env)"; fnm use default >/dev/null 2>&1 || true; fi
NODE_BIN="$(ls -d "$HOME"/.local/share/fnm/node-versions/*/installation/bin 2>/dev/null | sort -V | tail -1 || true)"
[ -n "$NODE_BIN" ] && export PATH="$NODE_BIN:$PATH"

# --- failure has to be LOUD -------------------------------------------------------
# This job failed silently for 11 days (2026-07-26 → 2026-07-30): `claude -p` lost its
# auth, `set -e` aborted, and absolutely nothing said so. Failing closed was right;
# failing *quietly* was the bug. Three channels, weakest dependency last:
#
#   1. a status file  — cannot fail; it is a local write, and it is what `--check` reads
#   2. a macOS notification — best effort, for the human at the keyboard
#   3. a deduplicated GitHub issue — mirrors scrape.yml's `scrape-failure` machinery
#      (and the self-healing-script repo consumes these), but `gh` authenticates via the
#      KEYRING, the same class of thing that broke here — so it must never be the only one.
alert() { # $1 = one-line reason
  local reason="$1" when; when="$(date '+%F %T')"
  printf '%s\n' "FAILED $when :: $reason" > "$STATUS" || true
  echo "✗ RECIPE REGEN FAILED — $reason" >&2
  osascript -e "display notification \"$reason\" with title \"Recipe regen failed\"" \
    >/dev/null 2>&1 || true
  if command -v gh >/dev/null 2>&1; then
    local body existing
    body=$(printf 'The weekly recipe regeneration failed on %s.\n\n**%s**\n\nLast lines of `.recipe-regen.log`:\n\n```\n%s\n```\n' \
      "$when" "$reason" "$(tail -n 25 "$LOG" 2>/dev/null || echo '(no log)')")
    existing=$(gh issue list --label "$ALERT_LABEL" --state open --limit 1 \
      --json number --jq '.[0].number' 2>/dev/null || true)
    if [ -n "${existing:-}" ]; then
      gh issue comment "$existing" --body "$body" >/dev/null 2>&1 || true
    else
      gh issue create --title "Weekly recipe regeneration is failing" \
        --label "$ALERT_LABEL" --body "$body" >/dev/null 2>&1 || true
    fi
  fi
}
on_error() { trap - ERR EXIT; alert "step failed at line $2 (exit $1)"; exit "$1"; }

# `--check` reports the last outcome and exits non-zero if it was a failure, so the
# schedule's health is answerable without reading the log. Handled BEFORE the ERR trap
# is armed: a check that correctly reports "FAILED" must not itself raise a new alert.
if [ "${1:-}" = "--check" ]; then
  cat "$STATUS" 2>/dev/null || echo "UNKNOWN (never run)"
  grep -q '^OK' "$STATUS" 2>/dev/null
  exit $?
fi

trap 'on_error $? $LINENO' ERR

echo "→ $(date '+%F %T') regenerating recipes for PLZ $PLZ"
cd "$ROOT"

# 0. Preflight the ONE dependency that can't be retried around: headless Claude auth.
#    Checked before the scrape on purpose — the scrape is ~30s and ~15 requests to the
#    flyer publishers, and firing that burst when we already can't author anything is
#    both wasteful and impolite. This is exactly what failed on 2026-07-26.
if ! claude -p "reply with exactly: OK" >/dev/null 2>&1; then
  alert "headless \`claude -p\` is not authenticated — run \`claude\` and /login, then re-run this script"
  exit 1
fi

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

# Completes the loop, exactly as scrape.yml does: a healthy run records success and
# closes any open alert issue, so the issue tracks the CURRENT state rather than
# accumulating one entry per bad week.
succeed() {
  trap - ERR EXIT
  printf '%s\n' "OK $(date '+%F %T') :: $1" > "$STATUS" || true
  if command -v gh >/dev/null 2>&1; then
    for n in $(gh issue list --label "$ALERT_LABEL" --state open --limit 10 \
                 --json number --jq '.[].number' 2>/dev/null || true); do
      gh issue comment "$n" --body "Recovered: $1 ($(date '+%F %T'))." >/dev/null 2>&1 || true
      gh issue close "$n" >/dev/null 2>&1 || true
    done
  fi
}

# 5. Ship: commit + push only if recipes.ts actually changed (→ CI → OTA).
if git diff --quiet -- "$RECIPES"; then
  echo "→ recipes.ts unchanged — nothing to ship"
  succeed "ran clean; recipes.ts unchanged"
  exit 0
fi
git add "$RECIPES"
git commit -m "chore(recipes): weekly regen $(date '+%F')"
git push
echo "→ pushed; eas-update will OTA after CI passes"
succeed "regenerated and pushed"
