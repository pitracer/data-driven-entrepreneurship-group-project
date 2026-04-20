"""
Step 01 — Clean raw XLSX into analysis-ready Parquet.

Reads DUESSELDORF.xlsx, deduplicates on bvd_id, renames columns,
drops constants, casts types, adds derived columns, and writes
firms_clean.parquet.

Idempotent: safe to re-run at any time.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from pipeline.config import (
    COLUMN_RENAMES,
    COLUMNS_TO_DROP,
    FIRMS_CLEAN,
    FLAG_PREFIXES,
    XLSX_SOURCE,
    ensure_dirs,
)

# Employee columns in chronological order — used for fallback growth calc
_EMP_YEARS = [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]


def _earliest_employee_year(row: pd.Series) -> int | None:
    """Return the earliest year with a non-null employee count."""
    for yr in _EMP_YEARS:
        val = row.get(f"employees_{yr}")
        if pd.notna(val) and val != 0:
            return yr
    return None


def run() -> pd.DataFrame:
    """Execute the cleaning pipeline and return the resulting DataFrame."""
    ensure_dirs()

    print(f"[step_01] Reading {XLSX_SOURCE.name} ...")
    df = pd.read_excel(XLSX_SOURCE, engine="openpyxl")
    print(f"[step_01] Raw shape: {df.shape[0]:,} rows x {df.shape[1]} columns")

    # ------------------------------------------------------------------
    # Deduplicate on BvD ID (source Excel contains exact duplicate rows)
    # ------------------------------------------------------------------
    before = len(df)
    df = df.drop_duplicates(subset=["BvD ID number"], keep="first")
    dropped = before - len(df)
    if dropped:
        print(f"[step_01] Dropped {dropped} duplicate rows (same bvd_id)")

    # ------------------------------------------------------------------
    # Drop constant / unnecessary columns
    # ------------------------------------------------------------------
    cols_to_drop = [c for c in COLUMNS_TO_DROP if c in df.columns]
    df = df.drop(columns=cols_to_drop)

    # ------------------------------------------------------------------
    # Rename to snake_case
    # ------------------------------------------------------------------
    df = df.rename(columns=COLUMN_RENAMES)

    # ------------------------------------------------------------------
    # Rename date_of_incorporation → incorporation_year (it holds bare years)
    # ------------------------------------------------------------------
    if "date_of_incorporation" in df.columns:
        df = df.rename(columns={"date_of_incorporation": "incorporation_year"})

    # ------------------------------------------------------------------
    # Cast binary flag columns to bool (~50% memory saving)
    # ------------------------------------------------------------------
    flag_cols = [
        c for c in df.columns
        if any(c.startswith(prefix) for prefix in FLAG_PREFIXES)
    ]
    for col in flag_cols:
        df[col] = df[col].fillna(0).astype(bool)

    # ------------------------------------------------------------------
    # Numeric types
    # ------------------------------------------------------------------
    emp_cols = [c for c in df.columns if c.startswith("employees_")]
    for col in emp_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    for col in [c for c in df.columns if c.startswith(("growth_", "aagr_"))]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Nullable integer year columns
    for col in ("incorporation_year", "founded_year"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    # Zero-pad NACE code to 4 characters (e.g., 130 → "0130")
    df["nace_code"] = df["nace_code"].apply(
        lambda v: str(int(v)).zfill(4) if pd.notna(v) else None
    )

    # ------------------------------------------------------------------
    # Derived columns
    # ------------------------------------------------------------------

    # category_2024: simplified 5-bucket classification in priority order.
    # Note: Scaleup, Superstar, VeryHighGrowth, ConsistentHGF flags are kept
    # as individual columns for granular filtering; this bucket is for display.
    conditions = [
        df["gazelle_2024"],
        df["scaler_2024"],
        df["high_growth_2024"],
        df["mature_2024"],
    ]
    choices = ["Gazelle", "Scaler", "HighGrowth", "Mature"]
    df["category_2024"] = np.select(conditions, choices, default="Other")

    # nace_letter: leading letter from nace_section (e.g. "G - Wholesale..." → "G")
    df["nace_letter"] = df["nace_section"].str.extract(r"^([A-Z])")

    # priority_enrich: Gazelles + Scalers enriched first (fits SerpAPI free tier)
    df["priority_enrich"] = df["gazelle_2024"] | df["scaler_2024"]

    # employee_change_abs and employee_change_pct vs. 2017 baseline
    mask_2017 = df["employees_2017"].notna() & (df["employees_2017"] != 0)
    df["employee_change_abs"] = pd.NA
    df["employee_change_pct"] = pd.NA
    df.loc[mask_2017, "employee_change_abs"] = (
        df.loc[mask_2017, "employees_2024"] - df.loc[mask_2017, "employees_2017"]
    )
    df.loc[mask_2017, "employee_change_pct"] = (
        df.loc[mask_2017, "employee_change_abs"] / df.loc[mask_2017, "employees_2017"]
    )
    df["employee_change_abs"] = df["employee_change_abs"].astype("Int64")

    # Fallback: for firms missing 2017 data, compute vs. earliest available year
    missing_baseline = ~mask_2017
    for yr in [2018, 2019, 2020, 2021, 2022, 2023]:
        col = f"employees_{yr}"
        mask_yr = missing_baseline & df[col].notna() & (df[col] != 0)
        if not mask_yr.any():
            continue
        diff = df.loc[mask_yr, "employees_2024"] - df.loc[mask_yr, col]
        df.loc[mask_yr, "employee_change_abs"] = diff.astype("Int64")
        df.loc[mask_yr, "employee_change_pct"] = diff / df.loc[mask_yr, col]
        missing_baseline = missing_baseline & ~mask_yr  # mark as resolved

    df["employee_change_abs"] = df["employee_change_abs"].astype("Int64")

    # ------------------------------------------------------------------
    # Integrity check
    # ------------------------------------------------------------------
    assert df["bvd_id"].is_unique, (
        f"bvd_id is not unique after dedup — "
        f"{df['bvd_id'].duplicated().sum()} duplicates remain"
    )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n[step_01] Category distribution (2024):")
    for cat, count in df["category_2024"].value_counts().sort_index().items():
        print(f"  {cat:<14s} {count:>5,}")
    print(f"  {'TOTAL':<14s} {len(df):>5,}")
    null_pct = df["employee_change_pct"].isna().sum()
    print(f"\n[step_01] Priority enrichment firms: {df['priority_enrich'].sum():,}")
    print(f"[step_01] NACE sections: {df['nace_letter'].nunique()}")
    print(f"[step_01] employee_change_pct null: {null_pct:,} / {len(df):,}")
    print(f"[step_01] Output columns: {len(df.columns)}")

    # ------------------------------------------------------------------
    # Write Parquet
    # ------------------------------------------------------------------
    df.to_parquet(FIRMS_CLEAN, index=False, engine="pyarrow")
    size_kb = FIRMS_CLEAN.stat().st_size / 1024
    print(f"\n[step_01] Wrote {FIRMS_CLEAN.name} ({size_kb:.0f} KB)")

    return df


if __name__ == "__main__":
    run()
    sys.exit(0)
