"""Build labelled contact sheets of product photos, for the weekly category audit.

The audit's whole point is that a photo settles what text cannot. A keyword pass can only
find products whose name, brand, path or caption disagree with the assigned category — it is
structurally blind to the class where all four read plausibly and all four are wrong. An
"Apfeltasche" is a pastry, a "Käsewiener" is a sausage, a "Pick Paprika Kolbasz" is salami:
nothing in the text says so, and the picture says it immediately.

Sheets are grouped BY CATEGORY and labelled with the assigned chip, so a reviewer reads one
question per sheet — "does every one of these belong in Cheese?" — rather than trying to
classify from scratch.

Usage:
    SCRAPE_REQUEST_GAP_S=0.15 python -m app.scripts.contact_sheets
    python -m app.scripts.contact_sheets --category other    # one chip
    python -m app.scripts.contact_sheets --manifest          # counts only, fetches nothing

Writes `<out>/<category>-NN.jpg` plus an `index.tsv` mapping every tile back to its product.

Images go through `tracked_client`, so they are counted in `/api/scrape-stats` and inherit the
429/5xx backoff. **Override the pacing gap for this script.** The 0.7s default is calibrated
for the flyer AGGREGATORS, which soft-throttle a burst by answering 200 with less content —
that is a property of their API, not of `content-media.bonial.biz`, which is a static image
CDN. At the default, ~2,000 images take about 100 minutes; at 0.15s it is a few minutes and
still well-mannered for static assets. The gap is read from settings when the client is built,
so it has to come from the environment rather than a flag.
"""
from __future__ import annotations

import argparse
import io
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable, List, NamedTuple, Optional

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select

from ..db import SessionLocal
from ..http import tracked_client
from ..models import Offer, Store
from ..validity import berlin_today

TILE = 320          # px per product image (square, letterboxed)
LABEL_H = 46        # px of caption strip under each tile
PAD = 6


class Item(NamedTuple):
    name: str
    category: str
    chain: str
    image_url: str


def _served(session, vertical_chains: Optional[set] = None) -> List[Item]:
    """One row per DISTINCT product currently on sale, mirroring what the app shows.

    Deliberately distinct-by-name: the same product repeats across brochures and chains, and
    a reviewer should not be shown the same photo five times. `valid_to >= today` matches the
    serve-time filter so the sheets describe THIS week, not the accreting table.
    """
    rows = session.execute(
        select(Offer.name, Offer.category, Store.chain, Offer.image_url)
        .join(Store, Offer.store_id == Store.id)
        .where(Offer.image_url.is_not(None))
        .where((Offer.valid_to.is_(None)) | (Offer.valid_to >= berlin_today()))
    ).all()
    seen: dict = {}
    for name, category, chain, url in rows:
        if vertical_chains and chain not in vertical_chains:
            continue
        seen.setdefault((name or "").strip().lower(), Item(name, category, chain, url))
    return sorted(seen.values(), key=lambda i: (i.category, i.name.lower()))


def _font(size: int):
    for path in ("/System/Library/Fonts/Supplemental/Arial.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()  # pragma: no cover - depends on the host


def _fetch(client, url: str) -> Optional[Image.Image]:
    try:
        r = client.get(url)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception as exc:  # noqa: BLE001 - one bad image must not end a 1900-image run
        print(f"  ! image failed ({exc}): {url[:70]}", file=sys.stderr)
        return None


def _tile(img: Optional[Image.Image], label: str, sub: str, font, small) -> Image.Image:
    """One product: the photo letterboxed into a square, with its name and chip under it."""
    cell = Image.new("RGB", (TILE, TILE + LABEL_H), "white")
    if img is not None:
        img.thumbnail((TILE - 2 * PAD, TILE - 2 * PAD))
        cell.paste(img, ((TILE - img.width) // 2, (TILE - img.height) // 2))
    else:
        ImageDraw.Draw(cell).text((PAD, TILE // 2), "(no image)", fill="#999", font=small)
    d = ImageDraw.Draw(cell)
    d.rectangle([0, TILE, TILE, TILE + LABEL_H], fill="#f2f2f2")
    d.text((PAD, TILE + 4), label[:38], fill="black", font=font)
    d.text((PAD, TILE + 24), sub[:44], fill="#666", font=small)
    return cell


def build(items: Iterable[Item], out: Path, cols: int, rows: int) -> int:
    out.mkdir(parents=True, exist_ok=True)
    font, small = _font(15), _font(12)
    per_sheet = cols * rows
    by_cat: dict = defaultdict(list)
    for it in items:
        by_cat[it.category].append(it)

    index = (out / "index.tsv").open("w", encoding="utf-8")
    index.write("sheet\ttile\tcategory\tchain\tname\n")
    sheets = 0
    with tracked_client(timeout=30) as client:
        for category, group in sorted(by_cat.items()):
            for n in range(0, len(group), per_sheet):
                chunk = group[n:n + per_sheet]
                sheet_name = f"{category}-{n // per_sheet + 1:02d}.jpg"
                sheet = Image.new("RGB", (cols * TILE, rows * (TILE + LABEL_H)), "white")
                for i, it in enumerate(chunk):
                    cell = _tile(_fetch(client, it.image_url), it.name,
                                 f"{it.category} · {it.chain}", font, small)
                    sheet.paste(cell, ((i % cols) * TILE, (i // cols) * (TILE + LABEL_H)))
                    index.write(f"{sheet_name}\t{i}\t{it.category}\t{it.chain}\t{it.name}\n")
                sheet.save(out / sheet_name, quality=82, optimize=True)
                sheets += 1
                print(f"  {sheet_name}  ({len(chunk)} products)")
    index.close()
    return sheets


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("contact-sheets"))
    ap.add_argument("--category", action="append", help="limit to these chips (repeatable)")
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--rows", type=int, default=4)
    ap.add_argument("--manifest", action="store_true",
                    help="write index.tsv and print counts, fetching no images")
    args = ap.parse_args()

    with SessionLocal() as session:
        items = _served(session)
    if args.category:
        wanted = set(args.category)
        items = [i for i in items if i.category in wanted]

    counts: dict = defaultdict(int)
    for i in items:
        counts[i.category] += 1
    print(f"{len(items)} distinct served products with an image, "
          f"across {len(counts)} categories")
    for cat, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {cat:14} {n}")
    if args.manifest:
        args.out.mkdir(parents=True, exist_ok=True)
        with (args.out / "index.tsv").open("w", encoding="utf-8") as fh:
            fh.write("category\tchain\tname\timage_url\n")
            for i in items:
                fh.write(f"{i.category}\t{i.chain}\t{i.name}\t{i.image_url}\n")
        print(f"\nmanifest only -> {args.out / 'index.tsv'}")
        return 0

    print(f"\nbuilding sheets of {args.cols}x{args.rows} into {args.out} …")
    print(f"done: {build(items, args.out, args.cols, args.rows)} sheets")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
