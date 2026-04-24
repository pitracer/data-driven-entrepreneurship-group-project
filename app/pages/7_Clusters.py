"""Cluster Analysis — business archetypes and growth strategies."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from pipeline.config import load_best_data

st.set_page_config(page_title="Clusters · Düsseldorf Growth", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@600;700&family=Open+Sans:wght@400;600&display=swap');
.stApp { background-color: #0B1F3A; }
section[data-testid="stSidebar"] { background-color: #071629; }
h1,h2,h3 { font-family: 'Rajdhani', sans-serif !important; color: #F7F8F7 !important; }
p, .stMarkdown { color: #F7F8F7; font-family: 'Open Sans', sans-serif; }
.section-label {
    font-size: 11px; font-weight: 600; color: rgba(247,248,247,.5);
    text-transform: uppercase; letter-spacing: .14em;
    border-bottom: 1px solid rgba(247,248,247,.12);
    padding-bottom: 8px; margin: 28px 0 16px;
}
.insight-card {
    background: rgba(30,111,212,0.15); border-left: 3px solid #42A5F5;
    border-radius: 0 4px 4px 0; padding: 12px 16px; margin: 8px 0 20px;
    font-size: 13px; color: #F7F8F7; line-height: 1.6;
}
</style>
""", unsafe_allow_html=True)

CHART_LAYOUT = dict(
    paper_bgcolor="#0F2440",
    plot_bgcolor="rgba(255,255,255,0.04)",
    font=dict(color="#F7F8F7", family="Open Sans"),
    margin=dict(l=10, r=10, t=36, b=10),
)

ARCHETYPE_COLORS = {
    "digital_scaler":               "#FFB300",
    "niche_industrial_specialist":  "#42A5F5",
    "traditional_local_service":    "#66BB6A",
    "holding_passive":              "#455A64",
}

GROWTH_COLORS = {
    "hiring_led":       "#FFB300",
    "expansion_led":    "#42A5F5",
    "acquisition_led":  "#AB47BC",
    "low_growth_stable":"#455A64",
}


@st.cache_data
def load_data():
    return load_best_data()


df = load_data()

st.markdown("# Business Archetype & Growth Clusters")
st.markdown(
    "Firms clustered by signal-based analysis: web presence, growth evidence, "
    "and business model — revealing hidden patterns beyond the Gazelle/Scaler labels."
)

# Check if cluster columns exist
has_archetype = "archetype_cluster" in df.columns and df["archetype_cluster"].notna().any()
has_growth = "growth_cluster" in df.columns and df["growth_cluster"].notna().any()
has_scaling = "scaling_signal_score" in df.columns and df["scaling_signal_score"].notna().any()

if not has_archetype and not has_growth:
    st.info(
        "Cluster data not yet available. Run the signal enrichment pipeline first:\n\n"
        "```bash\n"
        "python -m pipeline.step_02_search --provider serper --all-firms\n"
        "python -m pipeline.step_06_signal_search --query all\n"
        "python -m pipeline.step_07_extract_signals\n"
        "python -m pipeline.step_08_cluster\n"
        "python -m pipeline.enrich_batch\n"
        "```"
    )
    st.stop()

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filters")
    sectors = sorted(df["nace_letter"].dropna().unique())
    sel_sectors = st.multiselect("Sector (NACE letter)", sectors, default=[])

    categories = sorted(df["category_2024"].dropna().unique())
    sel_cats = st.multiselect("Growth category", categories, default=[])

filt = df.copy()
if sel_sectors:
    filt = filt[filt["nace_letter"].isin(sel_sectors)]
if sel_cats:
    filt = filt[filt["category_2024"].isin(sel_cats)]

# ── KPI row ───────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Firms with archetype label",
          int(filt["archetype_cluster"].notna().sum()) if has_archetype else "—")
k2.metric("Firms with growth label",
          int(filt["growth_cluster"].notna().sum()) if has_growth else "—")
k3.metric("Avg scaling signal",
          f"{filt['scaling_signal_score'].mean():.1f}" if has_scaling else "—")
k4.metric("Avg digital leverage",
          f"{filt['digital_leverage_score'].mean():.1f}" if "digital_leverage_score" in filt.columns else "—")

