"""
Aviation-weather analysis functions that read parsed METAR reports.

Everything in this module is a free function — nothing here mutates the
report. The corresponding methods on :class:`metar.parser.Metar` are thin
wrappers that delegate here, so the same logic powers both the
``analysis.flight_category(m)`` and ``m.flight_category()`` styles.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional, Tuple

from metar.datatypes import distance

if TYPE_CHECKING:
    from metar.parser import Metar


__all__ = [
    "ceiling",
    "flight_category",
    "relative_humidity",
    "wind_components",
]


def ceiling(metar: "Metar", units: str = "FT") -> Optional[distance]:
    """
    Return the ceiling — the lowest BKN, OVC, or VV layer — or ``None``.

    Parameters
    ----------
    metar : Metar
        A parsed report.
    units : str (default ``"FT"``)
        Unit used when synthesizing a zero-height distance for an
        indefinite ceiling (a ``VV`` layer with no numeric height).

    Returns
    -------
    distance or None
        The lowest ceiling-forming layer's height. CLR, SKC, FEW, and SCT
        layers are not ceilings.
    """
    if not metar.sky:
        return None
    lowest = None
    for cover, height, _cloud in metar.sky:
        if cover not in ("BKN", "OVC", "VV"):
            continue
        if height is None:
            return distance(0, units)
        if lowest is None or height.value("FT") < lowest.value("FT"):
            lowest = height
    return lowest


def flight_category(metar: "Metar") -> Optional[str]:
    """
    Classify a report against the FAA flight categories.

    Returns one of ``"VFR"``, ``"MVFR"``, ``"IFR"``, ``"LIFR"`` — or
    ``None`` when neither a visibility nor a sky-condition group is
    present. The returned category is the worse (lower) of the
    visibility-based and ceiling-based assessments.
    """
    ceiling_dist = ceiling(metar)
    if ceiling_dist is None and metar.vis is None:
        return None

    rank = {"VFR": 0, "MVFR": 1, "IFR": 2, "LIFR": 3}

    if metar.vis is None:
        vis_cat = "VFR"
    else:
        sm = metar.vis.value("SM")
        if sm < 1:
            vis_cat = "LIFR"
        elif sm < 3:
            vis_cat = "IFR"
        elif sm <= 5:
            vis_cat = "MVFR"
        else:
            vis_cat = "VFR"

    if ceiling_dist is None:
        ceil_cat = "VFR"
    else:
        ft = ceiling_dist.value("FT")
        if ft < 500:
            ceil_cat = "LIFR"
        elif ft < 1000:
            ceil_cat = "IFR"
        elif ft <= 3000:
            ceil_cat = "MVFR"
        else:
            ceil_cat = "VFR"

    return max([vis_cat, ceil_cat], key=lambda c: rank[c])


def relative_humidity(metar: "Metar") -> Optional[float]:
    """
    Estimate relative humidity (%) from temperature and dewpoint.

    Uses the August-Roche-Magnus saturation-vapor-pressure formulation,
    accurate to within ~0.4 % over the typical METAR range
    (-40 to +50 °C). Returns ``None`` if either reading is missing.
    """
    if metar.temp is None or metar.dewpt is None:
        return None
    a, b = 17.625, 243.04
    T = metar.temp.value("C")
    Td = metar.dewpt.value("C")
    es_T = 6.1094 * math.exp(a * T / (T + b))
    es_Td = 6.1094 * math.exp(a * Td / (Td + b))
    return 100.0 * es_Td / es_T


def wind_components(
    wind_dir_deg: float,
    wind_speed_kt: float,
    runway_heading_deg: float,
) -> Tuple[float, float]:
    """
    Compute the crosswind and headwind components for a wind and runway.

    Unit-agnostic — the ``_kt`` in the parameter name is convention only;
    pass any consistent speed unit and the result follows.

    Parameters
    ----------
    wind_dir_deg
        Direction the wind is *coming from*, in degrees true (0-360).
    wind_speed_kt
        Wind speed.
    runway_heading_deg
        Direction the aircraft points during the takeoff/landing roll on
        this runway, in degrees true (0-360). Runway 27 -> 270; 09 -> 90.

    Returns
    -------
    (crosswind, headwind) : tuple of float
        ``crosswind`` is a non-negative magnitude — it doesn't tell you
        which side of the centerline the wind is coming from.
        ``headwind`` is positive when the wind has a component into the
        nose and negative for a tailwind. Both rounded to 1 decimal.

    Notes
    -----
    Variable winds (``VRB``) have no single direction and cannot be
    decomposed. Callers should check ``Metar.wind_dir is not None`` first
    and may treat variable winds as worst-case crosswind for planning.

    Examples
    --------
    >>> wind_components(360, 10, 360)  # pure headwind
    (0.0, 10.0)
    >>> wind_components(90, 10, 360)   # pure crosswind from the right
    (10.0, 0.0)
    >>> wind_components(180, 10, 360)  # pure tailwind
    (0.0, -10.0)
    """
    angle = math.radians(wind_dir_deg - runway_heading_deg)
    crosswind = abs(wind_speed_kt * math.sin(angle))
    headwind = wind_speed_kt * math.cos(angle)
    return round(crosswind, 1), round(headwind, 1)
