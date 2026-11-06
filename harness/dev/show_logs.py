"""Print a compact view of a run directory: one line per call, then episodes and manager outputs.

  python dev/show_logs.py <log_dir> [--full N]   (--full N also prints the N-th call row in full)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def rows(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.exists() else []


def one_line(s: str | None, n: int) -> str:
    s = (s or "").replace("\n", "\\n")
    return s if len(s) <= n else s[: n - 1] + "…"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("log_dir")
    ap.add_argument("--full", type=int, default=None)
    a = ap.parse_args()
    d = Path(a.log_dir)
    calls = rows(d / "calls.jsonl")
    print(f"== calls.jsonl ({len(calls)} rows)")
    for r in calls:
        who = r["worker_id"] or f"{r['arm']}/s{r['sample']}"
        print(f"{r['set_id']} {r['family']} {r['stage'][:3]} {who:10s} {r['framing'] or '-':8s} t{r['turn']} try{r['try']} "
              f"seed={r['seed']:<10d} hash={r['prompt_hash'][:10]} ptok={r.get('prompt_tokens')} "
              f"ctok={r.get('completion_tokens')} cached={r.get('cached_tokens')} model={r['model']} "
              f"fin={r['finish_reason']} out={one_line(r['output'], 70)}")
    if a.full is not None:
        print(json.dumps(calls[a.full], indent=1, ensure_ascii=False))
    print("== episodes.jsonl")
    for e in rows(d / "episodes.jsonl"):
        print(f"{e['set_id']} {e['worker_id']} {e['cell']:5s} {e['problem_id']} try{e['try']} runs={e['n_runs']} "
              f"end={e['end_reason']} accepted={e['accepted']} hidden_pass={e['hidden_pass']} "
              f"failed_checks={[k for k, v in e['checks'].items() if not v]} "
              f"status={one_line((e['final_message'] or '').splitlines()[-1] if e['final_message'] else None, 90)}")
    print("== workers_final.jsonl")
    for f in rows(d / "workers_final.jsonl"):
        print(f"{f['set_id']} excluded={f['excluded']} "
              f"{[(p['worker_id'], p['cell'], p['problem_id']) for p in f['positions'] if p]}")
    print("== manager_outputs.jsonl")
    for m in rows(d / "manager_outputs.jsonl"):
        led = m["ledger"]
        print(f"{m['set_id']} {m['family']} {m['arm']:3s} {m['framing']:8s} s{m['sample']} "
              f"ledger_entries={None if led is None else len(led['issues'])} words={m['report_words']} "
              f"report={one_line(m['report'], 80)}")
    sw = rows(d / "swaps.jsonl")
    print(f"== swaps.jsonl ({len(sw)} rows)")
    for s in sw:
        print(s)


if __name__ == "__main__":
    main()
