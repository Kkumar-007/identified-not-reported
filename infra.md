# infra.md: compute and model choice
Chat 1 of 10 · planning only. Nothing here is a result; `[brackets]` = not yet measured. Tags: **[fact]** checked today on HF/docs, **[claim]** yours (proposal), **[sugg]** mine.

## 1. Models (pin the HF revision hash before the runs)
| Role | Model | Why | Watch |
|---|---|---|---|
| **A**: workers + managers | `Qwen/Qwen3-8B`, BF16, `enable_thinking: false` | dense GQA, mature vLLM prefix caching, Apache-2.0, ungated, 136M downloads [fact] | `max_position_embeddings` 40,960, so 32,768 fits at `--max-model-len 32768`. Measure the real manager prompt length in the pilot. If it's above ~29k, decide on YaRN **before** prereg |
| **B**: managers | `mistralai/Ministral-3-8B-Instruct-2512-BF16` | different lab, same size, dense, instruct-only (no hidden reasoning), Apache-2.0, ungated [fact] | Mistral recommends T < 0.1 and we run 0.7, so check the pilot for degenerate output. The repo ships a default `SYSTEM_PROMPT.txt`, so check that the rendered prompt carries only our system prompt |
| Judge | `gemma-4-31B-it` (open; see §4) | §4 | |

**Why 8B and not 14B [sugg].** In BF16, Qwen3-14B and Ministral-3-14B weigh about 28–30 GB. On an A100 40GB that leaves about 5 GB of KV cache, room for one 32k sequence. The 8B models (16.4 / 17.8 GB) leave about 16 GB, roughly 110k tokens at 136–144 KiB/token (computed from the configs). With 8B, a fallback GPU never forces a model change, and a mid-weekend model swap would be a deviation.

**Rejected:** `Qwen3.5-9B` is newer, but it's a hybrid Gated-DeltaNet model. Its vLLM prefix caching needs `--mamba-cache-mode align`, which LMCache's docs call experimental and not bit-exact between cached and fresh runs [fact], and prefix caching is our throughput plan. `gemma-4-12B-it` is the **B alternate** (vLLM-supported, ungated), but at 12B vs 8B it confounds family with scale. The default Ministral repo is FP8, which runs native FP8 on H100 and weight-only kernels on A100, so numerics would differ by GPU. Use `-BF16`. Llama-3.1-8B is gated and from 2024.

**Unsure:** whether Colab installs vLLM cleanly (the test checks this). Whether `cached_tokens` is reported in vLLM 0.33.0 (fallback: the "Prefix cache hit rate" line in `vllm.log`).

**Confound to name in the report:** A managers read A-written transcripts. B is the only control for same-family familiarity.

## 2. Serve + throughput test
`vllm` 0.33.0 is the current PyPI release [fact]. Pin the version that passes the test, and record `pip freeze`, GPU name and model revisions in a run manifest (not in the per-call JSONL keys).
```bash
pip install -q vllm==0.33.0 openai
nohup vllm serve Qwen/Qwen3-8B --dtype bfloat16 --max-model-len 32768 \
  --enable-prefix-caching --enable-prompt-tokens-details \
  --gpu-memory-utilization 0.90 --max-num-seqs 64 --seed 0 --port 8000 > vllm_A.log 2>&1 &
until curl -sf localhost:8000/health; do sleep 5; done
python infra_check/throughput_check.py --model Qwen/Qwen3-8B --qwen-no-think
# B: same flags plus  --tokenizer-mode mistral --config-format mistral --load-format mistral --limit-mm-per-prompt '{"image":0}'
# A100 40GB: --gpu-memory-utilization 0.92 --max-num-seqs 32
```
The script runs two phases. **A** is one 18k prefix with 20 parallel requests and a fixed 300-token output, giving decode tok/s. **B** is 20 *distinct* 18k prefixes with 1 output token each, giving prefill tok/s. I added phase B because one shared prefix ×20 overstates real cache reuse: a set gives about 6:1, not 20:1. The script prints a `PASTE THESE` line plus a projection. Delete it afterwards.

