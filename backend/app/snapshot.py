"""Snapshot mode: serving a week of deals that shipped inside the deployment artifact.

The deployed function has no writable disk and no database server. It serves a SQLite file
that the weekly pipeline scraped, gated and packaged next to the code, opened **read-only**.
That removes the startup work the previous host forced on every cold start — migrate, then
scrape `DEFAULT_PLZ` because the ephemeral disk left the offers table empty — which is the
30-60s wait this whole move exists to delete. Lambda would not tolerate it anyway: the init
phase is capped at 10 seconds.

Two things have to be true for that to be safe, and both fail QUIETLY if they are not, which
is why they are asserted at startup rather than trusted:

* **`mode=ro`** — without it the function could write to the file it serves. Nothing would
  break visibly; the data would simply stop being the artifact the gate approved.
* **`uri=true`** — SQLAlchemy passes the path to sqlite3 verbatim unless this is set, so
  `sqlite:///file:/var/task/week.db?mode=ro&uri=true` would be read as a *filename* containing
  question marks. sqlite3 would then CREATE that file and serve an empty database: every
  endpoint 200s with `[]`, the app shows "no deals", and nothing anywhere reports an error.
  A fail-open with no signal is the exact shape this repo has been bitten by before.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from .core.config import settings

logger = logging.getLogger(__name__)

# backend/ — the package's parent, which is also the root of the Lambda zip (where build.sh
# puts meta.json beside app/).
_APP_PARENT = Path(__file__).resolve().parent.parent
META_FILENAME = "meta.json"


def meta_path() -> Path:
    """Where the packaged week's provenance file lives."""
    return Path(settings.snapshot_meta_path) if settings.snapshot_meta_path else (
        _APP_PARENT / META_FILENAME
    )


def read_meta() -> dict:
    """The packaged week's provenance, or `{}` when there isn't one.

    Absent is normal and not an error: local dev, CI and the Docker path all serve a live
    database with no artifact behind them. Unreadable is logged but still degrades to `{}` —
    provenance is for humans answering "which week is live?", and it must never be the reason
    an otherwise healthy deployment fails its health check.
    """
    path = meta_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        logger.warning("snapshot meta at %s is unreadable: %s", path, exc)
        return {}
    return data if isinstance(data, dict) else {}


def sqlite_path(database_url: str) -> Path | None:
    """The on-disk path a SQLite URL points at, or None if the URL isn't SQLite.

    Handles the plain form (`sqlite:///./grocery.db`) and the URI form
    (`sqlite:///file:/var/task/week.db?mode=ro&uri=true`).
    """
    if not database_url.startswith("sqlite"):
        return None
    _, _, rest = database_url.partition(":///")
    if not rest:
        return None  # sqlite:// — in-memory
    rest = rest.split("?", 1)[0]
    if rest.startswith("file:"):
        rest = rest[len("file:"):]
    return Path(rest)


def verify_ready() -> None:
    """Refuse to start unless the packaged database is really there and really read-only.

    Called from `lifespan` only when `snapshot_mode` is on. Raising here fails the deployment
    loudly — the function never reports healthy, the deploy job's health poll times out, and
    the previous version stays live — which is the correct outcome for a misconfigured
    template. The alternative is serving wrong or empty data with a green tick.
    """
    url = settings.database_url
    missing = [flag for flag in ("mode=ro", "uri=true") if flag not in url]
    if missing:
        raise RuntimeError(
            "snapshot mode needs a read-only SQLite URI; DATABASE_URL is missing "
            f"{', '.join(missing)}. Expected the shape "
            "sqlite:///file:/var/task/week.db?mode=ro&uri=true — without uri=true sqlite3 "
            "reads the whole string as a filename, creates it, and serves an empty database."
        )
    path = sqlite_path(url)
    if path is None or not path.is_file():
        raise RuntimeError(
            f"snapshot mode found no database at {path} — the weekly pipeline packages "
            "week.db at the root of the deployment artifact (see infra/build.sh)."
        )
    meta = read_meta()
    logger.info(
        "snapshot mode: serving %s read-only (built %s, commit %s); no migrations, no scrape",
        path,
        meta.get("built_at", "unknown"),
        (meta.get("commit") or "unknown")[:12],
    )
