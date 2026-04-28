"""
Step 07 — Groq extraction of structured business signals from search results.

For each firm, takes the cached search results from step_06 (3 signal queries) and
calls Groq to extract structured JSON fields used for clustering.

Output columns per firm:
  business_model_refined    : "product-led SaaS" | "service-led B2B" | "industrial manufacturer" | ...
  target_segment            : "enterprise" | "SME" | "consumer" | "mixed" | "unknown"
  value_proposition_keywords: list of up to 5 keywords
  scaling_signal_score      : 0–3 (0=no signal, 3=strong evidence)
  scaling_types             : list of ["hiring","expansion","funding","acquisition"]
  growth_evidence           : one-sentence summary of growth evidence
  digital_leverage_score    : 0–3
  has_careers               : bool
  has_content_engine        : bool
  has_product_platform      : bool

Caches individual firm results so re-runs never re-call Groq for already-extracted firms.

Usage:
    python -m pipeline.step_07_extract_signals           # all firms with signal data
    python -m pipeline.step_07_extract_signals --limit 20
    python -m pipeline.step_07_extract_signals --rerun   # ignore cache, re-extract all
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlparse
import re

import pandas as pd
from groq import Groq, RateLimitError

from pipeline.cache import FileCache
from pipeline.config import (
    CACHE_SERP,
    CACHE_SIGNAL_FOCUS,
    CACHE_SIGNAL_SCALE,
    CACHE_SIGNAL_DIGITAL,
    CACHE_SIGNALS_EXTRACTED,
    FIRMS_ENRICHED,
    FIRMS_CLEAN,
    FIRM_SIGNALS,
    GROQ_KEYS,
    GROQ_MODEL,
    ensure_dirs,
)
from pipeline.key_pool import RoundRobinPool

EXTRACTION_PROMPT = """\
You are a business analyst. Based on the web search snippets below about a company, \
extract structured information.

Company: {company_name}
Location: Düsseldorf, Germany

Search result snippets:
{snippets}

Return ONLY valid JSON with these exact keys (no markdown, no explanation):
{{
  "business_model_refined": "<one of: product-led SaaS, service-led B2B, industrial manufacturer, \
holding/financial, professional services, retail/consumer, real estate, logistics/distribution, \
healthcare/pharma, media/marketing, construction/engineering, other>",
  "target_segment": "<one of: enterprise, SME, consumer, government, mixed, unknown>",
  "value_proposition_keywords": ["<keyword1>", "<keyword2>", "<keyword3>"],
  "scaling_signal_score": <0-3>,
  "scaling_types": ["<hiring|expansion|funding|acquisition>"],
  "growth_evidence": "<one sentence or empty string>",
  "digital_leverage_score": <0-3>,
  "has_careers": <true|false>,
  "has_content_engine": <true|false>,
  "has_product_platform": <true|false>
}}

Scoring guide:
  scaling_signal_score: 0=no evidence, 1=weak hint, 2=clear mention, 3=multiple strong signals
  digital_leverage_score: 0=no digital presence, 1=basic website, 2=blog/careers, 3=platform/software
"""

FALLBACK = {
    "business_model_refined": "unknown",
    "target_segment": "unknown",
    "value_proposition_keywords": [],
    "scaling_signal_score": 0,
    "scaling_types": [],
    "growth_evidence": "",
    "digital_leverage_score": 0,
    "has_careers": False,
    "has_content_engine": False,
    "has_product_platform": False,
}


def _extract_domain(website: str | None) -> str | None:
    if not website or pd.isna(website):
        return None
    url = website.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        parsed = urlparse(url)
        host = parsed.netloc or parsed.path
        host = re.sub(r"^www\.", "", host)
        host = host.split(":")[0]
        return host if host else None
    except Exception:
        return None


def _gather_snippets(firm: pd.Series) -> str:
    """
    Collect organic snippets from all available caches for this firm.

    Priority order:
      1. Signal caches (focus, scale, digital) — targeted queries
      2. Main CACHE_SERP — general company description snippet (covers all 1,555 firms)
    """
    name = firm["company_name"]
    domain = _extract_domain(firm.get("orbis_website") or firm.get("website"))

    snippets: list[str] = []

    # 1. Signal caches (targeted queries)
    signal_configs = [
        (FileCache(CACHE_SIGNAL_FOCUS),
         f"site:{domain} products OR services OR solutions" if domain else None),
        (FileCache(CACHE_SIGNAL_SCALE),
         f'"{name}" hiring OR expansion OR growth OR funding OR acquisition'),
        (FileCache(CACHE_SIGNAL_DIGITAL),
         f"site:{domain} careers OR blog OR resources OR platform OR software" if domain else None),
    ]
    for cache, query in signal_configs:
        if query is None:
            continue
        raw = cache.get(query)
        if not raw:
            continue
        for result in raw.get("organic", [])[:2]:
            s = result.get("snippet", "").strip()
            if s:
                snippets.append(s)
        ab = raw.get("answerBox", {})
        if ab.get("snippet"):
            snippets.append(ab["snippet"].strip())

    # 2. Main snippet cache fallback — normalised SerpAPI/Serper shape
    #    Covers all 1,555 firms regardless of domain availability
    serp_cache = FileCache(CACHE_SERP)
    serp_query = f'"{name}" Düsseldorf'
    serp_raw = serp_cache.get(serp_query)
    if serp_raw:
        # knowledge_graph description
        kg = serp_raw.get("knowledge_graph", {})
        if kg.get("description"):
            snippets.append(kg["description"].strip())
        # organic_results (SerpAPI/normalised Serper shape)
        for result in serp_raw.get("organic_results", [])[:2]:
            s = result.get("snippet", "").strip()
            if s:
                snippets.append(s)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for s in snippets:
        if s not in seen:
            seen.add(s)
            unique.append(s)

    return "\n".join(f"- {s}" for s in unique) if unique else "(no search results available)"


def _parse_groq_response(text: str) -> dict:
    """Extract JSON from Groq response, stripping markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0].strip()
    return json.loads(text)


