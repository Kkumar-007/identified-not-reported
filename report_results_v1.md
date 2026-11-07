# §4 Results — draft v1 (7 Nov 2026)

> EDITOR: Every number is from `results/analysis/results.json` (code `analysis.py` 778fe862, logs from the five folders in `s2431229_stress_results.tgz`, sha256 87b98056…) or `results/cause/cause_result.json`. The order follows prereg: gates → H1/H2 → H3–H5 → descriptives → exploratory. ~1,150 words of prose plus three tables: about 1.9 pages against a 1.5-page budget. Trim candidates are marked [trim].

**Reading rule for this section.** Two prereg rules decide how strongly anything here can be stated.
1. **Scoring.** The judge's strict field agreed with the 80 hand labels at κ = 0.09. The deterministic fallback rule scored κ = 0.13. Both are below the pre-registered 0.7, so H1–H5 are reported descriptively, with no confirmatory decision (prereg §5). The lenient field (κ = 0.79) and the downgrade field (κ = 0.83) passed and are kept.
2. **Gates.** Family B failed G1 and G2. Its H1–H5 are therefore reported as an instrument failure and not interpreted (prereg §6). They appear only in Appendix E.

Everything below is a description of what the managers did, not a test.

## 4.1 Validity gates

**Table 1. Validity gates and scoring validity.**

| Gate | Measure | Pass rule (prereg) | Family A | Family B |
|---|---|---|---|---|
| G1 Authorised changes | AU workers flagged in the ledger vs DE workers recorded | AU < ½ × DE | 35.0% vs 83.3% → **pass** | 75.0% vs 100% → **fail** |
| G2 Clean sets | Clean-set ledgers with ≥ 1 entry claiming a failure (J_FALSE) | < 15% | 0.0% (any entry: 0.0%) → **pass** | 25.6% (any entry: 51.1%) → **fail** |
| G3 Capacity | Loss when told to include every issue (CAP), high pressure, 97.5% upper bound | < 10% | judge-strict 11.8% → **fail**; lenient 2.2% | judge-strict 6.2% → pass |
| Scoring | κ vs 80 hand labels | ≥ 0.7 per field | strict 0.09 · rule 0.13 · lenient 0.79 · downgrade 0.83 (pooled across families) | |
| Exclusions | Sets excluded at stage B | reported only | 0 of 130 (shared: workers are generated once) | |

Caption: "G1 and G2 test whether the ledger records failures rather than test noise or nitpicks. A family that fails either has its H1–H5 treated as an instrument failure (prereg §6). G3 asks whether the 120-word cap itself forces loss. The downgrade κ rests on the 24 hand-labelled items that were strict-reported. Intervals: cluster bootstrap over sets, 2,000 resamples."

Family A's ledger passed both instrument gates. Family B's ledger over-flagged: it recorded 75% of workers whose deviation the director had approved, and half its clean-set ledgers listed something. B's ledger-conditioned numbers are not interpreted. Its reports are still scored, and they appear in §4.5 and §4.6, which do not depend on the ledger. G3 fails for A on the registered score (upper bound 11.8%) but passes on lenient (2.2%). Under the registered score, A's loss would carry the "capacity-limited" label. Since that score did not validate, we report both numbers and draw no prioritisation claim from either.

## 4.2 Detection and reporting loss by pressure (H1, H2)

**Detection is where failures disappear.** On the validated lenient score, family A's ledger recorded 99.7% [99.2, 100.0] of failures when three competed (n = 360), but only 54.2% [39.2, 68.3] when a failure was alone (n = 120). The gap is behaviour, not a parsing artefact. 55 of the 120 low-pressure ledgers are clean `{"issues": []}` outputs, generated first time and clustered by set: 15 sets are empty in all three samples, 20 in none. In 34 of those 55 samples, the same conversation's report goes on to mention the failure the ledger left out. The manager knew about it but did not log it.

**Reporting loss, once recorded, is near zero.** Table 2 gives L-arm loss: the share of failures recorded in a sample's ledger that are absent from that sample's report.

**Table 2. Reporting loss in the ledger arm, family A (descriptive; 97.5% intervals as pre-registered).**

| Score | H1: loss, high pressure | n pairs | H2: high − low |
|---|---|---|---|
| Lenient (κ 0.79) | 0.3% [0.0, 1.1] | 359 | +0.3 pts [+0.0, +1.1] |
| Judge-strict, case-insensitive ID (D-2) | 4.5% [0.5, 9.2] | 222 | +1.9 pts [−7.8, +7.9] |
| Judge-strict, registered case-sensitive ID | 46.4% [32.4, 59.9] | 222 | +43.8 pts [+28.2, +58.8] |
| Rule fallback (κ 0.13) | 18.8% [12.1, 26.0] | 260 | +5.2 pts [−11.4, +19.8] |

Caption: "Loss = P(not in the report | recorded in the same sample's ledger). Denominators differ by score because 'recorded' is scored with the same field. Rows 2–4 use unvalidated scores. Under the registered rules no H1/H2 decision is made."

On the lenient score, A's upper bound (1.1%) lies below the 5% band. Had lenient been the primary score, that would meet the pre-registered "faithful at this pressure" band. It was not the primary score, so we describe the result and make no decision. H2 shows no load effect on lenient or judge-strict. The H2 contrast also compares **selected populations**. The low-pressure denominator is the 54% of failures A's ledger chose to record, so the high − low difference mixes load with whatever made a lone failure worth logging. We state this regardless of the cause.

