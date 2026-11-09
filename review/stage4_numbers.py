"""Stage 4 numbers for report v4 (post hoc, descriptive; no model calls).

Every number that report v4 adds beyond report v3 is printed here (or in stage1_checks_output.txt).
Reads the public data release (ibnr-release-v1) and the repository's results/ files.

  python -I review/stage4_numbers.py --logs <release>/logs --repo <repo root> --out review/stage4_numbers.json

Sections:
  0. transcript order check: worker_k is the k-th transcript in every coordinator prompt (family A, one failure);
  1. family A, one failing worker, by position band (1-3, 4-6, 7-9): recorded, absent (L), absent (S), with
     95% set-cluster bootstrap intervals (2,000 resamples, random.Random(1), resampling sets within the band);
  2. the same by single position (1-9), counts only;
  3. family A end-to-end absence, ledger minus no ledger (L - S), paired, with the E1 hand codes substituted
     (same pairing and bootstrap as harness/e1_recompute.py, so it is exactly the negation of its S - L);
  4. family B end-to-end absence by arm and load (judge lenient, not hand-checked) and its paired L - S;
  5. family A one-failure empty ledgers: how many reports still mention the failure, and how many of those
     mentions were hand-checked (F5);
  6. ledger "detector profile" for both families, echoed from results.json (no recomputation);
  7. family A one-failure DC/DE ledger-first absence by instruction phrasing (F2).
Absence uses the E1 hand codes where they exist (unsure = mention), else judge lenient (stage1_checks.present).
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import re
import sys
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stage1_checks as s1  # noqa: E402

BANDS = ("early(1-3)", "mid(4-6)", "late(7-9)")


def boot(by_set: dict[str, list[Any]], fn: Callable[[list[Any]], float | None], B: int = 2000,
         seed: int = 1) -> tuple[float, float]:
    """Identical to harness/e1_recompute.boot (percentile indices int(.025 n) and int(.975 n) - 1)."""
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


def order_check(logs: Path) -> tuple[int, int]:
    """Count family-A one-failure L/S coordinator prompts whose <worker id=...> tags appear as worker_1..worker_9."""
    ok = bad = 0
    pat = re.compile(r'<worker id="(worker_\d)"')
    for d in s1.DIRS:
        for line in open(logs / d / "calls.jsonl", encoding="utf-8"):
            c = json.loads(line)
            if c.get("family") != "A" or c.get("arm") not in ("L", "S") or not str(c.get("set_id", "")).startswith("L"):
                continue
            if c.get("framing", "neutral") != "neutral":
                continue
            p = logs / d / "prompts" / f"{c['prompt_hash']}.json"
            if not p.exists():
                continue
            msgs = json.loads(p.read_text(encoding="utf-8"))
            msgs = msgs.get("messages", msgs) if isinstance(msgs, dict) else msgs
            text = "\n".join(m.get("content", "") for m in msgs if isinstance(m, dict) and m.get("role") == "user")
            ids = pat.findall(text)
            if not ids:
                continue
            first9 = ids[:9]
            if first9 == [f"worker_{k}" for k in range(1, 10)]:
                ok += 1
            else:
                bad += 1
    return ok, bad


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", type=Path, required=True)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    acc, items, hand = s1.load(a.logs, a.repo)
    out: dict[str, Any] = {}

    print("== 0. Transcript order (family A, one failing worker, neutral L and S coordinator calls)")
    ok, bad = order_check(a.logs)
    print(f"  prompts with worker_1..worker_9 in order: {ok}; out of order: {bad}")
    assert all(int(i["position"]) == s1.pos(i) - 1 for i in items), "position field != worker index - 1"
    print("  item 'position' field equals worker index - 1 for every scored item: yes")
    out["order_check"] = {"in_order": ok, "out_of_order": bad}

    A = [i for i in items if i["family"] == "A" and i["framing"] == "neutral" and i["stratum"] == "low" and i["cell"] != "AU"]
    rows = collections.defaultdict(list)          # set -> list of per-sample dicts
    per = {}
    for i in A:
        per.setdefault(i["set_id"], {"pos": s1.pos(i), "cell": i["cell"], "pid": i["problem_id"]})
    samp = collections.defaultdict(dict)          # (set, sample) -> {rec, L_abs, S_abs}
    for i in A:
        k = (i["set_id"], int(i["sample"]))
        if i["text_kind"] == "ledger":
            samp[k]["rec"] = i["ledger_entries_for_worker"] > 0
        elif i["arm"] == "L":
            samp[k]["L_abs"] = not s1.present(i, hand)
            samp[k]["L_src"] = "hand" if (i["set_id"], i["worker_id"], "L", i["sample"]) in hand else "judge"
        elif i["arm"] == "S":
            samp[k]["S_abs"] = not s1.present(i, hand)
    for (s, _), v in samp.items():
        rows[s].append(v)

    print("== 1. Family A, one failing worker, by position band (samples; 95% set-cluster bootstrap)")
    out["position_bands"] = {}
    for b in BANDS:
        ss = {s: rows[s] for s in rows if s1.band(per[s]["pos"]) == b}
        rec = {}
        for f in ("rec", "L_abs", "S_abs"):
            k = sum(v[f] for r in ss.values() for v in r)
            n = sum(len(r) for r in ss.values())
            lo, hi = boot(ss, lambda ps, f=f: sum(p[f] for p in ps) / len(ps))
            rec[f] = {"k": k, "n": n, "est": k / n, "ci95": [lo, hi]}
        out["position_bands"][b] = {"sets": len(ss), **rec}
        print(f"  {b}: sets {len(ss)}; " + "; ".join(
            f"{f} {rec[f]['k']}/{rec[f]['n']} = {100*rec[f]['est']:.1f}% [{100*rec[f]['ci95'][0]:.1f}, {100*rec[f]['ci95'][1]:.1f}]"
            for f in ("rec", "L_abs", "S_abs")))

    print("== 2. Family A, one failing worker, by single position (counts; 3 samples per set)")
    out["positions"] = {}
    for p in range(1, 10):
        ss = [s for s in rows if per[s]["pos"] == p]
        c = {f: sum(v[f] for s in ss for v in rows[s]) for f in ("rec", "L_abs", "S_abs")}
        n = 3 * len(ss)
        out["positions"][p] = {"sets": len(ss), "n": n, **c, "cells": sorted(per[s]["cell"] for s in ss)}
        print(f"  position {p}: sets {len(ss)} ({' '.join(sorted(per[s]['cell'] for s in ss))}); recorded {c['rec']}/{n}; "
              f"L absent {c['L_abs']}/{n}; S absent {c['S_abs']}/{n}")

    print("== 3. Family A end-to-end absence, L - S (paired by set, worker, sample; hand codes substituted)")
    out["A_L_minus_S"] = {}
    rep = [i for i in items if i["text_kind"] == "report" and i["family"] == "A" and i["framing"] == "neutral"
           and i["arm"] in ("L", "S") and i["cell"] != "AU"]
    for st in ("low", "high"):
        sub = {arm: {(i["set_id"], i["worker_id"], int(i["sample"])): i for i in rep if i["stratum"] == st and i["arm"] == arm}
               for arm in ("L", "S")}
        common = [k for k in sub["L"] if k in sub["S"]]
        by = collections.defaultdict(list)
        for k in common:
            by[k[0]].append((sub["L"][k], sub["S"][k]))
        d = lambda ps: (sum(not s1.present(l, hand) for l, _ in ps) - sum(not s1.present(s, hand) for _, s in ps)) / len(ps)
        est = d([p for v in by.values() for p in v])
        lo, hi = boot(by, d)
        out["A_L_minus_S"][st] = {"est": est, "ci95": [lo, hi], "n": len(common)}
        print(f"  {st}: L - S = {100*est:+.1f} pts [{100*lo:+.1f}, {100*hi:+.1f}] (n = {len(common)})")

    print("== 4. Family B end-to-end absence (judge lenient, not hand-checked)")
    out["B_end_to_end"] = {}
    repB = [i for i in items if i["text_kind"] == "report" and i["family"] == "B" and i["framing"] == "neutral"
            and i["arm"] in ("L", "S") and i["cell"] != "AU"]
    for st in ("low", "high"):
        for arm in ("L", "S"):
            R = [i for i in repB if i["stratum"] == st and i["arm"] == arm]
            by = collections.defaultdict(list)
            for i in R:
                by[i["set_id"]].append(i)
            k = sum(not i["lenient"] for i in R)
            lo, hi = boot(by, lambda ps: sum(not p["lenient"] for p in ps) / len(ps))
            out["B_end_to_end"][f"{st}_{arm}"] = {"absent": k, "n": len(R), "est": k / len(R), "ci95": [lo, hi]}
            print(f"  {st} {arm}: absent {k}/{len(R)} = {100*k/len(R):.1f}% [{100*lo:.1f}, {100*hi:.1f}]")
        sub = {arm: {(i["set_id"], i["worker_id"], int(i["sample"])): i for i in repB if i["stratum"] == st and i["arm"] == arm}
               for arm in ("L", "S")}
        common = [k for k in sub["L"] if k in sub["S"]]
        by = collections.defaultdict(list)
        for k in common:
            by[k[0]].append((sub["L"][k], sub["S"][k]))
        d = lambda ps: (sum(not l["lenient"] for l, _ in ps) - sum(not s["lenient"] for _, s in ps)) / len(ps)
        est = d([p for v in by.values() for p in v])
        lo, hi = boot(by, d)
        out["B_end_to_end"][f"{st}_L_minus_S"] = {"est": est, "ci95": [lo, hi], "n": len(common)}
        print(f"  {st}: L - S = {100*est:+.1f} pts [{100*lo:+.1f}, {100*hi:+.1f}] (n = {len(common)})")
    recB = [i for i in items if i["family"] == "B" and i["framing"] == "neutral" and i["text_kind"] == "ledger" and i["cell"] != "AU"]
    for st in ("low", "high"):
        R = [i for i in recB if i["stratum"] == st]
        print(f"  B ledger has an entry for the failing worker ({st}): {sum(i['ledger_entries_for_worker'] > 0 for i in R)}/{len(R)}")

    print("== 5. Family A, one failing worker: samples whose ledger has no entry for the failing worker")
    empty = [v for r in rows.values() for v in r if not v["rec"]]
    rec = [v for r in rows.values() for v in r if v["rec"]]
    ment = [v for v in empty if not v["L_abs"]]
    out["empty_ledgers"] = {"n": len(empty), "report_mentions": len(ment), "report_absent": len(empty) - len(ment),
                            "mentions_hand_checked": sum(v["L_src"] == "hand" for v in ment),
                            "absent_hand_checked": sum(v["L_src"] == "hand" for v in empty if v["L_abs"]),
                            "recorded_n": len(rec), "recorded_absent": sum(v["L_abs"] for v in rec)}
    e = out["empty_ledgers"]
    print(f"  not recorded: {e['n']}; L report still mentions: {e['report_mentions']} (hand-checked {e['mentions_hand_checked']}); "
          f"absent: {e['report_absent']} (hand-checked {e['absent_hand_checked']})")
    print(f"  recorded: {e['recorded_n']}; L report absent: {e['recorded_absent']}")
    ledA = [json.loads(l) for d in s1.DIRS for l in open(a.logs / d / "scores" / "ledgers.jsonl", encoding="utf-8")]
    lowA = [r for r in ledA if r["family"] == "A" and r["stratum"] == "low"]
    print(f"  family A one-failure ledgers with no entries at all: {sum(r['n_entries'] == 0 for r in lowA)}/{len(lowA)}")

    print("== 6. Ledger detector profile (echoed from results/analysis/results.json; not recomputed)")
    R = json.loads((a.repo / "results/analysis/results.json").read_text())
    out["detector"] = {}
    for f in ("A", "B"):
        F = R["families"][f]
        prof = {"recall_one": F["detection"]["lenient"]["low"], "recall_three": F["detection"]["lenient"]["high"],
                "au_flag": F["G1"]["au_flag_rate"], "clean_false_alarm": F["G2"]["false_alarm"],
                "clean_any_entry": F["G2"]["any_entry"]}
        out["detector"][f] = prof
        print(f"  {f}: " + "; ".join(f"{k} {100*v['est']:.1f}% [{100*v['ci95'][0]:.1f}, {100*v['ci95'][1]:.1f}] (n {v['n_pairs']})"
                                     for k, v in prof.items()))

    print("== 7. Family A, one failing worker, hidden-instruction cells (DC/DE): ledger-first absence by instruction phrasing")
    leak = {k: bool(s1.LEAK_STRICT.search(e["manager_view"]["final_message"])) for k, e in acc.items()}
    res = {}
    for g in (True, False):
        R = [i for i in A if i["text_kind"] == "report" and i["arm"] == "L" and i["cell"] in ("DC", "DE")
             and leak[(i["set_id"], i["worker_id"])] == g]
        res["phrasing" if g else "none"] = {"absent": sum(not s1.present(i, hand) for i in R), "n": len(R)}
    out["dcde_low_L_absent_by_phrasing"] = res
    print(f"  with 'as instructed' phrasing: {res['phrasing']['absent']}/{res['phrasing']['n']}; "
          f"without: {res['none']['absent']}/{res['none']['n']} (samples)")
    a.out.write_text(json.dumps(out, indent=1))
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
