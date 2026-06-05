"""
Fetch current METAR reports from aviationweather.gov.

Stdlib-only so the package stays dependency-free for Lambda deployment.
The aviationweather.gov endpoint is open (no auth) and returns raw
METAR text, which we hand straight to the parser.
"""

from __future__ import annotations

import urllib.parse
import urllib.request

from metar.parser import Metar


AVIATION_WEATHER_URL = "https://aviationweather.gov/api/data/metar"


def fetch_metar(icao: str, *, timeout: float = 3.0) -> Metar:
    """
    Fetch the most recent METAR for ``icao`` and return a parsed report.

    Parameters
    ----------
    icao : str
        Four-letter ICAO identifier (case-insensitive). e.g. ``"KOAK"``.
    timeout : float, default 3.0
        HTTP request timeout in seconds. 3 s aligns with Slack's
        synchronous slash-command response window.

    Returns
    -------
    Metar
        A parsed report.

    Raises
    ------
    ValueError
        ``icao`` is empty or not the right shape.
    LookupError
        The endpoint responded successfully but contained no METAR data
        for the requested station.
    urllib.error.URLError, TimeoutError
        Network failures pass through unchanged.
    metar.parser.ParserError
        Upstream returned a METAR the parser cannot decode.

    Notes
    -----
    Parsing uses ``strict=False`` so a trailing-fragment quirk in a real
    report does not crash the bot; warnings are emitted via the standard
    :mod:`warnings` machinery for the caller to filter or surface.
    """
    icao = icao.strip().upper()
    if not icao or not (3 <= len(icao) <= 4) or not icao.isalnum():
        raise ValueError("invalid ICAO identifier: %r" % icao)
    qs = urllib.parse.urlencode({"ids": icao, "format": "raw"})
    url = "%s?%s" % (AVIATION_WEATHER_URL, qs)
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    for line in body.splitlines():
        line = line.strip()
        if line:
            return Metar(line, strict=False)
    raise LookupError("no METAR returned for station %r" % icao)
