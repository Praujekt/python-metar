"""Tests for ``metar.slack`` Block Kit formatter."""

import json

from metar import slack
from metar.parser import Metar


SAMPLE_VFR = (
    "METAR KOAK 050153Z 26008KT 10SM CLR 17/11 A2989 "
    "RMK AO2 SLP121 T01720106"
)
SAMPLE_IFR = (
    "METAR KSFO 051256Z 19012KT 3SM -RA BKN008 OVC015 13/11 A2981 "
    "RMK AO2 SLP098"
)


def test_to_slack_blocks_has_required_top_level_shape():
    """Output is JSON-serializable with the keys Slack expects."""
    payload = slack.to_slack_blocks(Metar(SAMPLE_VFR))
    assert payload["response_type"] == "in_channel"
    assert isinstance(payload["blocks"], list)
    assert len(payload["blocks"]) >= 3
    # Round-trip through json so we know nothing exotic crept in.
    json.dumps(payload)


def test_header_block_carries_category_and_station_name():
    """Header text includes both the category emoji and the friendly name."""
    payload = slack.to_slack_blocks(Metar(SAMPLE_VFR), station_name="Oakland Int'l")
    header = payload["blocks"][0]
    assert header["type"] == "header"
    text = header["text"]["text"]
    assert "VFR" in text
    assert "KOAK" in text
    assert "Oakland Int'l" in text


def test_temperature_block_present_when_data_available():
    """A temp/dew/humidity section shows up for a normal report."""
    payload = slack.to_slack_blocks(Metar(SAMPLE_VFR))
    fields = []
    for b in payload["blocks"]:
        if b.get("type") == "section" and "fields" in b:
            fields.extend(b["fields"])
    field_text = " ".join(f["text"] for f in fields)
    assert "Temperature" in field_text
    assert "Dewpoint" in field_text
    assert "Humidity" in field_text


def test_raw_metar_appears_in_a_context_block():
    """The raw METAR code lands in a trailing context block."""
    code = SAMPLE_IFR
    payload = slack.to_slack_blocks(Metar(code))
    contexts = [b for b in payload["blocks"] if b["type"] == "context"]
    assert any(
        any(code in el["text"] for el in c["elements"])
        for c in contexts
    )


def test_ifr_report_block_count_is_reasonable():
    """An IFR report with weather + sky + temp + pressure has 5+ blocks."""
    payload = slack.to_slack_blocks(Metar(SAMPLE_IFR))
    types = [b["type"] for b in payload["blocks"]]
    assert types.count("header") == 1
    assert types.count("section") >= 2
    assert types.count("context") >= 1
