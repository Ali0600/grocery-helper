from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from .api.offers import router as offers_router
from .core.config import settings
from .db import Base, SessionLocal, engine
from .models import Offer  # noqa: F401  ensures tables are registered for create_all
from .scrapers.run import run_scrapers


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables, and seed once so a fresh checkout has data to show.
    Base.metadata.create_all(bind=engine)
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
    return {"status": "ok"}


@app.get("/stats", response_class=HTMLResponse)
def stats_page():
    """A tiny live dashboard for the outbound-call metrics (polls /api/scrape-stats)."""
    from .stats_page import STATS_HTML

    return STATS_HTML
