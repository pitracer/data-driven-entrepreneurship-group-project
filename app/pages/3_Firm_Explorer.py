"""Firm Explorer — searchable table + detail cards."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st

from pipeline.config import load_best_data
from app.components.sidebar_filters import render_sidebar
from app.components.firm_card import render_firm_card

st.set_page_config(page_title="Firm Explorer · Düsseldorf Growth", layout="wide")

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
 padding-bottom: 8px; margin: 20px 0 12px;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
 return load_best_data()


df_base = load_data()
df_filtered = render_sidebar(df_base)

st.markdown("# Firm Explorer")

# ── Search & sort ─────────────────────────────────────────────────────────────
col_search, col_sort = st.columns([3, 1])
with col_search:
 search = st.text_input("Search company name", placeholder="e.g. Deloitte, Amazon, MVISE...")
with col_sort:
 sort_options = ["employees_2024", "growth_2024", "company_name"]
 if "orbis_revenue_latest" in df_filtered.columns:
 sort_options.insert(1, "orbis_revenue_latest")
 sort_col = st.selectbox("Sort by", sort_options, index=0)

if search:
 df_filtered = df_filtered[
 df_filtered["company_name"].str.contains(search, case=False, na=False)
 ]

ascending = sort_col == "company_name"
df_filtered = df_filtered.sort_values(sort_col, ascending=ascending, na_position="last")

# ── Table ─────────────────────────────────────────────────────────────────────
st.markdown(
 f'<div class="section-label">{len(df_filtered):,} firms</div>',
 unsafe_allow_html=True,
)

display_cols = {
 "company_name": "Company",
 "category_2024": "Category",
 "nace_letter": "NACE",
 "employees_2024": "Employees 2024",
 "growth_2024": "Growth 2024",
 "employee_change_pct": "Change vs baseline",
 "orbis_revenue_latest": "Revenue (k EUR)",
 "mgmt_education_score": "Mgmt Education",
}
available = [c for c in display_cols if c in df_filtered.columns]

df_display = df_filtered[available].copy()
df_display = df_display.rename(columns=display_cols)

# Format percentages
for col in ["Growth 2024", "Change vs baseline"]:
 if col in df_display.columns:
 df_display[col] = df_display[col].apply(
 lambda v: f"{v:+.1%}" if pd.notna(v) else "n/a"
 )

if "Revenue (k EUR)" in df_display.columns:
 df_display["Revenue (k EUR)"] = df_display["Revenue (k EUR)"].apply(
 lambda v: f"{v:,.0f}" if pd.notna(v) else ""
 )

event = st.dataframe(
 df_display.head(200),
 hide_index=True,
 use_container_width=True,
 on_select="rerun",
 selection_mode="single-row",
)

# ── Detail card ───────────────────────────────────────────────────────────────
selected_rows = event.selection.get("rows", [])
if selected_rows:
 idx = selected_rows[0]
 firm = df_filtered.iloc[idx]
 st.markdown('<div class="section-label">Firm Detail</div>', unsafe_allow_html=True)
 render_firm_card(
 firm=firm,
 profile_text=firm.get("profile_text") if "profile_text" in firm.index else None,
 website=firm.get("website") if "website" in firm.index else None,
 expanded=True,
 )
