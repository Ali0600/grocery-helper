from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration, overridable via environment / .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Grocery Helper API"
    # Local dev defaults to SQLite (zero setup). Prod sets DATABASE_URL to Postgres.
    database_url: str = "sqlite:///./grocery.db"
    default_plz: str = "10115"  # Berlin Wilmersdorf
    cors_origins: str = "*"  # comma-separated list, or "*"
    # Optional guard for the destructive POST /api/reset (DB wipe). When unset (default),
    # reset is open like /api/scrape; set it (env ADMIN_TOKEN) to require a matching token.
    admin_token: str = ""


settings = Settings()
