"""
Step 02 — web search enrichment: website, address, snippet.

Supports two providers:
  - serpapi  : original SerpAPI (100 calls/month free tier)
  - serper   : Serper.dev (2,500 calls/account free tier, multi-key pooling)

All results are cached (MD5 of query string) — re-running never burns extra API calls.

Usage:
    python -m pipeline.step_02_search                          # serper, priority firms
    python -m pipeline.step_02_search --all-firms              # serper, all 1,555 firms
    python -m pipeline.step_02_search --limit 5                # test run
    python -m pipeline.step_02_search --provider serpapi       # use SerpAPI instead
    python -m pipeline.step_02_search --no-snippet-filter      # re-search even cached firms
"""
from __future__ import annotations

import argparse
import sys
import time

import pandas as pd
import requests

from pipeline.cache import FileCache
from pipeline.config import (
    CACHE_SERP,
    FIRMS_CLEAN,
    FIRMS_ENRICHED,
    DATA_PROCESSED,
    SERPAPI_KEY,
    SERPER_KEYS,
    ensure_dirs,
)
from pipeline.key_pool import ExhaustPool

# Output file
SEARCH_RESULTS = DATA_PROCESSED / "search_results.parquet"


# ---------------------------------------------------------------------------
# Serper provider
# ---------------------------------------------------------------------------

def _search_serper(query: str, api_key: str) -> dict:
    """
    Call Serper API and normalise the response to SerpAPI shape.

    The normalised shape is what _extract() already understands, so no changes
    are needed downstream.
    """
    resp = requests.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        json={"q": query, "gl": "de", "hl": "de", "num": 3},
        timeout=15,
    )
    resp.raise_for_status()
    raw = resp.json()

    organic = [
        {"link": r.get("link"), "snippet": r.get("snippet")}
        for r in raw.get("organic", [])
    ]
    kg = raw.get("knowledgeGraph", {})
    knowledge_graph: dict = {}
    if kg:
        knowledge_graph = {
            "website":     kg.get("website"),
            "address":     kg.get("address"),
            "description": kg.get("description"),
        }

    return {
        "organic_results":  organic,
        "knowledge_graph":  knowledge_graph,
        "search_metadata":  {"status": "Success", "provider": "serper"},
    }


# ---------------------------------------------------------------------------
# SerpAPI provider (original)
# ---------------------------------------------------------------------------

def _search_serpapi(query: str, api_key: str) -> dict:
    from serpapi import GoogleSearch
    params = {
        "q": query,
        "api_key": api_key,
        "num": 3,
        "hl": "de",
        "gl": "de",
    }
    return GoogleSearch(params).get_dict()


# ---------------------------------------------------------------------------
# Extraction (provider-agnostic — works on normalised/original SerpAPI shape)
# ---------------------------------------------------------------------------

def _extract(raw: dict) -> dict:
    """Pull website, address, and snippet from a (normalised) SerpAPI response dict."""
    website = None
    address = None
    snippet = None

    kg = raw.get("knowledge_graph", {})
    if kg:
        website = kg.get("website") or kg.get("official_website")
        address = kg.get("address")
        snippet = kg.get("description")

    organic = raw.get("organic_results", [])
    if organic:
        top = organic[0]
        if not website:
            website = top.get("link")
        if not snippet:
            snippet = top.get("snippet")

    answer_box = raw.get("answer_box", {})
    if answer_box and not address:
        address = answer_box.get("address")

    return {
        "website": website,
        "address": address,
        "snippet": snippet,
        "serp_cached": raw.get("search_metadata", {}).get("status") == "Cached",
    }


# ---------------------------------------------------------------------------
# Main run
# ---------------------------------------------------------------------------

