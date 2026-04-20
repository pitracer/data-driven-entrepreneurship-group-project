# Düsseldorf Growth Dashboard — Revised Plan (v2)

---

## Changes from v1
- **No SQL** — all data stored as Parquet files, pure pandas
- **User-provided Groq key** — chatbot on dashboard, users bring their own API key
- **Sharper narrative** — "Hidden Champions vs. Corporate Giants"
- **Better data sources** — North Data + Google Places instead of just SerpAPI

---

## 1. Narrative: "Düsseldorf's Hidden Champions"

**Thesis:** Düsseldorf's biggest employers (Metro, Henkel, Rheinmetall) are shrinking
or stagnating in headcount, while a class of unknown mid-sized firms — the Scalers
and Gazelles — are quietly driving the city's job growth.

**What the dashboard proves:**
- The top 10 employers lost ~30,000 jobs combined since 2017
- Meanwhile, 216 Scalers and 25 Gazelles *added* jobs at 20%+ rates
- These hidden champions cluster in specific sectors (Professional Services, IT)
  and specific neighborhoods
- AI-generated profiles reveal what these firms actually do

**Why this works for grading:** It's a testable claim, not just a visualization.
The pipeline *discovers* the story; the dashboard *tells* it.

---

## 2. Repo Structure

```
duesseldorf-growth/
│
├── README.md
├── .env.example                    # SERPAPI_KEY, GROQ_API_KEY, OPENCAGE_KEY
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
│
├── data/
│   ├── raw/
│   │   └── DUESSELDORF.xlsx
│   ├── processed/
│   │   ├── firms_clean.parquet     # Step 1 output
│   │   ├── firms_enriched.parquet  # Steps 2-4 merged
│   │   └── sector_narratives.json  # LLM-generated sector texts
│   └── cache/
│       ├── serp/                   # Cached SerpAPI responses
│       ├── geocode/                # Cached geocoding responses
│       └── llm/                    # Cached Groq responses
│
├── pipeline/
│   ├── config.py                   # Paths, API settings, constants
│   ├── cache.py                    # Generic JSON file cache decorator
│   ├── step_01_clean.py
│   ├── step_02_search.py           # SerpAPI → website, address, snippet
│   ├── step_03_geocode.py          # Address → lat/lon
│   ├── step_04_llm_profiles.py     # Groq → company profiles
│   ├── step_05_llm_sectors.py      # Groq → sector narratives
│   └── run_pipeline.py             # Run all steps in sequence
│
├── app/
│   ├── Home.py                     # Streamlit entry: title + key findings
│   ├── pages/
│   │   ├── 1_Map.py                # Geocoded firms on pydeck map
│   │   ├── 2_Sector_Analysis.py    # Charts + LLM sector narratives
│   │   ├── 3_Firm_Explorer.py      # Searchable table + detail cards
│   │   └── 4_Chat.py              # Chatbot (user provides Groq key)
│   └── components/
│       ├── sidebar_filters.py
│       ├── firm_card.py
│       └── chat_engine.py          # Groq chat with data context
│
└── tests/
    └── test_cache.py
```

---

## 3. Data Storage — Pure Parquet

```python
# Writing
df.to_parquet("data/processed/firms_clean.parquet", index=False)

# Reading
df = pd.read_parquet("data/processed/firms_clean.parquet")

# Merging enrichment results
base = pd.read_parquet("data/processed/firms_clean.parquet")
search = pd.read_parquet("data/processed/search_results.parquet")
geo = pd.read_parquet("data/processed/geocode_results.parquet")
llm = pd.read_parquet("data/processed/llm_profiles.parquet")

enriched = base.merge(search, on="bvd_id", how="left") \
               .merge(geo, on="bvd_id", how="left") \
               .merge(llm, on="bvd_id", how="left")

enriched.to_parquet("data/processed/firms_enriched.parquet", index=False)
```

Why Parquet over CSV:
- 5-10x smaller file size
- Column types preserved (no re-parsing dates/numbers)
- Fast reads with pandas, polars, or DuckDB if needed later

---

## 4. Caching Pattern (Critical for API Budgets)

