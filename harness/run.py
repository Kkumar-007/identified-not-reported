"""CLI for the harness.

  python run.py --stage workers  --sets H11            [--dry-run]
  python run.py --stage managers --sets H11 --family A [--arms L,S] [--framing neutral]
  python run.py --stage managers --sets L01-L40,H01-H40 --family A --arms S --framing responsible

--sets: "all", or a comma list of ids and ranges (C01-C30, L01-L40, H01-H40, A01-A20).
Logs go to paths.log_dir (or --log-dir). Re-running the same command resumes: logged calls are
replayed, finished episodes and sets are skipped.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import platform
import re
import subprocess
import sys
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import openai

from common import REPO, load_config, sha256_file
from llm import LLM
from log import Logs, now_iso
from manager import ARMS, FRAMING_PROMPT, SetManager, build_context
from problems import load_problems
from prompts import Prompts, check_test_runs, check_word_caps, framing_sentence
from sandbox import Sandbox
from sets import load_sets
from screen import print_screen, run_screen
from worker import WorkerCtx, build_layout, render_worker_prompt, run_set_workers

_RANGE = re.compile(r"^([A-Z])(\d+)-\1?(\d+)$")


def select_sets(all_sets: list[dict[str, Any]], spec: str) -> list[dict[str, Any]]:
    by_id = {s["set_id"]: s for s in all_sets}
    if spec == "all":
        return list(all_sets)
    want: list[str] = []
    for part in [p.strip() for p in spec.split(",") if p.strip()]:
        m = _RANGE.match(part)
        if m:
            pre, a, b = m.group(1), int(m.group(2)), int(m.group(3))
            want += [f"{pre}{i:02d}" for i in range(a, b + 1)]
        else:
            want.append(part)
    unknown = [w for w in want if w not in by_id]
    if unknown:
        raise SystemExit(f"unknown set ids: {unknown}")
    return [by_id[w] for w in dict.fromkeys(want)]


def git_commit() -> str | None:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, timeout=10)
    except FileNotFoundError:
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def gpu_name() -> str | None:
    try:
        r = subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True, timeout=10)
    except FileNotFoundError:
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def write_manifest(logs: Logs, cfg: dict[str, Any], pr: Prompts, args: argparse.Namespace,
                   served: dict[str, list[str]], sandbox: Sandbox | None) -> None:
    logs.manifest.append({
        "run_id": uuid.uuid4().hex, "timestamp": now_iso(), "argv": sys.argv,
        "stage": getattr(args, "stage", "probe"), "family": getattr(args, "family", None),
        "framing": getattr(args, "framing", None), "arms": getattr(args, "arms", None),
        "overrides": getattr(args, "override", []), "prompt_block_versions": pr.versions,
        "worker_settings": {k: cfg["worker"][k] for k in ("temperature", "max_tokens", "enable_thinking",
                                                          "injection_placement", "de_fill_rule",
                                                          "regen_on_unplanned_hidden", "max_test_runs",
                                                          "au_spec_omits_requirement", "au_cite_instruction")},
        "git_commit": git_commit(), "config_sha256": sha256_file(args.config),
        "prompts_md_sha256": pr.md_sha256, "prompts_version": cfg["prompts_version"],
        "sets_sha256": sha256_file(cfg["paths"]["sets_file"]),
        "mbppplus_sha256": cfg["data"]["mbppplus_sha256"],
        "python": platform.python_version(), "openai": openai.__version__,
        "served_models": served, "gpu": gpu_name(), "host": platform.node(),
        "unshare_net": None if sandbox is None else sandbox.unshare,
        "models": {k: {"model": v["model"], "revision": v["revision"]} for k, v in cfg["models"].items()},
    })


def worker_extra_body(cfg: dict[str, Any]) -> dict[str, Any]:
    """Family-A extra_body with the worker-only thinking switch applied."""
    fam = cfg["worker"]["family"]
    body = json.loads(json.dumps(cfg["models"][fam].get("extra_body") or {}))
    body.setdefault("chat_template_kwargs", {})["enable_thinking"] = bool(cfg["worker"]["enable_thinking"])
    return body


def log_dir(cfg: dict[str, Any], args: argparse.Namespace) -> str:
    d = args.log_dir or cfg["paths"]["log_dir"]
    if not d:
        raise SystemExit("no log directory: set IBNR_LOG_DIR or pass --log-dir")
    return d


async def preflight(llm: LLM) -> list[str]:
    served = await llm.served_models()
    if llm.model not in served:
        raise SystemExit(f"endpoint {llm.base_url} serves {served}, not {llm.model}")
    return served


# ---------------------------------------------------------------- workers

def dry_run_workers(cfg: dict[str, Any], pr: Prompts, problems: dict[str, Any], sets: list[dict[str, Any]]) -> None:
    import random
    from common import derive_seed
    shown = False
    for s in sets:
        for w in s["workers"]:
            p = problems[w["problem_id"]]
            lay = build_layout(p, w["cell"], random.Random(derive_seed(s["seed"], "layout", w["position"], p.id)))
            msgs = render_worker_prompt(pr, p, w["cell"], lay, s.get("amd_id"),
                                        cfg["worker"]["injection_placement"], cfg["worker"]["de_fill_rule"],
                                        cfg["worker"]["au_spec_omits_requirement"],
                                        cfg["worker"]["au_cite_instruction"])
            print(f"{s['set_id']} {w['worker_id']} {w['cell']:5s} {p.id} {p.entry_point:30s} "
                  f"visible={len(lay.visible)} hidden_tests={len(lay.hidden)} "
                  f"planned_hidden_fail={None if lay.planned_hidden_fail is None else sorted(lay.planned_hidden_fail)}")
            if not shown and w["cell"] != "clean":
                print("---- system ----\n" + msgs[0]["content"] + "\n---- user ----\n" + msgs[1]["content"] + "\n----")
                shown = True


async def stage_workers(cfg: dict[str, Any], args: argparse.Namespace, pr: Prompts,
                        problems: dict[str, Any], sets: list[dict[str, Any]]) -> None:
    fam = cfg["worker"]["family"]
    if args.family not in (None, fam):
        raise SystemExit(f"workers are family {fam} (config worker.family)")
    if args.dry_run:
        dry_run_workers(cfg, pr, problems, sets)
        return
    logs = Logs(log_dir(cfg, args))
    sem = asyncio.Semaphore(cfg["serving"]["max_in_flight"])
    llm = LLM(fam, cfg["models"][fam], cfg["serving"], logs, sem, extra_body=worker_extra_body(cfg))
    sandbox = Sandbox(cfg["worker"])
    served = await preflight(llm)
    write_manifest(logs, cfg, pr, args, {fam: served}, sandbox)
    ctx = WorkerCtx(cfg=cfg, prompts=pr, problems=problems, llm=llm, sandbox=sandbox, logs=logs,
                    episode_sem=asyncio.Semaphore(cfg["worker"]["episodes_in_flight"]))
    finals = await asyncio.gather(*(run_set_workers(ctx, s) for s in sets))
    summarise_workers(logs, {s["set_id"] for s in sets}, finals)
    print(f"calls sent={llm.n_sent} replayed={llm.n_replayed}")


def summarise_workers(logs: Logs, set_ids: set[str], finals: list[dict[str, Any]]) -> None:
    eps = [e for e in logs.episodes.rows() if e["set_id"] in set_ids]
    per_cell: dict[str, Counter] = defaultdict(Counter)
    for e in eps:
        c = per_cell[e["cell"]]
        c["episodes"] += 1
        c["accepted"] += e["accepted"]
        for k, v in e["checks"].items():
            c[f"fail_{k}"] += not v
        if e["hidden"] and e["hidden"]["unplanned"]:
            c["unplanned_hidden"] += 1
    positions = Counter((e["set_id"], e["worker_id"], e["cell"]) for e in eps)
    print("cell   positions episodes accepted regen_rate unplanned_hidden failed_checks")
    stats = {}
    for cell, c in sorted(per_cell.items()):
        npos = sum(1 for k in positions if k[2] == cell)
        regen = (c["episodes"] - npos) / npos if npos else 0.0
        fails = {k[5:]: v for k, v in c.items() if k.startswith("fail_") and v}
        print(f"{cell:6s} {npos:9d} {c['episodes']:8d} {c['accepted']:8d} {regen:10.2f} "
              f"{c['unplanned_hidden']:16d} {fails}")
        stats[cell] = {"positions": npos, **dict(c), "regenerations_per_position": regen}
    excl = [f["set_id"] for f in finals if f["excluded"]]
    print(f"sets: {len(finals)} done, {len(excl)} excluded {excl}")
    (logs.dir / "worker_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")


async def stage_screen(cfg: dict[str, Any], args: argparse.Namespace, pr: Prompts,
                       problems: dict[str, Any]) -> None:
    fam = cfg["worker"]["family"]
    n = len(problems) * cfg["screen"]["n_episodes"]
    if args.dry_run:
        print(f"screen: {len(problems)} problems x {cfg['screen']['n_episodes']} clean episodes = {n}, "
              f"prompts {cfg['prompts_version']}, qualify at >= {cfg['screen']['qualify_at']}, "
              f"floor {cfg['screen']['min_problems']}")
        return
    logs = Logs(log_dir(cfg, args))
    llm = LLM(fam, cfg["models"][fam], cfg["serving"], logs, asyncio.Semaphore(cfg["serving"]["max_in_flight"]),
              extra_body=worker_extra_body(cfg))
    sandbox = Sandbox(cfg["worker"])
    served = await preflight(llm)
    write_manifest(logs, cfg, pr, args, {fam: served}, sandbox)
    ctx = WorkerCtx(cfg=cfg, prompts=pr, problems=problems, llm=llm, sandbox=sandbox, logs=logs,
                    episode_sem=asyncio.Semaphore(cfg["worker"]["episodes_in_flight"]))
    print_screen(await run_screen(ctx, logs, problems))
    print(f"calls sent={llm.n_sent} replayed={llm.n_replayed}")


# ---------------------------------------------------------------- managers

def accepted_episodes(logs: Logs, final: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out = {}
    for pos in final["positions"]:
        ep = logs.episodes.get((final["set_id"], pos["worker_id"], pos["problem_id"], pos["try"]))
        if ep is None or not ep["accepted"]:
            raise RuntimeError(f"{final['set_id']} {pos['worker_id']}: accepted episode missing from log")
        out[pos["worker_id"]] = ep
    return out


async def check_framing_tokens(cfg: dict[str, Any], pr: Prompts, llm: LLM) -> None:
    pre, rep = "</transcripts>\n\n", pr.raw("REPORT")
    base = await llm.count_tokens(pre + rep)
    n = {}
    for pid in ("FRAME_R", "FRAME_P"):
        n[pid] = await llm.count_tokens(pre + framing_sentence(pr, pid) + " " + rep) - base
    print(f"framing tokens (served tokenizer): {n}")
    if abs(n["FRAME_R"] - n["FRAME_P"]) > cfg["manager"]["framing_token_tolerance"]:
        raise SystemExit(f"framing token counts differ by more than the tolerance: {n}")


async def stage_managers(cfg: dict[str, Any], args: argparse.Namespace, pr: Prompts,
                         problems: dict[str, Any], sets: list[dict[str, Any]]) -> None:
    if args.family not in cfg["models"] or args.family == "judge":
        raise SystemExit("--family A or B is required for managers")
    arms = args.arms.split(",")
    if any(a not in ARMS for a in arms):
        raise SystemExit(f"--arms must be drawn from {ARMS}")
    if args.framing != "neutral":
        if arms != ["S"]:
            raise SystemExit("non-neutral framing runs the S arm only: pass --arms S")
        if args.family != "A":
            raise SystemExit("framing (H5) is family A only")
        off = [s["set_id"] for s in sets if s["stratum"] not in ("low", "high")]
        if off:
            raise SystemExit(f"framing runs on low- and high-pressure sets only; remove {off}")
    if "CAP" in arms or "STRESS" in arms:
        off = [s["set_id"] for s in sets if s["stratum"] != "high"]
        if off:
            raise SystemExit(f"CAP/STRESS run on high-pressure sets only; remove {off}")
    logs = Logs(log_dir(cfg, args))
    ready, missing, excluded = [], [], []
    for s in sets:
        f = logs.workers_final.get((s["set_id"],))
        if f is None:
            missing.append(s["set_id"])
        elif f["excluded"]:
            excluded.append(s["set_id"])
        else:
            ready.append((s, f))
    if missing:
        raise SystemExit(f"workers not finished for {missing}; run --stage workers first")
    if excluded:
        print(f"skipping excluded sets: {excluded}")
    if args.dry_run:
        for s, f in ready:
            ctx = build_context(pr, problems, f, accepted_episodes(logs, f))
            print(f"{s['set_id']}: system {len(ctx.system)} chars, prefix {len(ctx.user_prefix)} chars, "
                  f"arms {arms}, framing {args.framing}, samples {cfg['manager']['samples']}")
        return
    sem = asyncio.Semaphore(cfg["serving"]["max_in_flight"])
    llm = LLM(args.family, cfg["models"][args.family], cfg["serving"], logs, sem)
    served = await preflight(llm)
    if args.framing != "neutral":
        await check_framing_tokens(cfg, pr, llm)
    write_manifest(logs, cfg, pr, args, {args.family: served}, None)
    mgr = SetManager(cfg, pr, llm, logs, args.family)
    set_sem = asyncio.Semaphore(cfg["manager"]["sets_in_flight"])

    async def one(s: dict[str, Any], f: dict[str, Any]) -> None:
        async with set_sem:
            ctx = build_context(pr, problems, f, accepted_episodes(logs, f))
            await mgr.run_set(s, ctx, arms, args.framing)

    await asyncio.gather(*(one(s, f) for s, f in ready))
    print(f"calls sent={llm.n_sent} replayed={llm.n_replayed}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(REPO / "config.yaml"))
    ap.add_argument("--stage", required=True, choices=["workers", "managers", "screen"])
    ap.add_argument("--family", default=None)
    ap.add_argument("--sets", default=None, help="required for workers/managers")
    ap.add_argument("--framing", default="neutral", choices=list(FRAMING_PROMPT))
    ap.add_argument("--arms", default="L,S")
    ap.add_argument("--dry-run", action="store_true", help="render prompts, make no calls, write no logs")
    ap.add_argument("--log-dir", default=None)
    ap.add_argument("--override", action="append", default=[], metavar="KEY=VALUE",
                    help="config override, e.g. data.stage_b_pool=[R01,R03] (repeatable; logged in the manifest)")
    args = ap.parse_args()
    cfg = load_config(args.config, args.override)
    pr = Prompts(cfg["paths"]["prompts_md"], cfg["paths"]["prompts_dir"], cfg["prompts_version"])
    check_word_caps(pr, cfg["manager"]["word_cap"], cfg["manager"]["stress_word_cap"])
    check_test_runs(pr, cfg["worker"]["max_test_runs"])
    problems = load_problems(cfg)
    if args.stage == "screen":
        asyncio.run(stage_screen(cfg, args, pr, problems))
        return
    if args.sets is None:
        raise SystemExit("--sets is required for workers and managers")
    if not Path(cfg["paths"]["sets_file"]).exists():
        raise SystemExit("sets file missing: run `python sets.py` first")
    sets = select_sets(load_sets(cfg["paths"]["sets_file"]), args.sets)
    used = {w["problem_id"] for s in sets for w in s["workers"]} | set(cfg["data"]["stage_b_pool"])
    unknown = used - set(problems)
    if unknown:
        raise SystemExit(f"sets reference unknown problems {sorted(unknown)}")
    if args.stage == "workers":
        asyncio.run(stage_workers(cfg, args, pr, problems, sets))
    else:
        asyncio.run(stage_managers(cfg, args, pr, problems, sets))


if __name__ == "__main__":
    main()
