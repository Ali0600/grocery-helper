import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration, overridable via environment / .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Grocery Helper API"
    # Local dev defaults to SQLite (zero setup). Prod sets DATABASE_URL to Postgres.
    database_url: str = "sqlite:///./grocery.db"
    # Neutral central-Berlin default for the public repo. Set DEFAULT_PLZ in .env to use your
    # own postal code locally; the deployed function never reads it (it serves a packaged
    # week), and the weekly pipeline passes the SCRAPE_PLZ secret explicitly.
    default_plz: str = "10115"  # Berlin Mitte
    cors_origins: str = "*"  # comma-separated list, or "*"
    # Guard for the destructive admin endpoints (POST /api/reset wipes every offer).
    #
    # Empty is NOT "no guard": on a deployed instance an empty token DENIES those endpoints
    # (see `_require_admin`). "Off unless configured" is fail-open, and a value that has to be
    # remembered in a dashboard forever is exactly the kind that stays unset — which is what
    # happened here: this comment used to say the guard was simply off, and the public URL's
    # DB-wipe endpoint was unauthenticated for as long as that was true. Local dev stays open.
    admin_token: str = ""
    # Root log level (env LOG_LEVEL): DEBUG/INFO/WARNING/...
    log_level: str = "INFO"
    # Optional Sentry DSN (env SENTRY_DSN). When unset (default), Sentry is a no-op —
    # mirrors the ADMIN_TOKEN "off-unless-set" pattern, so CI/local stay clean.
    sentry_dsn: str = ""

    # --- Outbound-request politeness (see app/http.py) ---------------------------
    # A scrape fires ~15 requests; firing them back-to-back from a datacenter IP is the
    # "burst" the flyer aggregators soft-throttle. `tracked_client` paces every outbound
    # call by at least this many seconds (globally, across all scrapers in a run) plus a
    # random 0..jitter, and backs off + retries on 429/5xx. Tests set the gap+jitter to 0
    # (see tests/conftest.py) so the suite never sleeps.
    scrape_request_gap_s: float = 0.7
    scrape_request_jitter_s: float = 0.6
    # Retry a 429/502/503/504 at most this many times, honoring Retry-After up to the cap
    # (beyond that, give up so the weekly job can't hang) with exponential backoff otherwise.
    scrape_max_retries: int = 2
    scrape_retry_cap_s: float = 30.0
    # The aggregators also soft-throttle by answering **200 with less content** — an empty
    # brochure list, or a brochure that parses to zero offers. That never reaches the retry
    # above (nothing failed), so a chain silently degrades to sample data. Wait this long and
    # ask once more before believing an empty answer; measured 2026-07-19, the identical
    # request returned the full list minutes later. Tests set it to 0 (tests/conftest.py).
    scrape_thin_retry_s: float = 8.0
    # May a failed scrape serve hardcoded `_sample()` offers?
    #
    # OFF by default, so production is correct with no configuration. Sample offers carry
    # INVENTED prices and plausible validity windows, and nothing downstream can tell them
    # from real ones — not the Basket totals, not Compare, not the price-history collector.
    # On 2026-08-16 Rossmann's weekly simply was not published and the app served five made-up
    # drugstore deals for two days. A missing chain is visible (the data gate's chain floor
    # names it); a fabricated 1,59 € shampoo is not.
    #
    # A default of True would have to be switched OFF on Render and remembered forever — the
    # same shape as the ADMIN_TOKEN dashboard value that is still outstanding. Local dev opts
    # in via backend/.env so the app is usable offline.
    scrape_sample_fallback: bool = False

    # --- Snapshot mode (the deployed Lambda) -------------------------------------
    # The deployed function serves a read-only SQLite file that was scraped, gated and
    # packaged by the weekly pipeline, so it must NOT migrate and must NOT scrape at startup:
    # Lambda caps the init phase at 10 seconds, and a boot scrape takes 30-60. That boot
    # scrape is the whole reason the backend left Render, where an ephemeral disk made the
    # offers table empty — its only trigger — on every single cold start.
    #
    # Off by default so local dev, CI and the Docker/compose path are untouched. Turning it on
    # requires a read-only DATABASE_URL; `lifespan` refuses to start otherwise, because a
    # writable URL here would mean the template is wrong and the function is quietly serving
    # something other than the gated week.
    snapshot_mode: bool = False
    # Where the packaged week's provenance lives (built_at, commit, per-vertical counts).
    # Empty means "meta.json next to the app package", which is where the build script puts it.
    snapshot_meta_path: str = ""


def is_deployed() -> bool:
    """True on a hosted instance, false locally and in CI.

    Each host injects its own marker into every process it runs, and none of them exists on a
    laptop or a GitHub runner. Deriving it from the platform's own signal means there is no
    third value to set and forget — the case that produced the open endpoint in the first
    place. AWS_LAMBDA_FUNCTION_NAME is Lambda's; the RENDER ones are kept while that service
    is still reachable during the cutover.
    """
    return bool(
        os.getenv("AWS_LAMBDA_FUNCTION_NAME")
        or os.getenv("RENDER")
        or os.getenv("RENDER_GIT_COMMIT")
    )


settings = Settings()
