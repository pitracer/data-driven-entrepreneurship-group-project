"""Sector Analysis — charts + LLM sector narratives."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from pipeline.config import load_best_data, SECTOR_NARRATIVES
from app.components.sidebar_filters import render_sidebar

st.set_page_config(page_title="Sector Analysis · Düsseldorf Growth", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@600;700&family=Open+Sans:wght@400;600&display=swap');
.stApp { background-color: #2B5354; }
section[data-testid="stSidebar"] { background-color: #244546; }
h1,h2,h3 { font-family: 'Rajdhani', sans-serif !important; color: #F7F8F7 !important; }
p, .stMarkdown { color: #F7F8F7; font-family: 'Open Sans', sans-serif; }
.narrative-card {
    background: rgba(255,255,255,0.05); border-left: 3px solid #558E8F;
    border-radius: 0 4px 4px 0; padding: 14px 18px; margin: 8px 0 20px;
    font-size: 13px; color: #F7F8F7; line-height: 1.6;
}
.section-label {
    font-size: 11px; font-weight: 600; color: rgba(247,248,247,.5);
    text-transform: uppercase; letter-spacing: .14em;
    border-bottom: 1px solid rgba(247,248,247,.12);
    padding-bottom: 8px; margin: 28px 0 16px;
}
</style>
""", unsafe_allow_html=True)

CHART_LAYOUT = dict(
    paper_bgcolor="#355E5F",
    plot_bgcolor="rgba(255,255,255,0.04)",
    font=dict(color="#F7F8F7", family="Open Sans"),
    margin=dict(l=10, r=10, t=30, b=10),
)


@st.cache_data
def load_data():
    df = load_best_data()
    narratives = {}
    if SECTOR_NARRATIVES.exists():
        narratives = json.loads(SECTOR_NARRATIVES.read_text(encoding="utf-8"))
    return df, narratives


df_base, narratives = load_data()
df = render_sidebar(df_base)

st.markdown("# 📊 Sector Analysis")

# ── Chart 1: Priority firms by sector ────────────────────────────────────────
st.markdown('<div class="section-label">Priority Firms by NACE Sector</div>', unsafe_allow_html=True)

sector_counts = (
    df[df["priority_enrich"]]
    .groupby("nace_letter")
    .agg(
        Gazelles=("gazelle_2024", "sum"),
        Scalers=("scaler_2024", "sum"),
        nace_section=("nace_section", "first"),
    )
    .reset_index()
    .sort_values("Gazelles", ascending=True)
    .tail(15)
)
sector_counts["label"] = sector_counts["nace_letter"] + " · " + sector_counts["nace_section"].str[:35]

fig1 = go.Figure()
fig1.add_trace(go.Bar(
    y=sector_counts["label"], x=sector_counts["Scalers"],
    name="Scalers", orientation="h",
    marker_color="#558E8F",
))
fig1.add_trace(go.Bar(
    y=sector_counts["label"], x=sector_counts["Gazelles"],
    name="Gazelles", orientation="h",
    marker_color="#FFD700",
))
fig1.update_layout(
    **CHART_LAYOUT,
    barmode="stack",
    height=420,
    legend=dict(orientation="h", y=1.05),
    xaxis_title="Number of firms",
)
st.plotly_chart(fig1, use_container_width=True)

# ── Chart 2: Employee trend for top 3 sectors ─────────────────────────────────
st.markdown('<div class="section-label">Employee Trend 2017–2024 · Top Sectors</div>', unsafe_allow_html=True)

top3_sectors = (
    df[df["priority_enrich"]]
    .groupby("nace_letter")["priority_enrich"]
    .count()
    .nlargest(3)
    .index.tolist()
)

emp_cols = [f"employees_{y}" for y in range(2017, 2025)]
years = list(range(2017, 2025))

fig2 = go.Figure()
colors = ["#FFD700", "#558E8F", "#72ACAD"]

for i, letter in enumerate(top3_sectors):
    sector_df = df[df["nace_letter"] == letter]
    means = [sector_df[c].mean() for c in emp_cols]
    nace_name = sector_df["nace_section"].iloc[0][:35] if len(sector_df) else letter
    fig2.add_trace(go.Scatter(
        x=years, y=means,
        mode="lines+markers",
        name=f"{letter} · {nace_name}",
        line=dict(color=colors[i], width=2),
        marker=dict(size=6),
    ))

fig2.update_layout(
    **CHART_LAYOUT,
    height=340,
    xaxis=dict(tickvals=years),
    yaxis_title="Avg employees",
)
st.plotly_chart(fig2, use_container_width=True)

# ── Sector narratives ─────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Sector Intelligence</div>', unsafe_allow_html=True)

if narratives:
    for letter, narrative in sorted(narratives.items()):
        sector_rows = df[df["nace_letter"] == letter]
        if sector_rows.empty:
            continue
        nace_full = sector_rows["nace_section"].iloc[0]
        n_priority = int(sector_rows["priority_enrich"].sum())
        with st.expander(f"{letter} — {nace_full[:60]}  ·  {n_priority} priority firms", expanded=False):
            st.markdown(
                f'<div class="narrative-card">{narrative}</div>',
                unsafe_allow_html=True,
            )
            # Mini stats
            c1, c2, c3 = st.columns(3)
            c1.metric("Gazelles", int(sector_rows["gazelle_2024"].sum()))
            c2.metric("Scalers", int(sector_rows["scaler_2024"].sum()))
            avg_g = sector_rows["growth_2024"].mean()
            c3.metric("Avg growth 2024", f"{avg_g:.1%}" if pd.notna(avg_g) else "n/a")
else:
    st.info(
        "Sector narratives not yet generated. "
        "Run `python -m pipeline.step_05_llm_sectors` to add AI analysis."
    )
    # Show raw stats anyway
    raw = (
        df.groupby("nace_letter")
        .agg(
            total=("bvd_id", "count"),
            gazelles=("gazelle_2024", "sum"),
            scalers=("scaler_2024", "sum"),
            avg_growth=("growth_2024", "mean"),
        )
        .reset_index()
        .sort_values("gazelles", ascending=False)
    )
    st.dataframe(raw, hide_index=True, use_container_width=True)
