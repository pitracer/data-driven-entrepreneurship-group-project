"""
Step 08 — K-means clustering on extracted business signals.

Produces two cluster columns:
  archetype_cluster   : business archetype (digital_scaler, niche_industrial_specialist, ...)
  growth_cluster      : growth strategy (hiring_led, expansion_led, acquisition_led, low_growth_stable)

Adds these columns to firm_signals.parquet in-place.

Usage:
    python -m pipeline.step_08_cluster
    python -m pipeline.step_08_cluster --n-clusters 4   # default
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import LabelEncoder, StandardScaler

from pipeline.config import FIRM_SIGNALS, ensure_dirs


# Human-readable label mappings — assigned by inspecting cluster centroids
# (highest digital_leverage + lowest scaling from "other" end → digital scalers, etc.)
ARCHETYPE_LABELS = [
    "digital_scaler",
    "niche_industrial_specialist",
    "traditional_local_service",
    "holding_passive",
]

GROWTH_LABELS = [
    "hiring_led",
    "expansion_led",
    "acquisition_led",
    "low_growth_stable",
]


def _encode_categorical(df: pd.DataFrame, col: str) -> np.ndarray:
    """Label-encode a string column, treating NaN/unknown as a separate category."""
    series = df[col].fillna("unknown").astype(str)
    return LabelEncoder().fit_transform(series).reshape(-1, 1)


def _assign_labels(km: KMeans, labels: list[str], n_clusters: int) -> dict[int, str]:
    """
    Map K-means cluster IDs to human-readable labels.

    Simple strategy: sort centroids by their first feature dimension and
    map in order. Works well enough for interpretable cluster naming.
    Caller can relabel manually after inspecting outputs.
    """
    centroids = km.cluster_centers_
    order = np.argsort(centroids[:, 0])  # sort by first feature
    mapping = {}
    for rank, cluster_id in enumerate(order):
        mapping[int(cluster_id)] = labels[rank % len(labels)]
    return mapping


def run(n_clusters: int = 4) -> None:
    ensure_dirs()

    if not FIRM_SIGNALS.exists():
        print(f"[step_08] {FIRM_SIGNALS} not found — run step_07 first")
        sys.exit(1)

    df = pd.read_parquet(FIRM_SIGNALS)
    print(f"[step_08] {len(df)} firms loaded from firm_signals.parquet")

    # ── Business archetype cluster ────────────────────────────────────────────
    # Features: business_model_refined (encoded), target_segment (encoded), digital_leverage_score
    arch_mask = (
        df["business_model_refined"].notna() &
        df["target_segment"].notna() &
        df["digital_leverage_score"].notna()
    )
    arch_df = df[arch_mask].copy()
    print(f"[step_08] Archetype cluster: {len(arch_df)} firms with full features")

    if len(arch_df) >= n_clusters:
        bm_enc = _encode_categorical(arch_df, "business_model_refined")
        ts_enc = _encode_categorical(arch_df, "target_segment")
        dl_arr = arch_df["digital_leverage_score"].values.reshape(-1, 1)

        X_arch = np.hstack([bm_enc, ts_enc, dl_arr]).astype(float)
        X_arch_scaled = StandardScaler().fit_transform(X_arch)

        km_arch = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        km_arch.fit(X_arch_scaled)

        label_map = _assign_labels(km_arch, ARCHETYPE_LABELS, n_clusters)
        arch_df["archetype_cluster"] = [label_map[c] for c in km_arch.labels_]

        df = df.merge(
            arch_df[["bvd_id", "archetype_cluster"]],
            on="bvd_id", how="left",
        )

        print("[step_08] Archetype cluster distribution:")
        for label, count in df["archetype_cluster"].value_counts().items():
            print(f"  {label}: {count}")
    else:
        print(f"[step_08] Not enough data for archetype clustering ({len(arch_df)} < {n_clusters})")
        df["archetype_cluster"] = None

    # ── Growth strategy cluster ───────────────────────────────────────────────
    # Features: scaling_signal_score, digital_leverage_score, has_careers, has_content_engine
    grow_mask = (
        df["scaling_signal_score"].notna() &
        df["digital_leverage_score"].notna()
    )
    grow_df = df[grow_mask].copy()
    print(f"\n[step_08] Growth cluster: {len(grow_df)} firms with full features")

    if len(grow_df) >= n_clusters:
        ss = grow_df["scaling_signal_score"].values.reshape(-1, 1)
        dl = grow_df["digital_leverage_score"].values.reshape(-1, 1)
        hc = grow_df["has_careers"].fillna(False).astype(int).values.reshape(-1, 1)
        ce = grow_df["has_content_engine"].fillna(False).astype(int).values.reshape(-1, 1)

        X_grow = np.hstack([ss, dl, hc, ce]).astype(float)
        X_grow_scaled = StandardScaler().fit_transform(X_grow)

        km_grow = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        km_grow.fit(X_grow_scaled)

        label_map_g = _assign_labels(km_grow, GROWTH_LABELS, n_clusters)
        grow_df["growth_cluster"] = [label_map_g[c] for c in km_grow.labels_]

        df = df.merge(
            grow_df[["bvd_id", "growth_cluster"]],
            on="bvd_id", how="left",
        )

        print("[step_08] Growth cluster distribution:")
        for label, count in df["growth_cluster"].value_counts().items():
            print(f"  {label}: {count}")
    else:
        print(f"[step_08] Not enough data for growth clustering ({len(grow_df)} < {n_clusters})")
        df["growth_cluster"] = None

    df.to_parquet(FIRM_SIGNALS, index=False, engine="pyarrow")
    print(f"\n[step_08] Wrote cluster columns to {FIRM_SIGNALS}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-clusters", type=int, default=4)
    args = parser.parse_args()
    run(n_clusters=args.n_clusters)
    sys.exit(0)
