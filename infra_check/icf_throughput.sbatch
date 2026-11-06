#!/bin/bash
# DISPOSABLE pre-sprint infra check (ICF Teaching partition). Not project code.
# One 71 GB H200 MIG slice on saxa. Submit only with the course organiser's OK for non-course use.
# Submit from ~/infra_check:  cd ~/infra_check && sbatch icf_throughput.sbatch
#SBATCH -J icf_throughput
#SBATCH -p Teaching
#SBATCH --gres=gpu:h200_3g.71gb:1
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH -o %x_%j.log
set -euo pipefail

# Few, large files (model weights, pip wheels): shared home, persists across nodes.
export HF_HOME=$HOME/hf_cache
export PIP_CACHE_DIR=$HOME/pip_cache
# Many small files (the venv): node-local scratch, reused if already there.
SCR=/disk/scratch/$USER
VENV=$SCR/venv
mkdir -p "$SCR" "$HF_HOME" "$PIP_CACHE_DIR"
# The node reaches the internet through a proxy; local calls to vLLM must bypass it.
export no_proxy="localhost,127.0.0.1${no_proxy:+,$no_proxy}"
export NO_PROXY="$no_proxy"

echo "node: $(hostname)  start: $(date)"
nvidia-smi -L

if [ ! -x "$VENV/bin/vllm" ]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q vllm==0.33.0 openai
fi
source "$VENV/bin/activate"
python -c "import sys, vllm; print('vllm', vllm.__version__, '| python', sys.version.split()[0])"

run_model () {  # $1 model id, $2 tag, $3 throughput-script flags, rest = extra vllm serve flags
  local model=$1 tag=$2 thru_flags=$3; shift 3
  echo "== $tag: $model  $(date)"
  vllm serve "$model" --dtype bfloat16 --max-model-len 32768 \
    --enable-prefix-caching --enable-prompt-tokens-details \
    --gpu-memory-utilization 0.90 --max-num-seqs 32 --seed 0 --port 8000 "$@" \
    > "$SCR/vllm_$tag.log" 2>&1 &
  local vpid=$!
  until curl -sf localhost:8000/health > /dev/null; do
    sleep 10
    if ! kill -0 "$vpid" 2> /dev/null; then
      echo "vLLM ($tag) exited during startup:"; tail -50 "$SCR/vllm_$tag.log"
      cp "$SCR/vllm_$tag.log" ~/infra_check/; return 1
    fi
  done
  python ~/infra_check/throughput_check.py --model "$model" $thru_flags
  grep -i "prefix cache hit" "$SCR/vllm_$tag.log" | tail -1 || echo "no prefix-cache line in log"
  kill "$vpid"; wait "$vpid" 2> /dev/null || true
  cp "$SCR/vllm_$tag.log" ~/infra_check/
}

# Family A
run_model Qwen/Qwen3-8B A "--qwen-no-think" || echo "FAMILY A FAILED"

# Family B: fetch only the consolidated weights (skip the duplicate HF shards, about 18 GB)
python -c "from huggingface_hub import snapshot_download as s; s('mistralai/Ministral-3-8B-Instruct-2512-BF16', ignore_patterns=['model-*.safetensors'])"
run_model mistralai/Ministral-3-8B-Instruct-2512-BF16 B "" \
  --tokenizer-mode mistral --config-format mistral --load-format mistral \
  --limit-mm-per-prompt '{"image":0}' || echo "FAMILY B FAILED"

echo "done: $(date)"
