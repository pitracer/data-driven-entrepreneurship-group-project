"""
RAG chat engine — FAISS retrieval + Groq generation.

Build an index from enriched firm data (name + category + sector +
employees + snippet + AI profile). At query time retrieve top-k
firms and feed them as context to Groq.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st
from groq import Groq

try:
    import faiss
    from sentence_transformers import SentenceTransformer
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False


EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
GROQ_MODEL = "llama-3.3-70b-versatile"
TOP_K = 5


def _firm_text(row: pd.Series) -> str:
    """Build a text representation of a firm for embedding."""
    parts = [
        row.get("company_name", ""),
        f"Category: {row.get('category_2024', '')}",
        f"Sector: {row.get('nace_section', '')}",
        f"Employees 2024: {row.get('employees_2024', 'unknown')}",
    ]
    if pd.notna(row.get("snippet")):
        parts.append(f"Description: {row['snippet']}")
    if pd.notna(row.get("profile_text")):
        parts.append(f"Profile: {row['profile_text']}")
    return " | ".join(str(p) for p in parts if p)


@st.cache_resource(show_spinner="Building search index...")
def build_index(df_firms: pd.DataFrame) -> tuple:
    """Build FAISS index over firm texts. Returns (index, df, model)."""
    if not FAISS_AVAILABLE:
        return None, df_firms, None

    df = df_firms.copy()
    model = SentenceTransformer(EMBED_MODEL)
    texts = df.apply(_firm_text, axis=1).tolist()
    embeddings = model.encode(texts, show_progress_bar=False).astype("float32")

    faiss.normalize_L2(embeddings)
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    return index, df, model


def retrieve(query: str, index, df: pd.DataFrame, model, k: int = TOP_K) -> pd.DataFrame:
    """Return top-k most relevant firms for a query."""
    if index is None or model is None:
        # Fallback: keyword matching
        mask = df["company_name"].str.contains(query, case=False, na=False)
        return df[mask].head(k) if mask.any() else df.head(k)

    q_emb = model.encode([query]).astype("float32")
    faiss.normalize_L2(q_emb)
    _, indices = index.search(q_emb, k)
    return df.iloc[indices[0]].copy()


def build_context(relevant: pd.DataFrame) -> str:
    lines = []
    for _, row in relevant.iterrows():
        emp = row.get("employees_2024")
        emp_str = f"{int(emp):,}" if pd.notna(emp) else "n/a"
        pct = row.get("employee_change_pct")
        pct_str = f"{pct:+.1%}" if pd.notna(pct) else "n/a"
        profile = row.get("profile_text") or row.get("snippet") or ""
        lines.append(
            f"• {row['company_name']} ({row.get('category_2024','?')}): "
            f"{emp_str} employees, growth {pct_str}. {profile}"
        )
    return "\n".join(lines)


def chat(
    api_key: str,
    messages: list[dict],
    index,
    df: pd.DataFrame,
    model,
) -> tuple[str, pd.DataFrame]:
    """Run one chat turn. Returns (answer, retrieved_firms)."""
    user_query = messages[-1]["content"]
    relevant = retrieve(user_query, index, df, model)
    context = build_context(relevant)

    system = (
        "You are a data analyst specializing in Düsseldorf's business landscape. "
        "Answer questions using the firm data below. Be concise and cite specific numbers.\n\n"
        f"Relevant firms:\n{context}\n\n"
        "Dataset overview: 1,555 firms in Düsseldorf, including 40 Gazelles (20%+/year growth) "
        "and 156 Scalers (sustained high growth)."
    )

    client = Groq(api_key=api_key)
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "system", "content": system}] + messages,
        temperature=0.3,
        max_tokens=600,
    )
    return resp.choices[0].message.content, relevant
