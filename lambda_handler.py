"""
AWS Lambda entry point for the ``/metar`` Slack slash command.

Wire-up
-------
- API Gateway HTTP API (POST) -> this function.
- Slack POSTs URL-encoded form data: ``token``, ``team_id``, ``channel_id``,
  ``user_id``, ``command``, ``text``, ``response_url``, ``trigger_id``.
- We respond synchronously within Slack's 3-second window.

Environment variables
---------------------
``SLACK_SIGNING_SECRET``
    Signing secret from your Slack app's "Basic Information" page. Used to
    verify request authenticity. If unset, signature checks are skipped
    (local dev / smoke testing only — never deploy without this set).
``METAR_FORMAT`` (optional, default ``"slack"``)
    ``"slack"`` -> Block Kit response. ``"plain"`` -> plain-text response.

Usage from inside Slack
-----------------------
``/metar KOAK``           -- show KOAK weather (Block Kit)
``/metar KOAK --plain``   -- force plain-text output
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import traceback
import urllib.parse
from typing import Any, Dict

from metar.airports import lookup
from metar.fetch import fetch_metar
from metar.format import to_plain_english
from metar.slack import to_slack_blocks


SLACK_SIGNATURE_VERSION = "v0"
SLACK_REPLAY_WINDOW_SECONDS = 300


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """API Gateway / Lambda entry point."""
    try:
        body = _decode_body(event)
        _verify_slack_signature(event, body)
        params = urllib.parse.parse_qs(body)
        text = params.get("text", [""])[0].strip()
        parts = text.split()
        if not parts:
            return _slack_text("Usage: `/metar KOAK` or `/metar KOAK --plain`")
        icao = parts[0].upper()
        plain = "--plain" in parts[1:]
        return _build_response(icao, plain)
    except PermissionError as exc:
        return {"statusCode": 401, "body": str(exc)}
    except (ValueError, LookupError) as exc:
        return _slack_text(":warning: %s" % exc)
    except Exception:
        # Server-side logging only — don't leak stack traces to Slack.
        traceback.print_exc()
        return _slack_text(":warning: An error occurred fetching the METAR.")


def _build_response(icao: str, plain: bool) -> Dict[str, Any]:
    metar = fetch_metar(icao)
    airport = lookup(icao)
    name = airport.name if airport else None
    if plain or os.environ.get("METAR_FORMAT", "slack").lower() == "plain":
        text_body = "```\n%s\n```\n%s" % (
            metar.code, to_plain_english(metar, station_name=name),
        )
        return _slack_text(text_body)
    payload = to_slack_blocks(metar, station_name=name)
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }


def _decode_body(event: Dict[str, Any]) -> str:
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    return body


def _verify_slack_signature(event: Dict[str, Any], body: str) -> None:
    """
    Validate the ``X-Slack-Signature`` header against the request body.

    Skipped when ``SLACK_SIGNING_SECRET`` is unset — useful only for
    local smoke tests. Always set the secret in real deployments.
    """
    secret = os.environ.get("SLACK_SIGNING_SECRET")
    if not secret:
        return
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    ts = headers.get("x-slack-request-timestamp", "")
    sig = headers.get("x-slack-signature", "")
    if not ts or not sig:
        raise PermissionError("missing slack signature headers")
    try:
        ts_int = int(ts)
    except ValueError:
        raise PermissionError("invalid slack timestamp")
    if abs(time.time() - ts_int) > SLACK_REPLAY_WINDOW_SECONDS:
        raise PermissionError("slack timestamp outside replay window")
    sig_basestring = "%s:%s:%s" % (SLACK_SIGNATURE_VERSION, ts, body)
    digest = hmac.new(
        secret.encode("utf-8"),
        sig_basestring.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    expected = "%s=%s" % (SLACK_SIGNATURE_VERSION, digest)
    if not hmac.compare_digest(sig, expected):
        raise PermissionError("slack signature mismatch")


def _slack_text(text: str) -> Dict[str, Any]:
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"response_type": "in_channel", "text": text}),
    }
