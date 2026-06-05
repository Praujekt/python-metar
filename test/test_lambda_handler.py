"""Tests for the Lambda entry point."""

import hashlib
import hmac
import json
import os
import time
import urllib.parse
from unittest.mock import patch

import pytest

import lambda_handler as lh


SAMPLE_METAR_LINE = (
    "KOAK 050153Z 26008KT 10SM CLR 17/11 A2989 "
    "RMK AO2 SLP121 T01720106"
)


class _FakeResponse:
    def __init__(self, body):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self._body


def _sign(body: str, secret: str, timestamp: int) -> dict:
    basestring = "%s:%s:%s" % (lh.SLACK_SIGNATURE_VERSION, timestamp, body)
    digest = hmac.new(
        secret.encode(), basestring.encode(), hashlib.sha256
    ).hexdigest()
    return {
        "x-slack-request-timestamp": str(timestamp),
        "x-slack-signature": "%s=%s" % (lh.SLACK_SIGNATURE_VERSION, digest),
    }


def _event(body: str, headers: dict = None):
    return {"body": body, "headers": headers or {}, "isBase64Encoded": False}


def test_handler_usage_message_when_text_empty():
    """No ICAO -> usage hint, no network call."""
    event = _event(urllib.parse.urlencode({"text": ""}))
    with patch.dict(os.environ, {}, clear=True):
        resp = lh.lambda_handler(event, None)
    body = json.loads(resp["body"])
    assert resp["statusCode"] == 200
    assert "/metar" in body["text"]


def test_handler_happy_path_block_kit():
    """With a valid ICAO and slack format, returns a Block Kit payload."""
    event = _event(urllib.parse.urlencode({"text": "KOAK"}))
    with patch.dict(os.environ, {"METAR_FORMAT": "slack"}, clear=True), \
         patch("metar.fetch.urllib.request.urlopen",
               return_value=_FakeResponse(SAMPLE_METAR_LINE.encode())):
        resp = lh.lambda_handler(event, None)
    payload = json.loads(resp["body"])
    assert resp["statusCode"] == 200
    assert "blocks" in payload
    assert any(b["type"] == "header" for b in payload["blocks"])


def test_handler_plain_flag_returns_plain_text():
    """The ``--plain`` flag forces plain-text formatting."""
    event = _event(urllib.parse.urlencode({"text": "KOAK --plain"}))
    with patch.dict(os.environ, {}, clear=True), \
         patch("metar.fetch.urllib.request.urlopen",
               return_value=_FakeResponse(SAMPLE_METAR_LINE.encode())):
        resp = lh.lambda_handler(event, None)
    body = json.loads(resp["body"])
    assert "blocks" not in body
    assert "VFR" in body["text"]


def test_handler_signature_verification_accepts_valid_sig():
    """A correctly-signed request passes verification and reaches fetch."""
    secret = "test-secret"
    body = urllib.parse.urlencode({"text": "KOAK"})
    event = _event(body, headers=_sign(body, secret, int(time.time())))
    with patch.dict(os.environ, {"SLACK_SIGNING_SECRET": secret}, clear=True), \
         patch("metar.fetch.urllib.request.urlopen",
               return_value=_FakeResponse(SAMPLE_METAR_LINE.encode())):
        resp = lh.lambda_handler(event, None)
    assert resp["statusCode"] == 200


def test_handler_signature_verification_rejects_bad_sig():
    """A bad signature returns 401 — no fetch attempted."""
    secret = "test-secret"
    body = urllib.parse.urlencode({"text": "KOAK"})
    bad_headers = _sign(body, "wrong-secret", int(time.time()))
    event = _event(body, headers=bad_headers)
    with patch.dict(os.environ, {"SLACK_SIGNING_SECRET": secret}, clear=True), \
         patch("metar.fetch.urllib.request.urlopen") as mock_open:
        resp = lh.lambda_handler(event, None)
    assert resp["statusCode"] == 401
    mock_open.assert_not_called()


def test_handler_signature_verification_rejects_old_timestamp():
    """A timestamp >5 min old is rejected (replay protection)."""
    secret = "test-secret"
    body = urllib.parse.urlencode({"text": "KOAK"})
    old_ts = int(time.time()) - 600
    event = _event(body, headers=_sign(body, secret, old_ts))
    with patch.dict(os.environ, {"SLACK_SIGNING_SECRET": secret}, clear=True):
        resp = lh.lambda_handler(event, None)
    assert resp["statusCode"] == 401


def test_handler_invalid_icao_returns_friendly_error():
    """A garbage ICAO produces a Slack-readable warning, not a 500."""
    event = _event(urllib.parse.urlencode({"text": "INVALID!"}))
    with patch.dict(os.environ, {}, clear=True):
        resp = lh.lambda_handler(event, None)
    body = json.loads(resp["body"])
    assert resp["statusCode"] == 200
    assert ":warning:" in body["text"]
