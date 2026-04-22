"""Shared sidebar filters — import and call render_sidebar() on every page."""
from __future__ import annotations

import pandas as pd
import streamlit as st


CATEGORY_COLORS = {
 "Gazelle": "#FFD700",
 "Scaler": "#1E6FD4",
 "HighGrowth": "#64B5F6",
 "Mature": "#78909C",
 "Other": "#555555",
}


def render_sidebar(df: pd.DataFrame) -> pd.DataFrame:
 """Render sidebar filters and return filtered DataFrame."""
 st.sidebar.markdown(
 '<p style="font-family:Rajdhani,sans-serif;font-size:18px;'
 'font-weight:700;color:#F7F8F7;letter-spacing:.05em;">'
 "Düsseldorf Growth</p>",
 unsafe_allow_html=True,
 )
 st.sidebar.markdown(
 '<p style="font-size:11px;color:rgba(247,248,247,.5);'
 'text-transform:uppercase;letter-spacing:.1em;">Hidden Champions Dashboard</p>',
 unsafe_allow_html=True,
 )
 st.sidebar.divider()

 # Category filter
 all_cats = sorted(df["category_2024"].unique().tolist())
 selected_cats = st.sidebar.multiselect(
 "Firm Category",
 options=all_cats,
 default=all_cats,
 key="filter_category",
 )

 # NACE section filter
 all_sectors = sorted(df["nace_letter"].dropna().unique().tolist())
 selected_sectors = st.sidebar.multiselect(
 "NACE Sector",
 options=all_sectors,
 default=all_sectors,
 key="filter_sector",
 help="Single-letter NACE classification",
 )

 # Employee size filter
 max_emp = int(df["employees_2024"].max()) if df["employees_2024"].notna().any() else 1000
 min_emp = st.sidebar.slider(
 "Min. Employees (2024)",
 min_value=0,
 max_value=min(max_emp, 500),
 value=0,
 step=10,
 key="filter_min_emp",
 )

 # Priority only toggle
 priority_only = st.sidebar.checkbox("Priority firms only", value=False, key="filter_priority")

 st.sidebar.divider()
 st.sidebar.caption("Data: BvD / Bureau van Dijk · Enriched via SerpAPI + Groq")
 st.sidebar.markdown("<div style='margin-top:auto;'></div>", unsafe_allow_html=True)
 st.sidebar.page_link("pages/5_Chat.py", label=" Ask the Data", help="Chat with the dataset using AI")

 # Apply filters
 mask = (
 df["category_2024"].isin(selected_cats)
 & df["nace_letter"].isin(selected_sectors)
 & (df["employees_2024"].fillna(0) >= min_emp)
 )
 if priority_only:
 mask = mask & df["priority_enrich"]

 return df[mask].copy()
