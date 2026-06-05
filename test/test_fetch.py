"""Tests for ``metar.fetch`` — the aviationweather.gov client."""

from io import BytesIO
from unittest.mock import patch

import pytest

from metar import fetch
from metar.parser import Metar


SAMPLE_METAR = (
    "KOAK 050153Z 26008KT 10SM CLR 17/11 A2989 "
    "RMK AO2 SLP121 T01720106"
)


class _FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._body


@pytest.mark.parametrize("bad", ["", "K", "AB", "KOAKK", "K1@K"])
def test_fetch_metar_rejects_bad_icao(bad):
    """Invalid identifiers raise ``ValueError`` before touching the network."""
    with pytest.raises(ValueError):
        fetch.fetch_metar(bad)


def test_fetch_metar_parses_first_nonempty_line():
    """The first non-empty line of the response is what gets parsed."""
    body = b"\n\n" + SAMPLE_METAR.encode() + b"\n"
    with patch("metar.fetch.urllib.request.urlopen",
               return_value=_FakeResponse(body)) as mocked:
        m = fetch.fetch_metar("koak")
    assert isinstance(m, Metar)
    assert m.station_id == "KOAK"
    # Verify case-folding and URL composition happen as expected.
    called_url = mocked.call_args[0][0]
    assert "ids=KOAK" in called_url
    assert "format=raw" in called_url


def test_fetch_metar_raises_lookup_error_on_empty_body():
    """An empty response body raises ``LookupError``."""
    with patch("metar.fetch.urllib.request.urlopen",
               return_value=_FakeResponse(b"\n\n")):
        with pytest.raises(LookupError):
            fetch.fetch_metar("KOAK")
