"""
Batch enrichment — run all enrichment steps with a single command.

Runs in order:
  1. Groq auto-enrich (website + address + snippet via LLM)
  2. Rebuild search_results.parquet from cache
  3. Geocode addresses via Nominatim (free, no key needed)
  4. Generate LLM company profiles via Groq
  5. Generate LLM sector narratives via Groq
  6. Merge everything into firms_enriched.parquet

Each step is cache-aware — re-running never burns an API call twice.
Teammates can clone the repo, add their own API keys, and pick up
where the last person left off.

Usage:
    python -m pipeline.enrich_batch                # enrich all remaining priority firms
    python -m pipeline.enrich_batch --limit 20     # limit to 20 new API calls per step
    python -m pipeline.enrich_batch --status        # show enrichment progress only
"""
from __future__ import annotations

import argparse
import sys

import pandas as pd

from pipeline.cache import FileCache
from pipeline.config import (
    CACHE_GEOCODE,
    CACHE_LLM,
    CACHE_SERP,
    DATA_PROCESSED,
    FIRMS_CLEAN,
    FIRMS_ENRICHED,
    ensure_dirs,
)


def status() -> None:
    """Print enrichment progress summary."""
    ensure_dirs()

    df = pd.read_parquet(FIRMS_CLEAN)
    priority = df[df["priority_enrich"]]
    n_total = len(priority)

    serp_cache = FileCache(CACHE_SERP)
    geo_cache = FileCache(CACHE_GEOCODE)
    llm_cache = FileCache(CACHE_LLM)

    n_serp = sum(
        1 for _, r in priority.iterrows()
        if serp_cache.exists(f'"{r["company_name"]}" Düsseldorf')
    )

    sr_path = DATA_PROCESSED / "search_results.parquet"
    n_with_address = 0
    if sr_path.exists():
        sr = pd.read_parquet(sr_path)
        n_with_address = sr["address"].notna().sum()

    n_geo = sum(1 for _ in CACHE_GEOCODE.glob("*.json"))
    n_profiles = sum(
        1 for _, r in priority.iterrows()
        if llm_cache.exists(f"profile_{r['bvd_id']}")
    )
    n_sectors = sum(
        1 for letter in df["nace_letter"].unique()
        if letter and llm_cache.exists(f"sector_{letter}")
    )

    total_sectors = df[df["priority_enrich"]].groupby("nace_letter").filter(lambda g: len(g) >= 2)["nace_letter"].nunique()

    print("=" * 55)
    print("  ENRICHMENT STATUS")
    print("=" * 55)
    print(f"  Priority firms:        {n_total}")
    print(f"  ─────────────────────────────────")
    print(f"  SerpAPI / Groq search: {n_serp:>4} / {n_total}  ({n_serp/n_total:.0%})")
    print(f"  Addresses found:       {n_with_address:>4} / {n_serp}")
    print(f"  Geocoded:              {n_geo:>4} / {n_with_address}")
    print(f"  LLM profiles:          {n_profiles:>4} / {n_total}  ({n_profiles/n_total:.0%})")
    print(f"  Sector narratives:     {n_sectors:>4} / {total_sectors}")
    print(f"  ─────────────────────────────────")

    remaining_serp = n_total - n_serp
    remaining_profiles = n_total - n_profiles
    print(f"  Remaining API calls needed:")
    print(f"    Groq (search):       ~{remaining_serp} calls")
    print(f"    Groq (profiles):     ~{remaining_profiles} calls")
    print(f"    Nominatim (geocode): free, no limit")
    print(f"  ─────────────────────────────────")

    if FIRMS_ENRICHED.exists():
        print(f"  firms_enriched.parquet: EXISTS")
    else:
        print(f"  firms_enriched.parquet: NOT YET BUILT")

    print("=" * 55)


def run(limit: int | None = None) -> None:
    """Run all enrichment steps in sequence."""
    import pipeline.enrich_groq as eg
    import pipeline.step_02_search as s02
    import pipeline.step_03_geocode as s03
    import pipeline.step_04_llm_profiles as s04
    import pipeline.step_05_llm_sectors as s05

    print("\n" + "=" * 55)
    print("  BATCH ENRICHMENT — Step 1/5: Groq auto-enrich")
    print("=" * 55)
    try:
        eg.run(limit=limit)
    except SystemExit:
        print("  [skip] Groq enrichment skipped (no GROQ_API_KEY?)")

    print("\n" + "=" * 55)
    print("  BATCH ENRICHMENT — Step 2/5: Rebuild search parquet")
    print("=" * 55)
    try:
        s02.run(limit=0)
    except SystemExit:
        print("  [skip] SerpAPI step skipped")

    print("\n" + "=" * 55)
    print("  BATCH ENRICHMENT — Step 3/5: Geocode addresses")
    print("=" * 55)
    try:
        s03.run()
    except SystemExit:
        print("  [skip] Geocoding skipped (no search results?)")

    print("\n" + "=" * 55)
    print("  BATCH ENRICHMENT — Step 4/5: LLM company profiles")
    print("=" * 55)
    try:
        s04.run(limit=limit)
    except SystemExit:
        print("  [skip] LLM profiles skipped (no GROQ_API_KEY?)")

    print("\n" + "=" * 55)
    print("  BATCH ENRICHMENT — Step 5/5: Sector narratives")
    print("=" * 55)
    try:
        s05.run()
    except SystemExit:
        print("  [skip] Sector narratives skipped (no GROQ_API_KEY?)")

    # Merge everything into firms_enriched.parquet
    print("\n" + "=" * 55)
    print("  BATCH ENRICHMENT — Merging into firms_enriched.parquet")
    print("=" * 55)
    _merge_enriched()

    print("\n")
    status()


def _merge_enriched() -> None:
    """Combine all parquet outputs into one firms_enriched.parquet."""
    df = pd.read_parquet(FIRMS_CLEAN)

    sr_path = DATA_PROCESSED / "search_results.parquet"
    geo_path = DATA_PROCESSED / "geocode_results.parquet"
    llm_path = DATA_PROCESSED / "llm_profiles.parquet"

    if sr_path.exists():
        sr = pd.read_parquet(sr_path)[["bvd_id", "website", "address", "snippet"]]
        df = df.merge(sr, on="bvd_id", how="left")

    if geo_path.exists():
        geo = pd.read_parquet(geo_path)[["bvd_id", "lat", "lon"]]
        df = df.merge(geo, on="bvd_id", how="left")

    if llm_path.exists():
        llm = pd.read_parquet(llm_path)[["bvd_id", "profile_text"]]
        df = df.merge(llm, on="bvd_id", how="left")

    df.to_parquet(FIRMS_ENRICHED, index=False)
    n = df[["website", "snippet", "profile_text"]].notna().any(axis=1).sum() if "website" in df.columns else 0
    print(f"  Wrote {FIRMS_ENRICHED.name} — {n} firms with enrichment data")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None,
                        help="Max new API calls per step (default: unlimited)")
    parser.add_argument("--status", action="store_true",
                        help="Show enrichment progress without running anything")
    args = parser.parse_args()

    if args.status:
        status()
    else:
        run(limit=args.limit)
    sys.exit(0)
