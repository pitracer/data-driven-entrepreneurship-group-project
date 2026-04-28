"""
Auto-enrich priority firms via Groq LLM.

Groq's Llama 3.3 knows many German companies from training data.
Results are written to the serp cache in the same synthetic format
that step_02's _extract() reads — downstream pipeline unchanged.

With multiple GROQ_KEYS the pool rotates round-robin, giving up to 3x throughput
(90 RPM effective vs 30 RPM on a single key).

Usage:
    python -m pipeline.enrich_groq            # all remaining priority firms
    python -m pipeline.enrich_groq --limit 20 # test with 20
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import pandas as pd
from groq import Groq, RateLimitError

from pipeline.cache import FileCache
from pipeline.config import CACHE_SERP, FIRMS_CLEAN, GROQ_KEYS, GROQ_MODEL, ensure_dirs
from pipeline.key_pool import RoundRobinPool


def _synthetic_entry(website: str | None, address: str | None, snippet: str | None) -> dict:
    """Build a minimal fake SerpAPI response that step_02's _extract() can read."""
    kg: dict = {}
    if website:
        kg["website"] = website
    if address:
        kg["address"] = address
    if snippet:
        kg["description"] = snippet
    return {
        "search_metadata": {"status": "Manual"},
        "knowledge_graph": kg,
        "organic_results": [{"link": website, "snippet": snippet or ""}] if website else [],
        "answer_box": {},
    }


def _call_groq(client: Groq, company_name: str) -> dict:
    prompt = (
        f'You are a German business directory. For "{company_name}" based in Düsseldorf, Germany:\n'
        '- website: official website URL (null if not confident)\n'
        '- address: street address in Düsseldorf (null if unknown)\n'
        '- snippet: one sentence describing what this company does\n\n'
        'Return ONLY a JSON object with keys "website", "address", "snippet". No markdown.'
    )
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=150,
    )
    text = resp.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0].strip()
    return json.loads(text)


def run(limit: int | None = None) -> None:
    ensure_dirs()

    if not GROQ_KEYS:
        print("[enrich_groq] ERROR: GROQ_KEYS / GROQ_API_KEY not set — aborting")
        sys.exit(1)

    df = pd.read_parquet(FIRMS_CLEAN)
    priority = df[df["priority_enrich"]].copy()
    cache = FileCache(CACHE_SERP)

    to_enrich = [
        row for _, row in priority.iterrows()
        if not cache.exists(f'"{row["company_name"]}" Düsseldorf')
    ]

    print(f"[enrich_groq] {len(cache)} already cached, {len(to_enrich)} to enrich")
    print(f"[enrich_groq] Groq key pool: {len(GROQ_KEYS)} key(s)")
    if limit:
        to_enrich = to_enrich[:limit]
        print(f"[enrich_groq] Limiting to {limit} firms")

    pool = RoundRobinPool(GROQ_KEYS)
    # With N keys, each key handles 1/N of calls so we can shrink the sleep
    sleep_s = max(0.7, 2.1 / len(GROQ_KEYS))
    print(f"[enrich_groq] Sleep between calls: {sleep_s:.1f}s")

    enriched = 0
    websites_found = 0

    for i, row in enumerate(to_enrich):
        name = row["company_name"]
        query = f'"{name}" Düsseldorf'

        client = Groq(api_key=pool.next())

        website, address, snippet = None, None, None
        try:
            data = _call_groq(client, name)
            website = data.get("website")
            address = data.get("address")
            snippet = data.get("snippet")
        except (json.JSONDecodeError, Exception) as exc:
            if isinstance(exc, RateLimitError):
                time.sleep(5)
            try:
                client = Groq(api_key=pool.next())
                data = _call_groq(client, name)
                website = data.get("website")
                address = data.get("address")
                snippet = data.get("snippet")
            except Exception:
                snippet = "Company based in Düsseldorf, Germany."

        entry = _synthetic_entry(website, address, snippet)
        cache.set(query, entry)
        enriched += 1
        if website:
            websites_found += 1

        status = "✓ website" if website else "✗"
        print(f"  [{i+1:>3}/{len(to_enrich)}] {name[:50]:<50s}  {status}")

        if i < len(to_enrich) - 1:
            time.sleep(sleep_s)

    print(f"\n[enrich_groq] Done — {enriched} enriched, {websites_found} websites found")
    print(f"[enrich_groq] Total cache size: {len(cache)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    run(limit=args.limit)
    sys.exit(0)
