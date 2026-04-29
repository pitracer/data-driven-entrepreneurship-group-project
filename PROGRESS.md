# Düsseldorf Growth Dashboard — Project Log

> **Last updated:** 2026-04-29
> **Status:** Pipeline complete ✓ | Web dashboard live on Vercel ✓ | All 1,555 firms enriched ✓ | UX fixes deployed ✓

---

## Current state — everything is done

| Layer | Status | Notes |
|-------|--------|-------|
| Raw data cleaning | ✅ | `step_01_clean.py` → `firms_clean.parquet` |
| Serper web enrichment | ✅ | All 1,555 firms cached in `data/cache/serp/` |
| Geocoding | ✅ | Nominatim → lat/lon in `data/cache/geocode/` |
| Groq LLM profiles | ✅ | `step_04` + `step_05` — profiles + sector narratives |
| Signal searches (Serper) | ✅ | 3 queries × 1,555 firms → `data/cache/signal_*/` |
| Signal extraction (Groq) | ✅ | `step_07` → archetypes, scores, boolean signals |
| Clustering | ✅ | `step_08` → `archetype_cluster` + `growth_cluster` for all 1,555 firms |
| Orbis financial data | ✅ | Revenue, profit, equity, management for 1,516 firms |
| Manual data review | ✅ | Adjustments made in `enriched.xlsx` (source of truth) |
| Web export | ✅ | `python -m pipeline.export_web` → `web/public/data/*.json` |
| Streamlit app | ✅ | 7 pages, runs locally (`streamlit run app/Home.py`) |
| Next.js web app | ✅ | 8 pages, deployed on Vercel |

---

## Source of truth: `data/final/enriched.xlsx`

`enriched.xlsx` is the single source of truth. It contains all 1,555 firms with ~119 columns including manual data quality adjustments. The web dashboard and all downstream outputs are generated from this file.

```
enriched.xlsx
    │
    ▼  python -m pipeline.export_web
    ├── web/public/data/firms.json          → Next.js / Vercel (3.5 MB)
    ├── web/public/data/stats.json          → Pre-computed regression
    ├── web/public/data/sector_narratives.json
    └── data/final/firms_enriched.parquet  → Streamlit + pipeline steps
```

To regenerate after any change to `enriched.xlsx`:
```bash
python -m pipeline.export_web
cd web && git add public/data/ && git commit -m "Regenerate web data" && git push
```

---

## Web dashboard

| Page | URL | Status | Notes |
|------|-----|--------|-------|
| Home / KPIs | `/` | ✅ | KPI cards + top-10 job changers |
| Map | `/map` | ✅ | Deck.gl + maplibre-gl; coordinates fixed to 5dp precision; jitter applied for same-address firms |
| Sector Analysis | `/sectors` | ✅ | Employee trend axis fixed (SI labels, starts at 0) |
| Firm Explorer | `/firms` | ✅ | Filterable table + detail panel |
| Leadership | `/leadership` | ✅ | Age (integer), PhD, equity charts all fixed; only Gazelle/Scaler/Other categories exist in data |
| Stats / Regression | `/stats` | ✅ | Correlation matrix label stacking fixed (height=540, tickangle=-45, large margins) |
| Clusters | `/clusters` | ✅ | Archetype + growth strategy charts |
| Chat | `/chat` | ✅ | Groq API, user-provided key; context bumped to 20 firms; prompt clarified |

### 2026-04-29 fixes (round 1)
- `export_web.py`: lat/lon now exported at 5 decimal places (was 2 → ~1km grid artefact)
- `export_web.py`: blank text fields backfilled from `firm_signals.parquet` + `search_results.parquet`
- `DeckMap.tsx`: deterministic jitter (~15m) for firms sharing exact address
- `sectors/page.tsx`: employee trend yaxis — `rangemode: tozero`, `tickformat: ~s`
- `leadership/page.tsx`: equity chart — `tickformat: .1f`, `hoverformat: .1f`
- `api/chat/route.ts`: system prompt reworded; context 12 → 20 firms

