"""Hidden Champions Profile — Orbis management & financial intelligence."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from pipeline.config import load_best_data
from app.components.sidebar_filters import render_sidebar

st.set_page_config(page_title="Leadership Profile · Düsseldorf Growth", layout="wide")

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
 background: rgba(255,255,255,0.05); border-left: 3px solid #FFD700;
 border-radius: 0 4px 4px 0; padding: 12px 16px; margin: 8px 0 20px;
 font-size: 13px; color: #F7F8F7; line-height: 1.6;
}
.coverage-note {
 font-size: 11px; color: rgba(247,248,247,.45); margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)

CHART_LAYOUT = dict(
 paper_bgcolor="#0F2440",
 plot_bgcolor="rgba(255,255,255,0.04)",
 font=dict(color="#F7F8F7", family="Open Sans"),
 margin=dict(l=10, r=10, t=36, b=10),
)
CAT_COLORS = {"Gazelle": "#FFB300", "Scaler": "#42A5F5", "Other": "#455A64"}
CAT_ORDER = ["Gazelle", "Scaler", "Other"]


@st.cache_data
def load_data():
 df = load_best_data()
 # Normalise has_phd which may be stored as string "True"/"False"
 df["has_phd"] = df["has_phd"].map(
 {True: True, False: False, "True": True, "False": False}
 )
 return df


df_base = load_data()
df = render_sidebar(df_base)

# Filter to categories that exist in this view
present_cats = [c for c in CAT_ORDER if c in df["category_2024"].values]

st.markdown("# Hidden Champions Profile")
st.markdown(
 "What Orbis reveals about the firms quietly driving Düsseldorf's job growth — "
 "management age, academic leadership, and financial resilience."
)

# ── KPI row ───────────────────────────────────────────────────────────────────
gaz = df[df["category_2024"] == "Gazelle"]
scaler = df[df["category_2024"] == "Scaler"]
other = df[df["category_2024"] == "Other"]

k1, k2, k3, k4 = st.columns(4)
gaz_age = gaz["avg_manager_age"].mean()
oth_age = other["avg_manager_age"].mean()
age_diff = oth_age - gaz_age
k1.metric("Gazelle mgmt age", f"{gaz_age:.1f} yrs", f"{-age_diff:.1f} yrs vs market avg")
k2.metric("PhD/Dr leadership (Gazelles)", f"{(gaz['has_phd']==True).mean()*100:.0f}%",
 f"{((gaz['has_phd']==True).mean() - (other['has_phd']==True).mean())*100:+.0f}pp vs Others")
gaz_eq = gaz["orbis_equity_ratio_latest"].median()
scl_eq = scaler["orbis_equity_ratio_latest"].median()
k3.metric("Gazelle equity ratio (median)", f"{gaz_eq:.0f}%", f"{gaz_eq - scl_eq:+.0f}pp vs Scalers")
k4.metric("Orbis firms matched", f"{df['n_managers'].notna().sum():,}", "out of 1,555 total")


# ── Chart 1: Manager Age by Category ─────────────────────────────────────────
st.markdown('<div class="section-label">Average Management Age by Growth Category</div>', unsafe_allow_html=True)

age_df = (
 df[df["category_2024"].isin(present_cats) & df["avg_manager_age"].notna()]
 .groupby("category_2024")["avg_manager_age"]
 .agg(mean="mean", median="median", count="count")
 .reindex(present_cats)
 .reset_index()
)

fig_age = go.Figure()
for _, row in age_df.iterrows():
 cat = row["category_2024"]
 fig_age.add_trace(go.Bar(
 x=[cat], y=[row["mean"]],
 name=cat,
 marker_color=CAT_COLORS.get(cat, "#888"),
 text=[f"{row['mean']:.1f} yrs"],
 textposition="outside",
 textfont=dict(size=13, color="#F7F8F7"),
 showlegend=False,
 ))

fig_age.update_layout(
 **CHART_LAYOUT,
 height=320,
 yaxis=dict(title="Average age (years)", range=[48, 62]),
 xaxis_title="",
)
st.plotly_chart(fig_age, use_container_width=True)

st.markdown(
 '<div class="insight-card">'
 f"Gazelle managers average <strong>{gaz_age:.1f} years</strong> vs "
 f"<strong>{oth_age:.1f} years</strong> for the broader market — a "
 f"<strong>{age_diff:.1f}-year gap</strong>. Hidden champions tend to be led by a "
 "younger generation of executives who have grown with their firms rather than inheriting them."
 "</div>",
 unsafe_allow_html=True,
)

# ── Chart 2: Education Level Breakdown ───────────────────────────────────────
st.markdown('<div class="section-label">Management Education Level</div>', unsafe_allow_html=True)

edu_raw = (
 df[df["category_2024"].isin(present_cats) & df["mgmt_education_score"].notna()]
 .groupby(["category_2024", "mgmt_education_score"])
 .size()
 .reset_index(name="n")
)
edu_total = edu_raw.groupby("category_2024")["n"].transform("sum")
edu_raw["pct"] = edu_raw["n"] / edu_total * 100

edu_colors = {"high": "#FFD700", "medium": "#64B5F6", "low": "#0F2440"}
edu_order = ["high", "medium", "low"]

fig_edu = go.Figure()
for level in edu_order:
 sub = edu_raw[edu_raw["mgmt_education_score"] == level].set_index("category_2024").reindex(present_cats)
 fig_edu.add_trace(go.Bar(
 x=present_cats,
 y=sub["pct"].fillna(0).values,
 name=level.title(),
 marker_color=edu_colors[level],
 text=[f"{v:.0f}%" if pd.notna(v) else "" for v in sub["pct"].values],
 textposition="inside",
 ))

fig_edu.update_layout(
 **CHART_LAYOUT,
 barmode="stack",
 height=320,
 yaxis=dict(title="% of firms", ticksuffix="%"),
 xaxis_title="",
 legend=dict(orientation="h", y=1.08),
)
st.plotly_chart(fig_edu, use_container_width=True)

# ── Chart 3: PhD / Doctor Leadership ─────────────────────────────────────────
st.markdown('<div class="section-label">PhD & Academic Leadership Rate</div>', unsafe_allow_html=True)

col_a, col_b = st.columns(2)

with col_a:
 phd_df = (
 df[df["category_2024"].isin(present_cats)]
 .groupby("category_2024")
 .agg(phd_pct=("has_phd", lambda x: (x == True).mean() * 100),
 n=("has_phd", "count"))
 .reindex(present_cats)
 .reset_index()
 )
 fig_phd = go.Figure([go.Bar(
 x=phd_df["category_2024"],
 y=phd_df["phd_pct"],
 marker_color=[CAT_COLORS.get(c, "#888") for c in phd_df["category_2024"]],
 text=[f"{v:.0f}%" for v in phd_df["phd_pct"]],
 textposition="outside",
 showlegend=False,
 )])
 fig_phd.update_layout(
 **CHART_LAYOUT,
 title="Firms with PhD/Prof in management (%)",
 height=300,
 yaxis=dict(title="%", range=[0, 45]),
 xaxis_title="",
 )
 st.plotly_chart(fig_phd, use_container_width=True)

with col_b:
 # Avg doctors per firm
 doc_df = (
 df[df["category_2024"].isin(present_cats) & df["n_doctors"].notna()]
 .groupby("category_2024")["n_doctors"]
 .mean()
 .reindex(present_cats)
 .reset_index()
 )
 fig_doc = go.Figure([go.Bar(
 x=doc_df["category_2024"],
 y=doc_df["n_doctors"],
 marker_color=[CAT_COLORS.get(c, "#888") for c in doc_df["category_2024"]],
 text=[f"{v:.1f}" for v in doc_df["n_doctors"]],
 textposition="outside",
 showlegend=False,
 )])
 fig_doc.update_layout(
 **CHART_LAYOUT,
 title="Avg. number of Dr./Prof. per firm",
 height=300,
 yaxis=dict(title="avg count"),
 xaxis_title="",
 )
 st.plotly_chart(fig_doc, use_container_width=True)


# ── Chart 4: Financial Resilience — Equity Ratio ─────────────────────────────
st.markdown('<div class="section-label">Financial Resilience — Equity Ratio</div>', unsafe_allow_html=True)

eq_df = df[
 df["category_2024"].isin(present_cats) &
 df["orbis_equity_ratio_latest"].notna() &
 (df["orbis_equity_ratio_latest"] >= 0) # exclude technically insolvent firms from visual
].copy()

fig_eq = px.box(
 eq_df,
 x="category_2024",
 y="orbis_equity_ratio_latest",
 category_orders={"category_2024": present_cats},
 color="category_2024",
 color_discrete_map=CAT_COLORS,
 labels={"orbis_equity_ratio_latest": "Equity ratio (%)", "category_2024": ""},
 points="outliers",
)
fig_eq.update_layout(
 **CHART_LAYOUT,
 height=360,
 showlegend=False,
 yaxis=dict(title="Equity ratio (%)", ticksuffix="%"),
)
# Coverage note
n_eq = {c: int((eq_df["category_2024"] == c).sum()) for c in present_cats}
st.plotly_chart(fig_eq, use_container_width=True)

st.markdown(
 '<div class="insight-card">'
 f"Gazelles carry a median equity ratio of <strong>{gaz_eq:.0f}%</strong> vs "
 f"<strong>{scl_eq:.0f}%</strong> for Scalers. Fast-growing Gazelles tend to be "
 "better self-financed — growing from a strong balance sheet rather than on debt. "
 "Scalers, often larger and older, show more leverage typical of asset-heavy expansion."
 "</div>",
 unsafe_allow_html=True,
)
st.markdown(
 f'<div class="coverage-note">Equity ratio available for: '
 + " · ".join(f"{c}: {n_eq[c]} firms" for c in present_cats if c in n_eq)
 + " (Orbis coverage)</div>",
 unsafe_allow_html=True,
)


# ── Sector leadership: Which sectors attract academic leaders? ────────────────
st.markdown('<div class="section-label">Academic Leadership by Sector (Top 12)</div>', unsafe_allow_html=True)

sector_edu = (
 df[df["has_phd"].notna()]
 .groupby("nace_letter")
 .agg(
 phd_pct=("has_phd", lambda x: (x == True).mean() * 100),
 n_firms=("bvd_id", "count"),
 nace_section=("nace_section", "first"),
 )
 .reset_index()
)
sector_edu = sector_edu[sector_edu["n_firms"] >= 10].nlargest(12, "phd_pct")
sector_edu["label"] = sector_edu["nace_letter"] + " · " + sector_edu["nace_section"].str[:40]

fig_sec = go.Figure([go.Bar(
 y=sector_edu["label"],
 x=sector_edu["phd_pct"],
 orientation="h",
 marker_color="#1E6FD4",
 text=[f"{v:.0f}%" for v in sector_edu["phd_pct"]],
 textposition="outside",
)])
fig_sec.update_layout(
 **CHART_LAYOUT,
 height=420,
 xaxis=dict(title="% of firms with PhD/Prof in management", ticksuffix="%"),
 yaxis=dict(automargin=True),
)
st.plotly_chart(fig_sec, use_container_width=True)