## 3. GPU-hour estimate (filled in when you paste numbers)
GPU-h ≈ Σ(unique prefill / P + decode / D) / 3600 × 1.5 overhead. All token sizes below are [sugg] assumptions to replace with pilot values (prefix 18k, ledger 800, report 200, worker 4k prefill / 1.5k decode).

| Component | Unique prefill | Decode |
|---|---|---|
| Workers (1,170 episodes) | 4.7M | 1.8M |
| Managers per family, 130 sets × 9 calls | 2.8M | 0.47M |
| Framing (480 calls) | 0.07M | 0.10M |

**Two runner rules that make this budget real [sugg; harness design]:**
1. **Schedule by set.** Submit L-turn-1 ×3 and S ×3 together, then L-turn-2, and keep about 4 sets in flight (≈ the test's concurrency). If calls interleave across sets, the cache evicts and manager prefill rises from about 2.8M to about 23M per family.
2. **Put the framing sentence after the transcripts,** inside the final instruction. Then framing reuses the cached prefix, and "arms differ only in the final instruction" stays literally true. If it goes in the system prompt, it adds about 2.9M prefill. This is a prereg decision.

**Family B at 130 sets:** under these assumptions B adds about 17% of decode tokens and about 25% of all tokens, because workers dominate. The verdict waits for your numbers.

### Measured (job 3700342, ICF Teaching, saxa, H200 MIG 3g.71gb, vLLM 0.33.0, Python 3.12.3) [fact]
| Model | decode tok/s (20 in flight) | prefill tok/s | phase-A cache frac |
|---|---|---|---|
| Qwen/Qwen3-8B (no-think) | 808 | 19,477 | 1.00 |
| Ministral-3-8B-Instruct-2512-BF16 | 836 | 19,023 | 1.00 |

Projection with §3 token assumptions: core incl. B@130 + framing = **1.1 GPU-h raw, about 1.7 with ×1.5**. D3 and D6 add minutes. **Verdict: keep B at 130 sets.** Caveats:
- Token sizes are assumptions; decode dominates, so ×3 longer outputs give about 4–5 GPU-h.
- Throughput was measured at 20 concurrent requests, so the runner must keep several sets or episodes in flight.
- Test prompts were about 15k tokens, not 18k.
- KV usage was about 6%, so `--max-num-seqs 64` is safe to try.

**Pinned [fact]:** `Qwen/Qwen3-8B` @ `b968826d9c46dd6066d109eabc6255188de91218`; `mistralai/Ministral-3-8B-Instruct-2512-BF16` @ `f6fae9795746f63c9be8344932f01275f3c63734`. Cached in `~/hf_cache`. In every sprint job, pass `--revision <hash>` to `vllm serve` and set `HF_HUB_OFFLINE=1`, so no job can silently pull a newer version. Runtime: vLLM 0.33.0, Python 3.12.3.

## 4. Judge: API vs open
| | `claude-sonnet-5-5` (API) | `gemma-4-31B-it` (open, H100) |
|---|---|---|
| Cost | About 2,800 calls, ~4.2M input, ≤3.2M output (with thinking). Batch $1/$5 per MTok, so ≤ $20; standard ≤ $40 [fact: prices] | $0 cash. [0.5–1] GPU-h on the run GPU plus a 62 GB download. Won't fit an A100 40GB in BF16 |
| Reliability | Stronger. Batch turnaround is not guaranteed | Weaker, and one more serving config to debug |
| Reproducibility | `temperature`/`top_p` return a 400 error [fact], so it can't be seeded, and the model may be retired later | Pinned revision, T = 0, anyone can rerun it |
| Independence | Third lab ✓ | Third lab only if B isn't Gemma |

**Recommend Sonnet 5.5:** Batch API for the main pass, standard API for the pilot, low effort, JSON output, blind to arm/framing/family. The judge is the *secondary* score and is gated by κ ≥ 0.7 against 80 hand labels, so accuracy on the lenient criterion matters most there. Reproducibility comes from the deterministic strict scorer plus the released judge logs. Haiku 5.5 (about $1) is the budget fallback. **Disclosure:** I'm a Claude model recommending a Claude judge. A comparable GPT or Gemini model is equally valid (I haven't checked their prices). The real constraint is that the judge is neither family A nor B.

