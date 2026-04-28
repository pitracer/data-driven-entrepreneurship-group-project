"""
Pipeline configuration — paths, API settings, column mappings.

All data directories are created at import time.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_FINAL = ROOT / "data" / "final"       # committed to git — app reads from here
CACHE_SERP = ROOT / "data" / "cache" / "serp"
CACHE_GEOCODE = ROOT / "data" / "cache" / "geocode"
CACHE_LLM = ROOT / "data" / "cache" / "llm"
CACHE_SIGNAL_FOCUS = ROOT / "data" / "cache" / "signal_focus"
CACHE_SIGNAL_SCALE = ROOT / "data" / "cache" / "signal_scale"
CACHE_SIGNAL_DIGITAL = ROOT / "data" / "cache" / "signal_digital"
CACHE_SIGNALS_EXTRACTED = ROOT / "data" / "cache" / "signals_extracted"


def ensure_dirs() -> None:
    """Create all required data directories. Call once at the start of each pipeline step."""
    for _dir in (
        DATA_RAW, DATA_PROCESSED, DATA_FINAL,
        CACHE_SERP, CACHE_GEOCODE, CACHE_LLM,
        CACHE_SIGNAL_FOCUS, CACHE_SIGNAL_SCALE, CACHE_SIGNAL_DIGITAL,
        CACHE_SIGNALS_EXTRACTED,
    ):
        _dir.mkdir(parents=True, exist_ok=True)

# Source / output files
XLSX_SOURCE = DATA_RAW / "DUESSELDORF.xlsx"
FIRMS_CLEAN = DATA_PROCESSED / "firms_clean.parquet"
FIRMS_ENRICHED = DATA_FINAL / "firms_enriched.parquet"      # app reads this
SECTOR_NARRATIVES = DATA_FINAL / "sector_narratives.json"   # app reads this
# Pipeline intermediates (local only, gitignored via data/processed/)
FIRMS_ENRICHED_PROCESSED = DATA_PROCESSED / "firms_enriched.parquet"
FIRM_SIGNALS = DATA_PROCESSED / "firm_signals.parquet"

# ---------------------------------------------------------------------------
# API settings (loaded from .env)
# ---------------------------------------------------------------------------
SERPAPI_KEY: str = os.getenv("SERPAPI_KEY", "")
SERPER_KEYS: list[str] = [
    k.strip() for k in os.getenv("SERPER_KEYS", "").split(",") if k.strip()
]

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_KEYS: list[str] = [
    k.strip()
    for k in os.getenv("GROQ_KEYS", os.getenv("GROQ_API_KEY", "")).split(",")
    if k.strip()
]

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_RATE_LIMIT_RPM = 30       # free tier: requests per minute
GROQ_RATE_LIMIT_TPM = 15_000   # free tier: tokens per minute

NOMINATIM_RATE_LIMIT = 1.0     # seconds between requests (required by ToS)
NOMINATIM_USER_AGENT = "duesseldorf-growth-study"

# ---------------------------------------------------------------------------
# Enrichment priorities
# ---------------------------------------------------------------------------
PRIORITY_CATEGORIES = ["Gazelle", "Scaler"]  # enriched first (SerpAPI budget)

# ---------------------------------------------------------------------------
# Column rename mapping  (original Excel name → snake_case target)
# ---------------------------------------------------------------------------
COLUMN_RENAMES: dict[str, str] = {
    "Company name Latin alphabet": "company_name",
    "BvD ID number": "bvd_id",
    "NACE Rev. 2, core code (4 digits)": "nace_code",
    "NACE Rev. 2 main section": "nace_section",
    "Date of incorporation": "date_of_incorporation",
    "Founded Year": "founded_year",
    # Employee counts
    "Number of employees\n2024": "employees_2024",
    "Number of employees\n2023": "employees_2023",
    "Number of employees\n2022": "employees_2022",
    "Number of employees\n2021": "employees_2021",
    "Number of employees\n2020": "employees_2020",
    "Number of employees\n2019": "employees_2019",
    "Number of employees\n2018": "employees_2018",
    "Number of employees\n2017": "employees_2017",
    # YoY growth rates
    "Growth 2024": "growth_2024",
    "Growth 2023": "growth_2023",
    "Growth 2022": "growth_2022",
    "Growth 2021": "growth_2021",
    "Growth 2020": "growth_2020",
    "Growth 2019": "growth_2019",
    "Growth 2018": "growth_2018",
    # Average annual growth rates (note: aagr 2019 does not exist in source data)
    "aagr 2024": "aagr_2024",
    "aagr 2023": "aagr_2023",
    "aagr 2022": "aagr_2022",
    "aagr 2021": "aagr_2021",
    "aagr 2020": "aagr_2020",
    # Scaler flags
    "Scaler 2024": "scaler_2024",
    "Scaler 2023": "scaler_2023",
    "Scaler 2022": "scaler_2022",
    "Scaler 2021": "scaler_2021",
    "Scaler 2020": "scaler_2020",
    # HighGrowthFirm flags
    "HighGrowthFirm 2024": "high_growth_2024",
    "HighGrowthFirm 2023": "high_growth_2023",
    "HighGrowthFirm 2022": "high_growth_2022",
    "HighGrowthFirm 2021": "high_growth_2021",
    "HighGrowthFirm 2020": "high_growth_2020",
    # ConsistentHighGrowthFirm flags
    "ConsistentHighGrowthFirm 2024": "consistent_hgf_2024",
    "ConsistentHighGrowthFirm 2023": "consistent_hgf_2023",
    "ConsistentHighGrowthFirm 2022": "consistent_hgf_2022",
    "ConsistentHighGrowthFirm 2021": "consistent_hgf_2021",
    "ConsistentHighGrowthFirm 2020": "consistent_hgf_2020",
    # VeryHighGrowthFirm flags
    "VeryHighGrowthFirm 2024": "very_high_growth_2024",
    "VeryHighGrowthFirm 2023": "very_high_growth_2023",
    "VeryHighGrowthFirm 2022": "very_high_growth_2022",
    "VeryHighGrowthFirm 2021": "very_high_growth_2021",
    "VeryHighGrowthFirm 2020": "very_high_growth_2020",
    # Gazelle flags
    "Gazelle 2024": "gazelle_2024",
    "Gazelle 2023": "gazelle_2023",
    "Gazelle 2022": "gazelle_2022",
    "Gazelle 2021": "gazelle_2021",
    "Gazelle 2020": "gazelle_2020",
    # Mature flags
    "Mature 2024": "mature_2024",
    "Mature 2023": "mature_2023",
    "Mature 2022": "mature_2022",
    "Mature 2021": "mature_2021",
    "Mature 2020": "mature_2020",
    # Scaleup flags
    "Scaleup 2024": "scaleup_2024",
    "Scaleup 2023": "scaleup_2023",
    "Scaleup 2022": "scaleup_2022",
    "Scaleup 2021": "scaleup_2021",
    "Scaleup 2020": "scaleup_2020",
    # Superstar flags
    "Superstar 2024": "superstar_2024",
    "Superstar 2023": "superstar_2023",
    "Superstar 2022": "superstar_2022",
    "Superstar 2021": "superstar_2021",
    "Superstar 2020": "superstar_2020",
}

# ---------------------------------------------------------------------------
# Data loader helper
# ---------------------------------------------------------------------------
def load_best_data() -> "pd.DataFrame":
    """Return firms_enriched if it exists, otherwise firms_clean."""
    import pandas as pd
    if FIRMS_ENRICHED.exists():
        return pd.read_parquet(FIRMS_ENRICHED)
    if FIRMS_CLEAN.exists():
        return pd.read_parquet(FIRMS_CLEAN)
    raise FileNotFoundError("No processed data found. Run step_01_clean first.")


ENRICHMENT_COLUMNS = ["website", "address", "lat", "lon", "snippet", "profile_text"]

# ---------------------------------------------------------------------------
# Orbis batch data
# ---------------------------------------------------------------------------
ORBIS_BATCH_FILES = [
    DATA_RAW / "Orbis_batch1done.xlsx",
    DATA_RAW / "Orbis_batch2done.xlsx",
]
ORBIS_DATA = DATA_PROCESSED / "orbis_data.parquet"

# Columns to drop entirely (all-constant values, no analytical use)
COLUMNS_TO_DROP: list[str] = [
    "Unnamed: 0",
    "Country ISO code",       # all "DE"
    "City\nLatin Alphabet",   # all "DUESSELDORF"
    "Status",                 # all "Active"
    "Region in country",      # all "Nordrhein-Westfalen"
    "Region in country clean",
]

# Binary flag column prefixes (used for bool casting in step_01)
FLAG_PREFIXES: list[str] = [
    "scaler_",
    "high_growth_",
    "consistent_hgf_",
    "very_high_growth_",
    "gazelle_",
    "mature_",
    "scaleup_",
    "superstar_",
]
