"""Re-apply the classifier to every stored offer.

Categories are computed at scrape time and persisted, so a change to the
classifier rules/brand map doesn't affect existing rows until they're re-scraped.
This backfill re-runs `classify(name, brand, path, unit)` over the whole table so rule
changes take effect immediately.

Usage:
    python -m app.scripts.recategorize
"""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..categories import classify
from ..db import SessionLocal
from ..models import Offer


def recategorize(session: Session) -> int:
    """Re-classify all offers in place. Returns the number of rows changed."""
    changed = 0
    for offer in session.scalars(select(Offer)).all():
        path = json.loads(offer.category_path) if offer.category_path else None
        new_category = classify(offer.name, offer.brand, path, offer.unit)
        if new_category != offer.category:
            offer.category = new_category
            changed += 1
    session.commit()
    return changed


def main() -> None:
    with SessionLocal() as session:
        changed = recategorize(session)
        print(f"Recategorized {changed} offer(s).")


if __name__ == "__main__":
    main()
