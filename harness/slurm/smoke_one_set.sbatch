#!/bin/bash
# One-set end-to-end smoke test with the real pinned models (ICF Teaching partition, saxa).
#   cd ~/ibnr && sbatch slurm/smoke_one_set.sbatch            # default set H11
#   cd ~/ibnr && sbatch --export=ALL,SETS=H11,A01 slurm/smoke_one_set.sbatch
# Logs go to ~/ibnr_logs/smoke_<jobid> (shared home = persistent). Not the pilot: no gates here.
#SBATCH -J ibnr_smoke
#SBATCH -p Teaching
#SBATCH --gres=gpu:h200_3g.71gb:1
#SBATCH --time=01:30:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH -o %x_%j.log
set -euo pipefail

REPO=${REPO:-$HOME/ibnr}
SETS=${SETS:-H11}
SCR=/disk/scratch/$USER
VENV=$SCR/venv
export IBNR_LOG_DIR=$HOME/ibnr_logs/smoke_${SLURM_JOB_ID}
export PIP_CACHE_DIR=$HOME/pip_cache
export no_proxy="localhost,127.0.0.1${no_proxy:+,$no_proxy}"; export NO_PROXY="$no_proxy"
mkdir -p "$SCR/hf_cache/hub" "$IBNR_LOG_DIR"

QWEN=Qwen/Qwen3-8B;                               QWEN_REV=b968826d9c46dd6066d109eabc6255188de91218
MINI=mistralai/Ministral-3-8B-Instruct-2512-BF16; MINI_REV=f6fae9795746f63c9be8344932f01275f3c63734

echo "node $(hostname)  start $(date)"; nvidia-smi -L
if [ ! -x "$VENV/bin/vllm" ]; then
  python3 -m venv "$VENV"; "$VENV/bin/pip" install -q vllm==0.33.0 openai
fi
source "$VENV/bin/activate"
pip install -q -r "$REPO/requirements.txt"
python -c "import sys, vllm; print('vllm', vllm.__version__, '| python', sys.version.split()[0])"

# Weights to node-local scratch (cluster tip). -L resolves the snapshot symlinks into the shared blobs.
for d in models--Qwen--Qwen3-8B models--mistralai--Ministral-3-8B-Instruct-2512-BF16; do
  rsync -aL --exclude 'blobs/' "$HOME/hf_cache/hub/$d/" "$SCR/hf_cache/hub/$d/"
done
export HF_HOME=$SCR/hf_cache HF_HUB_OFFLINE=1

cd "$REPO"
python -m pytest -q tests/
python sets.py            # refuses to overwrite if data/sets.jsonl would change

serve () {  # $1 model  $2 revision  $3 port  $4 tag, rest = extra flags
  local model=$1 rev=$2 port=$3 tag=$4; shift 4
  vllm serve "$model" --revision "$rev" --tokenizer-revision "$rev" --dtype bfloat16 \
    --max-model-len 32768 --enable-prefix-caching --enable-prompt-tokens-details \
    --gpu-memory-utilization 0.90 --max-num-seqs 64 --seed 0 --port "$port" "$@" \
    > "$IBNR_LOG_DIR/vllm_$tag.log" 2>&1 &
  VPID=$!
  until curl -sf "localhost:$port/health" > /dev/null; do
    sleep 10
    kill -0 "$VPID" 2> /dev/null || { echo "vLLM $tag died"; tail -50 "$IBNR_LOG_DIR/vllm_$tag.log"; exit 1; }
  done
}

# Family A: workers, then managers
serve "$QWEN" "$QWEN_REV" 8000 A
python run.py --stage workers --sets "$SETS"
python run.py --stage managers --family A --sets "$SETS" --arms L,S
grep -i "prefix cache hit" "$IBNR_LOG_DIR/vllm_A.log" | tail -1 || echo "no prefix-cache line"
kill "$VPID"; wait "$VPID" 2> /dev/null || true

# Family B: managers on the same worker transcripts
serve "$MINI" "$MINI_REV" 8001 B --tokenizer-mode mistral --config-format mistral --load-format mistral \
  --limit-mm-per-prompt '{"image":0}'
python run.py --stage managers --family B --sets "$SETS" --arms L,S
kill "$VPID"; wait "$VPID" 2> /dev/null || true

python dev/show_logs.py "$IBNR_LOG_DIR"
echo "done $(date)  logs: $IBNR_LOG_DIR"
