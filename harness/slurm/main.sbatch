#!/bin/bash
# Main run (prereg.md §3-§7), sharded: the 120 non-pilot sets are split into K shards
# (pilot.py shard), one job and one GPU per shard, each with its own log directory, because
# concurrent appends to one JSONL on the shared home filesystem are not safe. The pilot's 10 sets
# stay in the pilot directory (prereg §9: they count as part of the main run if nothing changed).
#   cd ~/ibnr && for i in 1 2 3 4; do
#     sbatch --gres=gpu:nvidia_rtx_a6000:1 --export=ALL,SHARD=$i,K=4,PILOT_DIR=$HOME/ibnr_logs/pilot_<id> slurm/main.sbatch
#   done
#   Logs: ~/ibnr_logs/main_s<i>/. PHASE=A|B|judge|all (default all). Every phase is resumable:
#   a job killed by its time limit is resubmitted with the same SHARD and continues where it stopped.
#   Ports are offset by 10*SHARD so several jobs on landonia11 never share a vLLM port.
# STRESS (D6) is not here: it is conditional on the H1 point estimate and runs separately.
# Hardware: one RTX A6000 on landonia11 (DEVIATION D-3); pass the --gres override as above.
#SBATCH -J ibnr_main
#SBATCH -p Teaching
#SBATCH --gres=gpu:nvidia_rtx_a6000:1
#SBATCH --time=06:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH -o %x_%j.log
set -euo pipefail

: "${SHARD:?set SHARD (1..K)}"; : "${K:?set K}"; : "${PILOT_DIR:?set PILOT_DIR (the pilot log directory)}"
PHASE=${PHASE:-all}
export IBNR_LOG_DIR=$HOME/ibnr_logs/main_s${SHARD}
OFF=$((10 * SHARD)); PA=$((8000 + OFF)); PB=$((8001 + OFF)); PJ=$((8002 + OFF))
OV_A=(--override "models.A.base_url=http://localhost:$PA/v1")
OV_B=(--override "models.B.base_url=http://localhost:$PB/v1")
OV_J=(--override "models.judge.base_url=http://localhost:$PJ/v1")
REPO=${REPO:-$HOME/ibnr}
SCR=/disk/scratch/$USER
VENV=$SCR/venv
export PIP_CACHE_DIR=$HOME/pip_cache
export no_proxy="localhost,127.0.0.1${no_proxy:+,$no_proxy}"; export NO_PROXY="$no_proxy"
mkdir -p "$SCR/hf_cache/hub" "$IBNR_LOG_DIR"

QWEN=Qwen/Qwen3-8B;                               QWEN_REV=b968826d9c46dd6066d109eabc6255188de91218
MINI=mistralai/Ministral-3-8B-Instruct-2512-BF16; MINI_REV=f6fae9795746f63c9be8344932f01275f3c63734
JUDGE=google/gemma-4-31B-it-qat-w4a16-ct;         JUDGE_REV=52f3f65bc7a02d555763bc923bd1d9094898219d

echo "node $(hostname)  start $(date)"; nvidia-smi -L
if [ ! -x "$VENV/bin/vllm" ]; then
  python3 -m venv "$VENV"; "$VENV/bin/pip" install -q vllm==0.33.0 openai
fi
source "$VENV/bin/activate"
if ! command -v nvcc > /dev/null; then export CUDA_HOME=/opt/cuda-13.2.1; export PATH="$CUDA_HOME/bin:$PATH"; fi
command -v nvcc > /dev/null || { echo "nvcc missing"; exit 1; }; echo "nvcc: $(command -v nvcc)"
pip install -q -r "$REPO/requirements.txt"
python -c "import sys, vllm; print('vllm', vllm.__version__, '| python', sys.version.split()[0])"

for d in models--Qwen--Qwen3-8B models--mistralai--Ministral-3-8B-Instruct-2512-BF16 \
         models--google--gemma-4-31B-it-qat-w4a16-ct; do
  rsync -aL --exclude 'blobs/' "$HOME/hf_cache/hub/$d/" "$SCR/hf_cache/hub/$d/"
done
export HF_HOME=$SCR/hf_cache HF_HUB_OFFLINE=1

cd "$REPO"
python -m pytest -q tests/
# No `python sets.py` here: parallel shards must not rewrite a shared file. Check the frozen hash instead.
sha256sum data/sets.jsonl | grep -q '^69760dc07f67cf48622dab23e3f5c870199950eaa03beb992958289ea7bcc93e' \
  || { echo "data/sets.jsonl does not match prereg §11"; exit 1; }
