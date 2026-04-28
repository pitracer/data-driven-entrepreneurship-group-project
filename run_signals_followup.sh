#!/bin/bash
PYTHON="/home/pit/.pyenv/versions/3.10.6/envs/lewagon/bin/python3"
cd "/home/pit/code/pitracer/102-WHU/05 Data Driven Entrepreneurship/group-assignment"
LOG="enrichment_signals_$(date +%Y%m%d_%H%M%S).log"
echo "=== Signal follow-up run at $(date) ===" | tee "$LOG"

echo "" | tee -a "$LOG"
echo "=== Step 1/4: Signal search — scaling_signal + digital_leverage ===" | tee -a "$LOG"
$PYTHON -m pipeline.step_06_signal_search --query scaling_signal 2>&1 | tee -a "$LOG" || echo "[step_06 scaling error]" | tee -a "$LOG"
$PYTHON -m pipeline.step_06_signal_search --query digital_leverage 2>&1 | tee -a "$LOG" || echo "[step_06 digital error]" | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== Step 2/4: Groq re-extraction (rerun with new signal data) ===" | tee -a "$LOG"
$PYTHON -m pipeline.step_07_extract_signals --rerun 2>&1 | tee -a "$LOG" || echo "[step_07 error]" | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== Step 3/4: Clustering ===" | tee -a "$LOG"
$PYTHON -m pipeline.step_08_cluster 2>&1 | tee -a "$LOG" || echo "[step_08 error]" | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== Step 4/4: Merge + rebuild final parquet ===" | tee -a "$LOG"
$PYTHON -m pipeline.enrich_batch 2>&1 | tee -a "$LOG" || echo "[enrich_batch error]" | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== Committing to GitHub ===" | tee -a "$LOG"
git add data/final/firms_enriched.parquet 2>&1 | tee -a "$LOG"
git commit -m "Enrich: full signal clusters with scaling + digital leverage data" 2>&1 | tee -a "$LOG"
git push 2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== ALL DONE at $(date) ===" | tee -a "$LOG"
