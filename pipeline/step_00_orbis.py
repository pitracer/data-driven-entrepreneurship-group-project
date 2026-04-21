"""
Step 00 — Parse Orbis batch exports into orbis_data.parquet.

Reads Orbis_batch1done.xlsx and Orbis_batch2done.xlsx, aggregates the
multi-row manager data per firm, and outputs one row per firm with
financial data, addresses, and management education indicators.

Usage: python -m pipeline.step_00_orbis
"""
from __future__ import annotations

import sys

import pandas as pd

from pipeline.config import (
    DATA_PROCESSED,
    FIRMS_CLEAN,
    ORBIS_BATCH_FILES,
    ORBIS_DATA,
    ensure_dirs,
)

REVENUE_COLS = {
    "Umsatz tsd EUR Letztes verf. Jahr": "orbis_revenue_latest",
    "Umsatz tsd EUR Jahr - 1": "orbis_revenue_y1",
    "Umsatz tsd EUR Jahr - 2": "orbis_revenue_y2",
    "Umsatz tsd EUR Jahr - 3": "orbis_revenue_y3",
    "Umsatz tsd EUR Jahr - 4": "orbis_revenue_y4",
    "Umsatz tsd EUR Jahr - 5": "orbis_revenue_y5",
}

PROFIT_COLS = {
    "Gewinn/Verlust vor Steuern tsd EUR Letztes verf. Jahr": "orbis_profit_latest",
    "Gewinn/Verlust vor Steuern tsd EUR Jahr - 1": "orbis_profit_y1",
    "Gewinn/Verlust vor Steuern tsd EUR Jahr - 2": "orbis_profit_y2",
    "Gewinn/Verlust vor Steuern tsd EUR Jahr - 3": "orbis_profit_y3",
    "Gewinn/Verlust vor Steuern tsd EUR Jahr - 4": "orbis_profit_y4",
    "Gewinn/Verlust vor Steuern tsd EUR Jahr - 5": "orbis_profit_y5",
}

EQUITY_COLS = {
    "Eigenkapitalquote Letztes verf. Jahr": "orbis_equity_ratio_latest",
    "Eigenkapitalquote Jahr - 1": "orbis_equity_ratio_y1",
    "Eigenkapitalquote Jahr - 2": "orbis_equity_ratio_y2",
    "Eigenkapitalquote Jahr - 3": "orbis_equity_ratio_y3",
    "Eigenkapitalquote Jahr - 4": "orbis_equity_ratio_y4",
    "Eigenkapitalquote Jahr - 5": "orbis_equity_ratio_y5",
}

ADDRESS_COLS = {
    "Web Adresse": "orbis_website",
    "Straße, Hausnr., Gebäude, etc., Zeile 1 Local Alphabet": "orbis_street",
    "Postleitzahl Latin Alphabet": "orbis_postcode",
    "Ort Latin Alphabet": "orbis_city",
}

ALL_RENAME = {**REVENUE_COLS, **PROFIT_COLS, **EQUITY_COLS, **ADDRESS_COLS}


def _has_doctoral(title: str | float) -> bool:
    if pd.isna(title):
        return False
    t = str(title).lower()
    return "dr" in t


def _has_prof(title: str | float) -> bool:
    if pd.isna(title):
        return False
    return "prof" in str(title).lower()


def _parse_one_file(path) -> pd.DataFrame:
    """Parse a single Orbis batch export into one-row-per-firm DataFrame."""
    df = pd.read_excel(path, engine="calamine", sheet_name="Ergebnisse")

    df["firm_group"] = df["Unnamed: 0"].ffill()
    df = df[df["firm_group"].notna()]

    firm_rows = df.groupby("firm_group").first().reset_index()
    firm_data = firm_rows[["Unternehmensname Latin alphabet"] + list(ALL_RENAME.keys())].copy()
    firm_data = firm_data.rename(columns={
        "Unternehmensname Latin alphabet": "orbis_company_name",
        **ALL_RENAME,
    })

    mgr_agg = (
        df.groupby("firm_group")
        .apply(_aggregate_managers, include_groups=False)
        .reset_index()
    )

    result = firm_data.merge(mgr_agg, left_index=True, right_index=True, how="left")
    result = result.drop(columns=["firm_group"], errors="ignore")

    numeric_cols = (
        list(REVENUE_COLS.values()) + list(PROFIT_COLS.values()) + list(EQUITY_COLS.values())
    )
    for col in numeric_cols:
        if col in result.columns:
            result[col] = pd.to_numeric(result[col], errors="coerce")

    if "orbis_postcode" in result.columns:
        result["orbis_postcode"] = pd.to_numeric(result["orbis_postcode"], errors="coerce").astype("Int64")

    return result


def _aggregate_managers(group: pd.DataFrame) -> pd.Series:
    """Aggregate manager-level rows into firm-level indicators."""
    n = len(group)
    titles = group["DMTitel"].dropna()
    degrees = group["DMAbschluss"].dropna()
    ages = group["DMAlter"].dropna()

    n_doctoral = sum(1 for t in titles if _has_doctoral(t))
    n_doctoral += sum(1 for d in degrees if str(d).upper() in ("PHD", "DS"))
    n_doctoral = min(n_doctoral, n)

    has_phd = n_doctoral > 0
    has_professor = any(_has_prof(t) for t in titles)
    n_with_degree = len(degrees)
    pct_educated = n_with_degree / n if n > 0 else 0.0

    if has_phd or has_professor:
        score = "high"
    elif n_with_degree > 0:
        score = "medium"
    else:
        score = "low"

    return pd.Series({
        "n_managers": n,
        "has_phd": has_phd,
        "has_professor": has_professor,
        "n_doctors": n_doctoral,
        "pct_university_educated": round(pct_educated, 3),
        "mgmt_education_score": score,
        "avg_manager_age": round(ages.mean(), 1) if len(ages) > 0 else None,
    })


def run() -> pd.DataFrame:
    ensure_dirs()

    existing = [f for f in ORBIS_BATCH_FILES if f.exists()]
    if not existing:
        print("[step_00] No Orbis batch files found — skipping")
        return pd.DataFrame()

    dfs = []
    for path in existing:
        print(f"[step_00] Parsing {path.name}...")
        dfs.append(_parse_one_file(path))

    orbis = pd.concat(dfs, ignore_index=True)

    df_clean = pd.read_parquet(FIRMS_CLEAN)[["bvd_id", "company_name"]]
    df_clean["_join_key"] = df_clean["company_name"].str.upper().str.strip()
    orbis["_join_key"] = orbis["orbis_company_name"].str.upper().str.strip()

    merged = orbis.merge(df_clean[["bvd_id", "_join_key"]], on="_join_key", how="inner")
    merged = merged.drop(columns=["_join_key"]).drop_duplicates(subset=["bvd_id"])

    merged.to_parquet(ORBIS_DATA, index=False, engine="pyarrow")

    n_rev = merged["orbis_revenue_latest"].notna().sum()
    n_addr = merged["orbis_street"].notna().sum()
    n_phd = merged["has_phd"].sum()
    print(f"\n[step_00] Wrote {ORBIS_DATA.name} — {len(merged)} firms matched")
    print(f"  Revenue data: {n_rev}")
    print(f"  Addresses:    {n_addr}")
    print(f"  Has PhD/Dr:   {n_phd}")

    return merged


if __name__ == "__main__":
    run()
    sys.exit(0)
