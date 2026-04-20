"""
Step 02 — SerpAPI enrichment: website, address, snippet.

For each firm (priority firms first), queries SerpAPI for
'"{company_name}" Düsseldorf' and extracts website, address, and snippet.

All results are cached — re-running never burns an extra API call.
On the free tier (100 calls/month) run with --limit 100 to stay in budget.

Usage:
    python -m pipeline.step_02_search            # all priority firms
    python -m pipeline.step_02_search --limit 5  # test run (5 calls max)
    python -m pipeline.step_02_search --all       # every firm (1,555 calls)
"""
from __future__ import annotations

import argparse
import sys
import time

import pandas as pd
from serpapi import GoogleSearch

from pipeline.cache import FileCache
from pipeline.config import (
    CACHE_SERP,
    FIRMS_CLEAN,
    DATA_PROCESSED,
    SERPAPI_KEY,
    ensure_dirs,
)

# Output file
SEARCH_RESULTS = DATA_PROCESSED / "search_results.parquet"


def _search(company_name: str, cache: FileCache) -> dict:
    """Run one SerpAPI query (or return cached result)."""
    query = f'"{company_name}" Düsseldorf'
    cached = cache.get(query)
    if cached is not None:
        return cached

    params = {
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": 3,
        "hl": "de",
        "gl": "de",
    }
    result = GoogleSearch(params).get_dict()
    cache.set(query, result)
    return result


def _extract(raw: dict) -> dict:
    """Pull website, address, and snippet from a SerpAPI response dict."""
    website = None
    address = None
    snippet = None

    # Knowledge graph (highest quality source)
    kg = raw.get("knowledge_graph", {})
    if kg:
        website = kg.get("website") or kg.get("official_website")
        address = kg.get("address")
        snippet = kg.get("description")

    # Organic results fallback
    organic = raw.get("organic_results", [])
    if organic:
        top = organic[0]
        if not website:
            website = top.get("link")
        if not snippet:
            snippet = top.get("snippet")

    # Answer box fallback
    answer_box = raw.get("answer_box", {})
    if answer_box and not address:
        address = answer_box.get("address")

    return {
        "website": website,
        "address": address,
        "snippet": snippet,
        "serp_cached": raw.get("search_metadata", {}).get("status") == "Cached",
    }


def run(limit: int | None = None, all_firms: bool = False) -> pd.DataFrame:
    ensure_dirs()

    df = pd.read_parquet(FIRMS_CLEAN)
    cache = FileCache(CACHE_SERP)

    # Ordering: priority firms first, then rest (if --all)
    priority = df[df["priority_enrich"]].copy()
    others = df[~df["priority_enrich"]].copy()
    queue = pd.concat([priority, others]) if all_firms else priority

    if limit:
        # Don't count already-cached firms against the limit
        uncached_mask = queue["company_name"].apply(
            lambda n: not cache.exists(f'"{n}" Düsseldorf')
        )
        uncached_count = uncached_mask.sum()
        print(f"[step_02] {len(cache)} already cached, "
              f"{uncached_count} new calls needed, limit={limit}")
    else:
        print(f"[step_02] {len(cache)} already cached, "
              f"processing {len(queue)} firms")

    if not SERPAPI_KEY and limit != 0:
        print("[step_02] ERROR: SERPAPI_KEY not set in .env — aborting")
        sys.exit(1)

    rows = []
    new_calls = 0

    for _, firm in queue.iterrows():
        name = firm["company_name"]
        query = f'"{name}" Düsseldorf'
        is_cached = cache.exists(query)

        if not is_cached:
            if limit is not None and new_calls >= limit:
                print(f"[step_02] Limit of {limit} new calls reached — stopping")
                break
            new_calls += 1
            time.sleep(1.2)  # stay well under SerpAPI rate limits

        raw = _search(name, cache)
        extracted = _extract(raw)
        rows.append({
            "bvd_id": firm["bvd_id"],
            "company_name": name,
            **extracted,
        })

        status = "cache" if is_cached else "api  "
        print(f"  [{status}] {name[:45]:<45s}  "
              f"{'✓ website' if extracted['website'] else '✗'}")

    results = pd.DataFrame(rows)
    results.to_parquet(SEARCH_RESULTS, index=False, engine="pyarrow")

    found = results["website"].notna().sum()
    print(f"\n[step_02] Done — {len(results)} firms processed")
    print(f"[step_02] Websites found: {found} / {len(results)}")
    print(f"[step_02] New API calls this run: {new_calls}")
    print(f"[step_02] Total cache size: {len(cache)}")
    print(f"[step_02] Wrote {SEARCH_RESULTS.name}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None,
                        help="Max new API calls this run (default: all priority firms)")
    parser.add_argument("--all", action="store_true",
                        help="Process all 1,555 firms, not just priority ones")
    args = parser.parse_args()
    run(limit=args.limit, all_firms=args.all)
    sys.exit(0)
