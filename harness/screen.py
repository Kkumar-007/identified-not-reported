"""Stage A clean screen (problem_set.md §7, rule amended in Chat 6).

All 60 problems (primaries + reserves) x n_episodes clean worker episodes, first try only, with the
frozen worker settings (prompts v4). An episode passes if its first try meets every acceptance check
that applies to clean workers (1, 2, 6, 7 and the hidden suite). Selection:
  1. a problem qualifies at >= qualify_at passes out of n_episodes;
  2. each non-qualifying primary (P order) is replaced by a qualifying reserve of the same edge type
     (lowest R first), else the lowest qualifying reserve of any type; each reserve used once;
     R04 (remove_odd) may replace only P13;
  3. unreplaced primaries are dropped;
  4. floor: if fewer than min_problems remain, add the best-scoring non-qualifying problems
     (ties: P before R, then lower number), never creating a function-name clash; each is flagged;
  5. stage-B pool = qualifying reserves not used, in R order.
No manager output is read. Outputs: screen_results.json and stage-A rows in swaps.jsonl.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from common import derive_seed
from log import Logs, now_iso
from problems import Problem
from worker import WorkerCtx, run_episode

R04_ONLY_FOR = {"R04": "P13"}


def screen_specs(pids: list[str], n: int, seed: int) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    out = []
    for pid in pids:
        for k in range(n):
            spec = {"set_id": f"SCREEN-{pid}-{k:02d}", "stratum": "screen",
                    "seed": derive_seed(seed, "screen", pid, k), "amd_id": None}
            w = {"worker_id": "worker_1", "position": 0, "problem_id": pid, "cell": "clean"}
            spec["workers"] = [w]
            out.append((spec, w))
    return out


def _num(pid: str) -> int:
    return int(pid[1:])


def select_problems(scores: dict[str, int], problems: dict[str, Problem], primaries: list[str],
                    reserves: list[str], qualify_at: int, min_problems: int) -> dict[str, Any]:
    qual = {p for p, s in scores.items() if s >= qualify_at}
    final: list[str] = []
    used: set[str] = set()
    swaps: list[dict[str, Any]] = []
    dropped: list[str] = []
    for p in primaries:
        if p in qual:
            final.append(p)
            continue
        def ok(r: str) -> bool:
            return r in qual and r not in used and R04_ONLY_FOR.get(r, p) == p
        same = [r for r in reserves if ok(r) and problems[r].edge_type == problems[p].edge_type]
        anyr = [r for r in reserves if ok(r)]
        pick = (same or anyr or [None])[0]
        swaps.append({"original_id": p, "replacement_id": pick, "score": scores[p],
                      "same_edge_type": bool(same) and pick in same})
        if pick is None:
            dropped.append(p)
        else:
            used.add(pick)
            final.append(pick)
    below: list[str] = []
    if len(final) < min_problems:
        names = {problems[x].entry_point for x in final}
        cands = sorted((x for x in primaries + reserves if x not in final and x not in qual),
                       key=lambda x: (-scores[x], x[0] != "P", _num(x)))
        for x in cands:
            if len(final) >= min_problems:
                break
            if problems[x].entry_point in names:
                continue
            final.append(x)
            names.add(problems[x].entry_point)
            below.append(x)
    names = [problems[x].entry_point for x in final]
    if len(names) != len(set(names)):
        raise RuntimeError("function-name clash in the screened problem list")
    pool = [r for r in reserves if r in qual and r not in used]
    return {"problem_list": final, "stage_b_pool": pool, "swaps": swaps, "dropped": dropped,
            "added_below_threshold": below, "qualifying": sorted(qual, key=lambda x: (x[0] != "P", _num(x)))}


async def run_screen(ctx: WorkerCtx, logs: Logs, problems: dict[str, Problem]) -> dict[str, Any]:
    scfg = ctx.cfg["screen"]
    primaries = list(ctx.cfg["data"]["screen_primaries"])  # never the post-screen problem_list
    reserves = sorted((p for p in problems if p.startswith("R")), key=_num)
    pids = primaries + reserves
    n = scfg["n_episodes"]
    recs = await asyncio.gather(*(run_episode(ctx, spec, w, w["problem_id"], 0)
                                  for spec, w in screen_specs(pids, n, ctx.cfg["seeds"]["screen_seed"])))
    scores = {p: 0 for p in pids}
    fails: dict[str, dict[str, int]] = {p: {} for p in pids}
    for r in recs:
        scores[r["problem_id"]] += r["accepted"]
        for k, v in r["checks"].items():
            if not v:
                fails[r["problem_id"]][k] = fails[r["problem_id"]].get(k, 0) + 1
    sel = select_problems(scores, problems, primaries, reserves, scfg["qualify_at"], scfg["min_problems"])
    for i, s in enumerate(sel["swaps"]):
        row = {"stage": "A", "set_id": None, "position": None, "seq": i, "cell": None,
               "original_id": s["original_id"], "replacement_id": s["replacement_id"],
               "reason": {"screen_passes": s["score"], "of": n, "same_edge_type": s["same_edge_type"]},
               "tries": 1, "timestamp": now_iso()}
        if logs.swaps.get(logs.swaps.key(row)) is None:
            logs.swaps.append(row)
    out = {"rule": {"n_episodes": n, "qualify_at": scfg["qualify_at"], "min_problems": scfg["min_problems"],
                    "prompts_version": ctx.cfg["prompts_version"]},
           "scores": scores, "failed_checks": fails, **sel, "timestamp": now_iso()}
    (logs.dir / "screen_results.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def print_screen(out: dict[str, Any]) -> None:
    sc, n = out["scores"], out["rule"]["n_episodes"]
    print(f"\nstage A screen: qualify at >= {out['rule']['qualify_at']}/{n}, floor {out['rule']['min_problems']}")
    for pid in sorted(sc, key=lambda x: (x[0] != "P", _num(x))):
        mark = "Q" if pid in out["qualifying"] else " "
        print(f"  {pid} {sc[pid]:2d}/{n} {mark}  {out['failed_checks'][pid]}")
    print(f"\nswaps: {[(s['original_id'], s['replacement_id']) for s in out['swaps']]}")
    print(f"dropped: {out['dropped']}   added below threshold: {out['added_below_threshold']}")
    print(f"problems in list: {len(out['problem_list'])}   stage-B pool: {out['stage_b_pool']}")
    print("\nPASTE INTO config.yaml (after review):")
    print(f"  problem_list: [{', '.join(out['problem_list'])}]")
    print(f"  stage_b_pool: [{', '.join(out['stage_b_pool'])}]")
