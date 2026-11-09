# Data release: "The Empty Ledger: When Logging Issues First Lets a Lone Failure Slip Through"

Kaustubh Kumar, University of Edinburgh. Swarm Alignment Hackathon (Apart Research), November 2026.
DOI: [10.5281/zenodo.24047673](https://doi.org/10.5281/zenodo.24047673). Cite as: Kumar, K. (2026). Data for "The Empty Ledger: When Logging Issues First Lets a Lone Failure Slip Through" (v1) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.24047673
(The copy of this file inside `ibnr-release-v1.tar.gz` carries the earlier working title, "When Writing Issues Down Lets the Lone Failure Slip Through"; the data are identical.)
Code, pre-registration and deviations log: https://github.com/Kkumar-007/identified-not-reported (commit `b013f83` or later).

## Contents

`logs/`: every log directory used in the paper. `pilot_h200/` holds the 10 pilot sets (pre-registration §9; they count as part of the main run) and `main_s1/` to `main_s4/` hold the other 120 sets in four shards. Each directory contains:

| File | Contents |
|---|---|
| `calls.jsonl` | Every worker and coordinator model call (set, worker, arm, sample, family, framing, prompt hash, output, model, revision, seed, timestamp). |
| `episodes.jsonl`, `workers_final.jsonl`, `swaps.jsonl`, `worker_stats.json` | Worker episodes, the accepted episode per position, stage-B swaps, and acceptance statistics. |
| `manager_outputs.jsonl` | Coordinator ledgers and reports per set, arm, sample, family and framing. |
| `judge_calls.jsonl` | Every judge call (`J_ITEM`, `J_FALSE`, `J_OPT`, `J_CAUSE`), with raw outputs. |
| `prompts/<sha256>.json` | The exact rendered message list for each `prompt_hash` in the call logs. |
| `scores/` | Scored rows: `items.jsonl` (one row per injected failure × output), `ledgers.jsonl`, `reports.jsonl`, `issues.jsonl`, `score_meta.json`. |
| `manifest.jsonl`, `git_head*.txt`, `render_*.json`, `judge_system_mode.txt`, `vllm_*.log` | Run provenance: code commit, chat-template render checks, judge system-role mode, and serving logs. |

`labels/labels_key.jsonl`: the key for the 80 hand-labelled validation pairs. The blind sheet and the filled labels are in the repository under `results/labels/`.

## Reproducing the paper's numbers

From a clone of the repository:

```
python harness/analysis.py --log-dirs logs/pilot_h200,logs/main_s1,logs/main_s2,logs/main_s3,logs/main_s4 --out out/
cd logs && python ../harness/posthoc_checks.py          # D-8, checks E2 to E4
python harness/e1_recompute.py --logs logs --posthoc results/posthoc   # D-8, hand-checked absences
```

On this release, `results.json` and `results.md` are byte-identical to `results/analysis/` in the repository, and both post hoc outputs match `results/posthoc/` exactly.

## Redaction

This release is a copy of the full run archive (stress-results backup, sha256 `87b98056a13bbf902e1f274916a7e4214411f36f47f269560101ec801c386788`), plus `labels/labels_key.jsonl`. The only change is that the cluster username, which appeared in cache paths, was replaced with `UUN_REDACTED` in 25 files: `manifest.jsonl`, `scores/score_meta.json` and `vllm_A.log`, `vllm_B.log` and `vllm_judge.log` in each of the five directories. No other byte was changed. All content is synthetic Python code on MBPP+-derived problems and model outputs; there is no personal data.

## Licence and sources

Released under CC BY 4.0. The tasks derive from MBPP (Austin et al., 2021; CC BY 4.0) and MBPP+ (EvalPlus, Liu et al., 2023; Apache-2.0). The outputs were produced by Qwen/Qwen3-8B, mistralai/Ministral-3-8B-Instruct-2512-BF16 and google/gemma-4-31B-it-qat-w4a16-ct; see their model cards for terms.

## Checksums

`SHA256SUMS` lists every file in this release.
