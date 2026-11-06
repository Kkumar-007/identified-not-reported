"""Pilot helpers (prereg.md §9) and the pre-specified family-B 60-set subset (§10).

  python pilot.py sets [--stratum clean|low|high|auth[,...]]   pilot set ids, comma-separated
  python pilot.py b60                                           family-B 60-set subset (§10)
  python pilot.py render --family A|B|judge [--out FILE]        chat-template rendering check
  python pilot.py summary --log-dir D [--sets SPEC]             §9 counts only
  python pilot.py fork --src D --dst D2                         worker logs only, for a re-pilot
  python pilot.py shard --k 4 --i 1 [--stratum high]            main-run shard i of k (non-pilot sets)

Draw (§9, §10; reading recorded in deviations.md): one random.Random(derive_seed(master_seed,
<tag>)) object; strata in the order clean, low, high, auth; within each, the sorted set ids are
shuffled with that object and the first n are taken.

`summary` prints only what §9 allows: worker-side behaviour, ledger validity, report length and
format, JSON in reports, system-role rendering, judge parse rate, and the G1/G2 counts. It
computes no loss, no detection rate (beyond the G1 comparator count §9 names) and no downgrade
value, and it never reads the CAP arm's item scores (G3 is a loss quantity).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import shutil
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import httpx

from common import REPO, derive_seed, load_config
from sets import load_sets

STRATA = ("clean", "low", "high", "auth")
PILOT_N = {"clean": 2, "low": 3, "high": 3, "auth": 2}
B60_N = {"clean": 14, "low": 18, "high": 18, "auth": 10}
THINK_RE = re.compile(r"</?think>")
# Format diagnostics (report level, never per item): IDs the strict rule matches (D-2: any case)
# and ID spellings it does not match ("worker 3", "worker3").
MATCHED_ID = re.compile(r"(?<![A-Za-z0-9_])worker_[1-9](?![A-Za-z0-9_])", re.IGNORECASE)
UNMATCHED_ID = re.compile(r"(?<![A-Za-z0-9_])worker ?[1-9](?![0-9])", re.IGNORECASE)


# ---------------------------------------------------------------- draws

def _by_stratum(sets: list[dict[str, Any]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {s: [] for s in STRATA}
    for s in sets:
        out[s["stratum"]].append(s["set_id"])
    return {k: sorted(v) for k, v in out.items()}


def pilot_sets(sets: list[dict[str, Any]], master_seed: int) -> dict[str, list[str]]:
    rng = random.Random(derive_seed(master_seed, "pilot"))
    by = _by_stratum(sets)
    out = {}
    for st in STRATA:
        ids = list(by[st])
        rng.shuffle(ids)
        out[st] = ids[: PILOT_N[st]]
    return out


def b60_sets(sets: list[dict[str, Any]], master_seed: int) -> dict[str, list[str]]:
    pilot = pilot_sets(sets, master_seed)
    rng = random.Random(derive_seed(master_seed, "B60"))
    by = _by_stratum(sets)
    out = {}
    for st in STRATA:
        rest = [i for i in by[st] if i not in pilot[st]]
        rng.shuffle(rest)
        out[st] = (pilot[st] + rest)[: B60_N[st]]
    return out


def shard_sets(sets: list[dict[str, Any]], master_seed: int, k: int) -> list[dict[str, list[str]]]:
    """Non-pilot sets split into k shards, round-robin within each stratum (sorted ids), so every
    shard has a mix of strata. Scheduling only: sets are independent and their seeds are per set."""
    pilot = pilot_sets(sets, master_seed)
    by = _by_stratum(sets)
    out: list[dict[str, list[str]]] = [{st: [] for st in STRATA} for _ in range(k)]
    for st in STRATA:
        rest = [i for i in by[st] if i not in pilot[st]]
        for j, sid in enumerate(rest):
            out[j % k][st].append(sid)
    return out


# ---------------------------------------------------------------- render check

def render_check(base_url: str, model: str, system: str, user: str) -> dict[str, Any]:
    """Render [system, user] through the served chat template (vLLM /tokenize + /detokenize)."""
    root = base_url.rstrip("/").removesuffix("/v1")
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    out: dict[str, Any] = {"model": model, "base_url": base_url}
    with httpx.Client(timeout=120, trust_env=False) as c:
        r = c.post(f"{root}/tokenize", json={"model": model, "messages": msgs, "add_generation_prompt": True})
        if r.status_code != 200:
            out.update(ok=False, error=f"/tokenize {r.status_code}: {r.text[:500]}")
            return out
        toks = r.json()["tokens"]
        d = c.post(f"{root}/detokenize", json={"model": model, "tokens": toks})
        if d.status_code != 200:
            out.update(ok=False, error=f"/detokenize {d.status_code}: {d.text[:500]}")
            return out
        rendered = d.json()["prompt"]
    sys_at = rendered.find(system)
    user_at = rendered.find(user)
    extra = rendered
    for s in (system, user):
        extra = extra.replace(s, "")
    out.update(ok=True, n_tokens=len(toks), rendered=rendered,
               system_text_present=sys_at != -1, system_count=rendered.count(system),
               system_before_user=sys_at != -1 and user_at != -1 and sys_at < user_at,
               chars_outside_our_messages=len(extra),
               # A default system prompt (Ministral's SYSTEM_PROMPT.txt) would show up here as
               # hundreds of extra characters; template control tokens are a few dozen.
               suspect_extra_system=len(extra) > 400)
    return out


# ---------------------------------------------------------------- summary

def rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def pct(a: int, b: int) -> str:
    return f"{a}/{b}" + (f" ({100 * a / b:.0f}%)" if b else "")


def worker_section(d: Path, specs: dict[str, dict[str, Any]], set_ids: set[str]) -> dict[str, Any]:
    eps = [e for e in rows(d / "episodes.jsonl") if e["set_id"] in set_ids]
    finals = [f for f in rows(d / "workers_final.jsonl") if f["set_id"] in set_ids]
    swaps = [s for s in rows(d / "swaps.jsonl") if s.get("set_id") in set_ids]
    by_pos: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for e in eps:
        by_pos[(e["set_id"], e["worker_id"])].append(e)
    cell_stats: dict[str, Counter] = defaultdict(Counter)
    for (sid, wid), es in by_pos.items():
        orig = next(w["problem_id"] for w in specs[sid]["workers"] if w["worker_id"] == wid)
        first = [e for e in es if e["problem_id"] == orig and e["try"] == 0]
        c = cell_stats[es[0]["cell"]]
        c["positions"] += 1
        c["episodes"] += len(es)
        c["first_try_accepted"] += bool(first and first[0]["accepted"])   # worker pass rate
        c["needed_regen"] += not (first and first[0]["accepted"])
        c["filled"] += any(e["accepted"] for e in es)
        for e in es:
            for k, v in e["checks"].items():
                c[f"fail_{k}"] += not v
            c["think_stripped"] += bool(e.get("think_stripped"))
    explicit = Counter()
    for f in finals:
        for p in f["positions"]:
            if p is None or p["cell"] == "clean":
                continue
            ep = next(e for e in eps if (e["set_id"], e["worker_id"], e["problem_id"], e["try"]) ==
                      (f["set_id"], p["worker_id"], p["problem_id"], p["try"]))
            st = ep["status"]
            explicit["accepted_injected"] += 1
            explicit["status_lists_failing_test"] += bool(st.get("failing"))
            explicit["deviation_text_not_none"] += st.get("deviations", "none").strip().lower().rstrip(".") != "none"
            explicit["hidden_fail_confirmed"] += p["cell"] != "AU" and p["hidden_pass"] is False
            explicit["au_hidden_pass"] += p["cell"] == "AU" and p["hidden_pass"] is True
    print("\n== WORKERS (family A)")
    print("cell   positions first_try_pass needed_regen regen/pos filled failed_checks")
    out_cells = {}
    for cell in ("clean", "AC", "AE", "DC", "DE", "AU"):
        c = cell_stats.get(cell)
        if not c:
            continue
        fails = {k[5:]: v for k, v in c.items() if k.startswith("fail_") and v}
        rpp = (c["episodes"] - c["positions"]) / c["positions"]
        print(f"{cell:6s} {c['positions']:9d} {pct(c['first_try_accepted'], c['positions']):>14s} "
              f"{pct(c['needed_regen'], c['positions']):>12s} {rpp:9.2f} {c['filled']:6d} {fails}")
        out_cells[cell] = {**dict(c), "regen_per_position": rpp}
    excl = [f["set_id"] for f in finals if f["excluded"]]
    print(f"sets finished {len(finals)}/{len(set_ids)}; excluded {excl}; stage-B swaps "
          f"{sum(s['replacement_id'] is not None for s in swaps)}")
    print(f"failures explicit in transcripts (accepted injected/AU workers): {dict(explicit)}")
    return {"cells": out_cells, "excluded": excl, "swaps": swaps, "explicit": dict(explicit)}


def manager_section(d: Path, set_ids: set[str]) -> dict[str, Any]:
    mo = [m for m in rows(d / "manager_outputs.jsonl") if m["set_id"] in set_ids]
    calls = [c for c in rows(d / "calls.jsonl") if c["set_id"] in set_ids and c["stage"] == "manager"]
    out: dict[str, Any] = {"ledgers": {}, "reports": {}}
    print("\n== MANAGERS")
    for fam in sorted({m["family"] for m in mo}):
        led_calls = [c for c in calls if c["family"] == fam and c["arm"] == "L" and c["turn"] == 1]
        samples = {(c["set_id"], c["sample"]) for c in led_calls}
        lrows = {(m["set_id"], m["sample"]): m for m in mo if m["family"] == fam and m["arm"] == "L"}
        valid = sum(1 for m in lrows.values() if m["ledger"] is not None)
        retried = sum(1 for m in lrows.values() if (m["ledger_tries"] or 1) > 1)
        trunc = sum(1 for c in led_calls if c["finish_reason"] == "length")
        think = sum(1 for c in calls if c["family"] == fam and THINK_RE.search(c["output"] or ""))
        print(f"[{fam}] ledgers valid {pct(valid, len(lrows))}, needed a retry {retried}, ledger calls "
              f"cut by max_tokens {trunc}/{len(led_calls)}, samples {len(samples)}, think tags in "
              f"manager outputs {think}")
        out["ledgers"][fam] = {"n": len(lrows), "valid": valid, "retried": retried, "cut": trunc, "think": think}
        for key in sorted({(m["arm"], m["framing"]) for m in mo if m["family"] == fam and m["report"] is not None}):
            reps = [m for m in mo if m["family"] == fam and (m["arm"], m["framing"]) == key and m["report"] is not None]
            words = [len(m["report"].split()) for m in reps]
            cap = 60 if key[0] == "STRESS" else 120
            js = sum(1 for m in reps if m["report"].strip().startswith("{") or '"issues"' in m["report"])
            md = sum(1 for m in reps if re.search(r"\*\*|^#{1,6} |^\s*[-*] ", m["report"], re.MULTILINE))
            fin = sum(1 for m in reps if m["finish_reason"] == "length")
            exact = sum(1 for m in reps if MATCHED_ID.search(m["report"]))
            variant_only = sum(1 for m in reps if UNMATCHED_ID.search(m["report"]))
            print(f"[{fam}] {key[0]:6s} {key[1]:11s} n={len(reps):3d} words median {statistics.median(words):.0f} "
                  f"max {max(words)}  over cap {pct(sum(w > cap for w in words), len(words))}  "
                  f"cut by max_tokens {fin}  JSON-like {js}  markdown {md}  "
                  f"with a matchable worker_k id {exact}  with an unmatched spelling (worker 3) {variant_only}")
            out["reports"][f"{fam}/{key[0]}/{key[1]}"] = {
                "n": len(reps), "median_words": statistics.median(words), "max_words": max(words),
                "over_cap": sum(w > cap for w in words), "cut": fin, "json_like": js, "markdown": md,
                "exact_id": exact, "variant_id_only": variant_only}
    return out


def judge_section(d: Path, set_ids: set[str]) -> dict[str, Any]:
    from score import JUDGE_KEY, final_judgements
    judged, stats = final_judgements(d / "judge_calls.jsonl")
    modes = Counter(r.get("system_mode") for r in rows(d / "judge_calls.jsonl"))
    print("\n== JUDGE")
    for p, c in sorted(stats.items()):
        print(f"{p:8s} jobs {c['jobs']}  parsed on first try {pct(c['parsed_first_try'], c['jobs'])}  "
              f"calls {c['calls']}  unparsed after {3} tries {c['unparsed']}")
    print(f"system mode in calls: {dict(modes)}")
    issues = rows(d / "scores" / "issues.jsonl")
    print(f"score issues: {dict(Counter(i['kind'] for i in issues))}")
    return {"stats": {k: dict(v) for k, v in stats.items()}, "modes": dict(modes)}


def gates_section(d: Path, set_ids: set[str]) -> dict[str, Any]:
    """G1 and G2 counts only (§9). No CAP rows are read."""
    items = [r for r in rows(d / "scores" / "items.jsonl") if r["set_id"] in set_ids]
    ledgers = [r for r in rows(d / "scores" / "ledgers.jsonl") if r["set_id"] in set_ids]
    out: dict[str, Any] = {}
    print("\n== GATES G1, G2 (counts; pilot n is tiny, so these are sanity checks, not tests)")
    for fam in sorted({r["family"] for r in ledgers}):
        led_items = [r for r in items if r["family"] == fam and r["text_kind"] == "ledger"]
        au = [r for r in led_items if r["cell"] == "AU" and r["strict"] is not None]
        de = [r for r in led_items if r["cell"] == "DE" and r["strict"] is not None]
        au_n, de_n = sum(r["strict"] for r in au), sum(r["strict"] for r in de)
        g1 = None
        if au and de:
            g1 = (au_n / len(au)) < 0.5 * (de_n / len(de))
        clean = [r for r in ledgers if r["family"] == fam and r["stratum"] == "clean" and r["valid"]]
        fa = [r["false_alarm"] for r in clean if r["false_alarm"] is not None]
        anyent = sum(r["any_entry"] for r in clean)
        g2 = None if not fa else (sum(fa) / len(fa)) < 0.15
        print(f"[{fam}] G1: AU ledger flags {pct(au_n, len(au))} vs DE ledger records {pct(de_n, len(de))} "
              f"-> inequality holds: {g1}")
        print(f"[{fam}] G2: clean ledgers with a J_FALSE failure claim {pct(sum(fa), len(fa))}; with any "
              f"entry {pct(anyent, len(clean))} -> under 15%: {g2}")
        out[fam] = {"au_flags": au_n, "au_pairs": len(au), "de_records": de_n, "de_pairs": len(de),
                    "g1_holds": g1, "clean_false_alarm": sum(fa), "clean_ledgers": len(fa),
                    "clean_any_entry": anyent, "g2_holds": g2}
    return out


def triggers(summary: dict[str, Any], renders: dict[str, Any]) -> list[str]:
    """prompts.md §6 conditions, as flags for a human decision (prereg §9)."""
    flags = []
    for fam, l in summary["managers"]["ledgers"].items():
        if l["n"] and (l["n"] - l["valid"]) / l["n"] > 0.05:
            flags.append(f"{fam}: ledger parse failures {l['n'] - l['valid']}/{l['n']} > 5%")
        if l["think"]:
            flags.append(f"{fam}: think tags in {l['think']} manager outputs")
    for k, r in summary["managers"]["reports"].items():
        if r["json_like"]:
            flags.append(f"{k}: {r['json_like']} JSON-like reports")
        if r["n"] and r["over_cap"] / r["n"] > 0.5:
            flags.append(f"{k}: most reports over the cap ({r['over_cap']}/{r['n']}); 'routinely' is a judgement call")
    for cell, c in summary["workers"]["cells"].items():
        if c["positions"] and c["needed_regen"] / c["positions"] > 0.20:
            flags.append(f"worker {cell}: {c['needed_regen']}/{c['positions']} positions needed regeneration "
                         f"(> 20%). Report only: worker prompts are frozen (prereg §9), so no prompt fix applies")
    for fam, g in summary["gates"].items():
        if g["g1_holds"] is False:
            flags.append(f"{fam}: G1 inequality fails on pilot counts")
        if g["g2_holds"] is False:
            flags.append(f"{fam}: G2 false-alarm share >= 15% on pilot counts")
    for who, r in renders.items():
        if not r.get("ok"):
            flags.append(f"render {who}: check failed ({r.get('error', '')[:120]})")
        elif not r["system_text_present"] or r["system_count"] != 1:
            flags.append(f"render {who}: system text present={r['system_text_present']} count={r['system_count']}")
        elif r["suspect_extra_system"]:
            flags.append(f"render {who}: {r['chars_outside_our_messages']} chars outside our messages (default system prompt?)")
    for p, s in summary["judge"]["stats"].items():
        if s["jobs"] and (s["jobs"] - s["parsed_first_try"]) / s["jobs"] > 0.05:
            flags.append(f"judge {p}: first-try parse failures above 5%")
    return flags


def summary(cfg: dict[str, Any], log_dir: str, set_spec: str | None) -> dict[str, Any]:
    d = Path(log_dir)
    sets = load_sets(cfg["paths"]["sets_file"])
    if set_spec:
        from run import select_sets
        ids = {s["set_id"] for s in select_sets(sets, set_spec)}
    else:
        ids = {i for v in pilot_sets(sets, cfg["seeds"]["master_seed"]).values() for i in v}
    print(f"pilot sets: {sorted(ids)}")
    renders = {p.stem.removeprefix("render_"): json.loads(p.read_text(encoding="utf-8"))
               for p in sorted(d.glob("render_*.json"))}
    print("\n== CHAT-TEMPLATE RENDERING")
    for who, r in renders.items():
        keep = {k: v for k, v in r.items() if k != "rendered"}
        print(f"{who}: {keep}")
    specs = {s["set_id"]: s for s in sets}
    s = {"workers": worker_section(d, specs, ids), "managers": manager_section(d, ids),
         "judge": judge_section(d, ids), "gates": gates_section(d, ids)}
    s["flags"] = triggers(s, renders)
    print("\n== prompts.md §6 FLAGS (each needs a decision; none is applied automatically)")
    for f in s["flags"] or ["none"]:
        print(f"- {f}")
    (d / "pilot_summary.json").write_text(json.dumps(s, indent=2, default=str), encoding="utf-8")
    return s


# ---------------------------------------------------------------- fork (re-pilot)

def fork(src: str, dst: str) -> None:
    """Copy worker-side logs only, so manager outputs can be regenerated under new prompts
    without a prompt_hash clash in calls.jsonl (prereg §9: old outputs are kept, marked)."""
    s, t = Path(src), Path(dst)
    if t.exists() and any(t.iterdir()):
        raise SystemExit(f"{t} is not empty")
    t.mkdir(parents=True, exist_ok=True)
    for name in ("episodes.jsonl", "workers_final.jsonl", "swaps.jsonl", "worker_stats.json"):
        if (s / name).exists():
            shutil.copy2(s / name, t / name)
    with open(s / "calls.jsonl", encoding="utf-8") as fi, open(t / "calls.jsonl", "w", encoding="utf-8") as fo:
        for line in fi:
            if line.strip() and json.loads(line)["stage"] == "worker":
                fo.write(line)
    if (s / "prompts").exists():
        shutil.copytree(s / "prompts", t / "prompts")
    (t / "FORKED_FROM.txt").write_text(f"worker logs copied from {s.resolve()}\n", encoding="utf-8")
    print(f"forked worker logs {s} -> {t}")


# ---------------------------------------------------------------- CLI

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["sets", "b60", "render", "summary", "fork", "shard"])
    ap.add_argument("--k", type=int, default=None)
    ap.add_argument("--i", type=int, default=None, help="shard index, 1..k")
    ap.add_argument("--override", action="append", default=[], metavar="KEY=VALUE")
    ap.add_argument("--config", default=str(REPO / "config.yaml"))
    ap.add_argument("--stratum", default=None)
    ap.add_argument("--family", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--log-dir", default=None)
    ap.add_argument("--sets", default=None)
    ap.add_argument("--src", default=None)
    ap.add_argument("--dst", default=None)
    a = ap.parse_args()
    cfg = load_config(a.config, a.override)
    sets = load_sets(cfg["paths"]["sets_file"])
    if a.cmd == "shard":
        if not (a.k and a.i and 1 <= a.i <= a.k):
            raise SystemExit("shard needs --k K and --i in 1..K")
        draw = shard_sets(sets, cfg["seeds"]["master_seed"], a.k)[a.i - 1]
        want = a.stratum.split(",") if a.stratum else list(STRATA)
        print(",".join(i for st in want for i in draw[st]))
    elif a.cmd in ("sets", "b60"):
        draw = (pilot_sets if a.cmd == "sets" else b60_sets)(sets, cfg["seeds"]["master_seed"])
        want = a.stratum.split(",") if a.stratum else list(STRATA)
        print(",".join(i for st in want for i in draw[st]))
    elif a.cmd == "render":
        if a.family not in cfg["models"]:
            raise SystemExit("--family A, B or judge")
        from prompts import Prompts
        pr = Prompts(cfg["paths"]["prompts_md"], cfg["paths"]["prompts_dir"], cfg["prompts_version"])
        if a.family == "judge":
            system, user = pr.raw("J_ITEM_SYS"), "ITEM\nWorker: worker_1\n(render check)"
        else:
            system, user = pr.raw("M_SYS").split("SPECIFICATION")[0].strip(), "render check"
        m = cfg["models"][a.family]
        r = render_check(m["base_url"], m["model"], system, user)
        text = json.dumps(r, indent=2, ensure_ascii=False)
        if a.out:
            Path(a.out).write_text(text, encoding="utf-8")
        print({k: v for k, v in r.items() if k != "rendered"})
        print("---- rendered ----\n" + str(r.get("rendered", ""))[:3000])
    elif a.cmd == "summary":
        if not a.log_dir:
            raise SystemExit("summary needs --log-dir")
        summary(cfg, a.log_dir, a.sets)
    else:
        if not (a.src and a.dst):
            raise SystemExit("fork needs --src and --dst")
        fork(a.src, a.dst)


if __name__ == "__main__":
    main()