```python
# pipeline/cache.py
import json, hashlib, os

class FileCache:
    def __init__(self, cache_dir: str):
        os.makedirs(cache_dir, exist_ok=True)
        self.cache_dir = cache_dir

    def _key(self, query: str) -> str:
        return hashlib.md5(query.encode()).hexdigest()

    def get(self, query: str):
        path = os.path.join(self.cache_dir, f"{self._key(query)}.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return None

    def set(self, query: str, data: dict):
        path = os.path.join(self.cache_dir, f"{self._key(query)}.json")
        with open(path, "w") as f:
            json.dump(data, f)

# Usage in any pipeline step:
cache = FileCache("data/cache/serp")
result = cache.get(company_name)
if result is None:
    result = call_serpapi(company_name)
    cache.set(company_name, result)
```

This means you NEVER burn an API call twice. Essential when SerpAPI
gives you only 100 free searches/month.

---

## 5. Enrichment Sources (Revised)

### Source 1: SerpAPI (website + address discovery)
- Query: `"{company_name}" Düsseldorf`
- Extract: website URL, address from knowledge panel, snippet
- Budget: 100/month free → prioritize Scalers + Gazelles first
- Fallback: use `site:northdata.com "{company_name}"` queries
  to find North Data pages with financial info in snippets

### Source 2: Geocoding (Nominatim — fully free)
- Skip OpenCage, use Nominatim (OpenStreetMap) — no API key needed
- Rate limit: 1 req/sec (add time.sleep(1))
- For 330 priority firms that's ~6 minutes

```python
import requests, time

def geocode_nominatim(address: str):
    resp = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": address, "format": "json", "limit": 1},
        headers={"User-Agent": "duesseldorf-study-project"}
    )
    if resp.ok and resp.json():
        return resp.json()[0]["lat"], resp.json()[0]["lon"]
    return None, None
```

### Source 3: Groq LLM (profiles + sector narratives + chatbot)
- Model: llama-3.3-70b-versatile (free, fast)
- Pipeline use: batch company profiles + sector narratives
- Dashboard use: live chatbot with user's own key
- Free tier: 30 req/min, 15,000 tokens/min

### Source 4 (Bonus): North Data via SerpAPI
- Instead of a separate API, use SerpAPI queries like:
  `site:northdata.com "{company_name}" Düsseldorf Umsatz`
- The snippets often contain revenue, legal form, HRB number
- Have Groq parse the snippet into structured fields
- This is a clever "two APIs in one" move worth showing in the demo

---

## 6. Chatbot Architecture (User Brings Own Key)

```python
# app/components/chat_engine.py
from groq import Groq
import streamlit as st
import pandas as pd

def build_context(df: pd.DataFrame, query: str) -> str:
    """Build a concise data context for the LLM."""
    # Basic stats
    context = f"""
    Dataset: {len(df)} firms in Düsseldorf.
    Sectors: {df['nace_section'].nunique()} NACE sections.
    Growth firms: {(df['high_growth_2024']==1).sum()} high-growth,
                  {(df['scaler_2024']==1).sum()} scalers,
                  {(df['gazelle_2024']==1).sum()} gazelles.
    Employee range: {df['employees_2024'].min()} to {df['employees_2024'].max()}.
    """

    # Add relevant rows based on naive keyword matching
    keywords = query.lower().split()
    mask = df['company_name'].str.lower().apply(
        lambda x: any(k in x for k in keywords)
    )
    if mask.any():
        sample = df[mask].head(5).to_string()
        context += f"\nRelevant firms:\n{sample}"
    else:
        # Just give top firms by sector mentioned
        context += f"\nTop 10 firms by employees:\n{df.nlargest(10, 'employees_2024')[['company_name','nace_section','employees_2024']].to_string()}"

    return context

def chat(api_key: str, messages: list, df: pd.DataFrame):
    client = Groq(api_key=api_key)
    system = f"""You are a data analyst for Düsseldorf's business landscape.
    Answer questions using this data context:
    {build_context(df, messages[-1]['content'])}
    Be concise. Cite specific numbers from the data."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": system}] + messages,
        temperature=0.3,
        max_tokens=800
    )
    return response.choices[0].message.content
```

