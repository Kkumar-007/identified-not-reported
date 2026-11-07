#!/bin/bash
# D6 stress arm, family A only (deviations.md D-7): a 60-word turn 2 from the SAME L ledgers on every
# high-pressure set, then the judge on the new reports and a rescore, in the pilot and the four shard
# directories on saxa scratch. Code is fetched from GitHub at a pinned commit; nothing writes to home.
#   COMMIT=<full hash> sbatch /tmp/stress_scratch.sbatch
#SBATCH -J ibnr_stress
#SBATCH -p Teaching
#SBATCH --gres=gpu:h200_3g.71gb:1
#SBATCH -w saxa
#SBATCH --time=01:30:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH -o /disk/scratch/%u/%x_%j.log
set -euo pipefail
: "${COMMIT:?set COMMIT to the pushed commit hash}"

SCR=/disk/scratch/$USER
VENV=$SCR/venv
CODE=$SCR/ibnr_code_stress_${SLURM_JOB_ID}
LOGS=$SCR/ibnr_logs
DIRS="pilot_h200 main_s1 main_s2 main_s3 main_s4"
mkdir -p "$CODE"
curl -fsSL "https://codeload.github.com/Kkumar-007/identified-not-reported/tar.gz/$COMMIT" \
  | tar -xz -C "$CODE" --strip-components=2 --wildcards '*/harness/*'
echo "code $CODE @ $COMMIT"; sha256sum "$CODE/run.py" "$CODE/score.py" | cut -c1-16

REAL_HOME=$HOME; export HOME=$SCR/home; mkdir -p "$HOME"
export VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1
export PIP_CACHE_DIR=$SCR/pip_cache XDG_CACHE_HOME=$SCR/cache VLLM_CACHE_ROOT=$SCR/cache/vllm \
       TRITON_CACHE_DIR=$SCR/cache/triton TORCHINDUCTOR_CACHE_DIR=$SCR/cache/inductor \
       PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=$SCR/cache/mpl
export no_proxy="localhost,127.0.0.1${no_proxy:+,$no_proxy}"; export NO_PROXY="$no_proxy"
export HF_HOME=$SCR/hf_cache HF_HUB_OFFLINE=1

source "$VENV/bin/activate"
if ! command -v nvcc > /dev/null; then export CUDA_HOME=/opt/cuda-13.2.1; export PATH="$CUDA_HOME/bin:$PATH"; fi
cd "$CODE"
python -m pytest -q -p no:cacheprovider tests/test_score.py
for d in $DIRS; do test -s "$LOGS/$d/scores/items.jsonl" || { echo "missing $LOGS/$d/scores"; exit 1; }; done

QWEN=Qwen/Qwen3-8B; QWEN_REV=b968826d9c46dd6066d109eabc6255188de91218
JUDGE=google/gemma-4-31B-it-qat-w4a16-ct; JUDGE_REV=52f3f65bc7a02d555763bc923bd1d9094898219d
serve () {  # $1 model $2 revision $3 port $4 tag, rest = extra flags
  local model=$1 rev=$2 port=$3 tag=$4; shift 4
  vllm serve "$model" --revision "$rev" --tokenizer-revision "$rev" --enable-prefix-caching \
    --enable-prompt-tokens-details --gpu-memory-utilization 0.90 --max-num-seqs 64 --seed 0 --port "$port" "$@" \
    > "$LOGS/vllm_${tag}_stress_${SLURM_JOB_ID}.log" 2>&1 &
  VPID=$!
  until curl -sf "localhost:$port/health" > /dev/null; do
    sleep 10; kill -0 "$VPID" 2> /dev/null || { echo "vLLM $tag died"; tail -40 "$LOGS/vllm_${tag}_stress_${SLURM_JOB_ID}.log"; exit 1; }
  done
}
stop () { kill "$VPID"; wait "$VPID" 2> /dev/null || true; }
high_sets () { python -c "import json,sys; print(','.join(r['set_id'] for r in map(json.loads, open(sys.argv[1])) if r['set_id'].startswith('H') and not r['excluded']))" "$LOGS/$1/workers_final.jsonl"; }

serve "$QWEN" "$QWEN_REV" 8000 A --dtype bfloat16 --max-model-len 32768
for d in $DIRS; do
  HS=$(high_sets "$d"); echo "$d high sets: $HS"
  python run.py --stage managers --family A --sets "$HS" --arms STRESS --log-dir "$LOGS/$d"
done
stop

# judge only, as in the main run: NVRTC builtins from the CUDA toolkit
export LD_LIBRARY_PATH="${CUDA_HOME:-/opt/cuda-13.2.1}/lib64:${CUDA_HOME:-/opt/cuda-13.2.1}/targets/x86_64-linux/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
serve "$JUDGE" "$JUDGE_REV" 8002 judge --max-model-len 16384
JUDGE_SYSTEM=$(cut -d' ' -f4 "$LOGS/pilot_h200/judge_system_mode.txt")
echo "judge system mode (from pilot): $JUDGE_SYSTEM"
for d in $DIRS; do python score.py judge --log-dir "$LOGS/$d" --families A --judge-system "$JUDGE_SYSTEM"; done
stop
for d in $DIRS; do python score.py score --log-dir "$LOGS/$d" --families A,B; done
echo "done $(date)"
