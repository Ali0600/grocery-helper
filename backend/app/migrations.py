"""Run Alembic migrations programmatically at startup (replaces create_all).

A fresh database (Render's ephemeral SQLite, a local checkout) gets every table
built from the migration scripts; an existing Postgres gets only the new ALTERs.
Driven by app settings, so no alembic.ini is needed at runtime — only the bundled
``alembic/`` directory (see backend/Dockerfile).
"""
from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from .core.config import settings
from .db import engine

logger = logging.getLogger(__name__)

# backend/  (parent of app/) — holds the alembic/ migration tree.
_BACKEND_DIR = Path(__file__).resolve().parent.parent


def run_migrations() -> None:
    """Bring the database to the latest schema revision at startup.

    Fresh DBs (Render's ephemeral SQLite, CI, a new checkout) upgrade from base,
    building every table. A DB created by the pre-Alembic ``create_all`` already
    has the tables but no ``alembic_version``; stamping it as already-at-head
    avoids a "table already exists" crash, after which future migrations apply
    normally.
    """
    cfg = Config()
    cfg.set_main_option("script_location", str(_BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)

    tables = set(inspect(engine).get_table_names())
    if "offers" in tables and "alembic_version" not in tables:
        command.stamp(cfg, "head")
        logger.info("Existing pre-Alembic database stamped at head")
    else:
        command.upgrade(cfg, "head")
        logger.info("Database migrated to head")
