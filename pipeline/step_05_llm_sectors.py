"""
Step 05 — Generate sector narratives via Groq.

Groups priority firms by NACE section, generates a 3-4 sentence
analytical narrative per sector, writes sector_narratives.json.

Usage: python -m pipeline.step_05_llm_sectors
"""
from __future__ import annotations

import json
import sys
import time

import pandas as pd
from groq import Groq

from pipeline.cache import FileCache
from pipeline.config import (
    CACHE_LLM,
    FIRMS_CLEAN,
    GROQ_API_KEY,
    GROQ_MODEL,
    SECTOR_NARRATIVES,
    ensure_dirs,
)

MIN_PRIORITY_FIRMS = 2  # minimum priority firms to generate a narrative


def _build_prompt(nace_section: str, stats: dict) -> str:
    top_names = ", ".join(stats["top_firms"])
    return (
        f"Sector: {nace_section}\n"
        f"Total Düsseldorf firms in sector: {stats['n_total']}\n"
        f"Gazelles (fastest growing, 20%+/year): {stats['n_gazelles']}\n"
        f"Scalers (sustained high growth): {stats['n_scalers']}\n"
        f"Top firms by employees 2024: {top_names}\n"
        f"Average 2024 growth rate: {stats['avg_growth']:.1%}\n\n"
        "Write a 3-4 sentence narrative for a business intelligence dashboard "
        "explaining the growth dynamics of this sector in Düsseldorf. "
        "Be analytical and specific — mention what is driving growth, "
        "what types of firms are growing, and what this means for the city. "
        "Do not use generic phrases like 'exciting growth' or 'dynamic sector'."
    )


def run() -> dict:
    ensure_dirs()

    if not GROQ_API_KEY:
        print("[step_05] ERROR: GROQ_API_KEY not set — aborting")
        sys.exit(1)

    df = pd.read_parquet(FIRMS_CLEAN)
    priority = df[df["priority_enrich"]]

    cache = FileCache(CACHE_LLM)
    client = Groq(api_key=GROQ_API_KEY)
    narratives: dict[str, str] = {}

    # Load existing narratives if any
    if SECTOR_NARRATIVES.exists():
        narratives = json.loads(SECTOR_NARRATIVES.read_text(encoding="utf-8"))

    sectors = df.groupby("nace_letter")
    print(f"[step_05] Processing {len(sectors)} NACE sectors...")

    for nace_letter, group in sectors:
        if nace_letter is None or str(nace_letter) == "nan":
            continue

        priority_in_sector = group[group["priority_enrich"]]
        if len(priority_in_sector) < MIN_PRIORITY_FIRMS:
            continue

        nace_section = group["nace_section"].iloc[0]
        cache_key = f"sector_{nace_letter}"

        if cache.get(cache_key):
            narratives[nace_letter] = cache.get(cache_key)["narrative"]
            print(f"  [cache] {nace_letter} — {nace_section[:50]}")
            continue

        stats = {
            "n_total": len(group),
            "n_gazelles": int(priority_in_sector["gazelle_2024"].sum()),
            "n_scalers": int(priority_in_sector["scaler_2024"].sum()),
            "avg_growth": float(group["growth_2024"].mean()) if group["growth_2024"].notna().any() else 0.0,
            "top_firms": (
                group.nlargest(5, "employees_2024")["company_name"]
                .str.slice(0, 30).tolist()
            ),
        }

        try:
            prompt = _build_prompt(nace_section, stats)
            resp = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=300,
            )
            narrative = resp.choices[0].message.content.strip()
        except Exception as e:
            narrative = (
                f"This sector has {stats['n_gazelles']} Gazelles and "
                f"{stats['n_scalers']} Scalers in Düsseldorf."
            )
            print(f"  [warn] {nace_letter}: {e}")

        cache.set(cache_key, {"narrative": narrative})
        narratives[nace_letter] = narrative
        print(f"  [api ] {nace_letter} — {nace_section[:50]}")
        print(f"         {narrative[:100]}...")
        time.sleep(2.1)

    SECTOR_NARRATIVES.write_text(
        json.dumps(narratives, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n[step_05] Wrote {len(narratives)} sector narratives → {SECTOR_NARRATIVES.name}")
    return narratives


if __name__ == "__main__":
    run()
    sys.exit(0)
