"""Post hoc checks E1-E4 from the external judge report (7 Nov 2026), computed 8 Nov 2026 ~00:55 UK.

Run from a directory holding the unpacked */scores/items.jsonl of the stress-results log archive.
Descriptive; decides no pre-registered hypothesis. All outputs reported regardless of direction.
"""
import json, glob, random
from collections import defaultdict, Counter
rows=[]
for f in glob.glob("*/scores/items.jsonl"):
    rows += [json.loads(l) for l in open(f)]
print("rows", len(rows), Counter((r["text_kind"], r["arm"], r.get("framing")) for r in rows))
def sel(**kw):
    return [r for r in rows if all(r.get(k)==v for k,v in kw.items())]
def boot(pairs_by_set, fn, B=2000, seed=1):
    sets=sorted(pairs_by_set); rng=random.Random(seed); vals=[]
    for _ in range(B):
        samp=[s for s in (rng.choice(sets) for _ in sets)]
        v=fn([p for s in samp for p in pairs_by_set[s]])
        if v is not None: vals.append(v)
    vals.sort(); return vals[int(.025*len(vals))], vals[int(.975*len(vals))-1]
def rate(ps, key): 
    return sum(key(p) for p in ps)/len(ps) if ps else None
# E2/E3: ledger recording, family A, judge-free (entry for worker) vs lenient
for fam in ("A","B"):
  for strat in ("low","high"):
    L=[r for r in sel(text_kind="ledger",family=fam,stratum=strat,arm="L") if r["cell"]!="AU"]
    print(f"\nE2 {fam} {strat}: n={len(L)} entry-for-worker {sum(r['ledger_entries_for_worker']>0 for r in L)} lenient {sum(r['lenient'] for r in L)} strict {sum(r['strict'] for r in L)}")
    if strat=="low":
      for c in ("AC","AE","DC","DE"):
        Lc=[r for r in L if r["cell"]==c]
        print(f"   cell {c}: entry {sum(r['ledger_entries_for_worker']>0 for r in Lc)}/{len(Lc)} lenient {sum(r['lenient'] for r in Lc)} strict {sum(r['strict'] for r in Lc)}")
  AU=[r for r in sel(text_kind="ledger",family=fam,arm="L") if r["cell"]=="AU"]
  print(f"   AU: n={len(AU)} entry {sum(r['ledger_entries_for_worker']>0 for r in AU)} lenient {sum(r['lenient'] for r in AU)} strict {sum(r['strict'] for r in AU)}")
# E4: unconditional end-to-end absence in reports (lenient), neutral framing
print()
for fam in ("A","B"):
  for strat in ("low","high"):
    out={}
    for arm in ("L","S"):
      R=[r for r in sel(text_kind="report",family=fam,stratum=strat,arm=arm,framing="neutral") if r["cell"]!="AU"]
      by=defaultdict(list)
      for r in R: by[r["set_id"]].append(r)
      est=rate(R, lambda p: not p["lenient"]); lo,hi=boot(by, lambda ps: rate(ps, lambda p: not p["lenient"]))
      out[arm]=(R,by); print(f"E4 {fam} {strat} {arm}: absent {sum(not r['lenient'] for r in R)}/{len(R)} = {est:.3f} [{lo:.3f},{hi:.3f}]")
    # paired S-L by set
    keys=lambda r:(r["set_id"],r["worker_id"],r["sample"])
    Ld={keys(r):r for r in out["L"][0]}; Sd={keys(r):r for r in out["S"][0]}
    common=[k for k in Ld if k in Sd]
    by=defaultdict(list)
    for k in common: by[k[0]].append((Sd[k],Ld[k]))
    d=lambda ps: (sum(not s["lenient"] for s,_ in ps)-sum(not l["lenient"] for _,l in ps))/len(ps)
    lo,hi=boot(by,d)
    print(f"   S−L absent (paired by set/worker/sample, n={len(common)}): {d([p for v in by.values() for p in v])*100:+.1f} pts [{lo*100:+.1f},{hi*100:+.1f}]")
# E1 categories, family A low L
R={ (r["set_id"],r["worker_id"],r["sample"]):r for r in sel(text_kind="report",family="A",stratum="low",arm="L",framing="neutral")}
G={ (r["set_id"],r["worker_id"],r["sample"]):r for r in sel(text_kind="ledger",family="A",stratum="low",arm="L")}
cat=Counter()
for k,g in G.items():
    rec=g["lenient"]; rep=R[k]["lenient"]
    cat[(rec,rep)]+=1
print("\nE1 A low L (recorded, reported):",cat)
Rh={ (r["set_id"],r["worker_id"],r["sample"]):r for r in sel(text_kind="report",family="A",stratum="high",arm="L",framing="neutral")}
Gh={ (r["set_id"],r["worker_id"],r["sample"]):r for r in sel(text_kind="ledger",family="A",stratum="high",arm="L")}
print("E1 A high L (recorded, reported):",Counter((g["lenient"],Rh[k]["lenient"]) for k,g in Gh.items()))
