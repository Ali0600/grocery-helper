"""The weekly pipeline's scrape entry point (`app.scripts.scrape`).

One thing is pinned here, and it is a privacy rule rather than a behaviour: **the postal code
never reaches stdout**. This script is what the weekly GitHub Actions job runs, and a public
repo's Actions logs are public. GitHub masks a secret's exact value, but the repo's standing
rule is broader than masking — `verify_deals.py` keys every number on `chain` for the same
reason, because store names are built as f"{store_label} {plz}" and leak the code indirectly.

The repo had to rewrite its own history once to remove a postal code (2026-06-30), which is why
a print statement gets a test.
"""
import pytest

from app.scripts import scrape

# Deliberately not the committed 10115 default: a test whose fixture equals the default cannot
# tell "the PLZ was withheld" from "the PLZ happened to be the neutral one".
PLZ = "54321"


@pytest.fixture()
def ran(monkeypatch):
    """Run main() with the scrape and the DB session stubbed, returning what it printed."""
    monkeypatch.setattr(scrape, "run_scrapers", lambda session, plz: 1712)

    class _NullSession:
        def __enter__(self):
            return None

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(scrape, "SessionLocal", lambda: _NullSession())
    return scrape


def test_it_reports_the_offer_count(ran, capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["scrape", "--plz", PLZ])
    ran.main()
    assert "scraped 1712 offers" in capsys.readouterr().out


def test_the_postal_code_never_reaches_stdout(ran, capsys, monkeypatch):
    """The one assertion that matters. Put the PLZ back in the f-string and this goes red."""
    monkeypatch.setattr("sys.argv", ["scrape", "--plz", PLZ])
    ran.main()
    out = capsys.readouterr().out
    assert PLZ not in out, f"the postal code was printed into a world-readable log: {out!r}"


def test_the_plz_argument_still_reaches_the_scrapers(ran, capsys, monkeypatch):
    """Withholding it from the log must not mean withholding it from the scrape — the
    inverse mistake, and one a "never print the PLZ" test alone would happily allow."""
    seen = []
    monkeypatch.setattr(ran, "run_scrapers", lambda session, plz: seen.append(plz) or 0)
    monkeypatch.setattr("sys.argv", ["scrape", "--plz", PLZ])
    ran.main()
    assert seen == [PLZ]
