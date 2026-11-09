"""Stage 4 numbers for report_v4 (post hoc, descriptive; no model calls).

Reads the public data release (ibnr-release-v1) and the repository's E1 hand codes, and prints every
number that report_v4 adds beyond results.json / results/posthoc / cause_result.json / deviations.md:

  1. family B end-to-end absence (judge lenient), ledger first (L) vs no ledger (S), one and three
     failing workers, with 95% set-cluster bootstrap intervals and the paired S - L difference;
  2. family A, one failing worker, by the failing worker's transcript position (band and 1-9):
     recorded in the ledger (judge-free), absent from the L report, absent from the S report, with 95%
     intervals per band;
  3. family A, three failing workers, ledger recording by position band;
  4. family A, one failing worker, recording by cell (judge-free) and approved-change (AU) entries;
  5. checks behind F5 (hand-checked share of empty-ledger mentions) and the 20/55 figure;
  6. family A, one failing worker, instructed-change cells (DC/DE): ledger-first end-to-end absence and DE
     recording split by instruction phrasing in the worker's final message (same regex as stage1_checks.py).

Absence uses the E1 hand codes where they exist (unsure = mention), else judge lenient, exactly as
harness/e1_recompute.py does. Intervals use the same bootstrap (2,000 resamples, random.Random(1),
percentile, sets resampled with replacement within the stratum).

Usage: python -I stage4_numbers.py --logs <release>/logs --repo <repo root> [--json out.json]
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import random
import re
from pathlib import Path
from typing import Any, Callable

DIRS = ["pilot_h200", "main_s1", "main_s2", "main_s3", "main_s4"]
BANDS = (("early (1-3)", range(1, 4)), ("mid (4-6)", range(4, 7)), ("late (7-9)", range(7, 10)))


def boot(by_set: dict[str, list[Any]], fn: Callable[[list[Any]], float | None], B: int = 2000,
         seed: int = 1) -> tuple[float, float]:
    """Percentile set-cluster bootstrap, identical to harness/e1_recompute.py."""
    sets = sorted(by_set)
    rng = random.Random(seed)
    vals = []
    for _ in range(B):
        samp = [rng.choice(sets) for _ in sets]
        v = fn([p for s in samp for p in by_set[s]])
        if v is not None:
            vals.append(v)
    vals.sort()
    return vals[int(.025 * len(vals))], vals[int(.975 * len(vals)) - 1]


def load_items(logs: Path) -> list[dict]:
    items: list[dict] = []
    for d in DIRS:
        with open(logs / d / "scores" / "items.jsonl", encoding="utf-8") as f:
            items.extend(json.loads(line) for line in f)
    return items


def load_hand(repo: Path) -> dict[tuple[str, str, str, int], str]:
    key = {}
    with open(repo / "results/posthoc/e1_key.jsonl", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            key[r["check_id"]] = r
    hand = {}
    with open(repo / "results/posthoc/e1_filled.csv", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    col = next(k for k in rows[0] if k.lower().startswith("mentions"))
    for r in rows:
        k = key[r["check_id"]]
        hand[(k["set_id"], k["worker_id"], k["arm"], int(k["sample"]))] = r[col].strip().lower()
    return hand


def mention(i: dict, hand: dict) -> bool:
    h = hand.get((i["set_id"], i["worker_id"], i["arm"], int(i["sample"])))
    return h in ("yes", "unsure") if h is not None else bool(i["lenient"])


def pos(i: dict) -> int:
    """1-based transcript position. The release's `position` field is 0-based; section 0 checks that the
    coordinator prompt lists transcripts in worker_1..worker_9 order, so worker_k is the k-th transcript."""
    p = int(i["worker_id"].split("_")[1])
    assert int(i["position"]) == p - 1, (i["set_id"], i["worker_id"], i["position"])
    return p


def rate_ci(rows: list[dict], flag: Callable[[dict], bool]) -> dict:
    by = collections.defaultdict(list)
    for r in rows:
        by[r["set_id"]].append(r)
    k = sum(flag(r) for r in rows)
    lo, hi = boot(by, lambda ps: sum(flag(p) for p in ps) / len(ps))
    return {"k": k, "n": len(rows), "est": k / len(rows), "ci95": [lo, hi]}


def fmt(d: dict) -> str:
    return f"{d['k']}/{d['n']} = {100 * d['est']:.1f}% [{100 * d['ci95'][0]:.1f}, {100 * d['ci95'][1]:.1f}]"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", type=Path, required=True)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--json", type=Path, default=None)
    a = ap.parse_args()
    items = load_items(a.logs)
    hand = load_hand(a.repo)
    out: dict[str, Any] = {}

    print("== 0. Transcript order in coordinator prompts (family A, neutral, one failing worker, turn 1, L and S)")
    checked, bad = 0, 0
    for d in DIRS:
        with open(a.logs / d / "calls.jsonl", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                if (r["stage"] != "manager" or r["arm"] not in ("L", "S") or r["family"] != "A"
                        or r.get("framing") != "neutral" or not r["set_id"].startswith("L") or r["turn"] != 1):
                    continue
                txt = (a.logs / d / "prompts" / f"{r['prompt_hash']}.json").read_text(encoding="utf-8")
                ids = re.findall(r'<worker id=\\?"(worker_\d)\\?"', txt)
                checked += 1
                bad += ids != [f"worker_{k}" for k in range(1, 10)]
    out["order_check"] = {"checked": checked, "out_of_order": bad}
    print(f"  prompts checked {checked}; transcripts not in worker_1..worker_9 order: {bad}")

    def sel(fam: str, stratum: str, kind: str, arm: str | None = None) -> list[dict]:
        return [i for i in items if i["family"] == fam and i["framing"] == "neutral" and i["stratum"] == stratum
                and i["text_kind"] == kind and i["cell"] != "AU" and (arm is None or i["arm"] == arm)]

    print("== 1. End-to-end absence from the report (neutral framing; A hand-checked via E1, B judge lenient)")
    for fam in ("A", "B"):
        for st, lab in (("low", "one failing"), ("high", "three failing")):
            sub = {}
            for arm in ("L", "S"):
                rows = sel(fam, st, "report", arm)
                f = (lambda r: not mention(r, hand)) if fam == "A" else (lambda r: not r["lenient"])
                d = rate_ci(rows, f)
                out[f"e2e_{fam}_{st}_{arm}"] = d
                print(f"  {fam} {lab} {arm}: absent {fmt(d)}")
                sub[arm] = {(r["set_id"], r["worker_id"], int(r["sample"])): f(r) for r in rows}
            common = [k for k in sub["L"] if k in sub["S"]]
            by = collections.defaultdict(list)
            for k in common:
                by[k[0]].append((sub["S"][k], sub["L"][k]))
            dfn = lambda ps: (sum(s for s, _ in ps) - sum(l for _, l in ps)) / len(ps)
            est = dfn([p for v in by.values() for p in v])
            lo, hi = boot(by, dfn)
            out[f"e2e_{fam}_{st}_S_minus_L"] = {"est": est, "ci95": [lo, hi], "n": len(common)}
            print(f"     S - L paired (n={len(common)}): {100 * est:+.1f} pts [{100 * lo:+.1f}, {100 * hi:+.1f}]")

    print("== 2. Family A, one failing worker, by transcript position of the failing worker")
    led = sel("A", "low", "ledger")
    rl = sel("A", "low", "report", "L")
    rs = sel("A", "low", "report", "S")
    rec = lambda r: r["ledger_entries_for_worker"] > 0
    absent = lambda r: not mention(r, hand)
    for name, rng_ in BANDS:
        ins = lambda rows: [r for r in rows if pos(r) in rng_]
        d = {"sets": len({r["set_id"] for r in ins(led)}), "recorded": rate_ci(ins(led), rec),
             "L_absent": rate_ci(ins(rl), absent), "S_absent": rate_ci(ins(rs), absent)}
        out[f"pos_A_low_{name.split()[0]}"] = d
        print(f"  {name}: sets {d['sets']}; recorded {fmt(d['recorded'])}; L absent {fmt(d['L_absent'])}; "
              f"S absent {fmt(d['S_absent'])}")
    print("  by position (sets; recorded; L absent; S absent):")
    per = {}
    for p in range(1, 10):
        L_ = [r for r in led if pos(r) == p]
        if not L_:
            print(f"   pos {p}: no sets")
            continue
        per[p] = {"sets": len({r["set_id"] for r in L_}), "recorded": sum(rec(r) for r in L_), "n": len(L_),
                  "L_absent": sum(absent(r) for r in rl if pos(r) == p),
                  "S_absent": sum(absent(r) for r in rs if pos(r) == p)}
        print(f"   pos {p}: {per[p]['sets']}; {per[p]['recorded']}/{per[p]['n']}; {per[p]['L_absent']}/{per[p]['n']}; "
              f"{per[p]['S_absent']}/{per[p]['n']}")
    out["pos_A_low_by_position"] = per

    print("== 3. Family A, three failing workers: ledger recording by position band (judge-free)")
    ledh = sel("A", "high", "ledger")
    for name, rng_ in BANDS:
        rows = [r for r in ledh if pos(r) in rng_]
        k = sum(rec(r) for r in rows)
        out[f"pos_A_high_{name.split()[0]}_recorded"] = {"k": k, "n": len(rows)}
        print(f"  {name}: recorded {k}/{len(rows)}")

    print("== 4. Family A, one failing worker: recording by cell (judge-free), and AU entries")
    for cell in ("AC", "AE", "DC", "DE"):
        rows = [r for r in led if r["cell"] == cell]
        k = sum(rec(r) for r in rows)
        out[f"rec_A_low_{cell}"] = {"k": k, "n": len(rows)}
        print(f"  {cell}: {k}/{len(rows)}")
    au = [i for i in items if i["family"] == "A" and i["framing"] == "neutral" and i["cell"] == "AU"
          and i["text_kind"] == "ledger"]
    k = sum(rec(r) for r in au)
    out["rec_A_AU_entries"] = {"k": k, "n": len(au)}
    print(f"  AU (approved change) ledger entries: {k}/{len(au)}")

    print("== 5. Checks: empty ledgers (family A, one failing worker)")
    lkey = {(r["set_id"], r["worker_id"], int(r["sample"])): r for r in led}
    empty = [r for r in rl if not rec(lkey[(r["set_id"], r["worker_id"], int(r["sample"]))])]
    recd = [r for r in rl if rec(lkey[(r["set_id"], r["worker_id"], int(r["sample"]))])]
    emp_abs = sum(absent(r) for r in empty)
    emp_men = [r for r in empty if not absent(r)]
    emp_men_hand = sum((r["set_id"], r["worker_id"], "L", int(r["sample"])) in hand for r in emp_men)
    out["empty_ledgers"] = {"n": len(empty), "absent": emp_abs, "mentioned": len(emp_men),
                            "mentioned_hand_checked": emp_men_hand,
                            "recorded_n": len(recd), "recorded_absent": sum(absent(r) for r in recd)}
    print(f"  empty ledgers {len(empty)}; report absent {emp_abs}; mentioned {len(emp_men)} "
          f"(hand-checked {emp_men_hand}); recorded {len(recd)}, absent {sum(absent(r) for r in recd)}")

    print("== 6. Instructed-change cells (DC/DE), one failing worker: split by 'as instructed' phrasing")
    leak_re = re.compile(r"as (?:i was )?instructed|as per (?:the|my) instructions?|instructed to", re.I)
    leak: dict[tuple[str, str], bool] = {}
    for d in DIRS:
        with open(a.logs / d / "episodes.jsonl", encoding="utf-8") as f:
            for line in f:
                e = json.loads(line)
                if e.get("accepted") and e["cell"] in ("DC", "DE"):
                    leak[(e["set_id"], e["worker_id"])] = bool(leak_re.search(e["manager_view"]["final_message"]))
    for flag in (True, False):
        rows = [r for r in rl if r["cell"] in ("DC", "DE") and leak[(r["set_id"], r["worker_id"])] == flag]
        de = [r for r in led if r["cell"] == "DE" and leak[(r["set_id"], r["worker_id"])] == flag]
        k = sum(absent(r) for r in rows)
        out[f"dcde_low_L_absent_leak_{flag}"] = {"k": k, "n": len(rows)}
        out[f"de_low_recorded_leak_{flag}"] = {"k": sum(rec(r) for r in de), "n": len(de)}
        print(f"  phrasing={flag}: L absent {k}/{len(rows)}; DE recorded {sum(rec(r) for r in de)}/{len(de)}")
    if a.json:
        a.json.write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
