"""Worker-prompt probe (Chat 6, pilot rule prompts.md §6): which worker variant to freeze for prereg.

Variants (same problems, cells, seeds, acceptance checks; only worker prompts/settings differ):
  A  v1 prompts (baseline): W_INJ_DEV in W_SYS, CSV edge-deviation labels
  B  v2 prompts: W_SYS v2 + W_INJ_DEV v2 (end of task message, requirement fill rule)
  C  B + Qwen3 thinking for workers (max_tokens 8192); thinking is stripped before anything else sees it

Design: 15 primaries (drawn with screen_seed) x 6 cells (clean, AC, AE, DC, DE, AU), ONE episode each
(first try only, no regeneration), so the outcome is a first-try acceptance rate per cell.
Only worker behaviour is measured; no manager is involved.

  D  v3: W_SYS v3 (one test run, every cell) + AU fill rule v3 (AU worker spec omits the withdrawn
     requirement). Probe 2 compares B vs D with --rule v3 (see select_v3).

Probe-1 selection rule (fixed before probe 1, approved; superseded for probe 2):
  1. score = minimum over cells of the first-try acceptance rate;
  2. among variants within 10 points of the best score, take the one with fewest changes (A < B < C);
  3. if no variant reaches >= 50% in both DC and DE, STOP: reconsider the deviation cells.

  python dev/worker_probe.py --out $IBNR_LOG_DIR/probe [--variants A,B,C] [--n-problems 15]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import derive_seed, load_config  # noqa: E402
from llm import LLM  # noqa: E402
from log import Logs  # noqa: E402
from problems import load_problems  # noqa: E402
from prompts import Prompts, check_test_runs, check_word_caps  # noqa: E402
from run import preflight, worker_extra_body, write_manifest  # noqa: E402
from sandbox import Sandbox  # noqa: E402
from worker import STATUS_ANYWHERE_RE, WorkerCtx, run_episode  # noqa: E402

CELLS = ["clean", "AC", "AE", "DC", "DE", "AU"]
VARIANTS: dict[str, list[str]] = {
    "A": ["prompts_version=v1", "worker.injection_placement=system", "worker.de_fill_rule=csv",
          "worker.max_test_runs=4", "worker.au_spec_omits_requirement=false", "worker.au_cite_instruction=false"],
    "B": ["prompts_version=v2", "worker.max_test_runs=4", "worker.au_spec_omits_requirement=false",
          "worker.au_cite_instruction=false"],
    "C": ["prompts_version=v2", "worker.max_test_runs=4", "worker.au_spec_omits_requirement=false",
          "worker.au_cite_instruction=false", "worker.enable_thinking=true", "worker.max_tokens=8192"],
    # v3 (Chat 6, probe 2): one test run in every cell + AU worker spec omits the withdrawn requirement
    "D": ["prompts_version=v3", "worker.max_test_runs=1", "worker.au_spec_omits_requirement=true",
          "worker.au_cite_instruction=false"],
    # v4 (Chat 6, probe 3): v3 + W_INJ_AU (AU worker asked to give the amendment ID in deviations)
    "E": ["prompts_version=v4", "worker.max_test_runs=1", "worker.au_spec_omits_requirement=true",
          "worker.au_cite_instruction=true"],
}
N_CHANGES = {"A": 0, "B": 1, "C": 2, "D": 2, "E": 3}


def probe_specs(problem_ids: list[str], seed: int, cells: list[str] | None = None
                ) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    out = []
    for cell in cells or CELLS:
        for pid in problem_ids:
            set_seed = derive_seed(seed, "probe", cell, pid)
            spec = {"set_id": f"PROBE-{cell}-{pid}", "stratum": "probe", "seed": set_seed,
                    "amd_id": f"AMD-{set_seed % 10000:04d}" if cell == "AU" else None}
            w = {"worker_id": "worker_1", "position": 0, "problem_id": pid, "cell": cell}
            spec["workers"] = [w]
            out.append((spec, w))
    return out


async def run_variant(name: str, base_cfg_path: str, out: Path, pids: list[str], seed: int,
                      cells: list[str] | None = None) -> list[dict[str, Any]]:
    cfg = load_config(base_cfg_path, VARIANTS[name])
    pr = Prompts(cfg["paths"]["prompts_md"], cfg["paths"]["prompts_dir"], cfg["prompts_version"])
    check_word_caps(pr, cfg["manager"]["word_cap"], cfg["manager"]["stress_word_cap"])
    check_test_runs(pr, cfg["worker"]["max_test_runs"])
    problems = load_problems(cfg)
    logs = Logs(out / f"variant_{name}")
    fam = cfg["worker"]["family"]
    llm = LLM(fam, cfg["models"][fam], cfg["serving"], logs, asyncio.Semaphore(cfg["serving"]["max_in_flight"]),
              extra_body=worker_extra_body(cfg))
    sandbox = Sandbox(cfg["worker"])
    served = await preflight(llm)
    ns = argparse.Namespace(stage="probe", config=base_cfg_path, override=VARIANTS[name])
    write_manifest(logs, cfg, pr, ns, {fam: served}, sandbox)
    ctx = WorkerCtx(cfg=cfg, prompts=pr, problems=problems, llm=llm, sandbox=sandbox, logs=logs,
                    episode_sem=asyncio.Semaphore(cfg["worker"]["episodes_in_flight"]))
    recs = await asyncio.gather(*(run_episode(ctx, spec, w, w["problem_id"], 0)
                                  for spec, w in probe_specs(pids, seed, cells)))
    print(f"[{name}] calls sent={llm.n_sent} replayed={llm.n_replayed}", flush=True)
    return recs


def summarise(recs: list[dict[str, Any]]) -> dict[str, Any]:
    by_cell: dict[str, dict[str, Any]] = {}
    for cell in CELLS:
        rs = [r for r in recs if r["cell"] == cell]
        if not rs:
            continue
        fails = Counter(k for r in rs for k, v in r["checks"].items() if not v)
        code_msgs = [t[0] for r in rs for t in r["manager_view"]["turns"]]
        by_cell[cell] = {
            "n": len(rs), "accepted": sum(r["accepted"] for r in rs),
            "rate": sum(r["accepted"] for r in rs) / len(rs) if rs else 0.0,
            "failed_checks": dict(fails),
            "status_line_in_code_msg": sum(bool(STATUS_ANYWHERE_RE.search(m)) for m in code_msgs),
            "code_msgs": len(code_msgs),
            "mean_runs": sum(r["n_runs"] for r in rs) / len(rs) if rs else 0.0,
            "think_stripped": sum(r["think_stripped"] for r in rs),
        }
    return by_cell


def select_v3(summary: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Probe-2 adoption rule (fixed before it ran, prompts.md changelog): adopt v3 (D) only if every
    cell >= 50% first-try acceptance AND D is no more than 10 points below B in clean, AC, AE."""
    d, b = summary["D"], summary["B"]
    all_cells = {c: d[c]["rate"] >= 0.5 for c in CELLS}
    not_worse = {c: d[c]["rate"] >= b[c]["rate"] - 0.10 for c in ("clean", "AC", "AE")}
    adopt = all(all_cells.values()) and all(not_worse.values())
    return {"rule": "v3", "D_cells_ge_50": all_cells, "D_not_10pts_below_B": not_worse, "adopt_v3": adopt,
            "otherwise": None if adopt else "option 4: drop deviation cells; decide AU / gate 1"}


