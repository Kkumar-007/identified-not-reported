#!/bin/bash
# Worker-prompt probe (dev/worker_probe.py: variants A/B/C, 15 problems x 6 cells, first try) and
# then a manager plumbing smoke test on clean set C01 with both families.
#   cd ~/ibnr && sbatch --export=ALL,CELLS=AU slurm/probe.sbatch   # probe 3: E (v4), AU only, rule au
# Logs: ~/ibnr_logs/probe_<jobid>/{probe,smoke_C01}. Worker behaviour only decides the probe.
#SBATCH -J ibnr_probe
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
ROOT=$HOME/ibnr_logs/probe_${SLURM_JOB_ID}
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
echo "== probe  $(date)"
CELLS_ARG=(); [ -n "${CELLS:-}" ] && CELLS_ARG=(--cells "$CELLS")
python dev/worker_probe.py --out "$ROOT/probe" --variants "${VARIANTS:-E}" --rule "${RULE:-au}" "${CELLS_ARG[@]}"
if [ "${SMOKE:-0}" != "1" ]; then
  kill "$VPID"; wait "$VPID" 2> /dev/null || true
  echo "done $(date)  logs: $ROOT"; exit 0
fi

echo "== manager smoke on C01 (v2 workers, no thinking; full reserve pool as a logged override)  $(date)"
export IBNR_LOG_DIR=$ROOT/smoke_C01
POOL='data.stage_b_pool=[R01,R02,R03,R04,R05,R06,R07,R08,R09,R10,R11,R12,R13,R14,R15]'
python run.py --stage workers --sets C01 --override "$POOL"
python run.py --stage managers --family A --sets C01 --arms L,S --override "$POOL" || echo "MANAGERS A FAILED"
kill "$VPID"; wait "$VPID" 2> /dev/null || true

serve "$MINI" "$MINI_REV" 8001 B --tokenizer-mode mistral --config-format mistral --load-format mistral \
  --limit-mm-per-prompt '{"image":0}'
python run.py --stage managers --family B --sets C01 --arms L,S --override "$POOL" || echo "MANAGERS B FAILED"
kill "$VPID"; wait "$VPID" 2> /dev/null || true

python dev/show_logs.py "$IBNR_LOG_DIR"
echo "done $(date)  logs: $ROOT"
