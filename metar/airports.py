"""
Lightweight ICAO -> airport metadata lookup.

The bundled :file:`metar/nsd_cccc.txt` is sparse for US airports, so this
module ships a curated table with just enough coverage for the Slack
bot's common stations. Callers can extend the table at runtime via
:func:`register` — the long-term plan is to load a CSV at startup
instead of hand-maintaining this dict.

Schema: each entry is :class:`Airport` with a human name and an optional
tuple of ``(runway_label, true_heading_degrees)`` pairs. Runway data is
*placeholder* for the scaffold — verify against AirNav / the FAA chart
supplement before relying on it for actual crosswind decisions.
"""

from __future__ import annotations

from typing import NamedTuple, Optional, Tuple


class Airport(NamedTuple):
    """An airport entry: human-readable name and optional runway list."""

    name: str
    runways: Tuple[Tuple[str, int], ...] = ()


# Seed table — names verified, runway headings approximated.
_AIRPORTS = {
    "KOAK": Airport("Oakland Int'l", (("12", 117), ("30", 297))),
    "KSFO": Airport("San Francisco Int'l",
                    (("01L", 11), ("19R", 191), ("10L", 117), ("28R", 297))),
    "KSJC": Airport("San Jose Int'l", (("12L", 117), ("30R", 297))),
    "KEWR": Airport("Newark Liberty Int'l",
                    (("04L", 41), ("22R", 221), ("11", 113), ("29", 293))),
    "KJFK": Airport("John F. Kennedy Int'l",
                    (("04L", 44), ("22R", 224), ("13L", 134), ("31R", 314))),
    "KLAX": Airport("Los Angeles Int'l",
                    (("06L", 69), ("24R", 249), ("07L", 69), ("25R", 249))),
}


def lookup(icao: str) -> Optional[Airport]:
    """
    Return the :class:`Airport` entry for ``icao``, or ``None`` if missing.

    The lookup is case-insensitive — ``"koak"`` and ``"KOAK"`` are equivalent.
    """
    return _AIRPORTS.get(icao.upper())


def register(icao: str, airport: Airport) -> None:
    """
    Add or override an entry in the lookup table.

    Useful for tests or for the Slack bot to enrich its own table at
    startup without forking this module.
    """
    _AIRPORTS[icao.upper()] = airport


def all_icaos() -> Tuple[str, ...]:
    """Return all known ICAO identifiers, sorted."""
    return tuple(sorted(_AIRPORTS))
