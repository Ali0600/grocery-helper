from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration, overridable via environment / .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Grocery Helper API"
    # Local dev defaults to SQLite (zero setup). Prod sets DATABASE_URL to Postgres.
    database_url: str = "sqlite:///./grocery.db"
    # Neutral central-Berlin default for the public repo. Set DEFAULT_PLZ in .env
    # (local) or the host's env (Render dashboard) to use your own postal code.
    default_plz: str = "10115"  # Berlin Mitte
    cors_origins: str = "*"  # comma-separated list, or "*"
    # Optional guard for the destructive POST /api/reset (DB wipe). When unset (default),
    # reset is open like /api/scrape; set it (env ADMIN_TOKEN) to require a matching token.
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


settings = Settings()
