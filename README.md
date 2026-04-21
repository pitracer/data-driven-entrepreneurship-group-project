# Düsseldorf Growth Dashboard

**"Hidden Champions vs. Corporate Giants"** — A data-driven exploration of how unknown mid-sized firms are quietly driving Düsseldorf's job growth while the city's biggest employers shrink.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the cleaning pipeline (XLSX → Parquet)
python -m pipeline.step_01_clean

# 3. Launch the dashboard
streamlit run app/Home.py
```

Or with Docker:
```bash
docker-compose up
# → http://localhost:8501
```

## Project Structure

```
group-assignment/
├── app/
│   ├── Home.py                    # Landing page with KPIs + narrative
│   ├── pages/
│   │   ├── 1_Map.py               # Geocoded firms on pydeck map
│   │   ├── 2_Sector_Analysis.py   # Charts + sector narratives
│   │   ├── 3_Firm_Explorer.py     # Searchable firm table + detail cards
│   │   └── 4_Chat.py              # RAG chatbot (bring your own Groq key)
│   └── components/
│       ├── sidebar_filters.py     # Shared sidebar filters
│       ├── firm_card.py           # Firm detail card component
│       └── chat_engine.py         # FAISS + Groq chat engine
├── pipeline/
│   ├── config.py                  # Paths, API settings, constants
│   ├── step_01_clean.py           # Raw XLSX → firms_clean.parquet
│   ├── enrich_batch.py            # One-command batch enrichment + status
│   ├── enrich_groq.py             # Groq LLM auto-enrich (website/address/snippet)
│   ├── step_02_search.py          # SerpAPI enrichment
│   ├── step_03_geocode.py         # Nominatim geocoding (free)
│   ├── step_04_llm_profiles.py    # Groq company profiles
│   ├── step_05_llm_sectors.py     # Groq sector narratives
│   ├── export_for_enrichment.py   # Export Excel for manual enrichment
│   ├── import_enriched.py         # Import enriched Excel → parquet
│   └── run_pipeline.py            # Orchestrate all pipeline steps
├── data/
│   ├── raw/DUESSELDORF.xlsx       # Source data (BvD)
│   ├── processed/                 # Parquet outputs (gitignored)
│   └── cache/                     # API response cache (COMMITTED to git)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Automated Enrichment (API-based)

The pipeline uses **Groq** (free, 30 req/min) and **SerpAPI** (100 free/month) to enrich firms automatically. All results are cached — re-running never burns an API call twice. The cache is committed to git so teammates share progress.

### Check progress

```bash
python -m pipeline.enrich_batch --status
```

### Run a batch

```bash
# Enrich everything your credits allow
python -m pipeline.enrich_batch

# Or limit to N new API calls per step (safe for free tiers)
python -m pipeline.enrich_batch --limit 20
```

This runs all 5 enrichment steps in sequence:
1. **Groq search** — finds website, address, snippet for each firm via LLM
2. **Rebuild parquet** — consolidates cache into search_results.parquet
3. **Geocode** — converts addresses to lat/lon via Nominatim (free, no key)
4. **LLM profiles** — generates 2-3 sentence company profiles via Groq
5. **Sector narratives** — generates per-sector analysis via Groq
6. **Merge** — combines everything into `firms_enriched.parquet`

---

## Team Enrichment Guide (for teammates)

We need 196 priority firms enriched. Each person's free API credits cover a chunk. The cache is shared via git, so each person picks up where the last one stopped.

### Setup (one-time, ~5 minutes)

```bash
# 1. Clone the repo
git clone git@github.com:pitracer/data-driven-entrepreneurship-group-project.git
cd data-driven-entrepreneurship-group-project

# 2. Create a virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate      # Linux/Mac
# .venv\Scripts\activate       # Windows
pip install -r requirements.txt

# 3. Copy .env.example and add YOUR API keys
cp .env.example .env
# Edit .env with your keys:
#   GROQ_API_KEY=gsk_...       ← get free key at https://console.groq.com
#   SERPAPI_KEY=...             ← optional, get at https://serpapi.com (100 free/month)

# 4. Run the cleaning step (creates the base parquet from raw Excel)
python -m pipeline.step_01_clean
```

### Enrich your batch

