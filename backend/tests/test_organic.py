"""Tests for organic ("Bio") detection from an offer's name/brand."""
from app.organic import is_organic


def test_detects_bio_markers():
    assert is_organic("Bio Avocado") is True
    assert is_organic("Biomilch 1,5%") is True            # German compound prefix
    assert is_organic("Deutsche Bioland Zucchini") is True
    assert is_organic("EDEKA Bio Freilandeier") is True
    assert is_organic("Apfelsaft", "EDEKA Bio") is True   # marker on the brand
    assert is_organic("Ökomilch") is True
    assert is_organic("Organic Bananas") is True
    assert is_organic("Demeter Joghurt") is True


def test_ignores_non_organic_and_substring_traps():
    assert is_organic("Avocado") is False
    assert is_organic("Vollmilch") is False
    assert is_organic("Symbiose Riegel") is False           # "bio" mid-word, not organic
    assert is_organic("Hähnchen antibiotikafrei") is False  # "bio" inside antibiotika-, not organic
    assert is_organic("Banane", None) is False
