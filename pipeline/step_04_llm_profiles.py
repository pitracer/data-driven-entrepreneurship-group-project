"""
Step 04 — Generate LLM company profiles via Groq.

Reads firms_clean.parquet + search_results.parquet, generates a
2-3 sentence profile per priority firm, writes llm_profiles.parquet.

Usage: python -m pipeline.step_04_llm_profiles
"""
from __future__ import annotations

import sys
import time

import pandas as pd
from groq import Groq

from pipeline.cache import FileCache
from pipeline.config import (
    CACHE_LLM,
    DATA_PROCESSED,
    FIRMS_CLEAN,
    GROQ_API_KEY,
    GROQ_MODEL,
    ensure_dirs,
)

SEARCH_RESULTS = DATA_PROCESSED / "search_results.parquet"
LLM_PROFILES = DATA_PROCESSED / "llm_profiles.parquet"


def _build_prompt(row: pd.Series) -> str:
    emp = row.get("employees_2024", "unknown")
    pct = row.get("employee_change_pct")
    pct_str = f"{pct:.1%}" if pd.notna(pct) else "unknown"
    snippet = row.get("snippet") or "not available"
    return (
        f"Company: {row['company_name']}\n"
        f"Sector: {row['nace_section']}\n"
        f"Employees 2024: {emp:,}\n"
        f"Growth since baseline: {pct_str}\n"
        f"Category: {row['category_2024']}\n"
        f"Web description: {snippet}\n\n"
        "Write a 2-3 sentence profile for a business intelligence dashboard. "
        "Be factual and specific about what this company does and why it is growing. "
        "Do not start with the company name. Do not use generic phrases."
    )


def run() -> pd.DataFrame:
    ensure_dirs()

    if not GROQ_API_KEY:
        print("[step_04] ERROR: GROQ_API_KEY not set — aborting")
        sys.exit(1)

    df = pd.read_parquet(FIRMS_CLEAN)
    priority = df[df["priority_enrich"]].copy()

    if SEARCH_RESULTS.exists():
        df_search = pd.read_parquet(SEARCH_RESULTS)[["bvd_id", "snippet", "website", "address"]]
        priority = priority.merge(df_search, on="bvd_id", how="left")
    else:
        print("[step_04] search_results.parquet not found — profiles will lack snippets")
        priority["snippet"] = None

    cache = FileCache(CACHE_LLM)
    client = Groq(api_key=GROQ_API_KEY)
    rows = []
    generated = 0
    cache_hits = 0

    print(f"[step_04] Generating profiles for {len(priority)} priority firms...")

    for i, (_, firm) in enumerate(priority.iterrows()):
        bvd_id = firm["bvd_id"]
        cache_key = f"profile_{bvd_id}"
        cached = cache.get(cache_key)

        if cached is not None:
            profile_text = cached["profile_text"]
            cache_hits += 1
        else:
            prompt = _build_prompt(firm)
            try:
                resp = client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=200,
                )
                profile_text = resp.choices[0].message.content.strip()
            except Exception as e:
                profile_text = f"A {firm['category_2024']} firm in Düsseldorf's {firm.get('nace_letter', '?')} sector."
                print(f"  [warn] {firm['company_name'][:40]}: {e}")

            cache.set(cache_key, {"profile_text": profile_text})
            generated += 1
            time.sleep(2.1)

        rows.append({"bvd_id": bvd_id, "profile_text": profile_text})

        if cache_hits == 0 or (i + 1) % 10 == 0:
            print(f"  [{i+1:>3}/{len(priority)}] {firm['company_name'][:50]}")

    result = pd.DataFrame(rows)
    result.to_parquet(LLM_PROFILES, index=False, engine="pyarrow")

    print(f"\n[step_04] Generated {generated} new profiles, {cache_hits} from cache")
    print(f"[step_04] Wrote {LLM_PROFILES.name}")
    return result


if __name__ == "__main__":
    run()
    sys.exit(0)