```bash
# 5. Check current progress
python -m pipeline.enrich_batch --status

# 6. Run enrichment (uses your free API credits)
python -m pipeline.enrich_batch --limit 30
#    ↑ adjust limit based on your remaining credits
#    Groq free tier: 30 req/min, 14,400/day
#    No limit needed if you have credits to spare: python -m pipeline.enrich_batch

# 7. Commit your cache and push
git add data/cache/
git commit -m "Enrich batch — [YOUR NAME]"
git push origin main
```

### That's it!

The next person pulls, runs `--status` to see progress, then runs their own batch. Repeat until 100%.

### Important notes
- **Always `git pull` before starting** to get the latest cache from others
- **Always `git push` after your batch** so others don't repeat your work
- The `--limit` flag controls new API calls per step, not total firms
- Geocoding (Nominatim) is **free with no key** — it runs automatically
- If you only have a Groq key (no SerpAPI), that's fine — Groq handles the search step too
- The Groq free tier rate-limits at 30 req/min; the pipeline sleeps ~2s between calls to stay safe

---

## Manual Enrichment (via Claude / Perplexity)

Alternative to the API pipeline — useful if APIs are exhausted.

### Step-by-step

```bash
# 1. Export priority firms to Excel
python -m pipeline.export_for_enrichment --priority-only
# → data/processed/firms_for_enrichment_priority.xlsx

# 2. Enrich the Excel using Claude / Perplexity (see prompt below)
#    Save the result as: data/processed/firms_enriched.xlsx

# 3. Import the enriched Excel back into the pipeline
python -m pipeline.import_enriched

# 4. Refresh Streamlit — the dashboard auto-detects enriched data
```

### Enrichment columns

| Column | Description | Example |
|--------|-------------|---------|
| `website` | Company homepage URL | `https://www.deloitte.com/de` |
| `address` | Street address in Düsseldorf | `Schwannstr. 6, 40476 Düsseldorf` |
| `lat` | Latitude (decimal) | `51.2456` |
| `lon` | Longitude (decimal) | `6.7891` |
| `snippet` | 1-2 sentence company description | `Management consulting firm specializing in...` |
| `profile_text` | 3-5 sentence AI-generated company profile | `Deloitte Consulting GmbH is a subsidiary of...` |

### Prompt for Claude / Perplexity

Upload `firms_for_enrichment_priority.xlsx` and use:

```
I have an Excel file with companies based in Düsseldorf, Germany. I need you to research
each company and fill in the empty columns. Here is what each column needs:

- **website**: The company's official homepage URL. If you can't find one, leave it blank.
- **address**: The company's headquarters street address in Düsseldorf.
  Format: "Street Nr, PLZ Düsseldorf" (e.g. "Schwannstr. 6, 40476 Düsseldorf")
- **lat**: Latitude of the address (decimal, e.g. 51.2456). Leave blank if no address found.
- **lon**: Longitude of the address (decimal, e.g. 6.7891). Leave blank if no address found.
- **snippet**: A 1-2 sentence factual description of what the company does.
  Focus on: industry, main products/services, size context.
- **profile_text**: A 3-5 sentence profile covering:
  (1) What the company does
  (2) Why it's notable in Düsseldorf's economy
  (3) Its growth trajectory based on the employee data provided

Important rules:
- Only use publicly available information.
- If you cannot find reliable information for a company, leave the cells blank — do NOT guess.
- Keep the bvd_id column unchanged — it's the unique identifier.
- For lat/lon, use the Düsseldorf office address, not a global HQ elsewhere.
- Return the result as an Excel file with the same structure (all original columns preserved).

The company_name, category_2024, and employees_2024 columns give you context —
Gazelles are young high-growth firms (20%+/yr), Scalers are sustained high-growth firms.

Please process all rows and return the completed Excel.
```

---

## Environment Setup

```bash
# .env file (copy from .env.example)
SERPAPI_KEY=your_key_here      # optional, for SerpAPI enrichment
GROQ_API_KEY=your_key_here     # required for Groq enrichment + profiles
```

The dashboard's Chat page uses a **user-provided Groq key** (entered in the sidebar at runtime), so no server-side key is needed for the chatbot.

## Key Definitions

| Term | Definition |
|------|-----------|
| **Scaler** | Avg annualized growth >10% over 3 years, >=10 employees at start |
| **High-Growth Firm** | Avg annualized growth >20% over 3 years, >=10 employees |
| **Gazelle** | Consistent HGF that is <=10 years old |
| **Mature HGF** | Consistent HGF that is >10 years old |
