"""
Import an enriched Excel back into the pipeline as firms_enriched.parquet.

Reads data/processed/firms_enriched.xlsx (or a custom path), merges
enrichment columns onto the full firms_clean.parquet, and writes
firms_enriched.parquet.

Usage:
    python -m pipeline.import_enriched
    python -m pipeline.import_enriched --file path/to/my_enriched.xlsx
"""
from __future__ import annotations

import argparse
import sys

import pandas as pd

from pipeline.config import (
    DATA_PROCESSED, ENRICHMENT_COLUMNS, FIRMS_CLEAN, FIRMS_ENRICHED,
)


def run(xlsx_path: str | None = None) -> None:
    if xlsx_path is None:
        xlsx_path = str(DATA_PROCESSED / "firms_enriched.xlsx")

    print(f"Reading enriched Excel: {xlsx_path}")
    enriched = pd.read_excel(xlsx_path, engine="openpyxl")

    if "bvd_id" not in enriched.columns:
        raise ValueError("Excel must contain a 'bvd_id' column for matching.")

    base = pd.read_parquet(FIRMS_CLEAN)

    enrich_cols = [c for c in ENRICHMENT_COLUMNS if c in enriched.columns]
    if not enrich_cols:
        raise ValueError(
            f"No enrichment columns found. Expected some of: {ENRICHMENT_COLUMNS}"
        )

    merge_cols = ["bvd_id"] + enrich_cols
    enriched_subset = enriched[merge_cols].copy()

    for col in enrich_cols:
        enriched_subset[col] = enriched_subset[col].replace("", pd.NA)

    merged = base.merge(enriched_subset, on="bvd_id", how="left", suffixes=("", "_new"))

    for col in enrich_cols:
        new_col = f"{col}_new"
        if new_col in merged.columns:
            merged[col] = merged[new_col].combine_first(merged[col])
            merged.drop(columns=[new_col], inplace=True)

    for col in ["lat", "lon"]:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors="coerce")

    merged.to_parquet(FIRMS_ENRICHED, index=False)

    n_enriched = merged[enrich_cols].notna().any(axis=1).sum()
    print(f"Saved {len(merged)} firms to {FIRMS_ENRICHED}")
    print(f"  {n_enriched} firms have at least one enrichment column filled")
    if "lat" in merged.columns:
        n_geo = merged["lat"].notna().sum()
        print(f"  {n_geo} firms have geocoding (lat/lon)")
    if "profile_text" in merged.columns:
        n_profiles = merged["profile_text"].notna().sum()
        print(f"  {n_profiles} firms have AI profiles")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, default=None,
                        help="Path to enriched Excel (default: data/processed/firms_enriched.xlsx)")
    args = parser.parse_args()
    run(xlsx_path=args.file)
    sys.exit(0)
