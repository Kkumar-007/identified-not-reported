# Identified but Not Reported — harness

Apart Research Swarm Alignment Hackathon, Track 4.

**Preexisting material, declared:** `data/problems.csv`, `data/problems_check.csv` and the first draft of
`data/prompts.md` are preexisting planning material. All code in this folder was written
after the sprint started. See the root `README.md`.
`data/MbppPlus.jsonl.gz` is MBPP+ v0.2.0 (sha256 pinned in `config.yaml`; MBPP CC-BY-4.0, EvalPlus Apache-2.0).
`vendor_evalplus.py` is copied verbatim from evalplus 0.3.1 (Apache-2.0).

## Layout
| File | Role |
|---|---|
| `config.yaml` | models + revisions, endpoints, seeds, paths, caps |
| `sets.py` | 130 set specs from `master_seed` → `data/sets.jsonl` |
| `worker.py` | worker episodes, visible/hidden tests, acceptance checks, stage-B swaps |
| `manager.py` | L arm (ledger → report, one conversation), S arm, CAP/STRESS turn-2 variants, framing |
| `log.py` | append-only JSONL with resume keys; prompt store |
| `llm.py` | vLLM OpenAI-compatible client with call replay |
| `sandbox.py`, `sandbox_runner.py` | subprocess test runner (timeouts, rlimits, no network) |
| `run.py` | CLI |
| `dev/mock_server.py` | scripted endpoint for plumbing tests only (rows say `MOCK::`) |

## Run
```bash
python sets.py
python -m pytest -q tests/
export IBNR_LOG_DIR=~/ibnr_logs/run1
python run.py --stage workers  --sets H11 --dry-run
python run.py --stage workers  --sets H11
python run.py --stage managers --sets H11 --family A --arms L,S
python dev/show_logs.py $IBNR_LOG_DIR
```
On saxa: `sbatch slurm/smoke_one_set.sbatch`.
