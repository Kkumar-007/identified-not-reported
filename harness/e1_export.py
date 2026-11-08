"""E1 (D-8): blind hand-check sheet for judge 'absent' calls on family A reports.

  python harness/e1_export.py --logs <dir with pilot_h200/ main_s1..4/ unpacked> --out results/posthoc

Sample (fixed in deviations.md D-8 before any coding): every family-A, neutral, L/S report pair that the
judge scored lenient-absent (injected failures only, AU excluded), plus 30 judge-present pairs drawn with
random.Random(derive_seed(master_seed, "e1")), 8/7/8/7 from L-low, S-low, L-high, S-high. The 72 rows are
shuffled with the same generator. The coder sees only worker, function, problem and report text.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import derive_seed  # noqa: E402

MASTER_SEED = 20261106
STRATA = (("L", "low", 8), ("S", "low", 7), ("L", "high", 8), ("S", "high", 7))


def jl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def key(r: dict[str, Any]) -> tuple[str, str, str, int]:
    return (r["set_id"], r["worker_id"], r["arm"], int(r["sample"]))


def load(logs: Path) -> tuple[list[dict[str, Any]], dict[tuple[str, str, str, int], dict[str, str]]]:
    items: list[dict[str, Any]] = []
    texts: dict[tuple[str, str, str, int], dict[str, str]] = {}
    for d in sorted(p for p in logs.iterdir() if (p / "scores" / "items.jsonl").exists()):
        items += [r for r in jl(d / "scores" / "items.jsonl")
                  if r["text_kind"] == "report" and r["family"] == "A" and r["framing"] == "neutral"
                  and r["arm"] in ("L", "S") and r["cell"] != "AU"]
        for c in jl(d / "judge_calls.jsonl"):
            if c["prompt"] != "J_ITEM" or c["text_kind"] != "report" or c["family"] != "A" or c["framing"] != "neutral":
                continue
            msgs = json.loads((d / "prompts" / f"{c['prompt_hash']}.json").read_text(encoding="utf-8"))
            user = next(m["content"] for m in msgs if m["role"] == "user")
            m = re.search(r"Function: (.*?)\nProblem: (.*?)\n\nTEXT \(REPORT\)\n<<<\n(.*?)\n>>>", user, re.S)
            if m is None:
                raise ValueError(f"unparsed judge prompt {c['prompt_hash']}")
            texts[key(c)] = {"function_name": m.group(1), "problem": m.group(2), "text": m.group(3)}
    return items, texts


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--logs", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    items, texts = load(a.logs)
    items.sort(key=lambda r: (r["set_id"], r["worker_id"], r["arm"], r["sample"]))
    absent = [r for r in items if not r["lenient"]]
    rng = random.Random(derive_seed(MASTER_SEED, "e1"))
    present: list[dict[str, Any]] = []
    for arm, stratum, n in STRATA:
        pool = [r for r in items if r["lenient"] and r["arm"] == arm and r["stratum"] == stratum]
        present += rng.sample(pool, n)
    rows = absent + present
    rng.shuffle(rows)
    a.out.mkdir(parents=True, exist_ok=True)
    with open(a.out / "e1_blind.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["check_id", "worker_id", "function_name", "problem", "report", "mentions (yes/no/unsure)", "notes"])
        with open(a.out / "e1_key.jsonl", "w", encoding="utf-8") as k:
            for i, r in enumerate(rows, 1):
                t = texts[key(r)]
                cid = f"E{i:02d}"
                w.writerow([cid, r["worker_id"], t["function_name"], t["problem"], t["text"], "", ""])
                k.write(json.dumps({"check_id": cid, "set_id": r["set_id"], "worker_id": r["worker_id"], "arm": r["arm"],
                                    "stratum": r["stratum"], "sample": r["sample"], "cell": r["cell"],
                                    "judge_lenient": r["lenient"]}) + "\n")
    print(f"absent {len(absent)} present {len(present)} total {len(rows)}")


if __name__ == "__main__":
    main()
