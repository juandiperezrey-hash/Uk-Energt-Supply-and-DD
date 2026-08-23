# Cordillera Energy — UK Grid Data Pipeline

Pulls Great Britain's electricity generation mix — both a rolling daily
snapshot and a year-to-date average — from **NESO** (National Energy System
Operator)'s public Carbon Intensity API. No API key or account needed.

## What this does

1. `scripts/fetch_uk_mix.py` calls NESO's public Carbon Intensity API:
   - Last 24h of half-hourly generation-mix readings → `data/uk_daily_mix.json`
   - Jan 1 of the current year through today (in 14-day chunks, since that's
     the API's max window per call) → `data/uk_ytd_mix.json`
2. A GitHub Actions workflow (`.github/workflows/update-uk-mix.yml`) runs this
   automatically every day and commits the updated files.

## Setup

No secrets or API keys needed — same as the Colombia pipeline. Once this is
pushed to GitHub, go to the **Actions** tab → **Update UK Generation Mix
(NESO)** → **Run workflow** to test it immediately.

## Reading the data

Once it runs successfully, both JSON files are available at:
```
https://raw.githubusercontent.com/<your-username>/<repo-name>/main/data/uk_daily_mix.json
https://raw.githubusercontent.com/<your-username>/<repo-name>/main/data/uk_ytd_mix.json
```

Both use the same shape the website's `renderPie()` function already expects:
```json
{
  "mix": [
    { "label": "Gas", "value": 28.4, "color": "#7C8B99" },
    { "label": "Wind", "value": 26.1, "color": "#14B8A6" },
    ...
  ]
}
```

## Note on methodology

The Carbon Intensity API reports the *percentage* fuel mix per half-hour
period rather than absolute energy, so the year-to-date figure here is a
simple average of each period's percentage share — a good approximation of
the year's mix, though not identical to an energy-weighted average across
periods of very different demand (e.g. a windy Sunday night vs. a still
weekday evening carry equal weight in this average). If a more precise
energy-weighted figure is needed later, NESO's Elexon BMRS API exposes
absolute MWh by fuel type and could replace this if it matters for the pitch.

## Testing locally first (recommended)

```bash
pip install requests
python scripts/fetch_uk_mix.py
```

If NESO changes their response field names, share the error message and
I'll adjust the script.
