#!/bin/bash
PYTHON="/home/pit/.pyenv/versions/3.10.6/envs/lewagon/bin/python3"
cd "/home/pit/code/pitracer/102-WHU/05 Data Driven Entrepreneurship/group-assignment"
LOG="enrichment_resume_$(date +%Y%m%d_%H%M%S).log"
echo "=== Resume run at $(date) ===" | tee "$LOG"

echo "" | tee -a "$LOG"
echo "=== Step 2/5: Signal searches (resume — focus cached, doing scale+digital) ===" | tee -a "$LOG"
$PYTHON -m pipeline.step_06_signal_search --query all 2>&1 | tee -a "$LOG" || echo "[step_06 error — continuing]" | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== Step 3/5: Groq signal extraction ===" | tee -a "$LOG"
$PYTHON -m pipeline.step_07_extract_signals 2>&1 | tee -a "$LOG" || echo "[step_07 error — continuing]" | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== Step 4/5: Clustering ===" | tee -a "$LOG"
$PYTHON -m pipeline.step_08_cluster 2>&1 | tee -a "$LOG" || echo "[step_08 error — continuing]" | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== Step 5/5: Merge + rebuild final parquet ===" | tee -a "$LOG"
$PYTHON -m pipeline.enrich_batch 2>&1 | tee -a "$LOG" || echo "[enrich_batch error — continuing]" | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== Committing to GitHub ===" | tee -a "$LOG"
git add data/final/firms_enriched.parquet 2>&1 | tee -a "$LOG"
git commit -m "Enrich: Serper snippets + signal clusters (archetype + growth strategy)" 2>&1 | tee -a "$LOG"
git push 2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== ALL DONE at $(date) ===" | tee -a "$LOG"
