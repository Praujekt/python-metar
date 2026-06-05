"""Tests for ``metar.airports``."""

from metar import airports


def test_lookup_known_icao():
    """A known identifier returns an Airport with a non-empty name."""
    a = airports.lookup("KOAK")
    assert a is not None
    assert "Oakland" in a.name


def test_lookup_is_case_insensitive():
    """Lookup should accept any case of the identifier."""
    assert airports.lookup("koak") == airports.lookup("KOAK")
    assert airports.lookup("kOaK") == airports.lookup("KOAK")


def test_lookup_unknown_returns_none():
    """Unknown identifiers return None, not an exception."""
    assert airports.lookup("XXXX") is None


def test_register_adds_entry():
    """``register`` adds a new airport that ``lookup`` then finds."""
    a = airports.Airport("Test Field", (("01", 9),))
    airports.register("KTST", a)
    try:
        assert airports.lookup("KTST") == a
    finally:
        # leave the table how we found it
        airports._AIRPORTS.pop("KTST", None)


def test_all_icaos_returns_sorted_tuple():
    """``all_icaos`` returns a sorted tuple including the seeded entries."""
    icaos = airports.all_icaos()
    assert "KOAK" in icaos
    assert list(icaos) == sorted(icaos)
