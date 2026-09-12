#!/usr/bin/env bash
# Build the Lambda deployment package: runtime dependencies + the app + the week's data.
#
# Usage: infra/build.sh [outdir]            (default: infra/build)
#
# `week.db` and `meta.json` must already be in the output directory — the weekly pipeline
# puts them there via `app.scripts.package_week`, and a code-only deploy copies them out of
# the CURRENTLY LIVE function first. That ordering is the whole safety property: a code
# deploy must never be able to change the data, and a data deploy must never be able to ship
# unreviewed code.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$REPO/infra/build}"
mkdir -p "$OUT"

for required in week.db meta.json; do
  if [ ! -f "$OUT/$required" ]; then
    echo "::error::$OUT/$required is missing — the package must carry the week it serves." >&2
    echo "  weekly run:  python -m app.scripts.package_week --db week.db --out $OUT ..." >&2
    echo "  code deploy: unzip the live function's week.db + meta.json into $OUT first" >&2
    exit 1
  fi
done

echo "Installing runtime dependencies for the function's architecture…"
# --platform + --only-binary is what makes a Linux/arm64 package buildable on any host, and
# it is also the verification: a runtime dependency with no aarch64 wheel fails HERE, in CI
# on a pull request, rather than at import time on the deployed function.
pip install --quiet --target "$OUT" \
  --platform manylinux2014_aarch64 \
  --implementation cp \
  --python-version 3.12 \
  --only-binary=:all: \
  --upgrade \
  -r "$REPO/backend/requirements.txt"

echo "Copying the application…"
rm -rf "$OUT/app"
# alembic/ is deliberately NOT packaged: the function never migrates (it serves a read-only
# file that CI already migrated), and shipping migration scripts it cannot run would only
# invite someone to try.
cp -R "$REPO/backend/app" "$OUT/app"
cp "$REPO/infra/run.sh" "$OUT/run.sh"
chmod 755 "$OUT/run.sh"
find "$OUT" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "$OUT" -name '*.pyc' -delete 2>/dev/null || true

UNZIPPED_KB=$(du -sk "$OUT" | cut -f1)
ZIPPED_KB=$( (cd "$OUT" && zip -qr - . | wc -c) | awk '{print int($1/1024)}')
echo
printf 'package: %d MB unzipped, %d MB zipped\n' "$((UNZIPPED_KB / 1024))" "$((ZIPPED_KB / 1024))"
printf 'week.db: %d MB\n' "$(( $(du -sk "$OUT/week.db" | cut -f1) / 1024 ))"

# Lambda's hard limits are 250 MB unzipped and 50 MB zipped via the API. Fail well short of
# both: the file grows with `raw_payload`, and discovering the ceiling during a Sunday deploy
# would mean a week with no refresh and a red alert nobody can fix quickly.
if [ "$UNZIPPED_KB" -gt 235520 ]; then
  echo "::error::package is ${UNZIPPED_KB} KB unzipped; Lambda's limit is 250 MB" >&2
  exit 1
fi
if [ "$ZIPPED_KB" -gt 46080 ]; then
  echo "::error::package is ${ZIPPED_KB} KB zipped; Lambda's limit is 50 MB" >&2
  exit 1
fi
echo "Package ready in $OUT"
