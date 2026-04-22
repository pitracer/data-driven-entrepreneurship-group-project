"""Chat page — RAG chatbot powered by FAISS + Groq."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st

from pipeline.config import load_best_data
from app.components.chat_engine import build_index, chat

st.set_page_config(page_title="Chat · Düsseldorf Growth", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@600;700&family=Open+Sans:wght@400;600&display=swap');
.stApp { background-color: #0B1F3A; }
section[data-testid="stSidebar"] { background-color: #071629; }
h1,h2,h3 { font-family: 'Rajdhani', sans-serif !important; color: #F7F8F7 !important; }
p, .stMarkdown { color: #F7F8F7; font-family: 'Open Sans', sans-serif; }
.sources-box {
    background: rgba(255,255,255,0.04); border-radius: 4px;
    padding: 8px 12px; margin-top: 6px; font-size: 11px;
    color: rgba(247,248,247,.6);
}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    try:
        return load_best_data()
    except FileNotFoundError:
        return None


# ── Sidebar: API key ──────────────────────────────────────────────────────────
st.sidebar.markdown(
    '<p style="font-family:Rajdhani,sans-serif;font-size:18px;'
    'font-weight:700;color:#F7F8F7;">Chat Setup</p>',
    unsafe_allow_html=True,
)
api_key = st.sidebar.text_input(
    "Groq API Key",
    type="password",
    placeholder="gsk_...",
    help="Free key at console.groq.com",
)
st.sidebar.caption("Your key is never stored — used only for this session.")
st.sidebar.divider()
st.sidebar.markdown(
    "**Suggested questions:**\n"
    "- Which IT firms are scaling fastest?\n"
    "- What are the top Gazelles by employee count?\n"
    "- Which sectors have the most hidden champions?\n"
    "- How does Metro compare to the Gazelles?"
)

# ── Main ─────────────────────────────────────────────────────────────────────
st.markdown("#  Chat with Düsseldorf's Data")

if not api_key:
    st.info(
        "Enter your free Groq API key in the sidebar to start chatting. "
        "Get one at [console.groq.com](https://console.groq.com) — it takes 30 seconds."
    )
    st.stop()

df = load_data()

if df is None:
    st.error("No data found. Run the pipeline first.")
    st.stop()

index, df_merged, model = build_index(df)

# ── Chat loop ─────────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            st.markdown(
                '<div class="sources-box"> Sources: '
                + " · ".join(msg["sources"])
                + "</div>",
                unsafe_allow_html=True,
            )

if prompt := st.chat_input("Ask about Düsseldorf's firms…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching firms…"):
            try:
                answer, relevant = chat(
                    api_key=api_key,
                    messages=st.session_state.messages,
                    index=index,
                    df=df_merged,
                    model=model,
                )
                source_names = relevant["company_name"].str.slice(0, 30).tolist()
            except Exception as e:
                answer = f"Sorry, something went wrong: {e}"
                source_names = []

        st.markdown(answer)
        if source_names:
            st.markdown(
                '<div class="sources-box"> Sources: '
                + " · ".join(source_names)
                + "</div>",
                unsafe_allow_html=True,
            )

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": source_names,
    })