**The registered match rule.** Row 3 is the pre-registered rule as committed. It matches worker IDs case-sensitively, as `worker_3`. On 6 Nov at 19:22 UK, before any pilot or main-run output existed, we changed the ID match to case-insensitive (D-2, pushed in `aacae4b`). The reason was a clean smoke-test set: in it, family A wrote `Worker_8` in 6 of 6 reports and never the lower-case form. The first outcome table was computed on 7 Nov at about 05:25 UK. The two rules put H1 at 4.5% and 46.4%. Nearly all of that 42-point gap is spelling: under the committed rule, "Worker_3's function fails two tests" counts as not reported unless the function is also named. §4.6 gives a second, independent sign that this is casing: when the budget changes, the casing changes, and the committed score moves with it.

## 4.3 Severity (H3)

Core and edge failures were dropped at the same, near-zero rate. On lenient, A's high-pressure L loss was 0.0% for core failures (n = 179) and 0.6% [0.0, 1.8] for edge failures (n = 180). Judge-strict gives 4.3% [0.0, 9.9] and 4.8% [0.0, 12.0]. There is no sign of triage by severity, because there is almost nothing to triage. Cell matters more than severity on judge-strict: admitted-failure cells lose 21.4% [2.9, 43.4] (n = 42), deviation cells 0.6% [0.0, 1.8] (n = 180). Only 42 admitted pairs were strict-recorded, against 179 on lenient, so this contrast rests on few pairs and an unvalidated score.

## 4.4 Does writing failures down first protect them? (H4)

We define **recoverable items** as failures recorded in at least 2 of the 3 ledgers of their set. They give a denominator for the spontaneous (S) arm, which writes no ledger. Among recoverable items at high pressure, A's S reports omitted 5.0% [2.5, 8.3] on lenient (n = 360), against 0.3% for L reports of the same items: +4.7 points [+1.9, +8.1]. Judge-strict gives +8.1 [+2.5, +15.3]. Writing the ledger first coincides with fewer omissions. This is descriptive. The ledger step also asks for a severity rating and evidence quote, so "writing it down" and "triaging it" are not separated (Appendix A).

## 4.5 Framing (H5)

Telling the manager it is responsible for what reaches the director made no difference against a placebo sentence: −0.7 points [−4.3, +2.6] on lenient, −0.4 [−7.7, +7.1] on judge-strict (S arm, recoverable items, both loads). Median report length was unchanged (57–58 words). [trim: J_OPT stratified table → Appendix E.]

## 4.6 Descriptives: what happens to failures that are reported

**Softening (D4, descriptive).** Among failures that were reported (judge-strict), A's spontaneous reports described 54.5% [44.4, 64.1] as fixed, minor, in progress, acceptable or not affecting delivery while they still failed (n = 233). B's described 60.2% [51.7, 68.5] (n = 256). With a ledger written first, the rates were 7.4% [3.3, 12.1] for A and 36.6% [30.1, 43.6] for B. These rates are softer than they look in one respect. A post hoc regex that removes downgrades whose only cue is "in progress" lowers A's spontaneous rate to 30% (56 cases removed). It barely moves the other cells: L/high 7% → 6%, and B is about unchanged. We therefore report A's spontaneous softening as a range of 30–55%. Two caveats apply. The downgrade κ of 0.83 rests on 24 hand-labelled cases, and the denominator is judge-strict-reported, which inherits that score's weakness.

**Cause flipping (D-6, exploratory, post hoc).** In the admitted cells, the failure is a contradictory test pair, so the true cause is always the test or specification. Of 80 worker messages (hand-coded):
- 32 blamed the test or spec only;
- 11 blamed both test/spec and code;
- 37 blamed only their own code (source misframing; the error starts with the worker).

Where the worker did blame the test or spec and the report mentioned the item, A's managers reported a code-only cause in 37.8% [27.0, 48.6] of cases (91/241). B's did so in 10.5% [5.6, 16.7] (27/257). The judge's cause codes agreed with 40 hand-coded reports at κ = 0.82 and 0.84. Pairs pool both loads and both arms, and the intervals bootstrap over sets.

**Word budget.** Reports sat well under the cap. A's median L report was 59 words (B 92), and no A report reached 120 words (B: 5 L reports truncated). Omission therefore does not come from running out of words.

## 4.7 Exploratory: a 60-word cap (D6, family A only)

The pre-registered trigger is a high-pressure H1 point estimate below 5%. It fired on judge-strict (4.5%), so we ran a 60-word cap on the same ledgers. We ran it for family A only, because B's ledger failed G1/G2 (D-7). Lenient loss was unchanged at 0.3% [0.0, 0.8] (n = 359; difference +0.0). Managers did not use the extra compression to drop failures, and the median report was 35 words, again well under the cap. Judge-strict loss rose from 4.5% to 10.4% [4.9, 16.4] (paired +5.9 pts [+1.8, +10.2]). Because that score failed validation, we do not read the rise as "the description is dropped". The committed and rule scores went the opposite way (−9.5, −8.8 pts). That is a casing artefact: at 120 words, A wrote `Worker_N` 304 times and `worker_N` 60 times; at 60 words, 140 and 216. The case-sensitive rule rewards the lower-case form. This arm supports no claim about H1 or H2.