def select_au(summary: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Probe-3 rule (fixed before it ran): adopt v4 (E) if AU first-try acceptance >= 50%, strict check 5."""
    rate = summary["E"]["AU"]["rate"]
    return {"rule": "au", "E_AU_rate": rate, "adopt_v4": rate >= 0.5,
            "otherwise": None if rate >= 0.5 else "option 4 with v3 workers, without gate 1: discuss"}


def select(summary: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Probe-1 rule. Superseded: degenerate when one cell is 0 in every variant (see prompts.md)."""
    score = {v: min(c["rate"] for c in s.values()) for v, s in summary.items()}
    best = max(score.values())
    near = [v for v in score if score[v] >= best - 0.10]
    chosen = min(near, key=lambda v: N_CHANGES[v])
    dev_ok = {v: s["DC"]["rate"] >= 0.5 and s["DE"]["rate"] >= 0.5 for v, s in summary.items()}
    return {"score_min_cell": score, "best": best, "within_10_points": near, "chosen": chosen,
            "dev_cells_ge_50": dev_ok, "stop_reconsider_deviation_cells": not any(dev_ok.values())}


async def main_async(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    pids = random.Random(derive_seed(cfg["seeds"]["screen_seed"], "probe")).sample(cfg["data"]["problem_list"],
                                                                                   args.n_problems)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    names = args.variants.split(",")
    cells = args.cells.split(",") if args.cells else None
    results = await asyncio.gather(*(run_variant(v, args.config, out, sorted(pids), cfg["seeds"]["screen_seed"], cells)
                                     for v in names))
    summary = {v: summarise(r) for v, r in zip(names, results)}
    decision = {"v3": select_v3, "au": select_au, "probe1": select}[args.rule](summary)
    print(f"\nproblems: {sorted(pids)}\n")
    print("variant cell   accepted  rate  code_msgs_with_status  mean_runs  failed_checks")
    for v in names:
        for cell in [c for c in CELLS if c in summary[v]]:
            c = summary[v][cell]
            print(f"{v:7s} {cell:6s} {c['accepted']:3d}/{c['n']:<3d}   {c['rate']:.2f}  "
                  f"{c['status_line_in_code_msg']:3d}/{c['code_msgs']:<3d}               {c['mean_runs']:.1f}       "
                  f"{c['failed_checks']}")
    print("\nselection:", json.dumps(decision))
    (out / "probe_summary.json").write_text(json.dumps({"problems": sorted(pids), "summary": summary,
                                                        "decision": decision}, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(Path(__file__).resolve().parents[1] / "config.yaml"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--variants", default="A,B,C")
    ap.add_argument("--n-problems", type=int, default=15)
    ap.add_argument("--rule", choices=["probe1", "v3", "au"], default="v3")
    ap.add_argument("--cells", default=None, help="comma list; default all six")
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()
