#!/bin/bash
# CAUSE judge pass (deviations.md D-6): J_CAUSE on the L/S-neutral reports of the admitted cells, in the
# pilot and the four main-run shard directories on saxa scratch. Code is fetched from GitHub at a pinned
# commit (home writes stall; nothing here writes to home). Submit from /tmp in the bare shell:
#   COMMIT=<full hash> sbatch /tmp/cause_scratch.sbatch
#SBATCH -J ibnr_cause
#SBATCH -p Teaching
#SBATCH --gres=gpu:h200_3g.71gb:1
#SBATCH -w saxa
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH -o /disk/scratch/%u/%x_%j.log
set -euo pipefail
: "${COMMIT:?set COMMIT to the pushed commit hash}"

SCR=/disk/scratch/$USER
VENV=$SCR/venv
CODE=$SCR/ibnr_code_cause_${SLURM_JOB_ID}
LOGS=$SCR/ibnr_logs
DIRS="pilot_h200 main_s1 main_s2 main_s3 main_s4"
mkdir -p "$CODE"
curl -fsSL "https://codeload.github.com/Kkumar-007/identified-not-reported/tar.gz/$COMMIT" \
  | tar -xz -C "$CODE" --strip-components=2 --wildcards '*/harness/*'
echo "code $CODE @ $COMMIT"; sha256sum "$CODE/cause.py" "$CODE/score.py" | cut -c1-16

REAL_HOME=$HOME; export HOME=$SCR/home; mkdir -p "$HOME"
export VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1
export PIP_CACHE_DIR=$SCR/pip_cache XDG_CACHE_HOME=$SCR/cache VLLM_CACHE_ROOT=$SCR/cache/vllm \
       TRITON_CACHE_DIR=$SCR/cache/triton TORCHINDUCTOR_CACHE_DIR=$SCR/cache/inductor \
       PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=$SCR/cache/mpl
export no_proxy="localhost,127.0.0.1${no_proxy:+,$no_proxy}"; export NO_PROXY="$no_proxy"
export HF_HOME=$SCR/hf_cache HF_HUB_OFFLINE=1

source "$VENV/bin/activate"
if ! command -v nvcc > /dev/null; then export CUDA_HOME=/opt/cuda-13.2.1; export PATH="$CUDA_HOME/bin:$PATH"; fi
export LD_LIBRARY_PATH="${CUDA_HOME:-/opt/cuda-13.2.1}/lib64:${CUDA_HOME:-/opt/cuda-13.2.1}/targets/x86_64-linux/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cd "$CODE"
python -m pytest -q -p no:cacheprovider tests/test_score.py
for d in $DIRS; do test -s "$LOGS/$d/scores/items.jsonl" || { echo "missing $LOGS/$d/scores"; exit 1; }; done

JUDGE=google/gemma-4-31B-it-qat-w4a16-ct; JUDGE_REV=52f3f65bc7a02d555763bc923bd1d9094898219d
vllm serve "$JUDGE" --revision "$JUDGE_REV" --tokenizer-revision "$JUDGE_REV" --max-model-len 16384 \
  --enable-prefix-caching --enable-prompt-tokens-details --gpu-memory-utilization 0.90 --max-num-seqs 64 \
  --seed 0 --port 8002 > "$LOGS/vllm_judge_cause_${SLURM_JOB_ID}.log" 2>&1 &
VPID=$!
until curl -sf localhost:8002/health > /dev/null; do
  sleep 10; kill -0 "$VPID" 2> /dev/null || { echo "vLLM judge died"; tail -40 "$LOGS/vllm_judge_cause_${SLURM_JOB_ID}.log"; exit 1; }
done
JUDGE_SYSTEM=$(cut -d' ' -f4 "$LOGS/pilot_h200/judge_system_mode.txt")
echo "judge system mode (from pilot): $JUDGE_SYSTEM"
for d in $DIRS; do python cause.py judge --log-dir "$LOGS/$d" --judge-system "$JUDGE_SYSTEM"; done
kill "$VPID"; wait "$VPID" 2> /dev/null || true
echo "done $(date)"
