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


settings = Settings()