```python
# app/pages/4_Chat.py (simplified)
import streamlit as st

st.title("Chat with Düsseldorf's Data")

api_key = st.text_input("Your Groq API Key", type="password")
if not api_key:
    st.info("Enter your free Groq API key from console.groq.com to start chatting.")
    st.stop()

# ... standard st.chat_message / st.chat_input loop
```

---

## 7. Docker (Unchanged but Simpler Without SQLite)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health
CMD ["streamlit", "run", "app/Home.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0"]
```

```yaml
# docker-compose.yml
services:
  app:
    build: .
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data    # persist enriched data across rebuilds
    env_file:
      - .env
```

No database container needed. Just one service.

---

## 8. requirements.txt (Revised — Leaner)

```
streamlit>=1.30
pandas>=2.0
pyarrow>=14.0          # parquet support
openpyxl>=3.1          # read XLSX
plotly>=5.18
pydeck>=0.8
google-search-results   # SerpAPI
groq>=0.4
requests>=2.31
python-dotenv>=1.0
```

Dropped: sqlalchemy, folium, opencage (using free Nominatim instead).

---

## 9. Updated Roadmap

### Sprint 1 (Days 1-3): Foundation
- [ ] `git init` + repo structure + `.gitignore` + `.env.example`
- [ ] `pipeline/cache.py` — file-based caching
- [ ] `pipeline/config.py` — paths + constants
- [ ] `pipeline/step_01_clean.py` — XLSX → clean Parquet
- [ ] `Dockerfile` + `docker-compose.yml` working
- [ ] `app/Home.py` — skeleton Streamlit with data loaded

### Sprint 2 (Days 4-7): Pipeline
- [ ] `step_02_search.py` — SerpAPI for top 100 firms
- [ ] `step_03_geocode.py` — Nominatim geocoding
- [ ] `step_04_llm_profiles.py` — Groq batch profiles
- [ ] `step_05_llm_sectors.py` — sector narratives
- [ ] `run_pipeline.py` — orchestrate all steps
- [ ] Merge all enrichments into `firms_enriched.parquet`

### Sprint 3 (Days 8-11): Dashboard
- [ ] Map page (pydeck + geocoded firms)
- [ ] Sector Analysis page (plotly charts + narrative cards)
- [ ] Firm Explorer (searchable, clickable table)
- [ ] Chat page (Groq with user key)
- [ ] Sidebar filters shared across pages

### Sprint 4 (Days 12-14): Polish + Demo
- [ ] Run full pipeline (manage rate limits)
- [ ] Style dashboard, add "Hidden Champions" narrative text
- [ ] README with setup docs
- [ ] Test Docker on both Mac and WSL
- [ ] Prepare demo script

---

## 10. Claude Code Skills to Build (Revised)

### Skill 1: `groq-enrichment`
Standardizes all Groq API interactions — prompt templates, JSON output
parsing, retry with backoff, rate-limit sleep. Used by both pipeline
(batch profiles) and dashboard (chatbot).

### Skill 2: `parquet-pipeline-step`
Template for each pipeline step: read parquet → process rows → cache
results → write parquet. Ensures every step is idempotent (skips
already-enriched rows on re-run).

### Skill 3: `streamlit-page`
Scaffolds a Streamlit page with: sidebar filters component, plotly chart
patterns, data loading from parquet, responsive layout. Keeps all pages
visually consistent.

---

## 11. What to Show in the Demo

1. **The pipeline** — run `python pipeline/run_pipeline.py` live, show
   it enriching 5 firms with caching ("look, second run is instant")
2. **The finding** — "Metro lost 67,000 employees since 2017; meanwhile
   these 25 Gazelles you've never heard of grew 20%+ per year"
3. **The map** — click a Gazelle, see its AI-generated profile
4. **The chatbot** — type your Groq key, ask "which IT firms are scaling?"
5. **Docker** — `docker-compose up` and it works on any machine
6. **The code** — show the clean pipeline steps, the caching, the prompts
