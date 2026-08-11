"""Penny — the sixth grocery chain (meinprospekt publisher ``DE-1050``).

Measured 2026-08-11 against the live Berlin flyer: 258 offers parsed (255 after dedup) with
no parser change at all, 100% image, 99.2% category_path, 98.4% caption, 43.8% strike price,
73.6% €/kg-sortable. These tests pin the wiring, not the numbers — a live count belongs in
the Sunday gate, which is the only thing that sees a real week.
"""
from datetime import date, timedelta

from app.scrapers.bonial import PennyScraper
from app.verticals import CHAIN_VERTICAL


def test_publisher_config():
    s = PennyScraper()
    assert s.publisher_id == "DE-1050"
    assert s.publisher_page == "https://www.meinprospekt.de/penny-de"
    assert s.chain == "penny"
    assert s.store_label == "Penny"
    assert s.source == "flyer"


def test_penny_is_a_grocery_chain():
    assert CHAIN_VERTICAL["penny"] == "grocery"


def test_penny_is_scraped_so_the_store_directory_offers_it():
    """`ACTIVE_CHAINS` is what flips a directory row from "Deals coming soon" to Add/Added."""
    from app.services.store_locator import ACTIVE_CHAINS
    assert "penny" in ACTIVE_CHAINS


def test_only_pennys_own_brochures_are_collected():
    """The publisher page embeds competitors' brochures — measured, /penny-de carries Lidl,
    REWE, EDEKA, E center and both Nettos alongside Penny. `publisher.id` is the only filter,
    so this is the test that stops a Penny scrape ingesting Lidl's 73-page flyer."""
    node = {
        "penny": {"id": 1, "pageCount": 36, "validUntil": "2026-08-15",
                  "publisher": {"id": "DE-1050", "name": "Penny"}},
        "lidl": {"id": 2, "pageCount": 73, "validUntil": "2026-08-15",
                 "publisher": {"id": "DE-1013", "name": "Lidl"}},
        "netto": {"id": 3, "pageCount": 71, "validUntil": "2026-08-15",
                  "publisher": {"id": "DE-1034", "name": "Netto Marken-Discount"}},
    }
    out: dict = {}
    PennyScraper()._collect_brochures(node, out)
    assert list(out) == ["1"], "a competitor's brochure leaked into Penny's scrape"


def test_sample_is_non_empty_and_uniquely_prefixed():
    """Without a `_sample()` a failed fetch returns [] -> no rows -> no Store row -> the chain
    vanishes with no error. The `pe-` prefix keeps its external_ids from colliding with any
    other chain's."""
    offers = PennyScraper()._sample()
    assert offers, "a chain with no sample disappears silently when the source fails"
    assert all(o.external_id.startswith("pe-") for o in offers)
    assert len({o.external_id for o in offers}) == len(offers)
    today = date.today()
    for o in offers:
        assert o.valid_from == today and o.valid_to == today + timedelta(days=6)
    # Penny's real flyer prints a strike price on ~44% of offers, so the sample carries both
    # shapes — a sample that was all-or-nothing would not exercise the discount path.
    assert any(o.regular_price_cents for o in offers)
    assert any(o.regular_price_cents is None for o in offers)
