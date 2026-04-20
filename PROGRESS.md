# Düsseldorf Growth Dashboard — Project Log

> **Last updated:** 2026-04-21  
> **Status:** Sprint 1 complete ✓ | Sprint 2 in progress (enrichment 40/196)

---

## Quick-start (pick up where we left off)

```bash
cd "group-assignment"

# Check enrichment progress
python -m pipeline.enrich_manual status

# Export next batch of 20 firms → paste into Claude.ai → save reply → import
python -m pipeline.enrich_manual export --batch 20
python -m pipeline.enrich_manual import --file response.json

# After all 196 firms are cached, rebuild parquet
python -m pipeline.step_02_search --limit 0

# Then run geocoding (no API key needed, ~6 min)
python -m pipeline.step_03_geocode

# Then LLM profiles via Groq
python -m pipeline.step_04_llm_profiles
python -m pipeline.step_05_llm_sectors

# Launch dashboard
streamlit run app/Home.py
```

---

## What exists right now

### Pipeline files
| File | Status | What it does |
|------|--------|-------------|
| `pipeline/config.py` | ✅ Done | All paths, API keys, column mappings |
| `pipeline/cache.py` | ✅ Done | File-based JSON cache (atomic writes) |
| `pipeline/step_01_clean.py` | ✅ Done | XLSX → `firms_clean.parquet` |
| `pipeline/step_02_search.py` | ✅ Done | SerpAPI → website, address, snippet |
| `pipeline/enrich_manual.py` | ✅ Done | Semi-manual enrichment via LLM chat |
| `pipeline/step_03_geocode.py` | ❌ Not built | Address → lat/lon (Nominatim) |
| `pipeline/step_04_llm_profiles.py` | ❌ Not built | Groq → company profiles |
| `pipeline/step_05_llm_sectors.py` | ❌ Not built | Groq → sector narratives |
| `pipeline/run_pipeline.py` | ❌ Not built | Orchestrate all steps |

### Data files
| File | Status | Contents |
|------|--------|---------|
| `data/raw/DUESSELDORF.xlsx` | ✅ | 1,886 raw rows (source) |
| `data/processed/firms_clean.parquet` | ✅ | 1,555 unique firms, 71 columns |
| `data/cache/serp/` | 🔄 40/196 | SerpAPI + manual enrichment cache |
| `data/processed/search_results.parquet` | 🔄 Partial | Rebuilt after enrichment is complete |

### App files
| File | Status |
|------|--------|
| `app/Home.py` | ❌ Not built |
| `app/pages/1_Map.py` | ❌ Not built |
| `app/pages/2_Sector_Analysis.py` | ❌ Not built |
| `app/pages/3_Firm_Explorer.py` | ❌ Not built |
| `app/pages/4_Chat.py` | ❌ Not built |

---

## Data & key numbers (firms_clean.parquet)

- **1,555 unique firms** in Düsseldorf
- **40 Gazelles** — grew 20%+ per year, young firms (the stars of the story)
- **156 Scalers** — sustained high-growth (supporting cast)
- **196 priority firms** → to be fully enriched (website, address, AI profile)
- **18 NACE sectors** represented
- **471 firms** have 2017 employee baseline (full historical range)
- Largest employers: Metro AG (87,810), Henkel (47,150), Rheinmetall (28,539)

---

## Enrichment status

| Source | Method | Status |
|--------|--------|--------|
| SerpAPI (35 calls) | Automated | ✅ Done |
| Manual batch (Claude/ChatGPT) | Semi-auto via `enrich_manual.py` | 🔄 156 remaining |
| Nominatim geocoding | Automated, free | ❌ Pending step_03 |
| Groq LLM profiles | Automated | ❌ Pending step_04 |

**SerpAPI budget remaining:** ~60 calls (100 free/month − 40 used)

---

## Narrative: "Düsseldorf's Hidden Champions"

