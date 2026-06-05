"""
Slack Block Kit formatter for METAR reports.

:func:`to_slack_blocks` returns a dict that can be ``json.dumps``-ed
directly into a Slack slash-command HTTP response body. Use this when
you want the richer phone- and screen-reader-friendly layout; reach for
:func:`metar.format.to_plain_english` instead when you need a single
ASCII string.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from metar.analysis import flight_category, relative_humidity
from metar.format import (
    FLIGHT_CATEGORY_EMOJI,
    sky_sentence,
    station_status_sentence,
    wind_sentence,
)
from metar.parser import Metar


def to_slack_blocks(
    metar: Metar,
    station_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a Slack Block Kit payload for a parsed METAR.

    Parameters
    ----------
    metar
        Parsed report.
    station_name
        Friendly airport name (e.g. ``"Oakland Int'l"``) shown in the
        header alongside the ICAO. The :mod:`metar.airports` module is
        the typical source.

    Returns
    -------
    dict
        ``{"response_type": "in_channel", "blocks": [...]}`` — the exact
        shape Slack expects in a slash-command response body.
    """
    blocks: List[Dict[str, Any]] = []
    blocks.append(_header_block(metar, station_name))
    blocks.append(_conditions_block(metar))
    temp_block = _temperature_block(metar)
    if temp_block is not None:
        blocks.append(temp_block)
    press_block = _pressure_block(metar)
    if press_block is not None:
        blocks.append(press_block)
    status = station_status_sentence(metar)
    if status:
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": status}],
        })
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": "`%s`" % metar.code}],
    })
    return {"response_type": "in_channel", "blocks": blocks}


def _header_block(metar: Metar, station_name: Optional[str]) -> Dict[str, Any]:
    cat = flight_category(metar)
    parts = []
    if cat:
        parts.append("%s %s" % (FLIGHT_CATEGORY_EMOJI[cat], cat))
    sta = metar.station_id or "????"
    if station_name:
        sta = "%s — %s" % (sta, station_name)
    parts.append(sta)
    if metar.time:
        parts.append("observed %sZ" % metar.time.strftime("%H:%M"))
    return {
        "type": "header",
        "text": {"type": "plain_text", "text": " | ".join(parts), "emoji": True},
    }


def _conditions_block(metar: Metar) -> Dict[str, Any]:
    parts = [wind_sentence(metar)]
    if metar.vis is not None:
        parts.append("Visibility %s." % metar.vis.string("SM"))
    if metar.weather:
        parts.append("Weather: %s." % metar.present_weather())
    sky = sky_sentence(metar)
    if sky:
        parts.append(sky)
    return {
        "type": "section",
        "text": {"type": "mrkdwn", "text": " ".join(parts)},
    }


def _temperature_block(metar: Metar) -> Optional[Dict[str, Any]]:
    if metar.temp is None or metar.dewpt is None:
        return None
    rh = relative_humidity(metar)
    return {
        "type": "section",
        "fields": [
            {"type": "mrkdwn", "text": "*Temperature*\n%.0f°F (%.0f°C)" % (
                metar.temp.value("F"), metar.temp.value("C"))},
            {"type": "mrkdwn", "text": "*Dewpoint*\n%.0f°F (%.0f°C)" % (
                metar.dewpt.value("F"), metar.dewpt.value("C"))},
            {"type": "mrkdwn", "text": "*Humidity*\n%.0f%%" % rh},
        ],
    }


def _pressure_block(metar: Metar) -> Optional[Dict[str, Any]]:
    if metar.press is None:
        return None
    fields = [{
        "type": "mrkdwn",
        "text": "*Altimeter*\n%.2f inHg" % metar.press.value("IN"),
    }]
    if metar.press_sea_level is not None:
        fields.append({
            "type": "mrkdwn",
            "text": "*Sea level*\n%.1f hPa" % metar.press_sea_level.value("HPA"),
        })
    return {"type": "section", "fields": fields}
