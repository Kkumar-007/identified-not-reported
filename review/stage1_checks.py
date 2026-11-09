"""Stage 1 review checks (post hoc, exploratory; no model calls).

Reads the public data release (ibnr-release-v1) and the repository's E1 hand codes,
and prints the numbers quoted in stage1_diagnosis.md:
  1. instruction-leak phrasing in accepted DC/DE worker messages, by cell and load;
  2. family A one-failure recording and end-to-end absence by the failing worker's
     position in the coordinator's context (worker_k is the k-th transcript);
  3. the same function at different positions;
  4. family B end-to-end absence (judge lenient).
Absence uses the E1 hand codes where they exist (unsure = mention), else judge lenient,
exactly as harness/e1_recompute.py does.

Usage: python -I stage1_checks.py --logs <release>/logs --repo <repo root>
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import random
import re
from pathlib import Path

DIRS = ["pilot_h200", "main_s1", "main_s2", "main_s3", "main_s4"]
LEAK_STRICT = re.compile(r"as (?:i was )?instructed|as per (?:the|my) instructions?|instructed to", re.I)
LEAK_BROAD = re.compile(r"as (?:i was )?instructed|as per (?:the|my) instructions?|instructed to|as requested", re.I)


def load(logs: Path, repo: Path):
    acc: dict[tuple[str, str], dict] = {}
    items: list[dict] = []
    for d in DIRS:
        with open(logs / d / "episodes.jsonl", encoding="utf-8") as f:
            for line in f:
                e = json.loads(line)
                if e.get("accepted"):
                    acc[(e["set_id"], e["worker_id"])] = e
        with open(logs / d / "scores" / "items.jsonl", encoding="utf-8") as f:
            items.extend(json.loads(line) for line in f)
    key = {}
    with open(repo / "results/posthoc/e1_key.jsonl", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            key[r["check_id"]] = r
    codes = {}
    with open(repo / "results/posthoc/e1_filled.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            codes[r["check_id"]] = r["mentions (yes/no/unsure)"].strip().lower()
    hand = {(k["set_id"], k["worker_id"], k["arm"], k["sample"]): codes[c] for c, k in key.items()}
    return acc, items, hand


def present(i: dict, hand: dict) -> bool:
    h = hand.get((i["set_id"], i["worker_id"], i["arm"], i["sample"]))
    return h in ("yes", "unsure") if h is not None else bool(i["lenient"])


def pos(i: dict) -> int:
    return int(i["worker_id"].split("_")[1])


def band(p: int) -> str:
    return "early(1-3)" if p <= 3 else ("mid(4-6)" if p <= 6 else "late(7-9)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", type=Path, required=True)
    ap.add_argument("--repo", type=Path, required=True)
    a = ap.parse_args()
    acc, items, hand = load(a.logs, a.repo)

    print("== 1. Instruction-leak phrasing in accepted worker final messages")
    for name, pat in (("strict", LEAK_STRICT), ("broad (+ 'as requested')", LEAK_BROAD)):
        c = collections.Counter()
        n = collections.Counter()
        for (s, w), e in acc.items():
            if e["cell"] in ("DC", "DE"):
                g = (e["cell"], "low" if s.startswith("L") else "high")
                n[g] += 1
                c[g] += bool(pat.search(e["manager_view"]["final_message"]))
        other = sum(bool(pat.search(e["manager_view"]["final_message"])) for e in acc.values() if e["cell"] not in ("DC", "DE"))
        print(f"  {name}: " + ", ".join(f"{g[0]} {g[1]} {c[g]}/{n[g]}" for g in sorted(n)) + f"; all other cells {other}")
    leak = {k: bool(LEAK_STRICT.search(e["manager_view"]["final_message"])) for k, e in acc.items()}

    A = [i for i in items if i["family"] == "A" and i["framing"] == "neutral" and i["stratum"] == "low" and i["cell"] != "AU"]
    de = collections.defaultdict(lambda: [0, 0])
    for i in A:
        if i["text_kind"] == "ledger" and i["cell"] == "DE":
            g = leak[(i["set_id"], i["worker_id"])]
            de[g][0] += i["ledger_entries_for_worker"] > 0
            de[g][1] += 1
    print(f"  family A one-failure DE ledger recording: leak-phrasing {de[True][0]}/{de[True][1]}, none {de[False][0]}/{de[False][1]} (samples)")

    print("== 2. Family A, one failing worker: by position of the failing worker's transcript")
    per = collections.defaultdict(lambda: {"rec": 0, "Labs": 0, "Sabs": 0, "pos": 0, "cell": "", "pid": ""})
    for i in A:
        r = per[i["set_id"]]
        r["pos"], r["cell"], r["pid"] = pos(i), i["cell"], i["problem_id"]
        if i["text_kind"] == "ledger":
            r["rec"] += i["ledger_entries_for_worker"] > 0
        elif i["arm"] == "L":
            r["Labs"] += not present(i, hand)
        elif i["arm"] == "S":
            r["Sabs"] += not present(i, hand)
    groups = collections.defaultdict(list)
    for s, r in per.items():
        groups[band(r["pos"])].append(s)
    for b in sorted(groups):
        ss = groups[b]
        tot = lambda f: sum(per[s][f] for s in ss)
        print(f"  {b}: sets {len(ss)}; recorded {tot('rec')}/{3*len(ss)}; L absent {tot('Labs')}/{3*len(ss)}; S absent {tot('Sabs')}/{3*len(ss)}")
    p2 = [s for s in per if per[s]["pos"] == 2]
    print(f"  position 2 only: sets {len(p2)}; recorded {sum(per[s]['rec'] for s in p2)}/{3*len(p2)}")
    lsets = sorted((s for s in per if per[s]["Labs"]), key=lambda s: -per[s]["Labs"])
    print(f"  L absences: {sum(per[s]['Labs'] for s in per)} from {len(lsets)} sets: " + ", ".join(f"{s}(pos {per[s]['pos']}, {per[s]['cell']}, {per[s]['Labs']})" for s in lsets))
    E, L = groups["early(1-3)"], groups["late(7-9)"]
    rate = lambda ss, f: sum(per[s][f] for s in ss) / (3 * len(ss))
    rng = random.Random(1)
    d_abs, d_rec = [], []
    for _ in range(2000):
        e = [rng.choice(E) for _ in E]
        l = [rng.choice(L) for _ in L]
        d_abs.append(rate(e, "Labs") - rate(l, "Labs"))
        d_rec.append(rate(e, "rec") - rate(l, "rec"))
    d_abs.sort(); d_rec.sort()
    print(f"  early - late, L absent: {100*(rate(E,'Labs')-rate(L,'Labs')):+.1f} pts [{100*d_abs[49]:+.1f}, {100*d_abs[1949]:+.1f}] (95% set-cluster bootstrap, 2000, Random(1))")
    print(f"  early - late, recorded: {100*(rate(E,'rec')-rate(L,'rec')):+.1f} pts [{100*d_rec[49]:+.1f}, {100*d_rec[1949]:+.1f}]")

    print("== 3. Same function, different positions (family A, one failing worker)")
    byp = collections.defaultdict(list)
    for s, r in per.items():
        byp[r["pid"]].append((r["pos"], r["cell"], s, f"{r['rec']}/3"))
    for p, v in sorted(byp.items()):
        if len(v) > 1 and len({x[0] for x in v}) > 1:
            print(f"  {p}: " + "; ".join(f"pos {x[0]} {x[1]} {x[2]} recorded {x[3]}" for x in sorted(v)))

    print("== 4. Family B, end-to-end absence (judge lenient, not hand-checked)")
    for st in ("low", "high"):
        for arm in ("L", "S"):
            rows = [i for i in items if i["family"] == "B" and i["framing"] == "neutral" and i["stratum"] == st
                    and i["text_kind"] == "report" and i["arm"] == arm and i["cell"] != "AU"]
            print(f"  {st} {arm}: absent {sum(not i['lenient'] for i in rows)}/{len(rows)}")


if __name__ == "__main__":
    main()
