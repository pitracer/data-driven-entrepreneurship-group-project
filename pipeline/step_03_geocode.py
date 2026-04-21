"""
Step 03 — Geocode firm addresses via Nominatim (free, no API key).
Rate limit: 1 req/sec. ~3-6 min for 196 firms.

Reads search_results.parquet, geocodes addresses, writes geocode_results.parquet.

Usage: python -m pipeline.step_03_geocode
"""
from __future__ import annotations

import sys
import time

import pandas as pd
import requests

from pipeline.cache import FileCache
from pipeline.config import (
    CACHE_GEOCODE,
    DATA_PROCESSED,
    FIRMS_CLEAN,
    NOMINATIM_RATE_LIMIT,
    NOMINATIM_USER_AGENT,
    ORBIS_DATA,
    ensure_dirs,
)

SEARCH_RESULTS = DATA_PROCESSED / "search_results.parquet"
GEOCODE_RESULTS = DATA_PROCESSED / "geocode_results.parquet"


def geocode_nominatim(address: str) -> tuple[float | None, float | None]:
    """Query Nominatim for lat/lon of an address in Düsseldorf."""
    if not address:
        return None, None
    query = address.title()
    if "düsseldorf" not in query.lower() and "duesseldorf" not in query.lower():
        query += ", Düsseldorf, Germany"
    elif "germany" not in query.lower():
        query += ", Germany"
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": NOMINATIM_USER_AGENT},
            timeout=10,
        )
        if resp.ok and resp.json():
            r = resp.json()[0]
            return float(r["lat"]), float(r["lon"])
    except Exception:
        pass
    return None, None


def run() -> pd.DataFrame:
    ensure_dirs()

    # Load base firms
    df_firms = pd.read_parquet(FIRMS_CLEAN)[["bvd_id", "company_name"]]
    df = df_firms.copy()
    df["address"] = None

    # Merge search results addresses
    if SEARCH_RESULTS.exists():
        df_search = pd.read_parquet(SEARCH_RESULTS)[["bvd_id", "address"]]
        df = df.drop(columns=["address"]).merge(df_search, on="bvd_id", how="left")

    # Fill gaps with Orbis addresses
    if ORBIS_DATA.exists():
        orbis = pd.read_parquet(ORBIS_DATA)[["bvd_id", "orbis_street", "orbis_postcode", "orbis_city"]]
        df = df.merge(orbis, on="bvd_id", how="left")
        orbis_addr = (
            df["orbis_street"].fillna("") + ", "
            + df["orbis_postcode"].astype(str).replace("<NA>", "") + " "
            + df["orbis_city"].fillna("")
        ).str.strip(", ")
        mask = df["address"].isna() & df["orbis_street"].notna()
        df.loc[mask, "address"] = orbis_addr[mask]
        df = df.drop(columns=["orbis_street", "orbis_postcode", "orbis_city"])

    cache = FileCache(CACHE_GEOCODE)
    rows = []
    cache_hits = 0
    found = 0
    failed = 0

    firms_with_address = df[df["address"].notna()]
    print(f"[step_03] {len(firms_with_address)} firms with addresses to geocode")

    for _, row in firms_with_address.iterrows():
        address = str(row["address"]).strip()
        cached = cache.get(address)

        if cached is not None:
            lat, lon = cached.get("lat"), cached.get("lon")
            source = "cache"
            cache_hits += 1
        else:
            lat, lon = geocode_nominatim(address)
            cache.set(address, {"lat": lat, "lon": lon})
            source = "nominatim" if lat is not None else "failed"
            time.sleep(NOMINATIM_RATE_LIMIT)

        if lat is not None:
            found += 1
        else:
            failed += 1

        rows.append({
            "bvd_id": row["bvd_id"],
            "lat": lat,
            "lon": lon,
            "geocode_source": source,
        })

        status = f"✓ {lat:.4f}, {lon:.4f}" if lat else "✗"
        if source != "cache":
            print(f"  [{source}] {row['company_name'][:45]:<45s}  {status}")

    results = pd.DataFrame(rows)
    results.to_parquet(GEOCODE_RESULTS, index=False, engine="pyarrow")

    print(f"\n[step_03] Geocoded: {found} found, {failed} failed, {cache_hits} cache hits")
    print(f"[step_03] Wrote {GEOCODE_RESULTS.name}")
    return results


if __name__ == "__main__":
    run()
    sys.exit(0)
