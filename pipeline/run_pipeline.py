"""
Run the full Düsseldorf pipeline end-to-end.

Steps:
  1. Clean XLSX → firms_clean.parquet
  2. Auto-enrich via Groq LLM
  3. Rebuild search_results.parquet from cache
  4. Geocode addresses via Nominatim
  5. Generate LLM company profiles
  6. Generate LLM sector narratives

Usage:
    python -m pipeline.run_pipeline              # run all steps
    python -m pipeline.run_pipeline --from-step 3  # restart from step 3
"""
from __future__ import annotations

import argparse
import sys
import time


def _run_step(name: str, fn, *args, **kwargs) -> bool:
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    t0 = time.time()
    try:
        fn(*args, **kwargs)
        elapsed = time.time() - t0
        print(f"\n  ✓ Done in {elapsed:.1f}s")
        return True
    except SystemExit:
        return False
    except Exception as e:
        elapsed = time.time() - t0
        print(f"\n  ✗ Failed after {elapsed:.1f}s: {e}")
        return False


def main(from_step: int = 1) -> None:
    import pipeline.step_01_clean as s01
    import pipeline.enrich_groq as eg
    import pipeline.step_02_search as s02
    import pipeline.step_03_geocode as s03
    import pipeline.step_04_llm_profiles as s04
    import pipeline.step_05_llm_sectors as s05

    steps = [
        (1, "Step 01 — Clean XLSX",             s01.run,        {}),
        (2, "Step 02a — Groq auto-enrichment",  eg.run,         {}),
        (3, "Step 02b — Rebuild search parquet", s02.run,       {"limit": 0}),
        (4, "Step 03 — Geocode addresses",       s03.run,        {}),
        (5, "Step 04 — LLM company profiles",    s04.run,        {}),
        (6, "Step 05 — LLM sector narratives",   s05.run,        {}),
    ]

    total_start = time.time()
    results = []

    for step_num, name, fn, kwargs in steps:
        if step_num < from_step:
            print(f"  Skipping {name}")
            continue
        ok = _run_step(name, fn, **kwargs)
        results.append((name, ok))

    print(f"\n{'='*60}")
    print(f"  Pipeline complete in {time.time() - total_start:.1f}s")
    print(f"{'='*60}")
    for name, ok in results:
        icon = "✓" if ok else "✗"
        print(f"  {icon} {name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-step", type=int, default=1, dest="from_step",
                        help="Start from this step (1-6)")
    args = parser.parse_args()
    main(from_step=args.from_step)
    sys.exit(0)
