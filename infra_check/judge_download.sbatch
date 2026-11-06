#!/bin/bash
# DISPOSABLE pre-sprint infra step: download the judge weights (no GPU). Not project code.
# Runs on saxa to reuse the vLLM venv on its local scratch (it already has huggingface_hub).
# Submit from ~/infra_check:  cd ~/infra_check && sbatch judge_download.sbatch
#SBATCH -J judge_download
#SBATCH -p Teaching
#SBATCH -w saxa
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH -o %x_%j.log
set -euo pipefail

export HF_HOME=$HOME/hf_cache
VENV=/disk/scratch/$USER/venv
if [ ! -x "$VENV/bin/python" ]; then
  echo "venv missing on $(hostname); run icf_throughput.sbatch first"; exit 1
fi
source "$VENV/bin/activate"
echo "node: $(hostname)  start: $(date)"

python - <<'PY'
from huggingface_hub import snapshot_download

for repo in ["google/gemma-4-31B-it", "google/gemma-4-31B-it-qat-w4a16-ct"]:
    path = snapshot_download(repo)
    print(f"PIN {repo} @ {path.rstrip('/').split('/')[-1]}", flush=True)
PY

du -sh "$HF_HOME"/hub/models--google--gemma-4-31B-it*
echo "done: $(date)"
