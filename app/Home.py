"""
Düsseldorf Growth Dashboard — Home page.
"Hidden Champions vs. Corporate Giants"
"""
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
.stApp { background-color: #2B5354; }
section[data-testid="stSidebar"] { background-color: #244546; }
h1,h2,h3 { font-family: 'Rajdhani', sans-serif !important; color: #F7F8F7 !important; }
p, li, .stMarkdown { color: #F7F8F7; font-family: 'Open Sans', sans-serif; }
.metric-card {
    background: #355E5F; border-radius: 4px; padding: 20px 24px;
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
    border-left: 3px solid #558E8F; background: rgba(255,255,255,0.06);
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

# ── Callout ───────────────────────────────────────────────────────────────────
st.markdown(
    f'<div class="callout">'
    f"<strong>The paradox:</strong> Düsseldorf's 10 largest employers "
    f"(Metro, Henkel, Rheinmetall…) have shed jobs since their peak. "
    f"Meanwhile, {n_gazelles} Gazelles and {n_scalers} Scalers nobody has heard of "
    f"are growing at 20%+ per year — and they cluster in just a handful of sectors."
    f"</div>",
    unsafe_allow_html=True,
)

# ── Narrative ─────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">The Story</div>', unsafe_allow_html=True)

col_l, col_r = st.columns([2, 1])
with col_l:
    st.markdown("""
**Act I — The Giants are shrinking.**
Metro AG employed over 155,000 people in 2017; by 2024 that number had fallen to 87,810.
Henkel, Rheinmetall, and most of Düsseldorf's headline employers tell a similar story of
restructuring, automation, and global headcount rebalancing. The city's anchor firms are no
longer the engine of local employment growth.

**Act II — The Hidden Champions rise.**
While the giants contract, a class of mid-sized firms most people have never heard of is
quietly adding jobs at extraordinary rates. These Gazelles — young firms growing 20% or more
per year — and their larger cousins, the Scalers, are concentrated in Professional Services,
IT, and Healthcare. They are the real drivers of Düsseldorf's labour market resilience.

**Act III — What does this mean?**
The shift from corporate giants to agile hidden champions has profound implications for
economic policy, real-estate demand, and talent flows in the city. This dashboard makes
that shift visible — by firm, by sector, and by neighbourhood — for the first time.
""")

with col_r:
    # Quick breakdown table
    cat_counts = df["category_2024"].value_counts().reset_index()
    cat_counts.columns = ["Category", "Firms"]
    st.dataframe(
        cat_counts,
        hide_index=True,
        use_container_width=True,
    )

# ── Navigation ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Explore</div>', unsafe_allow_html=True)
nc1, nc2, nc3, nc4 = st.columns(4)
nc1.page_link("pages/1_Map.py",             label="🗺️ Map",             help="Geocoded firms on an interactive map")
nc2.page_link("pages/2_Sector_Analysis.py", label="📊 Sector Analysis", help="Charts + AI sector narratives")
nc3.page_link("pages/3_Firm_Explorer.py",   label="🔍 Firm Explorer",   help="Search and filter all firms")
nc4.page_link("pages/4_Chat.py",            label="💬 Chat",            help="Ask questions about the data")