### 2026-04-29 fixes (round 2)
- `leadership/page.tsx`: removed non-existent categories `HighGrowth`/`Mature` from charts — data only has `Gazelle`, `Scaler`, `Other`; null traces were breaking Plotly rendering for age + PhD charts
- `leadership/page.tsx`: age + PhD charts switched from 5 separate single-bar traces to one multi-bar trace
- `leadership/page.tsx`: age chart integer formatting (`tickformat: .0f`); PhD chart returns `null` (not `0`) for empty categories to avoid Plotly axis-rescaling bug on data update
- `stats/page.tsx`: correlation matrix `height` passed as prop `height={540}` (was inside layout object, overridden by prop default of 380px); margins l/b=180px; `tickangle=-45`

Deployed on Vercel — see project settings for URL.
Local dev: `cd web && npm run dev` → http://localhost:3000

---

## Enrichment coverage (as of last export)

| Signal | Coverage |
|--------|----------|
| website | ~1,400+ / 1,555 firms |
| address | ~1,400+ / 1,555 firms |
| lat / lon | ~1,300+ / 1,555 firms |
| archetype_cluster | 1,555 / 1,555 |
| growth_cluster | 1,555 / 1,555 |
| has_careers (boolean) | ~154+ firms flagged |
| orbis_revenue_latest | ~1,516 / 1,555 firms |
| profile_text (Groq) | Priority firms only |

---

## Pipeline steps reference

```bash
# Full rebuild from scratch
python -m pipeline.step_01_clean
python -m pipeline.step_02_search --all-firms --no-snippet-filter
python -m pipeline.step_03_geocode
python -m pipeline.step_04_llm_profiles
python -m pipeline.step_05_llm_sectors
python -m pipeline.step_06_signal_search --all-firms
python -m pipeline.step_07_extract_signals --rerun
python -m pipeline.step_08_cluster
python -m pipeline.enrich_batch      # merge everything → enriched.xlsx
python -m pipeline.export_web        # → web/public/data/

# Quick re-export after manual edits to enriched.xlsx
python -m pipeline.export_web
```

---

## Distributed Serper enrichment (how it was done)

Serper rate-limits by IP. The 1,555 firms were split across 3 machines:

| Person | Firms | Command |
|--------|-------|---------|
| Pit | 0–799 | `python -m pipeline.step_02_search --all-firms --no-snippet-filter` |
| Friend B | 800–1179 | `python -m pipeline.step_02_search --all-firms --offset 800 --limit 380 --no-snippet-filter` |
| Friend C | 1180–end | `python -m pipeline.step_02_search --all-firms --offset 1180 --no-snippet-filter` |

Cache files were committed to git so everyone shares enrichment progress without re-spending credits.

---

## Key numbers

- **1,555 unique firms** in Düsseldorf (Orbis/BvD source)
- **40 Gazelles** — grew 20%+ per year, ≤10 years old
- **156 Scalers** — sustained high-growth, any age
- **18 NACE sectors** represented
- Largest employers: Metro AG (87,810), Henkel (47,150), Rheinmetall (28,539)

---

## Narrative: "Hidden Champions vs. Corporate Giants"

**Core thesis:**
Düsseldorf's headline employers (Metro, Henkel, Rheinmetall) lost tens of thousands of jobs since 2017, while 196 firms nobody has heard of — Gazelles and Scalers — quietly added jobs at 20%+ annual rates.

**Dashboard structure:**
1. **Home** — KPIs, category breakdown, top-level story
2. **Map** — geocoded dots, size = employees, color = category
3. **Sectors** — which NACE sections drive growth
4. **Firms** — filterable explorer with AI profiles + financials
5. **Leadership** — manager education, age, PhDs vs. growth
6. **Stats** — logistic regression: what predicts being a Gazelle/Scaler?
7. **Clusters** — AI-classified archetypes + growth strategies
8. **Chat** — ask questions about firms (Groq + keyword search)
