"""Map page — geocoded firms on a pydeck dark map."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import pydeck as pdk
import streamlit as st

from pipeline.config import load_best_data
from app.components.sidebar_filters import render_sidebar, CATEGORY_COLORS

st.set_page_config(page_title="Map · Düsseldorf Growth", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@600;700&family=Open+Sans:wght@400;600&display=swap');
.stApp { background-color: #2B5354; }
section[data-testid="stSidebar"] { background-color: #244546; }
h1,h2,h3 { font-family: 'Rajdhani', sans-serif !important; color: #F7F8F7 !important; }
p, .stMarkdown { color: #F7F8F7; font-family: 'Open Sans', sans-serif; }
</style>
""", unsafe_allow_html=True)

CATEGORY_RGB = {
    "Gazelle":    [255, 215,   0],
    "Scaler":     [ 85, 142, 143],
    "HighGrowth": [114, 172, 173],
    "Mature":     [154, 176, 176],
    "Other":      [ 80,  80,  80],
}


@st.cache_data
def load_data():
    df = load_best_data()
    has_geo = "lat" in df.columns and df["lat"].notna().any()
    return df, has_geo


df_base, has_geo = load_data()
df_filtered = render_sidebar(df_base)

st.markdown("# 🗺️ Firm Map")

if not has_geo:
    st.warning(
        "No geocoding data yet. Enrich firms with lat/lon columns, "
        "then run `python -m pipeline.import_enriched` to enable the map."
    )
    st.info(f"Showing {len(df_filtered):,} firms — map will appear once addresses are geocoded.")
    st.dataframe(
        df_filtered[["company_name", "category_2024", "nace_letter", "employees_2024"]]
        .sort_values("employees_2024", ascending=False)
        .head(50),
        hide_index=True,
        use_container_width=True,
    )
    st.stop()

df_map = df_filtered[df_filtered["lat"].notna()].copy()

df_map["color"] = df_map["category_2024"].map(CATEGORY_RGB).apply(
    lambda c: c if isinstance(c, list) else [80, 80, 80]
)
df_map["radius"] = (df_map["employees_2024"].fillna(50) / 10).clip(20, 300)
df_map["emp_str"] = df_map["employees_2024"].apply(
    lambda v: f"{int(v):,}" if pd.notna(v) else "n/a"
)

layer = pdk.Layer(
    "ScatterplotLayer",
    data=df_map,
    get_position=["lon", "lat"],
    get_fill_color="color",
    get_radius="radius",
    radius_scale=6,
    pickable=True,
    opacity=0.85,
    stroked=True,
    get_line_color=[247, 248, 247, 60],
    line_width_min_pixels=1,
)

view = pdk.ViewState(
    latitude=51.2217,
    longitude=6.7762,
    zoom=11,
    pitch=0,
)

tooltip = {
    "html": (
        "<b>{company_name}</b><br/>"
        "{category_2024} · {nace_letter}<br/>"
        "Employees: {emp_str}"
    ),
    "style": {
        "backgroundColor": "#244546",
        "color": "#F7F8F7",
        "fontFamily": "Open Sans, sans-serif",
        "fontSize": "12px",
        "padding": "8px 12px",
    },
}

st.pydeck_chart(
    pdk.Deck(
        layers=[layer],
        initial_view_state=view,
        tooltip=tooltip,
        map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
    ),
    use_container_width=True,
    height=560,
)

# Legend
lcols = st.columns(len(CATEGORY_RGB))
for col, (cat, rgb) in zip(lcols, CATEGORY_RGB.items()):
    hex_color = "#{:02x}{:02x}{:02x}".format(*rgb)
    n = int((df_map["category_2024"] == cat).sum())
    col.markdown(
        f'<span style="display:inline-block;width:12px;height:12px;'
        f'background:{hex_color};border-radius:50%;margin-right:6px;"></span>'
        f'<span style="font-size:12px;color:#F7F8F7;">{cat} ({n})</span>',
        unsafe_allow_html=True,
    )

n_missing = df_filtered["lat"].isna().sum() if "lat" in df_filtered.columns else 0
st.caption(f"Showing {len(df_map):,} geocoded firms · {n_missing} without coordinates")
