#!/bin/bash
# 10-set pilot, prereg.md §9: the pre-specified sets (pilot.py sets), run in full, both families,
# then the judge, scoring and the §9 summary. Prints format and gate counts only.
#   SCRATCH VERSION (home writes stall): submit from /tmp, e.g.
#   SEED_LOG_DIR=$HOME/ibnr_logs/pilot_v5 IBNR_LOG_DIR=/disk/scratch/$USER/ibnr_logs/pilot_v5 sbatch /tmp/pilot_scratch.sbatch
# Logs: ~/ibnr_logs/pilot_<jobid>/  (if nothing changes after the pilot, this is also the main
# run's log directory: the pilot sets count as part of the main run, §9).
# Phases run one model at a time on one 71 GB slice: A (workers + managers), B (managers), judge.
#SBATCH -J ibnr_pilot_scr
#SBATCH -p Teaching
#SBATCH --gres=gpu:nvidia_rtx_a6000:1
#SBATCH -w landonia11
#SBATCH --time=03:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH -o /disk/scratch/%u/%x_%j.log
set -euo pipefail

# SCRATCH MODE: the home filesystem stalls on writes (6 Nov, 23:3x), so nothing in this job writes
# to home. Code is read from ~/ibnr and copied to scratch; logs, caches and this job's log are on
# landonia11's /disk/scratch. SEED_LOG_DIR (read only) seeds the log dir on first use.
SCR=/disk/scratch/$USER
VENV=$SCR/venv
CODE=$SCR/ibnr_code_${SLURM_JOB_ID}
mkdir -p "$CODE"
rsync -a --exclude 'logs_*' --exclude '__pycache__' --exclude '/prompts/' --exclude '*.log' "$HOME/ibnr/" "$CODE/"
REPO=$CODE
export IBNR_LOG_DIR=${IBNR_LOG_DIR:-$SCR/ibnr_logs/pilot_${SLURM_JOB_ID}}
mkdir -p "$IBNR_LOG_DIR"
if [ -n "${SEED_LOG_DIR:-}" ] && [ ! -e "$IBNR_LOG_DIR/calls.jsonl" ]; then
  rsync -a "$SEED_LOG_DIR/" "$IBNR_LOG_DIR/"; echo "seeded $IBNR_LOG_DIR from $SEED_LOG_DIR"
fi
REAL_HOME=$HOME; export HOME=$SCR/home; mkdir -p "$HOME"   # stray ~/.cache, ~/.config, ~/.triton writes land on scratch
export VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1
export PIP_CACHE_DIR=$SCR/pip_cache XDG_CACHE_HOME=$SCR/cache VLLM_CACHE_ROOT=$SCR/cache/vllm \
       TRITON_CACHE_DIR=$SCR/cache/triton TORCHINDUCTOR_CACHE_DIR=$SCR/cache/inductor \
       PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=$SCR/cache/mpl
echo "code $CODE | logs $IBNR_LOG_DIR"
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
  rsync -aL --exclude 'blobs/' "$REAL_HOME/hf_cache/hub/$d/" "$SCR/hf_cache/hub/$d/"
done
export HF_HOME=$SCR/hf_cache HF_HUB_OFFLINE=1

cd "$REPO"
python -m pytest -q -p no:cacheprovider tests/
python sets.py            # refuses to overwrite if data/sets.jsonl would change
git rev-parse HEAD > "$IBNR_LOG_DIR/git_head.txt" 2> /dev/null || true

SETS=$(python pilot.py sets)
HIGH=$(python pilot.py sets --stratum high)
LOWHIGH=$(python pilot.py sets --stratum low,high)
echo "pilot sets: $SETS"

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

# ---- family A: workers, then managers (L, S; CAP on high; framing on low+high)
serve "$QWEN" "$QWEN_REV" 8000 A --dtype bfloat16 --max-model-len 32768
python pilot.py render --family A --out "$IBNR_LOG_DIR/render_A.json" || echo "render A failed"
python run.py --stage workers --sets "$SETS"
python run.py --stage managers --family A --sets "$SETS" --arms L,S
python run.py --stage managers --family A --sets "$HIGH" --arms CAP
python run.py --stage managers --family A --sets "$LOWHIGH" --arms S --framing responsible
python run.py --stage managers --family A --sets "$LOWHIGH" --arms S --framing placebo
grep -i "prefix cache hit" "$IBNR_LOG_DIR/vllm_A.log" | tail -1 || echo "no prefix-cache line"
stop

# ---- family B: managers on the same worker transcripts
serve "$MINI" "$MINI_REV" 8001 B --dtype bfloat16 --max-model-len 32768 \
  --tokenizer-mode mistral --config-format mistral --load-format mistral --limit-mm-per-prompt '{"image":0}'
python pilot.py render --family B --out "$IBNR_LOG_DIR/render_B.json" || echo "render B failed"
python run.py --stage managers --family B --sets "$SETS" --arms L,S
python run.py --stage managers --family B --sets "$HIGH" --arms CAP
stop

# ---- judge (QAT 4-bit Gemma 4 31B). First time this model is served: check vllm_judge.log if it dies.
serve "$JUDGE" "$JUDGE_REV" 8002 judge --max-model-len 16384
python pilot.py render --family judge --out "$IBNR_LOG_DIR/render_judge.json" || echo "render judge failed"
# prereg §5: native system role if the template renders our system text once; otherwise fold.
JUDGE_SYSTEM=$(python - "$IBNR_LOG_DIR/render_judge.json" <<'PY'
import json, sys
try:
    r = json.load(open(sys.argv[1]))
    print("native" if r.get("ok") and r["system_text_present"] and r["system_count"] == 1 else "fold")
except FileNotFoundError:
    print("fold")
PY
)
echo "judge system mode: $JUDGE_SYSTEM" | tee "$IBNR_LOG_DIR/judge_system_mode.txt"
python score.py judge --log-dir "$IBNR_LOG_DIR" --sets "$SETS" --families A,B --judge-system "$JUDGE_SYSTEM"
stop

python score.py score --log-dir "$IBNR_LOG_DIR" --sets "$SETS" --families A,B
python pilot.py summary --log-dir "$IBNR_LOG_DIR" | tee "$IBNR_LOG_DIR/pilot_summary.txt"
echo "done $(date)  logs (scratch on $(hostname)): $IBNR_LOG_DIR"
