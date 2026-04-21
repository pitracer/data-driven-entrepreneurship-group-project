"""
Export firms data to Excel for manual enrichment via Claude Chat.

Produces data/processed/firms_for_enrichment.xlsx with key columns
plus empty enrichment columns to fill in.

Usage:
    python -m pipeline.export_for_enrichment
    python -m pipeline.export_for_enrichment --priority-only
"""
from __future__ import annotations

import argparse
import sys

import pandas as pd

from pipeline.config import FIRMS_CLEAN, DATA_PROCESSED, ENRICHMENT_COLUMNS


def run(priority_only: bool = False) -> None:
    df = pd.read_parquet(FIRMS_CLEAN)

    if priority_only:
        df = df[df["priority_enrich"]].copy()

    keep_cols = [
        "bvd_id", "company_name", "category_2024", "nace_section",
        "nace_letter", "employees_2024", "founded_year",
        "growth_2024", "employee_change_pct",
    ]

    out = df[keep_cols].copy()
    for col in ENRICHMENT_COLUMNS:
        if col not in out.columns:
            out[col] = ""

    suffix = "_priority" if priority_only else ""
    dest = DATA_PROCESSED / f"firms_for_enrichment{suffix}.xlsx"
    out.to_excel(dest, index=False, engine="openpyxl")
    print(f"Exported {len(out)} firms to {dest}")
    if not priority_only:
        print(f"  ({int(df['priority_enrich'].sum())} are priority firms)")
    print(f"  Fill in columns: {ENRICHMENT_COLUMNS}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--priority-only", action="store_true",
                        help="Export only Gazelles + Scalers")
    args = parser.parse_args()
    run(priority_only=args.priority_only)
    sys.exit(0)
