"""
Düsseldorf Growth Dashboard — Home page.
"Hidden Champions vs. Corporate Giants"
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from pipeline.config import load_best_data, FIRMS_ENRICHED

st.set_page_config(
    page_title="Düsseldorf Growth Dashboard",
    page_icon="🦌",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@600;700&family=Open+Sans:wght@400;600&display=swap');
.stApp { background-color: #0B1F3A; }
section[data-testid="stSidebar"] { background-color: #071629; }
h1,h2,h3 { font-family: 'Rajdhani', sans-serif !important; color: #F7F8F7 !important; }
p, li, .stMarkdown { color: #F7F8F7; font-family: 'Open Sans', sans-serif; }
.metric-card {
    background: #0F2440; border-radius: 4px; padding: 20px 24px;
    border: 1px solid rgba(247,248,247,.12); text-align: center;
}
.metric-label {
    font-size: 10px; font-weight: 600; color: rgba(247,248,247,.6);
    text-transform: uppercase; letter-spacing: .10em; margin-bottom: 6px;
}
.metric-value {
    font-family: 'Rajdhani', sans-serif; font-size: 36px;
    font-weight: 700; color: #F7F8F7; line-height: 1;
}
.metric-sub { font-size: 11px; color: rgba(247,248,247,.5); margin-top: 4px; }
.callout {
    border-left: 3px solid #1E6FD4; background: rgba(255,255,255,0.06);
    border-radius: 0 4px 4px 0; padding: 18px 22px; margin: 20px 0;
}
.section-label {
    font-size: 11px; font-weight: 600; color: rgba(247,248,247,.5);
    text-transform: uppercase; letter-spacing: .14em;
    border-bottom: 1px solid rgba(247,248,247,.12);
    padding-bottom: 8px; margin: 28px 0 16px;
}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data() -> pd.DataFrame | None:
    try:
        return load_best_data()
    except FileNotFoundError:
        return None


df = load_data()
is_enriched = FIRMS_ENRICHED.exists()

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown(
    '<h1 style="font-size:38px;margin-bottom:2px;">Düsseldorf\'s Hidden Champions</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p style="font-size:16px;color:rgba(247,248,247,.6);margin-top:0;">'
    "How unknown mid-sized firms are quietly driving the city's job growth"
    "</p>",
    unsafe_allow_html=True,
)

if df is None:
    st.error("firms_clean.parquet not found. Run `python -m pipeline.step_01_clean` first.")
    st.stop()

# ── KPI Row ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Key Metrics — 2024</div>', unsafe_allow_html=True)
c1, c2, c3, c4, c5 = st.columns(5)


def kpi(col, label, value, sub=""):
    col.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-sub">{sub}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


n_gazelles = int(df["gazelle_2024"].sum())
n_scalers = int(df["scaler_2024"].sum())
n_priority = int(df["priority_enrich"].sum())
n_sectors = df["nace_letter"].nunique()

# Compute job loss at top 10 firms
top10 = df.nlargest(10, "employees_2024")
job_change_top10 = int(
    top10["employee_change_abs"]
    .dropna()
    .sum()
)
job_change_str = f"{job_change_top10:+,}"

n_with_revenue = int(df["orbis_revenue_latest"].notna().sum()) if "orbis_revenue_latest" in df.columns else 0
n_phd_mgmt = int(df["has_phd"].sum()) if "has_phd" in df.columns else 0

kpi(c1, "Total Firms", f"{len(df):,}", "unique BvD IDs")
kpi(c2, "Gazelles 🦌", str(n_gazelles), "≥20% growth/year")
kpi(c3, "Scalers 📈", str(n_scalers), "sustained high growth")
kpi(c4, "Top-10 Job Δ", job_change_str, "since earliest baseline")
kpi(c5, "PhD/Dr Mgmt", str(n_phd_mgmt), f"of {len(df):,} firms")

# ── Category breakdown + navigation ──────────────────────────────────────────
col_l, col_r = st.columns([1, 1])

with col_l:
    cat_counts = df["category_2024"].value_counts().reset_index()
    cat_counts.columns = ["Category", "Firms"]
    st.dataframe(cat_counts, hide_index=True, use_container_width=True)

with col_r:
    st.markdown('<div class="section-label">Explore</div>', unsafe_allow_html=True)
    st.page_link("pages/1_Map.py",             label="🗺️ Map — geocoded firm locations")
    st.page_link("pages/2_Sector_Analysis.py", label="📊 Sector Analysis — growth by NACE sector")
    st.page_link("pages/3_Firm_Explorer.py",   label="🔍 Firm Explorer — search all 1,555 firms")
    st.page_link("pages/4_Leadership.py",      label="🧬 Leadership Profile — Orbis management data")
    st.page_link("pages/6_Stats.py",           label="📐 Stats — regression analysis of scaling factors")
    st.page_link("pages/5_Chat.py",            label="💬 Chat — ask questions about the data")
