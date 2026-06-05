"""
Human-readable formatters for parsed METAR reports.

Everything in this module is a free function. The
:meth:`metar.parser.Metar.to_plain_english` method is a thin wrapper
around :func:`to_plain_english` here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from metar.analysis import ceiling, flight_category, relative_humidity

if TYPE_CHECKING:
    from metar.parser import Metar


__all__ = [
    "COMPASS_PLAIN",
    "FLIGHT_CATEGORY_EMOJI",
    "to_plain_english",
    "wind_sentence",
    "sky_sentence",
    "station_status_sentence",
]


COMPASS_PLAIN = {
    "N":   "north",         "NNE": "north-northeast",
    "NE":  "northeast",     "ENE": "east-northeast",
    "E":   "east",          "ESE": "east-southeast",
    "SE":  "southeast",     "SSE": "south-southeast",
    "S":   "south",         "SSW": "south-southwest",
    "SW":  "southwest",     "WSW": "west-southwest",
    "W":   "west",          "WNW": "west-northwest",
    "NW":  "northwest",     "NNW": "north-northwest",
}

# Standard FAA category colors used on aviation-weather maps and apps.
FLIGHT_CATEGORY_EMOJI = {
    "VFR":  "\U0001F7E2",  # green circle
    "MVFR": "\U0001F535",  # blue circle
    "IFR":  "\U0001F534",  # red circle
    "LIFR": "\U0001F7E3",  # purple circle
}


def wind_sentence(metar: "Metar") -> str:
    """Plain-English sentence describing wind direction, speed, and gusts."""
    if metar.wind_speed is None or metar.wind_speed.value("KT") == 0:
        return "Winds calm."
    spd = "%.0f knots" % metar.wind_speed.value("KT")
    if metar.wind_dir is None:
        if metar.wind_dir_from is not None and metar.wind_dir_to is not None:
            heading = "variable from %.0f° to %.0f°" % (
                metar.wind_dir_from.value(), metar.wind_dir_to.value()
            )
        else:
            heading = "variable"
    else:
        heading = COMPASS_PLAIN.get(
            metar.wind_dir.compass(), metar.wind_dir.compass()
        )
    sentence = "Winds %s at %s" % (heading, spd)
    if metar.wind_gust is not None:
        sentence += ", gusting to %.0f knots" % metar.wind_gust.value("KT")
    return sentence + "."


def sky_sentence(metar: "Metar") -> str:
    """Plain-English sentence describing sky cover and ceiling."""
    if not metar.sky:
        return ""
    description = metar.sky_conditions()
    if description:
        description = description[0].upper() + description[1:]
    ceil = ceiling(metar)
    if description.lower().startswith("clear"):
        return "Clear skies, no ceiling."
    if ceil is None:
        return "%s. No ceiling." % description
    return "%s. Ceiling %.0f feet." % (description, ceil.value("FT"))


def station_status_sentence(metar: "Metar") -> str:
    """
    Plain-English sentence describing key sensor and station flags.

    Returns an empty string if nothing notable is set. Reads parsed
    attributes only — no raw-code regexing.
    """
    items = []
    if "Automated station (type 2)" in metar._remarks:
        items.append("Station is automated (AO2).")
    elif "Automated station" in metar._remarks:
        items.append("Station is automated (AO1).")
    sensor_flags = []
    if metar.tsno:
        sensor_flags.append("thunderstorm sensor not operating (TSNO)")
    if metar.pwino:
        sensor_flags.append("present-weather sensor not operating (PWINO)")
    if metar.fzrano:
        sensor_flags.append("freezing-rain sensor not operating (FZRANO)")
    if metar.rvrno:
        sensor_flags.append("RVR data not available (RVRNO)")
    if sensor_flags:
        items.append("Sensor issues: " + ", ".join(sensor_flags) + ".")
    if metar.maintenance_needed:
        items.append("Station needs maintenance ($).")
    return " ".join(items)


def to_plain_english(metar: "Metar", station_name: Optional[str] = None) -> str:
    """
    Multi-line human-readable summary of a METAR report.

    Suitable for Slack messages, terminal dumps, or any context where a
    non-pilot reader wants the gist without learning METAR codes.

    Parameters
    ----------
    metar : Metar
        Parsed report.
    station_name : str, optional
        Friendly airport name to display in the header alongside the
        ICAO identifier (e.g. ``"Oakland Int'l"``). The bundled NSD data
        is sparse for most US airports, so callers usually supply this.

    Returns
    -------
    str
        Multi-line string. First line is a header with category, station
        id (and optional name), and observation time. Body lines describe
        winds + visibility + sky, then temperature/humidity, then
        pressure, then station-status flags.
    """
    lines = []

    cat = flight_category(metar)
    header_parts = []
    if cat:
        header_parts.append("%s %s" % (FLIGHT_CATEGORY_EMOJI[cat], cat))
    sta = metar.station_id or "????"
    if station_name:
        sta = "%s — %s" % (sta, station_name)
    header_parts.append(sta)
    if metar.time:
        header_parts.append("observed %sZ" % metar.time.strftime("%H:%M"))
    lines.append(" | ".join(header_parts))
    lines.append("")

    body = [wind_sentence(metar)]
    if metar.vis is not None:
        body.append("Visibility %s." % metar.vis.string("SM"))
    weather = metar.present_weather() if metar.weather else ""
    if weather:
        body.append("Weather: %s." % weather)
    sky = sky_sentence(metar)
    if sky:
        body.append(sky)
    lines.append(" ".join(body))

    if metar.temp is not None and metar.dewpt is not None:
        rh = relative_humidity(metar)
        lines.append(
            "Temperature %.0f°F (%.0f°C), "
            "dewpoint %.0f°F (%.0f°C), humidity %.0f%%."
            % (
                metar.temp.value("F"), metar.temp.value("C"),
                metar.dewpt.value("F"), metar.dewpt.value("C"),
                rh,
            )
        )

    if metar.press is not None:
        press_sentence = "Altimeter %.2f inHg." % metar.press.value("IN")
        if metar.press_sea_level is not None:
            press_sentence += " Sea level pressure %.1f hPa." % (
                metar.press_sea_level.value("HPA"),
            )
        lines.append(press_sentence)

    status = station_status_sentence(metar)
    if status:
        lines.append(status)

    return "\n".join(lines)