# ── Archetype cluster ─────────────────────────────────────────────────────────
if has_archetype:
    st.markdown('<div class="section-label">Business Archetype Clusters</div>',
                unsafe_allow_html=True)

    arch_df = filt[filt["archetype_cluster"].notna()].copy()

    col_a, col_b = st.columns([1, 1])

    with col_a:
        arch_counts = arch_df["archetype_cluster"].value_counts().reset_index()
        arch_counts.columns = ["Archetype", "Count"]
        fig_bar = go.Figure([go.Bar(
            x=arch_counts["Count"],
            y=arch_counts["Archetype"],
            orientation="h",
            marker_color=[ARCHETYPE_COLORS.get(a, "#888") for a in arch_counts["Archetype"]],
            text=arch_counts["Count"],
            textposition="outside",
        )])
        fig_bar.update_layout(
            **CHART_LAYOUT,
            height=280,
            xaxis_title="Number of firms",
            yaxis=dict(automargin=True),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_b:
        # Archetype × growth category crosstab
        cross = (
            arch_df.groupby(["archetype_cluster", "category_2024"])
            .size()
            .reset_index(name="n")
        )
        fig_cross = px.bar(
            cross,
            x="archetype_cluster",
            y="n",
            color="category_2024",
            color_discrete_map={"Gazelle": "#FFB300", "Scaler": "#42A5F5", "Other": "#455A64"},
            barmode="stack",
            labels={"archetype_cluster": "", "n": "Firms", "category_2024": "Category"},
        )
        fig_cross.update_layout(
            **CHART_LAYOUT,
            height=280,
            legend=dict(orientation="h", y=1.1),
            xaxis=dict(tickangle=-15),
        )
        st.plotly_chart(fig_cross, use_container_width=True)

# ── Growth strategy cluster ───────────────────────────────────────────────────
if has_growth:
    st.markdown('<div class="section-label">Growth Strategy Clusters</div>',
                unsafe_allow_html=True)

    grow_df = filt[filt["growth_cluster"].notna()].copy()

    col_c, col_d = st.columns([1, 1])

    with col_c:
        grow_counts = grow_df["growth_cluster"].value_counts().reset_index()
        grow_counts.columns = ["Strategy", "Count"]
        fig_grow = go.Figure([go.Bar(
            x=grow_counts["Count"],
            y=grow_counts["Strategy"],
            orientation="h",
            marker_color=[GROWTH_COLORS.get(g, "#888") for g in grow_counts["Strategy"]],
            text=grow_counts["Count"],
            textposition="outside",
        )])
        fig_grow.update_layout(
            **CHART_LAYOUT,
            height=260,
            xaxis_title="Number of firms",
            yaxis=dict(automargin=True),
        )
        st.plotly_chart(fig_grow, use_container_width=True)

    with col_d:
        if has_scaling and "digital_leverage_score" in grow_df.columns:
            fig_scatter = px.scatter(
                grow_df[grow_df["scaling_signal_score"].notna() & grow_df["digital_leverage_score"].notna()],
                x="digital_leverage_score",
                y="scaling_signal_score",
                color="growth_cluster",
                color_discrete_map=GROWTH_COLORS,
                hover_data=["company_name", "category_2024"],
                labels={
                    "digital_leverage_score": "Digital Leverage Score (0–3)",
                    "scaling_signal_score": "Scaling Signal Score (0–3)",
                    "growth_cluster": "Strategy",
                },
                opacity=0.75,
            )
            fig_scatter.update_layout(
                **CHART_LAYOUT,
                height=260,
                legend=dict(orientation="h", y=1.1),
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

# ── Signal score distributions ────────────────────────────────────────────────
if has_scaling:
    st.markdown('<div class="section-label">Signal Score Distribution by Growth Category</div>',
                unsafe_allow_html=True)

    score_col = st.selectbox(
        "Score to compare",
        options=["scaling_signal_score", "digital_leverage_score"],
        format_func=lambda x: "Scaling Signal Score" if x == "scaling_signal_score" else "Digital Leverage Score",
    )

    score_df = filt[["category_2024", score_col]].dropna()
    fig_hist = px.histogram(
        score_df,
        x=score_col,
        color="category_2024",
        barmode="overlay",
        opacity=0.7,
        color_discrete_map={"Gazelle": "#FFB300", "Scaler": "#42A5F5", "Other": "#455A64"},
        labels={score_col: score_col.replace("_", " ").title()},
        nbins=4,
    )
    fig_hist.update_layout(**CHART_LAYOUT, height=300, legend=dict(orientation="h", y=1.08))
    st.plotly_chart(fig_hist, use_container_width=True)

# ── Firm table ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Firm Detail Table</div>', unsafe_allow_html=True)

table_cols = [
    "company_name", "category_2024", "nace_letter",
    "archetype_cluster", "growth_cluster",
    "scaling_signal_score", "digital_leverage_score",
    "business_model_refined", "growth_evidence",
]
avail_table = [c for c in table_cols if c in filt.columns]

if has_archetype:
    cluster_filter = st.selectbox(
        "Filter by archetype",
        options=["All"] + sorted(filt["archetype_cluster"].dropna().unique().tolist()),
    )
    table_df = filt if cluster_filter == "All" else filt[filt["archetype_cluster"] == cluster_filter]
else:
    table_df = filt

st.dataframe(
    table_df[avail_table].sort_values("scaling_signal_score", ascending=False)
    .head(200)
    .reset_index(drop=True),
    hide_index=True,
    use_container_width=True,
)
st.caption(f"Showing up to 200 of {len(table_df):,} firms")