def _call_groq(client: Groq, company_name: str, snippets: str) -> dict:
    prompt = EXTRACTION_PROMPT.format(company_name=company_name, snippets=snippets)
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=300,
    )
    return _parse_groq_response(resp.choices[0].message.content)


def run(limit: int | None = None, rerun: bool = False) -> None:
    ensure_dirs()

    if not GROQ_KEYS:
        print("[step_07] ERROR: GROQ_KEYS / GROQ_API_KEY not set — aborting")
        sys.exit(1)

    data_path = FIRMS_ENRICHED if FIRMS_ENRICHED.exists() else FIRMS_CLEAN
    df = pd.read_parquet(data_path)

    extraction_cache = FileCache(CACHE_SIGNALS_EXTRACTED)
    pool = RoundRobinPool(GROQ_KEYS)
    sleep_s = max(0.7, 2.1 / len(GROQ_KEYS))

    print(f"[step_07] {len(df)} firms | Groq keys: {len(GROQ_KEYS)} | sleep: {sleep_s:.1f}s")
    print(f"[step_07] Already extracted: {len(extraction_cache)}")

    # Build work queue
    queue = []
    for _, firm in df.iterrows():
        cache_key = firm["bvd_id"]
        if not rerun and extraction_cache.exists(cache_key):
            continue
        # Only process firms that have at least some signal data
        snippets = _gather_snippets(firm)
        if snippets == "(no search results available)":
            continue
        queue.append((firm, snippets))

    if limit:
        queue = queue[:limit]

    print(f"[step_07] {len(queue)} firms to extract")

    records = []
    ok = 0
    fallback_count = 0

    for i, (firm, snippets) in enumerate(queue):
        name = firm["company_name"]
        cache_key = firm["bvd_id"]

        client = Groq(api_key=pool.next())

        result = None
        for attempt in range(2):
            try:
                result = _call_groq(client, name, snippets)
                break
            except RateLimitError:
                time.sleep(5)
                client = Groq(api_key=pool.next())
            except (json.JSONDecodeError, Exception):
                if attempt == 0:
                    time.sleep(2)
                    client = Groq(api_key=pool.next())

        if result is None:
            result = dict(FALLBACK)
            fallback_count += 1

        extraction_cache.set(cache_key, result)
        records.append({"bvd_id": firm["bvd_id"], "company_name": name, **result})
        ok += 1

        sig = result.get("scaling_signal_score", 0)
        dig = result.get("digital_leverage_score", 0)
        print(f"  [{i+1:>4}/{len(queue)}] {name[:45]:<45s}  scale={sig} digital={dig}")

        if i < len(queue) - 1:
            time.sleep(sleep_s)

    # Also include already-cached firms
    print(f"\n[step_07] Building full output including cached extractions...")
    all_records = []
    for _, firm in df.iterrows():
        cached = extraction_cache.get(firm["bvd_id"])
        if cached:
            all_records.append({"bvd_id": firm["bvd_id"], "company_name": firm["company_name"], **cached})

    out_df = pd.DataFrame(all_records)

    # Normalise list columns to strings for parquet compatibility
    for col in ["value_proposition_keywords", "scaling_types"]:
        if col in out_df.columns:
            out_df[col] = out_df[col].apply(
                lambda v: ",".join(v) if isinstance(v, list) else (v or "")
            )

    out_df.to_parquet(FIRM_SIGNALS, index=False, engine="pyarrow")

    print(f"[step_07] Done — {ok} extracted this run, {fallback_count} fallbacks")
    print(f"[step_07] Total in output: {len(out_df)} firms")
    print(f"[step_07] Wrote {FIRM_SIGNALS}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--rerun", action="store_true",
                        help="Ignore cache and re-extract all firms")
    args = parser.parse_args()
    run(limit=args.limit, rerun=args.rerun)
    sys.exit(0)
