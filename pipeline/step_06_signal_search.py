"""
Step 06 — Signal-targeted search queries for clustering.

Runs three focused web searches per firm to extract signals for business archetype
and growth strategy clustering. Results are cached per query type so re-runs are free.

Query types:
  focus_positioning   site:{domain} products OR services OR solutions
  scaling_signal      "{company_name}" hiring OR expansion OR growth OR funding OR acquisition
  digital_leverage    site:{domain} careers OR blog OR resources OR platform OR software

Usage:
    python -m pipeline.step_06_signal_search                         # all 3 queries, all firms
    python -m pipeline.step_06_signal_search --query scaling_signal  # one query only
    python -m pipeline.step_06_signal_search --limit 10              # test run
    python -m pipeline.step_06_signal_search --all-firms             # skip priority filter
"""
from __future__ import annotations

import argparse
import re
import sys
from urllib.parse import urlparse

import pandas as pd
import requests

from pipeline.cache import FileCache
from pipeline.config import (
    CACHE_SIGNAL_FOCUS,
    CACHE_SIGNAL_SCALE,
    CACHE_SIGNAL_DIGITAL,
    FIRMS_ENRICHED,
    FIRMS_CLEAN,
    SERPER_KEYS,
    ensure_dirs,
)
from pipeline.key_pool import ExhaustPool

QUERY_CONFIGS = {
    "focus_positioning": {
        "cache_dir": CACHE_SIGNAL_FOCUS,
        "needs_domain": True,
        "template": "site:{domain} products OR services OR solutions",
    },
    "scaling_signal": {
        "cache_dir": CACHE_SIGNAL_SCALE,
        "needs_domain": False,
        "template": '"{company_name}" hiring OR expansion OR growth OR funding OR acquisition',
    },
    "digital_leverage": {
        "cache_dir": CACHE_SIGNAL_DIGITAL,
        "needs_domain": True,
        "template": "site:{domain} careers OR blog OR resources OR platform OR software",
    },
}

ALL_QUERIES = list(QUERY_CONFIGS.keys())


def _extract_domain(website: str | None) -> str | None:
    """Return bare domain from a URL (e.g. 'www.example.com' → 'example.com')."""
    if not website or pd.isna(website):
        return None
    url = website.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        parsed = urlparse(url)
        host = parsed.netloc or parsed.path
        # Strip www.
        host = re.sub(r"^www\.", "", host)
        # Remove port
        host = host.split(":")[0]
        return host if host else None
    except Exception:
        return None


def _search_serper(query: str, api_key: str) -> dict:
    """Call Serper and return the raw JSON response."""
    resp = requests.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        json={"q": query, "gl": "de", "hl": "de", "num": 3},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _run_query(
    query_name: str,
    df: pd.DataFrame,
    pool: ExhaustPool,
    limit: int | None = None,
) -> int:
    cfg = QUERY_CONFIGS[query_name]
    cache = FileCache(cfg["cache_dir"])
    needs_domain = cfg["needs_domain"]
    template = cfg["template"]

    # Build work queue
    rows = []
    for _, firm in df.iterrows():
        domain = _extract_domain(
            firm.get("orbis_website") or firm.get("website")
        )
        if needs_domain and not domain:
            continue
        query = template.format(
            domain=domain or "",
            company_name=firm["company_name"],
        )
        if not cache.exists(query):
            rows.append({"firm": firm, "query": query})

    if limit:
        rows = rows[:limit]

    print(f"  [{query_name}] {len(cache)} cached, {len(rows)} to fetch")

    new_calls = 0
    for item in rows:
        query = item["query"]
        firm = item["firm"]

        if pool.is_exhausted():
            print(f"  [{query_name}] All Serper keys exhausted — stopping")
            break

        while not pool.is_exhausted():
            key = pool.current()
            try:
                raw = _search_serper(query, key)
                cache.set(query, raw)
                new_calls += 1
                break
            except requests.HTTPError as exc:
                status_code = exc.response.status_code if exc.response is not None else 0
                if status_code in (403, 429):
                    print(f"  [{query_name}] key exhausted / rate-limit — rotating...")
                    if not pool.rotate():
                        print(f"  [{query_name}] No more keys — stopping")
                        return new_calls
                elif status_code == 400:
                    # Bad query (e.g. malformed domain) — skip this firm, don't rotate
                    print(f"  [{query_name}] 400 Bad Request — skipping query: {query[:60]}")
                    break
                else:
                    # Unexpected error — log and skip, don't crash the whole run
                    print(f"  [{query_name}] HTTP {status_code} — skipping: {exc}")
                    break
            except Exception as exc:
                print(f"  [{query_name}] Error — skipping: {exc}")
                break

        name_short = firm["company_name"][:45]
        print(f"    [api] {name_short:<45s} ✓")

    print(f"  [{query_name}] {new_calls} new calls, {len(cache)} total cached")
    return new_calls


def run(
    queries: list[str] | None = None,
    limit: int | None = None,
    all_firms: bool = False,
) -> None:
    ensure_dirs()

    if not SERPER_KEYS:
        print("[step_06] ERROR: SERPER_KEYS not set in .env — aborting")
        sys.exit(1)

    if queries is None:
        queries = ALL_QUERIES

    # Load data
    data_path = FIRMS_ENRICHED if FIRMS_ENRICHED.exists() else FIRMS_CLEAN
    df = pd.read_parquet(data_path)

    if not all_firms:
        priority = df[df["priority_enrich"]].copy()
        others = df[~df["priority_enrich"]].copy()
        df = pd.concat([priority, others])

    pool = ExhaustPool(SERPER_KEYS)
    print(f"[step_06] {len(df)} firms | queries: {queries} | keys: {len(pool)}")

    total_calls = 0
    for q in queries:
        if q not in QUERY_CONFIGS:
            print(f"[step_06] Unknown query '{q}' — skipping")
            continue
        print(f"\n[step_06] Running query: {q}")
        total_calls += _run_query(q, df, pool, limit=limit)
        if pool.is_exhausted():
            print("[step_06] All Serper keys exhausted — stopping early")
            break

    print(f"\n[step_06] Done — {total_calls} total new API calls")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--query",
        choices=ALL_QUERIES + ["all"],
        default="all",
        help="Which signal query to run (default: all)",
    )
    parser.add_argument("--limit", type=int, default=None,
                        help="Max new API calls per query (for testing)")
    parser.add_argument("--all-firms", action="store_true",
                        help="Process all firms (default: priority first)")
    args = parser.parse_args()

    selected = ALL_QUERIES if args.query == "all" else [args.query]
    run(queries=selected, limit=args.limit, all_firms=args.all_firms)
    sys.exit(0)
