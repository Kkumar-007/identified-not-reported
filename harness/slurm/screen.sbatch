#!/bin/bash
# Stage A clean screen (screen.py): 60 problems x 10 clean episodes, frozen v4 workers, first try.
#   cd ~/ibnr && sbatch slurm/screen.sbatch
# Logs: ~/ibnr_logs/screen_<jobid>/ (screen_results.json, swaps.jsonl). Reads no manager output.
#SBATCH -J ibnr_screen
#SBATCH -p Teaching
#SBATCH --gres=gpu:h200_3g.71gb:1
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH -o %x_%j.log
set -euo pipefail

REPO=${REPO:-$HOME/ibnr}
SCR=/disk/scratch/$USER
VENV=$SCR/venv
ROOT=$HOME/ibnr_logs/screen_${SLURM_JOB_ID}
export PIP_CACHE_DIR=$HOME/pip_cache
export no_proxy="localhost,127.0.0.1${no_proxy:+,$no_proxy}"; export NO_PROXY="$no_proxy"
mkdir -p "$SCR/hf_cache/hub" "$ROOT"

QWEN=Qwen/Qwen3-8B;                               QWEN_REV=b968826d9c46dd6066d109eabc6255188de91218
MINI=mistralai/Ministral-3-8B-Instruct-2512-BF16; MINI_REV=f6fae9795746f63c9be8344932f01275f3c63734

echo "node $(hostname)  start $(date)"; nvidia-smi -L
if [ ! -x "$VENV/bin/vllm" ]; then
  python3 -m venv "$VENV"; "$VENV/bin/pip" install -q vllm==0.33.0 openai
fi
source "$VENV/bin/activate"
pip install -q -r "$REPO/requirements.txt"
for d in models--Qwen--Qwen3-8B models--mistralai--Ministral-3-8B-Instruct-2512-BF16; do
  rsync -aL --exclude 'blobs/' "$HOME/hf_cache/hub/$d/" "$SCR/hf_cache/hub/$d/"
done
export HF_HOME=$SCR/hf_cache HF_HUB_OFFLINE=1

cd "$REPO"
python -m pytest -q tests/
python sets.py

serve () {  # $1 model  $2 revision  $3 port  $4 tag, rest = extra flags
  local model=$1 rev=$2 port=$3 tag=$4; shift 4
  vllm serve "$model" --revision "$rev" --tokenizer-revision "$rev" --dtype bfloat16 \
    --max-model-len 32768 --enable-prefix-caching --enable-prompt-tokens-details \
    --gpu-memory-utilization 0.90 --max-num-seqs 64 --seed 0 --port "$port" "$@" \
    > "$ROOT/vllm_$tag.log" 2>&1 &
  VPID=$!
  until curl -sf "localhost:$port/health" > /dev/null; do
    sleep 10
    kill -0 "$VPID" 2> /dev/null || { echo "vLLM $tag died"; tail -50 "$ROOT/vllm_$tag.log"; exit 1; }
  done
}

serve "$QWEN" "$QWEN_REV" 8000 A
echo "== stage A screen  $(date)"
python run.py --stage screen --log-dir "$ROOT"
kill "$VPID"; wait "$VPID" 2> /dev/null || true
echo "done $(date)  logs: $ROOT"
