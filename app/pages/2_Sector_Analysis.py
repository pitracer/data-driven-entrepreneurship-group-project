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
.stApp { background-color: #0B1F3A; }
section[data-testid="stSidebar"] { background-color: #071629; }
h1,h2,h3 { font-family: 'Rajdhani', sans-serif !important; color: #F7F8F7 !important; }
p, .stMarkdown { color: #F7F8F7; font-family: 'Open Sans', sans-serif; }
.narrative-card {
    background: rgba(255,255,255,0.05); border-left: 3px solid #1E6FD4;
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
    paper_bgcolor="#0F2440",
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
df_sidebar = render_sidebar(df_base)

st.markdown("#  Sector Analysis")

# ── Global page filter ────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Filter</div>', unsafe_allow_html=True)
fc1, fc2, fc3 = st.columns([2, 2, 2])
with fc1:
    focus = st.radio(
        "Firm scope",
        ["All firms", "Growth firms only", "Gazelles", "Scalers"],
        horizontal=True,
    )
with fc2:
    min_firms = st.slider("Min. firms per sector (for charts)", 1, 30, 5)
with fc3:
    top_n = st.slider("Top N sectors shown", 5, 20, 12)

# Apply scope filter on top of sidebar selection
if focus == "Growth firms only":
    df = df_sidebar[df_sidebar["priority_enrich"]]
elif focus == "Gazelles":
    df = df_sidebar[df_sidebar["category_2024"] == "Gazelle"]
elif focus == "Scalers":
    df = df_sidebar[df_sidebar["category_2024"] == "Scaler"]
else:
    df = df_sidebar

st.caption(f"Showing **{len(df):,} firms** — {focus}")

# ── Chart 1: Gazelles & Scalers by sector ────────────────────────────────────
st.markdown('<div class="section-label">Gazelles & Scalers by NACE Sector</div>', unsafe_allow_html=True)

sector_counts = (
    df.groupby("nace_letter")
    .agg(
        Gazelles=("gazelle_2024", "sum"),
        Scalers=("scaler_2024", "sum"),
        total=("bvd_id", "count"),
        nace_section=("nace_section", "first"),
    )
    .reset_index()
)
sector_counts = (
    sector_counts[sector_counts["total"] >= min_firms]
    .sort_values("Gazelles", ascending=True)
    .tail(top_n)
)
sector_counts["label"] = sector_counts["nace_letter"] + " · " + sector_counts["nace_section"].str[:35]

fig1 = go.Figure()
fig1.add_trace(go.Bar(
    y=sector_counts["label"], x=sector_counts["Scalers"],
    name="Scalers", orientation="h",
    marker_color="#1E6FD4",
))
fig1.add_trace(go.Bar(
    y=sector_counts["label"], x=sector_counts["Gazelles"],
    name="Gazelles", orientation="h",
    marker_color="#FFD700",
))
fig1.update_layout(
    **CHART_LAYOUT,
    barmode="stack",
    height=max(320, top_n * 30),
    legend=dict(orientation="h", y=1.05),
    xaxis_title="Number of firms",
)
st.plotly_chart(fig1, use_container_width=True)

# ── Chart 2: Employee trend for top 3 sectors ─────────────────────────────────
st.markdown('<div class="section-label">Employee Trend 2017–2024 · Top Sectors</div>', unsafe_allow_html=True)

top3_sectors = (
    df.groupby("nace_letter")["bvd_id"]
    .count()
    .nlargest(3)
    .index.tolist()
)

emp_cols = [f"employees_{y}" for y in range(2017, 2025)]
years = list(range(2017, 2025))

fig2 = go.Figure()
colors = ["#FFD700", "#1E6FD4", "#64B5F6"]

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

# ── Chart 3: Equity Ratio by Sector (Orbis) ──────────────────────────────────
if "orbis_equity_ratio_latest" in df.columns:
    st.markdown('<div class="section-label">Financial Health · Median Equity Ratio by Sector</div>', unsafe_allow_html=True)

    eq_sector = (
        df[df["orbis_equity_ratio_latest"].notna() & (df["orbis_equity_ratio_latest"] >= 0)]
        .groupby("nace_letter")
        .agg(
            median_eq=("orbis_equity_ratio_latest", "median"),
            n=("orbis_equity_ratio_latest", "count"),
            nace_section=("nace_section", "first"),
        )
        .reset_index()
    )
    eq_sector = eq_sector[eq_sector["n"] >= min_firms].sort_values("median_eq", ascending=True).tail(top_n)
    eq_sector["label"] = eq_sector["nace_letter"] + " · " + eq_sector["nace_section"].str[:35]

    fig3 = go.Figure([go.Bar(
        y=eq_sector["label"],
        x=eq_sector["median_eq"],
        orientation="h",
        marker_color="#64B5F6",
        text=[f"{v:.0f}%" for v in eq_sector["median_eq"]],
        textposition="outside",
    )])
    fig3.update_layout(
        **CHART_LAYOUT,
        height=420,
        xaxis=dict(title="Median equity ratio (%)", ticksuffix="%"),
        yaxis=dict(automargin=True),
    )
    st.plotly_chart(fig3, use_container_width=True)
    st.markdown(
        f'<p style="font-size:11px;color:rgba(247,248,247,.4);margin-top:-12px;">'
        f'Orbis equity data available for {int(df["orbis_equity_ratio_latest"].notna().sum())} firms</p>',
        unsafe_allow_html=True,
    )

# ── Chart 4: Management Age by Sector ────────────────────────────────────────
if "avg_manager_age" in df.columns:
    st.markdown('<div class="section-label">Leadership Age · Average Manager Age by Sector</div>', unsafe_allow_html=True)

    age_sector = (
        df[df["avg_manager_age"].notna()]
        .groupby("nace_letter")
        .agg(
            mean_age=("avg_manager_age", "mean"),
            n=("avg_manager_age", "count"),
            nace_section=("nace_section", "first"),
        )
        .reset_index()
    )
    age_sector = age_sector[age_sector["n"] >= min_firms].sort_values("mean_age", ascending=True)
    age_sector["label"] = age_sector["nace_letter"] + " · " + age_sector["nace_section"].str[:35]

    fig4 = go.Figure([go.Bar(
        y=age_sector["label"],
        x=age_sector["mean_age"],
        orientation="h",
        marker_color="#1E6FD4",
        text=[f"{v:.1f} yrs" for v in age_sector["mean_age"]],
        textposition="outside",
    )])
    fig4.update_layout(
        **CHART_LAYOUT,
        height=420,
        xaxis=dict(title="Average manager age (years)", range=[48, 68]),
        yaxis=dict(automargin=True),
    )
    st.plotly_chart(fig4, use_container_width=True)

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
