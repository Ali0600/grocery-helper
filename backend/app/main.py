import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from . import snapshot
from .api.offers import router as offers_router
from .core.config import settings
from .db import SessionLocal
from .logging_config import configure_logging
from .migrations import run_migrations
from .models import Offer
from .scrapers.run import run_scrapers

configure_logging()
logger = logging.getLogger(__name__)

# Error tracking is opt-in: only initialises when SENTRY_DSN is set (no-op otherwise).
# sentry-sdk auto-instruments FastAPI, so unhandled 500s are captured automatically.
if settings.sentry_dsn:
    import sentry_sdk

    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)
    logger.info("Sentry error tracking enabled")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The deployed function serves a week that was scraped, gated and packaged by the weekly
    # pipeline, so there is nothing to migrate and nothing to seed — see app/snapshot.py.
    # Skipping this is the entire point of the move: on the previous host an ephemeral disk
    # left the offers table empty on every cold start, so the condition below fired every
    # time and the API could not answer for 30-60s. Lambda caps init at 10s regardless.
    if settings.snapshot_mode:
        snapshot.verify_ready()
        yield
        return

    # Migrate to the latest schema, then seed once so a fresh checkout has data.
    run_migrations()
    with SessionLocal() as session:
        if session.scalar(select(Offer).limit(1)) is None:
            run_scrapers(session, settings.default_plz)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

origins = (
    ["*"]
    if settings.cors_origins.strip() == "*"
    else [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(offers_router, prefix="/api")


@app.get("/health")
def health():
    """Liveness, plus the two facts the deploy pipelines poll for.

    `commit` makes "is my code live yet?" a queryable fact — the CI deploy job polls it until
    it matches the merged SHA before it will verify the served feature. GIT_COMMIT is set from
    the template on the Lambda; RENDER_GIT_COMMIT is the previous host's own injected value,
    kept until that service is switched off. None locally.

    `data_built_at` is the same question about the DATA, which is now a separately deployed
    artifact: the weekly pipeline polls this until it sees the week it just packaged. Without
    it, "the deploy succeeded" would say nothing about whether the new week is being served —
    the shape of failure that let a green tick sit over stale data before.

    This is also the Lambda Web Adapter's readiness check, so it must stay cheap and must not
    touch the database.
    """
    return {
        "status": "ok",
        "commit": os.getenv("GIT_COMMIT") or os.getenv("RENDER_GIT_COMMIT"),
        "data_built_at": snapshot.read_meta().get("built_at"),
    }


@app.get("/stats", response_class=HTMLResponse)
def stats_page():
    """A tiny live dashboard for the outbound-call metrics (polls /api/scrape-stats)."""
    from .stats_page import STATS_HTML

    return STATS_HTML
