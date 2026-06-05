"""Test metar/station.py."""
from metar import station


def test_station():
    """Can we build a station object."""
    st = station.station("KDSM")
    assert st.id == "KDSM"
