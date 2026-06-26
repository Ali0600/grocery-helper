"""Tests for the day-validity label + flag derived from an offer's valid_from/valid_to."""
from datetime import date

from app.validity import is_day_limited, valid_days_label

# 2026-06-22 is a Monday.
MON, THU, FRI, SAT, SUN = (
    date(2026, 6, 22),
    date(2026, 6, 25),
    date(2026, 6, 26),
    date(2026, 6, 27),
    date(2026, 6, 28),
)


def test_is_day_limited():
    assert is_day_limited(MON, SAT) is False   # Mon–Sat (6d) = the normal week
    assert is_day_limited(MON, FRI) is True    # ends Friday (5d)
    assert is_day_limited(THU, SAT) is True    # weekend special (3d)
    assert is_day_limited(FRI, FRI) is True     # single day
    assert is_day_limited(MON, SUN) is False   # full 7-day window
    assert is_day_limited(None, SAT) is False  # missing dates
    assert is_day_limited(SAT, MON) is False   # reversed / malformed


def test_valid_days_label():
    assert valid_days_label(THU, SAT) == "Do–Sa"
    assert valid_days_label(MON, FRI) == "Mo–Fr"
    assert valid_days_label(FRI, FRI) == "Fr"   # single day -> just the day
    assert valid_days_label(MON, SAT) is None   # full week -> no badge
    assert valid_days_label(None, None) is None
