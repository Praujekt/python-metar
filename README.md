# python-metar (personal fork)

Personal fork of [python-metar/python-metar](https://github.com/python-metar/python-metar) with pilot-friendly extensions and Slack-bot scaffolding.

The upstream parser is unchanged in spirit — it still decodes METAR/SPECI weather reports. This fork adds:

- **Flight category classifier** — VFR / MVFR / IFR / LIFR per FAA thresholds
- **Plain-English output layer** — human-readable summary for non-pilots
- **Crosswind / headwind helper** — pure math for runway planning
- **Expanded remarks coverage** — `TSNO`, `PWINO`, `FZRANO`, `RVRNO`, `$`, `VIRGA`, `FROPA`, `PRESRR`, `PRESFR`, variable ceiling, variable visibility, surface and tower visibility
- **Slack-bot scaffolding** — fetch / airports / Block Kit formatter / AWS Lambda handler

## Module layout

| Module | Purpose |
|---|---|
| `metar.parser` | The METAR / SPECI parser. Defines the `Metar` class. |
| `metar.datatypes` | Unit-aware value types: `temperature`, `pressure`, `speed`, `distance`, `direction`, `precipitation`. |
| `metar.station` | ICAO -> station-metadata lookup using the bundled NSD data. Sparse for US stations. |
| `metar.analysis` | Free functions over a parsed `Metar`: `ceiling`, `flight_category`, `relative_humidity`, `wind_components`. |
| `metar.format` | Plain-English / sentence formatters. Used by `to_plain_english`. |
| `metar.fetch` | Stdlib HTTP client for the aviationweather.gov API. |
| `metar.airports` | Small curated ICAO -> airport-name / runways table. |
| `metar.slack` | Slack Block Kit formatter. |
| `lambda_handler.py` | AWS Lambda entry point for the `/metar` slash command. |

The historical `from metar import Metar` and `from metar import Station` imports still work via aliases in `metar/__init__.py`.

## Quick start

```python
from metar.parser import Metar
from metar.airports import lookup
from metar.format import to_plain_english

m = Metar("METAR KOAK 050153Z 26008KT 10SM CLR 17/11 A2989 RMK AO2 SLP121")
print(m.flight_category())            # VFR
print(m.ceiling())                    # None  (CLR = no ceiling)
print(to_plain_english(m, station_name=lookup("KOAK").name))
```

```
🟢 VFR | KOAK — Oakland Int'l | observed 01:53Z

Winds west at 8 knots. Visibility 10 miles. Clear skies, no ceiling.
Temperature 63°F (17°C), dewpoint 51°F (11°C), humidity 65%.
Altimeter 29.89 inHg. Sea level pressure 1012.1 hPa.
Station is automated (AO2).
```

## Slack bot

End goal is a Lambda-backed `/metar KOAK` slash command. The pieces:

```python
from metar.fetch import fetch_metar
from metar.slack import to_slack_blocks
from metar.airports import lookup

m = fetch_metar("KOAK")
payload = to_slack_blocks(m, station_name=lookup("KOAK").name)
# payload is now a dict; json.dumps() it into a Slack response body.
```

`lambda_handler.py` ties this to API Gateway + Slack signature verification. Set `SLACK_SIGNING_SECRET` in the Lambda environment before deploying.

## Tests

```sh
python3 -m venv .venv
.venv/bin/pip install -e .[tests]
.venv/bin/python -m pytest -q
```

Currently **147 tests, all passing**.

## License

BSD 2-Clause, inherited from upstream. See `LICENSE`.