git rev-parse HEAD > "$IBNR_LOG_DIR/git_head.txt" 2> /dev/null || true

git rev-parse HEAD > "$IBNR_LOG_DIR/git_head_main_${SLURM_JOB_ID}.txt" 2> /dev/null || true
ALL=$(python pilot.py shard --k "$K" --i "$SHARD")
HIGH=$(python pilot.py shard --k "$K" --i "$SHARD" --stratum high)
LOWHIGH=$(python pilot.py shard --k "$K" --i "$SHARD" --stratum low,high)
cp "$PILOT_DIR/judge_system_mode.txt" "$IBNR_LOG_DIR/judge_system_mode.txt"
echo "main run: shard $SHARD/$K, phase $PHASE, logs $IBNR_LOG_DIR, ports $PA $PB $PJ"
echo "sets: $ALL"

serve () {  # $1 model  $2 revision  $3 port  $4 tag, rest = extra flags
  local model=$1 rev=$2 port=$3 tag=$4; shift 4
  vllm serve "$model" --revision "$rev" --tokenizer-revision "$rev" \
    --enable-prefix-caching --enable-prompt-tokens-details \
    --gpu-memory-utilization 0.90 --max-num-seqs 64 --seed 0 --port "$port" "$@" \
    > "$IBNR_LOG_DIR/vllm_$tag.log" 2>&1 &
  VPID=$!
  until curl -sf "localhost:$port/health" > /dev/null; do
    sleep 10
    kill -0 "$VPID" 2> /dev/null || { echo "vLLM $tag died"; tail -50 "$IBNR_LOG_DIR/vllm_$tag.log"; exit 1; }
  done
}
stop () { kill "$VPID"; wait "$VPID" 2> /dev/null || true; }

if [[ $PHASE == all || $PHASE == A ]]; then
  serve "$QWEN" "$QWEN_REV" "$PA" A --dtype bfloat16 --max-model-len 32768
  python run.py --stage workers --sets "$ALL" "${OV_A[@]}"
  python run.py --stage managers --family A --sets "$ALL" --arms L,S "${OV_A[@]}"
  python run.py --stage managers --family A --sets "$HIGH" --arms CAP "${OV_A[@]}"
  python run.py --stage managers --family A --sets "$LOWHIGH" --arms S --framing responsible "${OV_A[@]}"
  python run.py --stage managers --family A --sets "$LOWHIGH" --arms S --framing placebo "${OV_A[@]}"
  grep -i "prefix cache hit" "$IBNR_LOG_DIR/vllm_A.log" | tail -1 || echo "no prefix-cache line"
  stop
fi

if [[ $PHASE == all || $PHASE == B ]]; then
  serve "$MINI" "$MINI_REV" "$PB" B --dtype bfloat16 --max-model-len 32768 \
    --tokenizer-mode mistral --config-format mistral --load-format mistral --limit-mm-per-prompt '{"image":0}'
  python run.py --stage managers --family B --sets "$ALL" --arms L,S "${OV_B[@]}"
  python run.py --stage managers --family B --sets "$HIGH" --arms CAP "${OV_B[@]}"
  stop
fi

if [[ $PHASE == all || $PHASE == judge ]]; then
  if [ -n "${CUDA_HOME:-}" ]; then   # judge only: NVRTC needs libnvrtc-builtins from the same toolkit (saxa, 7 Nov)
    export LD_LIBRARY_PATH="$CUDA_HOME/lib64:$CUDA_HOME/targets/x86_64-linux/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    ls "$CUDA_HOME"/lib64/libnvrtc-builtins* "$CUDA_HOME"/targets/x86_64-linux/lib/libnvrtc-builtins* 2> /dev/null || echo "WARNING: no libnvrtc-builtins under $CUDA_HOME"
  fi
  JUDGE_SYSTEM=$(cut -d' ' -f4 "$IBNR_LOG_DIR/judge_system_mode.txt")   # fixed by the pilot (D-1 item 10)
  echo "judge system mode (from pilot): $JUDGE_SYSTEM"
  serve "$JUDGE" "$JUDGE_REV" "$PJ" judge --max-model-len 16384
  python score.py judge --log-dir "$IBNR_LOG_DIR" --families A,B --judge-system "$JUDGE_SYSTEM" "${OV_J[@]}"
  stop
  python score.py score --log-dir "$IBNR_LOG_DIR" --families A,B
fi
echo "done $(date)  logs: $IBNR_LOG_DIR"
