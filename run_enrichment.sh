#!/bin/bash
set -e
LOG="enrichment_$(date +%Y%m%d_%H%M%S).log"
echo "=== Enrichment pipeline started at $(date) ===" | tee "$LOG"

echo "" | tee -a "$LOG"
echo "=== Step 1/5: Snippet search (Serper, all firms) ===" | tee -a "$LOG"
python3 -m pipeline.step_02_search --provider serper --all-firms 2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== Step 2/5: Signal searches (focus + scaling + digital) ===" | tee -a "$LOG"
python3 -m pipeline.step_06_signal_search --query all 2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== Step 3/5: Groq signal extraction ===" | tee -a "$LOG"
python3 -m pipeline.step_07_extract_signals 2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== Step 4/5: Clustering ===" | tee -a "$LOG"
python3 -m pipeline.step_08_cluster 2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== Step 5/5: Merge + rebuild final parquet ===" | tee -a "$LOG"
python3 -m pipeline.enrich_batch 2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== Committing to GitHub ===" | tee -a "$LOG"
git add data/final/firms_enriched.parquet
git commit -m "Enrich: Serper snippets, signal clusters (archetype + growth strategy)"
git push

echo "" | tee -a "$LOG"
echo "=== ALL DONE at $(date) ===" | tee -a "$LOG"
