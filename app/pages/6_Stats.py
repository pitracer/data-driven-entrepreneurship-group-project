"""Statistical Analysis — factors explaining why firms scale."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from pipeline.config import load_best_data

st.set_page_config(page_title="Stats · Düsseldorf Growth", layout="wide")

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
.finding-card {
    background: rgba(30,111,212,0.15); border-left: 3px solid #42A5F5;
    border-radius: 0 4px 4px 0; padding: 12px 16px; margin: 8px 0 20px;
    font-size: 13px; color: #F7F8F7; line-height: 1.6;
}
.sig { color: #FFB300; font-weight: 700; }
.insig { color: rgba(247,248,247,.4); }
</style>
""", unsafe_allow_html=True)

CHART_LAYOUT = dict(
    paper_bgcolor="#0F2440",
    plot_bgcolor="rgba(255,255,255,0.04)",
    font=dict(color="#F7F8F7", family="Open Sans"),
    margin=dict(l=10, r=10, t=36, b=10),
)


@st.cache_data
def load_and_prepare():
    df = load_best_data()

    # --- Feature engineering ---
    df["is_growth"] = df["category_2024"].isin(["Gazelle", "Scaler"]).astype(int)
    df["is_gazelle"] = (df["category_2024"] == "Gazelle").astype(int)

    # Growth volatility: std of YoY growth rates 2018-2024
    growth_cols = [f"growth_{y}" for y in range(2018, 2025) if f"growth_{y}" in df.columns]
    df["growth_volatility"] = df[growth_cols].std(axis=1)

    # has_phd_bin for correlation display only (n_doctors used in regression — more granular)
    df["has_phd_bin"] = df["has_phd"].map(
        {True: 1, False: 0, "True": 1, "False": 0}
    ).fillna(0).astype(int)

    # Core regression features — selected to avoid collinearity
    # (edu_high dropped: derived from same Orbis field as n_doctors/has_phd)
    feature_cols = [
        "avg_manager_age",       # Orbis: mean age of named managers
        "n_doctors",             # Orbis: count of Dr./Prof. in management
        "growth_volatility",     # BvD: std of YoY growth 2018-2024
        "orbis_equity_ratio_latest",  # Orbis: equity ratio (optional — reduces sample)
    ]
    return df, feature_cols


df_full, feature_cols = load_and_prepare()

st.markdown("# 📐 What Makes a Firm Scale?")
st.markdown(
    "Logistic regression and correlation analysis identifying which structural factors "
    "— management quality, financial health, sector — predict whether a Düsseldorf firm "
    "becomes a Gazelle or Scaler."
)

# ── Sample size info ──────────────────────────────────────────────────────────
n_growth = int(df_full["is_growth"].sum())
n_total  = len(df_full)
k1, k2, k3 = st.columns(3)
k1.metric("Growth firms (target=1)", n_growth, f"{n_growth/n_total*100:.1f}% of sample")
k2.metric("Non-growth firms (target=0)", n_total - n_growth)
k3.metric("Firms with full Orbis data",
          int(df_full[feature_cols].dropna().shape[0]))

# ── Regression setup ─────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Model — Logistic Regression (Growth vs Non-Growth)</div>',
            unsafe_allow_html=True)

use_equity = st.checkbox("Include equity ratio (reduces sample to ~800 firms)", value=False)

if use_equity:
    features_used = feature_cols
else:
    features_used = [c for c in feature_cols if c != "orbis_equity_ratio_latest"]

# Build model dataset
model_df = df_full[["is_growth"] + features_used].dropna()
X_raw = model_df[features_used].values
y     = model_df["is_growth"].values

st.caption(f"Regression sample: **{len(model_df):,} firms** · Target: Gazelle or Scaler = 1, Other = 0")

