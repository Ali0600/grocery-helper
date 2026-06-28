#!/usr/bin/env bash
#
# dev.sh — run the backend (FastAPI on :8001) and the web app (Expo Web on :8081)
# together for local development. Ctrl-C stops both.
#
#   ./dev.sh
#
# The web app reads mobile/.env (EXPO_PUBLIC_API_URL=http://localhost:8001), so it
# talks to the backend started here. Run it, don't `source` it (it kills its own
# process group on exit).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT=8001
WEB_PORT=8081

# --- preflight -------------------------------------------------------------
if [[ ! -x "$ROOT/backend/.venv/bin/uvicorn" ]]; then
  echo "✗ backend venv not found at backend/.venv" >&2
  echo "  create it:  cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt" >&2
  exit 1
fi

if [[ ! -d "$ROOT/mobile/node_modules" ]]; then
  echo "✗ mobile/node_modules not found" >&2
  echo "  install it: cd mobile && npm install" >&2
  exit 1
fi

if lsof -nP -iTCP:"$BACKEND_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "✗ port $BACKEND_PORT is already in use — is the backend already running?" >&2
  echo "  free it:  lsof -ti tcp:$BACKEND_PORT | xargs kill" >&2
  exit 1
fi

# --- run -------------------------------------------------------------------
# kill 0 targets this script's process group, taking down uvicorn's --reload
# child and Metro's workers too (a plain kill <pid> would orphan them).
cleanup() {
  echo ""
  echo "→ stopping backend + web…"
  trap - INT TERM EXIT
  kill 0
}
trap cleanup INT TERM EXIT

echo "→ backend  : http://localhost:$BACKEND_PORT  (docs: /docs, dashboard: /stats)"
echo "→ web app  : http://localhost:$WEB_PORT"
echo "→ Ctrl-C to stop both"
echo ""

( cd "$ROOT/backend" && exec .venv/bin/uvicorn app.main:app --reload --port "$BACKEND_PORT" ) &
( cd "$ROOT/mobile" && exec npm run web ) &

wait