**Judge decision:** `gemma-4-31B-it` (open weights, Google, a third lab; $0), replacing the Sonnet recommendation because there's no API budget. Both variants are cached in `~/hf_cache`, with byte sizes checked against the Hub [fact]:
- BF16 `google/gemma-4-31B-it` @ `842da3794eaa0b77d5f08bae87a17459d91ff475` (62.5 GB). Needs the full `gpu:h200:1` on saxa (one card, may be busy).
- QAT 4-bit `google/gemma-4-31B-it-qat-w4a16-ct` @ `52f3f65bc7a02d555763bc923bd1d9094898219d` (23.3 GB). Fits one `h200_3g.71gb` slice.

**Chosen (pre-prereg): QAT w4a16 @ `52f3f65b…219d` on one `h200_3g.71gb` slice.** BF16 copy deleted from `~/hf_cache`. Methods must say "QAT 4-bit (w4a16)". Any change after prereg is a DEVIATION. Judge GPU time is about 3 GPU-h [extrapolated, unmeasured], so measure it in the pilot. Jobs should rsync the weights to `/disk/scratch` before loading (cluster tips: don't read heavily from the shared filesystem).

## 5. Compute at £0 (paid Colab and Eddie ruled out)
Run the throughput test on each route. Pick the best route that passes before the runs. The models and the design are the same on every route; only precision can change (the T4 has no BF16).

| Route | Hardware | Cost | Blocker |
|---|---|---|---|
| **1. ICF Teaching partition ✓ tested; course organiser OK'd non-course use** | Teaching nodes: 8× RTX A6000 48 GB, H200 141 GB split into vGPU slices [fact, config may change] | free teaching allocation for PGT [fact] | Is non-course use OK? Ask the course organiser explicitly. Gres names, slice sizes, internet on nodes and home quota are [unverified]; check with `sinfo`. A6000 decode is slower than an A100 |
| **2. Modal Starter** | H100 $3.95/h, A100-80 $2.50/h [fact] | $30/month free ≈ 7.6 H100-h or 12 A100-80-h | Card requirement [unverified]. Billed per second while the container is up. The academic grant (up to $10k) is apply-only, so unlikely in time |
| **3. Kaggle** | 2×T4 16GB, `--tensor-parallel-size 2 --dtype float16` | free, ~30 h/week [reported], 12 h sessions | Phone verification needed for GPU and internet. Decode much slower (T4 bandwidth is about 1/10 of an H100). fp16, not BF16. vLLM 0.33 on T4 [unverified] |
| ✗ Eddie | A100 80GB – H200 | — | Ruled out: needs a staff supervisor with a connection to the work, and the sprint organisers aren't University staff |
| ✗ ICF non-teaching 2080 Ti nodes | RTX 2080 Ti 11 GB | free | 8B in fp16 doesn't fit. CPU work only |
| ✗ Colab free | 1×T4 15 GB | free | 8B in fp16 doesn't fit |

Also ask the Apart help desk whether the sprint offers compute credits.

**Fit check:** the proposal says the core "fits in a few GPU-hours on one H100" [claim]. If that's true, Modal's $30 covers it. Confirm with the throughput numbers before relying on it.

**Rules:**
- Use one route per family manager run. Record GPU, dtype and vLLM version in the manifest.
- Fix the precision (BF16 or fp16 on T4) in prereg.md, then disclose it in Methods. A change after prereg is a **DEVIATION**.
- Hardware never changes the model.
- If the chosen route can't finish the core in the window, apply the cut order from D9 (`design_decisions.md`): AI Village → D6 → B to 60 sets → framing. Never cut family A core, gates 1–3 or the hand labels.
- Budget D3 (about 240 manager calls) into the core estimate.

**Judge with no API budget:** D4 roughly doubles judge calls. That puts the §4 Sonnet estimate at about $40 batch, and Haiku 5.5 batch at about $2 [estimate]. If even that's unaffordable: strict-only plus the hand labels. The κ-fallback definition is open issue F (Chat 5).
