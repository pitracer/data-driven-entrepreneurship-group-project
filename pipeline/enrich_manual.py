"""
Semi-automated manual enrichment for firms not covered by SerpAPI budget.

Workflow:
  1. Export a prompt:   python -m pipeline.enrich_manual export --batch 20
  2. Paste the prompt into Claude / ChatGPT / Perplexity
  3. Save the JSON reply to a file, then import:
                        python -m pipeline.enrich_manual import --file response.json

The import writes synthetic cache entries in the same format that step_02 reads,
so the downstream pipeline (step_03, step_04, ...) is completely unchanged.

Status overview:  python -m pipeline.enrich_manual status
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

from pipeline.cache import FileCache
from pipeline.config import CACHE_SERP, FIRMS_CLEAN, DATA_PROCESSED, ensure_dirs

SEARCH_RESULTS = DATA_PROCESSED / "search_results.parquet"

# ── helpers ──────────────────────────────────────────────────────────────────

def _cache_key(company_name: str) -> str:
    query = f'"{company_name}" Düsseldorf'
    return hashlib.md5(query.encode("utf-8")).hexdigest()


def _synthetic_entry(company_name: str, website: str | None,
                     address: str | None, snippet: str | None) -> dict:
    """Build a minimal fake SerpAPI response that _extract() in step_02 can read."""
    kg = {}
    if website:
        kg["website"] = website
    if address:
        kg["address"] = address
    if snippet:
        kg["description"] = snippet

    organic = []
    if website:
        organic.append({"link": website, "snippet": snippet or ""})

    return {
        "search_metadata": {"status": "Manual"},
        "knowledge_graph": kg,
        "organic_results": organic,
        "answer_box": {},
    }


def _load_queue(cache: FileCache) -> pd.DataFrame:
    """Return priority firms that still need enrichment (not yet cached)."""
    df = pd.read_parquet(FIRMS_CLEAN)
    priority = df[df["priority_enrich"]].copy()
    priority["cached"] = priority["company_name"].apply(
        lambda n: cache.exists(f'"{n}" Düsseldorf')
    )
    return priority


# ── commands ──────────────────────────────────────────────────────────────────

def cmd_status(args: argparse.Namespace) -> None:
    cache = FileCache(CACHE_SERP)
    queue = _load_queue(cache)
    total = len(queue)
    done = queue["cached"].sum()
    remaining = total - done

    print(f"\n{'─'*48}")
    print(f"  Priority firms total : {total}")
    print(f"  Enriched (cached)    : {done}")
    print(f"  Still needed         : {remaining}")
    print(f"{'─'*48}\n")

    if remaining > 0:
        print("Firms still needing enrichment:")
        for _, r in queue[~queue["cached"]].iterrows():
            cat = "🦌 Gazelle" if r["gazelle_2024"] else "📈 Scaler "
            print(f"  {cat}  {r['company_name']}")
    else:
        print("✓ All priority firms are enriched!")


def cmd_export(args: argparse.Namespace) -> None:
    cache = FileCache(CACHE_SERP)
    queue = _load_queue(cache)
    remaining = queue[~queue["cached"]].head(args.batch)

    if remaining.empty:
        print("All priority firms already enriched — nothing to export.")
        return

    companies = "\n".join(
        f"{i+1}. {r['company_name']}"
        for i, (_, r) in enumerate(remaining.iterrows())
    )

    prompt = f"""For each company below, find their website, their street address in Düsseldorf, and write a 1-sentence description of what the company does.

All companies are based in Düsseldorf, Germany.

Return ONLY a valid JSON array — no markdown, no explanation, just the array.

Companies:
{companies}

Required format:
[
  {{
    "company_name": "EXACT NAME AS GIVEN",
    "website": "https://...",
    "address": "Street, Düsseldorf",
    "snippet": "One sentence describing the company."
  }},
  ...
]

Rules:
- If you cannot find a website, set "website" to null
- If you cannot find an address, set "address" to null
- Always write a snippet even if brief
- Keep company_name exactly as given above
- Return {len(remaining)} objects, one per company"""

    print("\n" + "="*60)
    print("PASTE THIS INTO CLAUDE / CHATGPT / PERPLEXITY:")
    print("="*60)
    print(prompt)
    print("="*60)
    print(f"\nCovers {len(remaining)} firms "
          f"({args.batch - len(remaining)} fewer than batch size — all remaining)."
          if len(remaining) < args.batch else
          f"\nCovers {len(remaining)} of {(~queue['cached']).sum()} remaining firms.")
    print("Save the JSON reply to a file, then run:")
    print("  python -m pipeline.enrich_manual import --file response.json\n")

    # Also write prompt to file for convenience
    out = Path("enrich_prompt.txt")
    out.write_text(prompt, encoding="utf-8")
    print(f"(Prompt also saved to {out})")


def cmd_import(args: argparse.Namespace) -> None:
    cache = FileCache(CACHE_SERP)

    # Load JSON from file or stdin
    if args.file:
        raw = Path(args.file).read_text(encoding="utf-8").strip()
    else:
        print("Paste JSON response and press Ctrl+D when done:")
        raw = sys.stdin.read().strip()

    # Strip markdown code fences if model wrapped it
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0].strip()

    try:
        records = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: Could not parse JSON — {e}")
        sys.exit(1)

    if not isinstance(records, list):
        print("ERROR: Expected a JSON array at the top level.")
        sys.exit(1)

    imported = 0
    skipped = 0
    for rec in records:
        name = rec.get("company_name", "").strip()
        if not name:
            print("  SKIP — missing company_name")
            skipped += 1
            continue

        entry = _synthetic_entry(
            company_name=name,
            website=rec.get("website"),
            address=rec.get("address"),
            snippet=rec.get("snippet"),
        )

        query = f'"{name}" Düsseldorf'
        cache.set(query, entry)
        imported += 1
        print(f"  ✓ {name[:55]}")

    print(f"\nImported {imported} entries into cache "
          f"({skipped} skipped). Total cache size: {len(cache)}")
    print("Run step_02 now to rebuild search_results.parquet from the full cache:")
    print("  python -m pipeline.step_02_search --limit 0")


# ── entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ensure_dirs()
    parser = argparse.ArgumentParser(description="Semi-automated manual enrichment")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="Show enrichment progress")

    p_export = sub.add_parser("export", help="Generate a prompt to paste into an LLM")
    p_export.add_argument("--batch", type=int, default=20,
                          help="How many firms per prompt (default: 20)")

    p_import = sub.add_parser("import", help="Import JSON from LLM into cache")
    p_import.add_argument("--file", type=str, default=None,
                          help="Path to JSON file (omit to paste from stdin)")

    args = parser.parse_args()
    {"status": cmd_status, "export": cmd_export, "import": cmd_import}[args.cmd](args)
    sys.exit(0)
