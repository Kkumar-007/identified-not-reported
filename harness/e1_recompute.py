"""E1 (D-8): substitute the blind hand codes for the judge's lenient call on the 72 checked report pairs,
report judge-human agreement, recompute E4 (family A, L vs S, one and three failing workers) with the
same paired set-cluster bootstrap as posthoc_checks.py (2,000 resamples, random.Random(1)), and apply
the D-8 headline rule.

  python harness/e1_recompute.py --logs <dir with */scores/items.jsonl> --posthoc results/posthoc
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable


def boot(pairs_by_set: dict[str, list[Any]], fn: Callable[[list[Any]], float | None], B: int = 2000,
         seed: int = 1) -> tuple[float, float]:
    sets = sorted(pairs_by_set)
    rng = random.Random(seed)
    vals = []
    for _ in range(B):
        samp = [rng.choice(sets) for _ in sets]
        v = fn([p for s in samp for p in pairs_by_set[s]])
        if v is not None:
            vals.append(v)
    vals.sort()
    return vals[int(.025 * len(vals))], vals[int(.975 * len(vals)) - 1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", type=Path, required=True)
    ap.add_argument("--posthoc", type=Path, required=True)
    a = ap.parse_args()
    key = {json.loads(l)["check_id"]: json.loads(l) for l in open(a.posthoc / "e1_key.jsonl", encoding="utf-8")}
    filled = list(csv.DictReader(open(a.posthoc / "e1_filled.csv", encoding="utf-8-sig", newline="")))
    col = next(k for k in filled[0] if k.lower().startswith("mentions"))
    human: dict[tuple[str, str, str, int], bool] = {}
    agree = Counter()
    for r in filled:
        k = key[r["check_id"]]
        code = r[col].strip().lower()
        h = code in ("yes", "unsure")                      # D-8: unsure counts as a mention
        human[(k["set_id"], k["worker_id"], k["arm"], int(k["sample"]))] = h
        agree[(("judge_present" if k["judge_lenient"] else "judge_absent"), code, k["arm"], k["stratum"])] += 1
    print("Agreement table (judge call, human code, arm, count):")
    for kk, v in sorted(agree.items()):
        print("  ", kk, v)
    ja = [c for (j, c, *_), v in agree.items() if j == "judge_absent" for _ in range(v)]
    jp = [c for (j, c, *_), v in agree.items() if j == "judge_present" for _ in range(v)]
    print(f"Judge-absent confirmed by human 'no': {ja.count('no')}/{len(ja)}  (yes {ja.count('yes')}, unsure {ja.count('unsure')})")
    print(f"Judge-present confirmed by human yes/unsure: {len(jp) - jp.count('no')}/{len(jp)}  (no {jp.count('no')})")

    rows = []
    for f in glob.glob(str(a.logs / "*" / "scores" / "items.jsonl")):
        rows += [json.loads(l) for l in open(f)]
    rep = [r for r in rows if r["text_kind"] == "report" and r["family"] == "A" and r["framing"] == "neutral"
           and r["arm"] in ("L", "S") and r["cell"] != "AU"]
    for r in rep:
        k = (r["set_id"], r["worker_id"], r["arm"], int(r["sample"]))
        r["mention"] = human.get(k, r["lenient"])
        r["source"] = "human" if k in human else "judge"
    assert sum(r["source"] == "human" for r in rep) == 72
    print()
    decision = None
    out: dict[str, Any] = {"agreement": {"judge_absent_human_no": ja.count("no"), "judge_absent_n": len(ja),
                                         "judge_absent_human_unsure": ja.count("unsure"),
                                         "judge_present_human_yes_or_unsure": len(jp) - jp.count("no"), "judge_present_n": len(jp)}}
    for strat in ("low", "high"):
        sub = {arm: {(r["set_id"], r["worker_id"], int(r["sample"])): r for r in rep if r["stratum"] == strat and r["arm"] == arm}
               for arm in ("L", "S")}
        for arm in ("L", "S"):
            R = list(sub[arm].values())
            by = defaultdict(list)
            for r in R:
                by[r["set_id"]].append(r)
            n_abs = sum(not r["mention"] for r in R)
            lo, hi = boot(by, lambda ps: sum(not p["mention"] for p in ps) / len(ps))
            print(f"A {strat} {arm}: absent {n_abs}/{len(R)} = {n_abs / len(R):.3f} [{lo:.3f}, {hi:.3f}]")
            out[f"A_{strat}_{arm}"] = {"absent": n_abs, "n": len(R), "est": n_abs / len(R), "ci95": [lo, hi]}
        common = [k for k in sub["L"] if k in sub["S"]]
        by = defaultdict(list)
        for k in common:
            by[k[0]].append((sub["S"][k], sub["L"][k]))
        d = lambda ps: (sum(not s["mention"] for s, _ in ps) - sum(not l["mention"] for _, l in ps)) / len(ps)
        est = d([p for v in by.values() for p in v])
        lo, hi = boot(by, d)
        print(f"   S - L absent, paired (n={len(common)}): {est * 100:+.1f} pts [{lo * 100:+.1f}, {hi * 100:+.1f}]")
        out[f"A_{strat}_S_minus_L"] = {"est": est, "ci95": [lo, hi], "n": len(common)}
        if strat == "low":
            L_abs = sum(not r["mention"] for r in sub["L"].values()); S_abs = sum(not r["mention"] for r in sub["S"].values())
            decision = (L_abs > S_abs) and (hi < 0)
    out["d8_rule_met"] = bool(decision)
    (a.posthoc / "e1_result.json").write_text(json.dumps(out, indent=1))
    print()
    print("D-8 headline rule (one failing worker: L absence > S absence AND paired 95% interval of S - L excludes 0):",
          "MET -> headline may claim the ledger step loses lone failures" if decision else
          "NOT MET -> headline keeps the v2 framing; L/S comparison reported descriptively")


if __name__ == "__main__":
    main()
