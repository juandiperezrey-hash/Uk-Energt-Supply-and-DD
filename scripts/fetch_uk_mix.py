"""
fetch_uk_mix.py

Pulls Great Britain's electricity generation mix from NESO's (National Energy
System Operator) public Carbon Intensity API — no API key or account needed.

Produces two files:
  data/uk_daily_mix.json   -> mix for the most recently completed 24h
  data/uk_ytd_mix.json     -> average mix from Jan 1 of the current year through today

Docs: https://carbon-intensity.github.io/api-definitions/
"""

import json
import time
import datetime as dt
from collections import defaultdict

import requests

BASE_URL = "https://api.carbonintensity.org.uk"
HEADERS = {"Accept": "application/json"}

# The /generation/{from}/{to} endpoint caps out at a 14-day window per call,
# so year-to-date queries are fetched in chunks and combined.
CHUNK_DAYS = 14

# Website's existing color palette, keyed by label used elsewhere on the site.
COLORS = {
    "Gas": "#7C8B99",
    "Wind": "#14B8A6",
    "Biomass": "#A0522D",
    "Nuclear": "#22C55E",
    "Net Imports": "#8B5CF6",
    "Solar": "#F2A93B",
    "Coal": "#5B4636",
    "Hydropower": "#2E86DE",
    "Other": "#E8B923",
}

# Maps the API's raw fuel-type keys to the labels used on the website's chart.
LABEL_MAP = {
    "gas": "Gas",
    "coal": "Coal",
    "nuclear": "Nuclear",
    "biomass": "Biomass",
    "hydro": "Hydropower",
    "imports": "Net Imports",
    "solar": "Solar",
    "wind": "Wind",
    "other": "Other",
}


def iso(d: dt.datetime) -> str:
    return d.strftime("%Y-%m-%dT%H:%MZ")


def fetch_range(start: dt.datetime, end: dt.datetime) -> list:
    """Returns the list of half-hourly generationmix periods between start and end."""
    url = f"{BASE_URL}/generation/{iso(start)}/{iso(end)}"
    resp = requests.get(url, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    return payload.get("data", [])


def average_mix(periods: list) -> dict:
    """Given a list of half-hourly periods (each with a generationmix array),
    returns the simple average percentage share per fuel type across all periods."""
    totals = defaultdict(float)
    counts = defaultdict(int)

    for period in periods:
        for fuel_entry in period.get("generationmix", []):
            fuel = fuel_entry["fuel"]
            pct = fuel_entry["perc"]
            totals[fuel] += pct
            counts[fuel] += 1

    averaged = {}
    for fuel, total in totals.items():
        averaged[fuel] = total / counts[fuel] if counts[fuel] else 0.0

    return averaged


def to_chart_mix(averaged: dict) -> list:
    labeled = defaultdict(float)
    for raw_fuel, pct in averaged.items():
        label = LABEL_MAP.get(raw_fuel, "Other")
        labeled[label] += pct

    # Normalise so the shares sum to exactly 100 (rounding can drift slightly).
    total = sum(labeled.values()) or 1.0
    mix = [
        {
            "label": label,
            "value": round(pct / total * 100, 1),
            "color": COLORS.get(label, "#9AA5B1"),
        }
        for label, pct in sorted(labeled.items(), key=lambda kv: -kv[1])
    ]
    return mix


def fetch_daily() -> dict:
    """Most recently completed 24h window."""
    now = dt.datetime.utcnow()
    end = now.replace(minute=0, second=0, microsecond=0)
    start = end - dt.timedelta(hours=24)

    print(f"Fetching UK daily mix: {start} -> {end}")
    periods = fetch_range(start, end)
    averaged = average_mix(periods)
    mix = to_chart_mix(averaged)

    return {
        "country": "United Kingdom",
        "period_start": start.isoformat() + "Z",
        "period_end": end.isoformat() + "Z",
        "generated_at_utc": dt.datetime.utcnow().isoformat() + "Z",
        "source": "NESO Carbon Intensity API (api.carbonintensity.org.uk)",
        "mix": mix,
    }


def fetch_ytd() -> dict:
    """Average mix from Jan 1 of the current year through today, in 14-day chunks."""
    today = dt.datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    jan_1 = dt.datetime(today.year, 1, 1)

    print(f"Fetching UK YTD mix: {jan_1} -> {today}")

    all_periods = []
    cur = jan_1
    while cur < today:
        chunk_end = min(cur + dt.timedelta(days=CHUNK_DAYS), today)
        print(f"  Chunk {cur} -> {chunk_end}")
        periods = fetch_range(cur, chunk_end)
        all_periods.extend(periods)
        cur = chunk_end
        time.sleep(0.5)  # be polite to the public API

    averaged = average_mix(all_periods)
    mix = to_chart_mix(averaged)

    return {
        "country": "United Kingdom",
        "period_start": jan_1.date().isoformat(),
        "period_end": today.date().isoformat(),
        "generated_at_utc": dt.datetime.utcnow().isoformat() + "Z",
        "source": "NESO Carbon Intensity API (api.carbonintensity.org.uk)",
        "periods_averaged": len(all_periods),
        "mix": mix,
    }


def main():
    daily = fetch_daily()
    with open("data/uk_daily_mix.json", "w", encoding="utf-8") as f:
        json.dump(daily, f, indent=2, ensure_ascii=False)
    print("Wrote data/uk_daily_mix.json")
    print(json.dumps(daily, indent=2))

    ytd = fetch_ytd()
    with open("data/uk_ytd_mix.json", "w", encoding="utf-8") as f:
        json.dump(ytd, f, indent=2, ensure_ascii=False)
    print("Wrote data/uk_ytd_mix.json")
    print(json.dumps(ytd, indent=2))


if __name__ == "__main__":
    main()
