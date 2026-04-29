"""
Export pipeline data to static JSON files for the Next.js web dashboard.

Generates:
  web/public/data/firms.json           — all 1,555 firms (trimmed columns)
  web/public/data/sector_narratives.json — LLM sector intelligence
  web/public/data/embeddings.json      — per-firm text embeddings for chat
  web/public/data/stats.json           — pre-computed regression results

Usage:
    python -m pipeline.export_web
"""
from __future__ import annotations

import json
import math
import os
import shutil
import warnings
import numpy as np
import pandas as pd
from pathlib import Path

warnings.filterwarnings("ignore")

from pipeline.config import FIRMS_ENRICHED, FIRMS_CLEAN, SECTOR_NARRATIVES, ROOT, DATA_FINAL, ensure_dirs

WEB_DATA = ROOT / "web" / "public" / "data"
ENRICHED_XLSX = DATA_FINAL / "enriched.xlsx"


def _ensure_web_data_dir() -> None:
    WEB_DATA.mkdir(parents=True, exist_ok=True)


def _json_safe(value):
    """Convert pandas/numpy scalars and missing values into strict JSON values."""
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if value is None:
        return None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


# ---------------------------------------------------------------------------
# Column selection — keep only what the frontend actually uses
# ---------------------------------------------------------------------------
KEEP_COLS = [
    # Identity
    "bvd_id", "company_name", "nace_code", "nace_section", "nace_letter",
    "founded_year", "incorporation_year",
    # Classification
    "category_2024", "priority_enrich",
    "gazelle_2024", "scaler_2024", "high_growth_2024",
    # Employees (all years for trend chart)
    "employees_2017", "employees_2018", "employees_2019", "employees_2020",
    "employees_2021", "employees_2022", "employees_2023", "employees_2024",
    "employee_change_abs", "employee_change_pct",
    # Growth rates
    "growth_2018", "growth_2019", "growth_2020", "growth_2021",
    "growth_2022", "growth_2023", "growth_2024",
    "aagr_2023", "aagr_2024",
    # Enrichment
    "website", "orbis_website", "address", "snippet", "profile_text",
    "lat", "lon",
    # Orbis financial
    "orbis_revenue_latest", "orbis_profit_latest", "orbis_equity_ratio_latest",
    "orbis_street", "orbis_postcode", "orbis_city",
    # Management
    "n_managers", "has_phd", "has_professor", "n_doctors",
    "mgmt_education_score", "avg_manager_age", "pct_university_educated",
    # Signal clusters
    "archetype_cluster", "growth_cluster",
    "business_model_refined", "target_segment", "value_proposition_keywords",
    "scaling_signal_score", "scaling_types", "growth_evidence",
    "digital_leverage_score", "has_careers", "has_content_engine", "has_product_platform",
]


def _backfill_from_parquets(df: pd.DataFrame) -> None:
    """Fill blank text/signal columns from raw pipeline parquets (in-place).

    enriched.xlsx is the source of truth for manual corrections, but cells that
    were cleared end up as NaN in the export. This function restores the original
    pipeline output for those blanks without overwriting anything the user kept.
    """
    DATA_PROCESSED = ROOT / "data" / "processed"

    # Backfill signal fields from firm_signals.parquet
    SIGNAL_COLS = [
        "growth_evidence", "business_model_refined", "target_segment",
        "value_proposition_keywords", "scaling_signal_score", "scaling_types",
        "digital_leverage_score", "has_careers", "has_content_engine", "has_product_platform",
    ]
    signal_path = DATA_PROCESSED / "firm_signals.parquet"
    if signal_path.exists():
        avail = ["bvd_id"] + [c for c in SIGNAL_COLS if c not in ("has_careers", "has_content_engine", "has_product_platform")]
        try:
            signals = pd.read_parquet(signal_path)[[c for c in avail if c in pd.read_parquet(signal_path).columns]]
            df_merged = df.merge(signals, on="bvd_id", how="left", suffixes=("", "_sig"))
            for col in SIGNAL_COLS:
                sig_col = f"{col}_sig"
                if sig_col in df_merged.columns and col in df_merged.columns:
                    df[col] = df_merged[col].fillna(df_merged[sig_col]).values
            print(f"[export_web] Backfilled signal fields from firm_signals.parquet")
        except Exception as e:
            print(f"[export_web] Could not backfill from firm_signals.parquet: {e}")

    # Backfill snippet from search_results.parquet
    search_path = DATA_PROCESSED / "search_results.parquet"
    if search_path.exists() and "snippet" in df.columns:
        try:
            searches = pd.read_parquet(search_path)
            if "snippet" in searches.columns:
                snip = searches[["bvd_id", "snippet"]].drop_duplicates("bvd_id")
                df_merged = df[["bvd_id", "snippet"]].merge(snip, on="bvd_id", how="left", suffixes=("", "_src"))
                df["snippet"] = df_merged["snippet"].fillna(df_merged["snippet_src"]).values
                print(f"[export_web] Backfilled snippets from search_results.parquet")
        except Exception as e:
            print(f"[export_web] Could not backfill from search_results.parquet: {e}")