try:
    import statsmodels.api as sm
    from sklearn.preprocessing import StandardScaler

    # Standardise for comparable coefficients
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)
    X_sm = sm.add_constant(X_scaled)

    model = sm.Logit(y, X_sm)
    result = model.fit(disp=0)

    # Build results table
    coef_names = ["(intercept)"] + features_used
    pretty_names = {
        "avg_manager_age":          "Manager age (avg)",
        "n_doctors":                "Number of Dr/PhD managers",
        "growth_volatility":        "Growth volatility (σ)",
        "orbis_equity_ratio_latest":"Equity ratio (%)",
        "(intercept)":              "Intercept",
    }

    results_df = pd.DataFrame({
        "Feature":   [pretty_names.get(n, n) for n in coef_names],
        "Coef (std)": result.params.round(3),
        "Odds Ratio": np.exp(result.params).round(3),
        "p-value":   result.pvalues.round(4),
        "Significant": result.pvalues < 0.05,
    })
    results_df = results_df[results_df["Feature"] != "Intercept"].copy()

    # ── Results table ─────────────────────────────────────────────────────────
    def style_row(row):
        color = "rgba(255,179,0,0.15)" if row["Significant"] else ""
        return [f"background-color: {color}"] * len(row)

    st.dataframe(
        results_df.drop(columns="Significant").style.apply(style_row, axis=1),
        hide_index=True,
        use_container_width=True,
    )

    # ── Coefficient plot ──────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Feature Importance (Standardised Coefficients)</div>',
                unsafe_allow_html=True)

    plot_df = results_df.copy()
    plot_df = plot_df.sort_values("Coef (std)")
    colors = ["#FFB300" if s else "#42A5F5" for s in plot_df["Significant"]]
    conf_low  = (result.conf_int()[0][1:]).values
    conf_high = (result.conf_int()[1][1:]).values

    fig_coef = go.Figure()
    fig_coef.add_trace(go.Bar(
        x=plot_df["Coef (std)"],
        y=plot_df["Feature"],
        orientation="h",
        marker_color=colors,
        error_x=dict(
            type="data",
            symmetric=False,
            array=(conf_high - result.params[1:].values)[np.argsort(result.params[1:].values)],
            arrayminus=(result.params[1:].values - conf_low)[np.argsort(result.params[1:].values)],
            color="rgba(247,248,247,0.4)",
            thickness=1.5,
        ),
    ))
    fig_coef.add_vline(x=0, line_color="rgba(247,248,247,0.3)", line_dash="dash")
    fig_coef.update_layout(
        **CHART_LAYOUT,
        height=350,
        xaxis_title="Standardised coefficient (positive = increases odds of scaling)",
        yaxis=dict(automargin=True),
    )
    st.plotly_chart(fig_coef, use_container_width=True)

    # Key finding
    sig_positive = results_df[(results_df["Significant"]) & (results_df["Coef (std)"] > 0)]
    sig_negative = results_df[(results_df["Significant"]) & (results_df["Coef (std)"] < 0)]

    findings = []
    for _, row in sig_positive.iterrows():
        findings.append(f"<b>{row['Feature']}</b> increases scaling odds by {(row['Odds Ratio']-1)*100:.0f}% (p={row['p-value']:.3f})")
    for _, row in sig_negative.iterrows():
        findings.append(f"<b>{row['Feature']}</b> decreases scaling odds (p={row['p-value']:.3f})")

    if findings:
        st.markdown(
            '<div class="finding-card">🔑 <strong>Significant factors:</strong><br>' +
            "<br>".join(findings) + "</div>",
            unsafe_allow_html=True,
        )

    # ── Model fit ─────────────────────────────────────────────────────────────
    st.caption(
        f"Model fit — Log-likelihood: {result.llf:.1f} · "
        f"Pseudo R²: {result.prsquared:.3f} · "
        f"AIC: {result.aic:.1f} · n={len(model_df):,}"
    )

except ImportError:
    st.warning("Install statsmodels: `pip install statsmodels`")
except Exception as e:
    st.error(f"Regression failed: {e}")

# ── Correlation heatmap ───────────────────────────────────────────────────────
st.markdown('<div class="section-label">Feature Correlation Matrix</div>', unsafe_allow_html=True)

corr_features = {
    "is_growth":             "Is Growth Firm",
    "avg_manager_age":       "Manager Age",
    "has_phd_bin":           "PhD in Mgmt",
    "n_doctors":             "# Doctors",
    "growth_volatility":     "Growth Volatility",
    "orbis_equity_ratio_latest": "Equity Ratio",
}
avail = {k: v for k, v in corr_features.items() if k in df_full.columns}
corr_df = df_full[list(avail.keys())].rename(columns=avail).dropna()

corr_matrix = corr_df.corr()

fig_corr = px.imshow(
    corr_matrix,
    color_continuous_scale=[[0, "#0B1F3A"], [0.5, "#0F2440"], [1, "#FFB300"]],
    zmin=-1, zmax=1,
    text_auto=".2f",
)
fig_corr.update_layout(
    **CHART_LAYOUT,
    height=420,
    coloraxis_colorbar=dict(title="r", tickvals=[-1, -0.5, 0, 0.5, 1]),
)
fig_corr.update_traces(textfont=dict(size=11, color="#F7F8F7"))
st.plotly_chart(fig_corr, use_container_width=True)
st.caption(f"Pearson correlation · {len(corr_df):,} firms with complete data")

# ── Distribution comparison ───────────────────────────────────────────────────
st.markdown('<div class="section-label">Distribution Comparison — Growth vs Non-Growth Firms</div>',
            unsafe_allow_html=True)

dist_feature = st.selectbox(
    "Feature to compare",
    options=["avg_manager_age", "n_doctors", "growth_volatility", "orbis_equity_ratio_latest"],
    format_func=lambda x: corr_features.get(x, x),
)

dist_df = df_full[["category_2024", dist_feature, "is_growth"]].dropna()
dist_df["Group"] = dist_df["is_growth"].map({1: "Growth (Gazelle/Scaler)", 0: "Non-Growth"})

fig_dist = px.histogram(
    dist_df,
    x=dist_feature,
    color="Group",
    barmode="overlay",
    opacity=0.7,
    color_discrete_map={"Growth (Gazelle/Scaler)": "#FFB300", "Non-Growth": "#42A5F5"},
    labels={dist_feature: corr_features.get(dist_feature, dist_feature)},
    nbins=30,
)
fig_dist.update_layout(**CHART_LAYOUT, height=320, showlegend=True,
                        legend=dict(orientation="h", y=1.08))
st.plotly_chart(fig_dist, use_container_width=True)

# Mann-Whitney U test
try:
    from scipy import stats as sp_stats
    g1 = dist_df[dist_df["is_growth"] == 1][dist_feature].dropna()
    g0 = dist_df[dist_df["is_growth"] == 0][dist_feature].dropna()
    stat, p = sp_stats.mannwhitneyu(g1, g0, alternative="two-sided")
    sig_str = "✅ statistically significant" if p < 0.05 else "⚠️ not significant"
    st.caption(
        f"Mann-Whitney U test: U={stat:.0f}, p={p:.4f} — "
        f"difference between groups is {sig_str} (α=0.05) · "
        f"Growth firms: n={len(g1)}, Non-growth: n={len(g0)}"
    )
except ImportError:
    pass