def run(
    limit: int | None = None,
    offset: int = 0,
    all_firms: bool = False,
    provider: str = "serper",
    snippet_only: bool = True,
) -> pd.DataFrame:
    ensure_dirs()

    df = pd.read_parquet(FIRMS_CLEAN)
    cache = FileCache(CACHE_SERP)

    # Ordering: priority firms first, then rest (if --all-firms)
    priority = df[df["priority_enrich"]].copy()
    others = df[~df["priority_enrich"]].copy()
    queue = pd.concat([priority, others]) if all_firms else priority

    # Apply offset/limit on the FULL ordered list (before cache filtering)
    # so that teammates can each take an explicit, non-overlapping slice.
    if offset or limit:
        end = (offset + limit) if limit else None
        queue = queue.iloc[offset:end]
        print(f"[step_02] Slice: firms [{offset}:{end}] ({len(queue)} firms)")

    # If snippet_only: skip firms that are already cached within this slice
    if snippet_only:
        queue = queue[
            queue["company_name"].apply(
                lambda n: not cache.exists(f'"{n}" Düsseldorf')
            )
        ]

    print(f"[step_02] Provider: {provider}")
    print(f"[step_02] {len(cache)} already cached")
    print(f"[step_02] {len(queue)} firms to process this run")

    # Set up key pool
    if provider == "serper":
        if not SERPER_KEYS:
            print("[step_02] ERROR: SERPER_KEYS not set in .env — aborting")
            sys.exit(1)
        pool = ExhaustPool(SERPER_KEYS)
        print(f"[step_02] Serper key pool: {len(pool)} keys available")
    else:
        if not SERPAPI_KEY:
            print("[step_02] ERROR: SERPAPI_KEY not set in .env — aborting")
            sys.exit(1)
        pool = None  # SerpAPI uses a single key

    rows = []
    new_calls = 0

    for _, firm in queue.iterrows():
        name = firm["company_name"]
        query = f'"{name}" Düsseldorf'

        # Always check cache first regardless of provider
        cached = cache.get(query)
        if cached is not None:
            extracted = _extract(cached)
            rows.append({"bvd_id": firm["bvd_id"], "company_name": name, **extracted})
            continue

        # Live API call
        raw = None
        if provider == "serper":
            while not pool.is_exhausted():
                key = pool.current()
                try:
                    raw = _search_serper(query, key)
                    break
                except requests.HTTPError as exc:
                    if exc.response.status_code in (403, 429):
                        print(f"  [key exhausted / rate-limit] rotating key...")
                        if not pool.rotate():
                            print("[step_02] All Serper keys exhausted — stopping")
                            break
                    else:
                        raise
            if raw is None:
                print("[step_02] No Serper keys available — stopping")
                break
        else:
            raw = _search_serpapi(query, SERPAPI_KEY)
            time.sleep(1.2)

        cache.set(query, raw)
        extracted = _extract(raw)
        rows.append({"bvd_id": firm["bvd_id"], "company_name": name, **extracted})
        new_calls += 1

        status = "✓ website" if extracted["website"] else "✗"
        print(f"  [api ] {name[:50]:<50s}  {status}")

    print(f"\n[step_02] Done — {len(rows)} firms processed")
    print(f"[step_02] New API calls this run: {new_calls}")
    print(f"[step_02] Total cache size: {len(cache)}")

    if not rows:
        # Return empty with correct columns
        results = pd.DataFrame(columns=["bvd_id", "company_name", "website", "address", "snippet", "serp_cached"])
    else:
        results = pd.DataFrame(rows)
        found = results["website"].notna().sum()
        print(f"[step_02] Websites found: {found} / {len(results)}")

    results.to_parquet(SEARCH_RESULTS, index=False, engine="pyarrow")
    print(f"[step_02] Wrote {SEARCH_RESULTS.name}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None,
                        help="Max firms to process this run")
    parser.add_argument("--offset", type=int, default=0,
                        help="Start from this index in the firm list (for teammate batches)")
    parser.add_argument("--all-firms", action="store_true",
                        help="Process all 1,555 firms (default: priority firms only)")
    parser.add_argument("--provider", choices=["serpapi", "serper"], default="serper",
                        help="Search provider (default: serper)")
    parser.add_argument("--no-snippet-filter", action="store_true",
                        help="Also re-search firms that already have cached results")
    args = parser.parse_args()
    run(
        limit=args.limit,
        offset=args.offset,
        all_firms=args.all_firms,
        provider=args.provider,
        snippet_only=not args.no_snippet_filter,
    )
    sys.exit(0)
