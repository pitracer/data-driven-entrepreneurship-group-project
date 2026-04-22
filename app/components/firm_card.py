"""Firm detail card component."""
from __future__ import annotations

import pandas as pd
import streamlit as st

CATEGORY_BADGE = {
    "Gazelle":    ("🦌", "#FFD700", "#1A1A00"),
    "Scaler":     ("📈", "#1E6FD4", "#F7F8F7"),
    "HighGrowth": ("🚀", "#64B5F6", "#F7F8F7"),
    "Mature":     ("🏛️",  "#78909C", "#1A3334"),
    "Other":      ("·",  "#444",    "#F7F8F7"),
}


def render_firm_card(
    firm: pd.Series,
    profile_text: str | None = None,
    website: str | None = None,
    expanded: bool = False,
) -> None:
    cat = firm.get("category_2024", "Other")
    icon, bg, fg = CATEGORY_BADGE.get(cat, CATEGORY_BADGE["Other"])
    emp = firm.get("employees_2024")
    emp_str = f"{int(emp):,}" if pd.notna(emp) else "n/a"
    pct = firm.get("employee_change_pct")
    pct_str = f"{pct:+.1%}" if pd.notna(pct) else "n/a"
    pct_color = "#4CAF50" if (pd.notna(pct) and pct > 0) else "#EF5350"

    label = f"{icon} {firm['company_name']}"
    with st.expander(label, expanded=expanded):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                f'<span style="background:{bg};color:{fg};padding:3px 10px;'
                f'border-radius:4px;font-size:11px;font-weight:700;'
                f'text-transform:uppercase;letter-spacing:.08em;">{cat}</span>',
                unsafe_allow_html=True,
            )
        with col2:
            st.metric("Employees 2024", emp_str)
        with col3:
            st.markdown(
                f'<div style="font-size:11px;color:rgba(247,248,247,.6);'
                f'text-transform:uppercase;letter-spacing:.08em;">Growth</div>'
                f'<div style="font-size:22px;font-weight:700;color:{pct_color};">'
                f'{pct_str}</div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            f"**Sector:** {firm.get('nace_section', 'Unknown')}  \n"
            f"**NACE code:** {firm.get('nace_code', 'n/a')}  \n"
            f"**Founded:** {firm.get('founded_year', 'n/a')}"
        )

        if profile_text:
            st.markdown(
                f'<div style="background:rgba(255,255,255,0.04);border-left:3px solid #1E6FD4;'
                f'padding:12px 16px;border-radius:0 4px 4px 0;margin-top:8px;'
                f'font-size:13px;color:#F7F8F7;">{profile_text}</div>',
                unsafe_allow_html=True,
            )

        # Financial data from Orbis
        rev = firm.get("orbis_revenue_latest")
        profit = firm.get("orbis_profit_latest")
        if pd.notna(rev) or pd.notna(profit):
            fcols = st.columns(2)
            with fcols[0]:
                if pd.notna(rev):
                    rev_m = rev / 1000
                    st.metric("Revenue (M EUR)", f"{rev_m:,.0f}")
            with fcols[1]:
                if pd.notna(profit):
                    profit_m = profit / 1000
                    st.metric("Profit before tax (M EUR)", f"{profit_m:,.0f}")

        # Management education
        edu_score = firm.get("mgmt_education_score")
        if pd.notna(edu_score) and edu_score != "low":
            n_mgr = firm.get("n_managers", 0)
            n_doc = firm.get("n_doctors", 0)
            has_prof = firm.get("has_professor", False)
            badges = []
            if has_prof:
                badges.append("Prof.")
            if n_doc > 0:
                badges.append(f"{int(n_doc)} Dr./PhD")
            badge_str = " · ".join(badges) if badges else edu_score.title()
            color = "#FFD700" if edu_score == "high" else "#64B5F6"
            st.markdown(
                f'<span style="background:{color};color:#1A1A00;padding:2px 8px;'
                f'border-radius:3px;font-size:11px;font-weight:600;">'
                f'Mgmt: {badge_str}</span>'
                f' <span style="font-size:11px;color:rgba(247,248,247,.5);">'
                f'{int(n_mgr)} managers</span>',
                unsafe_allow_html=True,
            )

        if website and pd.notna(website):
            st.markdown(f"🌐 [{website}]({website})")