**Core thesis:**  
Düsseldorf's headline employers (Metro, Henkel, Rheinmetall) lost tens of thousands of jobs since 2017, while 196 firms nobody has heard of — Gazelles and Scalers — quietly added jobs at 20%+ annual rates.

**Three-act structure for the demo:**
1. **Act 1 — The Giants are shrinking** → employee trend chart, top 10 employers
2. **Act 2 — The Hidden Champions** → map of Gazelles, sector breakdown
3. **Act 3 — What are they?** → AI-generated profiles, chatbot

**Sectors to watch:** Professional Services, IT/Tech, Healthcare (early signal from NACE distribution)

---

## Style reference

Fonts: **Rajdhani** (headings) + **Open Sans** (body)  
Colors: `#2B5354` bg · `#355E5F` cards · `#558E8F` accent · `#F7F8F7` text  
Source: `../01 Individual Assignemnt/index.html`

---

## Next session: pick up here

1. Finish manual enrichment batches (`enrich_manual export/import` ×8)
2. Build `step_03_geocode.py` — Nominatim, 1 req/sec, ~6 min for 196 firms
3. Build `step_04_llm_profiles.py` — Groq batch profiles for 196 firms
4. Build `app/Home.py` skeleton — load parquet, show KPI cards

---

## Questions for professor coaching session (tomorrow)

These are open questions where the professor's input will sharpen the project.

### Narrative & framing

**1. Is "Hidden Champions" the right label?**  
Hermann Simon's original Hidden Champions are mid-sized *exporters* — most of our Gazelles are local service firms (dentist labs, property managers, clinics). Should we adopt a different term, or lean into the tension between Simon's definition and our data?

**2. Is job *loss* at Metro/Henkel a fair comparison anchor?**  
Metro shed 67,000 employees globally since 2017 — much of that is international restructuring, not Düsseldorf specifically. Does framing this as local job loss risk being misleading, or is it fair as a "headline employment" story?

**3. How granular should the sector story go?**  
We have 18 NACE sections but our Gazelles concentrate in 3-4 letters. Is a sector-level finding (e.g. "Professional Services is the engine") strong enough, or do we need to drill to sub-sector (4-digit NACE code) to say something novel?

**4. What's the most surprising finding we should lead with?**  
Currently the story is framed around job growth vs. decline. Is there a more counterintuitive angle in the data — e.g. the *age* of Gazelles (young vs. old), the *size* paradox, or the *sector* distribution — that would be more memorable?

### Data & enrichment

**5. Is website + address + AI profile sufficient enrichment for the dashboard?**  
We enrich 196 firms with website, Düsseldorf address, and a Groq-generated description. What additional data point would most strengthen the story — revenue, founding year, ownership structure, or something else that's freely available?

**6. How should we handle the 1,359 "Other" firms on the map?**  
They're not Gazelles or Scalers but they're still on the map. Should we show them as grey dots (context), hide them by default, or use them to make a density/clustering point?

**7. 156 Scalers vs. 40 Gazelles — which category deserves more screen time?**  
Gazelles are the most extreme growers but only 40 firms. Scalers are 156 firms with a consistent story. Which cohort makes a stronger narrative centrepiece, and does it change depending on whether the audience is policy-makers vs. investors?

**8. What's the acceptable geocoding miss rate for the map to be credible?**  
Nominatim is free but may fail on some Düsseldorf addresses. If 20% of firms can't be geocoded, is the map still publishable, or does it need to hit a minimum threshold to be meaningful?

### AI & methodology

**9. How should AI-generated company profiles be disclosed in academic work?**  
We use Groq (Llama 3.3) to write one-paragraph profiles for each firm. What level of disclosure is expected — footnote, methodology section, or visible "AI-generated" label on each card in the dashboard?

**10. The pipeline itself as a methodological contribution — how much should we emphasise it?**  
We built a reproducible, cached, Dockerised pipeline that could be re-run for any European city. Is this worth highlighting as a *methodological* contribution separate from the Düsseldorf findings, or does it distract from the data story?