def export_firms() -> pd.DataFrame:
    # Prefer enriched.xlsx (manual adjustments + complete cluster data) over parquet
    if ENRICHED_XLSX.exists():
        print(f"[export_web] Loading {ENRICHED_XLSX.name} (source of truth)...")
        df = pd.read_excel(ENRICHED_XLSX, engine="openpyxl")
        # Drop internal index column if present
        df = df.drop(columns=["orig_idx"], errors="ignore")
        # Sync back to parquet so downstream pipeline steps stay in sync
        df.to_parquet(FIRMS_ENRICHED, index=False)
        print(f"[export_web] Synced enriched.xlsx → firms_enriched.parquet")
    elif FIRMS_ENRICHED.exists():
        print("[export_web] Loading firms_enriched.parquet...")
        df = pd.read_parquet(FIRMS_ENRICHED)
    else:
        print("[export_web] Loading firms_clean.parquet (fallback)...")
        df = pd.read_parquet(FIRMS_CLEAN)

    # Only keep columns that exist
    cols = [c for c in KEEP_COLS if c in df.columns]
    df = df[cols].copy()

    # Backfill missing text/signal fields from raw pipeline parquets.
    # enriched.xlsx has manual corrections but may have cleared some cells;
    # the raw parquets hold the original pipeline output for every firm.
    _backfill_from_parquets(df)

    # Convert bool columns to plain True/False/None (JSON-safe)
    bool_cols = ["gazelle_2024", "scaler_2024", "high_growth_2024", "priority_enrich",
                 "has_phd", "has_professor", "has_careers", "has_content_engine", "has_product_platform"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map(lambda v: bool(v) if pd.notna(v) else None)

    # Convert Int64 → int (JSON-safe)
    for col in df.select_dtypes(include=["Int64", "int64"]).columns:
        df[col] = df[col].apply(lambda v: int(v) if pd.notna(v) else None)

    # Round floats to 2 decimal places — but preserve coordinate precision
    GEO_COLS = {"lat", "lon"}
    for col in df.select_dtypes(include=["float64", "float32"]).columns:
        if col not in GEO_COLS:
            df[col] = df[col].round(2)
    # Keep coordinates at 5 decimal places (~1m precision)
    for col in GEO_COLS:
        if col in df.columns:
            df[col] = df[col].round(5)

    out = WEB_DATA / "firms.json"
    records = df.astype(object).where(pd.notna(df), None).to_dict(orient="records")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(_json_safe(records), f, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    size_mb = out.stat().st_size / 1_000_000
    print(f"[export_web] firms.json → {len(records)} rows, {size_mb:.1f} MB")
    return df


def export_sector_narratives() -> None:
    if not SECTOR_NARRATIVES.exists():
        print("[export_web] sector_narratives.json not found — skipping")
        return
    dst = WEB_DATA / "sector_narratives.json"
    shutil.copy(SECTOR_NARRATIVES, dst)
    print(f"[export_web] sector_narratives.json → copied")


def export_embeddings(df: pd.DataFrame) -> None:
    if os.getenv("EXPORT_EMBEDDINGS") != "1":
        print("[export_web] Skipping embeddings (set EXPORT_EMBEDDINGS=1 to generate them)")
        return

    print("[export_web] Computing embeddings for chat search...")
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as e:
        print(f"[export_web] sentence-transformers unavailable ({e.__class__.__name__}) — skipping embeddings (chat will use keyword search)")
        return

    model = SentenceTransformer("all-MiniLM-L6-v2")

    # Build text corpus: snippet + profile_text + business_model_refined + nace_section
    texts = []
    for _, row in df.iterrows():
        parts = [
            str(row.get("company_name") or ""),
            str(row.get("snippet") or ""),
            str(row.get("profile_text") or ""),
            str(row.get("business_model_refined") or ""),
            str(row.get("nace_section") or ""),
            str(row.get("target_segment") or ""),
            str(row.get("growth_evidence") or ""),
        ]
        texts.append(" ".join(p for p in parts if p and p != "None").strip())

    print(f"[export_web] Encoding {len(texts)} firms...")
    vectors = model.encode(texts, batch_size=64, show_progress_bar=True, normalize_embeddings=True)

    records = [
        {"bvd_id": str(df.iloc[i]["bvd_id"]), "vector": vectors[i].tolist()}
        for i in range(len(df))
    ]

    out = WEB_DATA / "embeddings.json"
    with open(out, "w") as f:
        json.dump(_json_safe(records), f, separators=(",", ":"), allow_nan=False)
    size_mb = out.stat().st_size / 1_000_000
    print(f"[export_web] embeddings.json → {len(records)} vectors, {size_mb:.1f} MB")


def export_stats(df: pd.DataFrame) -> None:
    print("[export_web] Running regression for stats.json...")
    try:
        import statsmodels.api as sm
        from sklearn.preprocessing import StandardScaler
        from scipy import stats as sp_stats
    except ImportError:
        print("[export_web] statsmodels/sklearn not installed — skipping stats")
        return

    df2 = df.copy()
    df2["is_growth"] = df2["category_2024"].isin(["Gazelle", "Scaler"]).astype(int)

    growth_cols = [f"growth_{y}" for y in range(2018, 2025) if f"growth_{y}" in df2.columns]
    df2["growth_volatility"] = df2[growth_cols].std(axis=1)

    feature_cols = ["avg_manager_age", "n_doctors", "growth_volatility"]
    pretty = {
        "avg_manager_age":  "Manager age (avg)",
        "n_doctors":        "Number of Dr/PhD managers",
        "growth_volatility": "Growth volatility (σ)",
        "orbis_equity_ratio_latest": "Equity ratio (%)",
    }

    results_out = {}

    for use_equity in [False, True]:
        feats = feature_cols + (["orbis_equity_ratio_latest"] if use_equity else [])
        model_df = df2[["is_growth"] + feats].dropna()
        if len(model_df) < 50:
            continue

        X = StandardScaler().fit_transform(model_df[feats].values)
        y = model_df["is_growth"].values
        X_sm = sm.add_constant(X)

        try:
            result = sm.Logit(y, X_sm).fit(disp=0)
        except Exception as e:
            print(f"[export_web] Regression failed ({feats}): {e}")
            continue

        coef_names = feats
        rows = []
        for i, name in enumerate(coef_names):
            rows.append({
                "feature": name,
                "label": pretty.get(name, name),
                "coef": round(float(result.params[i + 1]), 4),
                "odds_ratio": round(float(np.exp(result.params[i + 1])), 4),
                "p_value": round(float(result.pvalues[i + 1]), 4),
                "significant": bool(result.pvalues[i + 1] < 0.05),
            })

        # Correlation matrix
        corr_feats = ["is_growth", "avg_manager_age", "n_doctors", "growth_volatility", "orbis_equity_ratio_latest"]
        avail_corr = [c for c in corr_feats if c in df2.columns]
        corr_df = df2[avail_corr].dropna()
        corr_mat = corr_df.corr().round(3)

        # Mann-Whitney for each feature
        mw = {}
        for feat in feats:
            sub = df2[["is_growth", feat]].dropna()
            g1 = sub[sub["is_growth"] == 1][feat]
            g0 = sub[sub["is_growth"] == 0][feat]
            if len(g1) > 0 and len(g0) > 0:
                _, p = sp_stats.mannwhitneyu(g1, g0, alternative="two-sided")
                mw[feat] = round(float(p), 4)

        key = "with_equity" if use_equity else "without_equity"
        results_out[key] = {
            "n_firms": int(len(model_df)),
            "n_growth": int(y.sum()),
            "pseudo_r2": round(float(result.prsquared), 4),
            "log_likelihood": round(float(result.llf), 2),
            "aic": round(float(result.aic), 2),
            "coefficients": rows,
            "correlation_matrix": {
                "labels": [pretty.get(c, c) for c in corr_mat.columns.tolist()],
                "values": corr_mat.values.tolist(),
            },
            "mann_whitney": mw,
        }

    out = WEB_DATA / "stats.json"
    with open(out, "w") as f:
        json.dump(_json_safe(results_out), f, separators=(",", ":"), allow_nan=False)
    print(f"[export_web] stats.json → regression + correlation data")


def run() -> None:
    _ensure_web_data_dir()
    df = export_firms()
    export_sector_narratives()
    export_stats(df)
    export_embeddings(df)
    print("\n[export_web] Done. Files in:", WEB_DATA)


if __name__ == "__main__":
    run()
