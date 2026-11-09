# Stage 2+3 (compressed): narrative for "The Empty Ledger"

Written 8 Nov 2026, about 18:50 UK. Status: **awaiting Kaustubh's approval**; nothing in the manuscript, prereg or deviations log has changed.
Inputs: `review/stage1_diagnosis.md` (F1–F9), handoff Chat 11, `prereg.md`, `deviations.md`, `report/report.md`.
F1–F3 re-confirmed: `review/stage1_checks.py` rerun on `release/ibnr-release-v1.tar.gz` (sha256 `2f8ad0ff…a52d`, matches the .sha256 file) gives output byte-identical to `review/stage1_checks_output.txt`.
Constraints from Kaustubh: not yet submitted; title stays "The Empty Ledger: When Logging Issues First Lets a Lone Failure Slip Through"; no position-swap run (F1 is post hoc, D-9).

Every number below is already in `results.json`, `results/posthoc/`, `cause_result.json`, `deviations.md` or `review/stage1_checks_output.txt`. The only derived figure is 20/55 (absent reports among empty ledgers): 55 empty ledgers (deviations.md, 7 Nov record) minus 35 with a mention (A.2) = 20, which equals Table 2's L count.

## Thesis (one sentence)

A coordinator agent forwards almost every failure it writes down, so the risk sits in what it writes down: in a Qwen3-8B coordinator, a "log issues first" step that closes every gap when three of nine workers fail misses one lone failure in six, mostly when that worker's transcript comes early in its context.

## Claims and evidence

| # | Claim | Status | Evidence | Validation | Main threat |
|---|---|---|---|---|---|
| C1 | Once a failure is in the ledger, it reaches the director | **Pre-registered** question (H1–H3); descriptive only, because the primary score failed κ | Transmission loss 0.3% [0.0, 1.1] (1/359, three failures; that one hand-coded unsure); 0/65 with one failure; H2 +0.3 pts; core 0/179; CAP 0.6%; median 59 words, so the cap never bound | Lenient κ 0.79 (positives only), plus every judge absence hand-checked (40/42 confirmed, 2 unsure) | Family A only (B gate-failed). "Reaches" means *mentioned*, not stated accurately. Judge-strict 4.5% is unvalidated |
| C2 | A ledger-first step changes which failures get written down, and the report often follows the ledger | **Post hoc.** L vs S: D-8 (rule committed before hand-coding). Position: D-9 (new; observational; found in review after three moderators were examined) | One failure: L 20/120 vs S 2/120 (S − L −15.0 pts [−25.8, −5.8]). Three: L 0/360 vs S 18/360 (+5.0 [+2.2, +8.1]). Absent given an empty ledger 20/55, given a recorded failure 0/65. 18/20 losses at positions 1–3; recorded 7/39 early vs 34/48 late; position 2: 0/24; P07, P23 and R11 flip with position. Family B: ledger recorded 120/120; reports absent 0/120 in both arms | Absences hand-checked (E1); recording is judge-free | One model. 5 sets supply 15 of the 20 losses. Position was never counterbalanced. B's "no loss" comes with a ledger that flags almost everything |
| C3 | A presence check overstates fidelity: forwarded failures are often softened or misattributed | **Exploratory.** Softening is a pre-registered descriptive (D4) on an unvalidated denominator; the "in progress" split is post hoc; cause flipping is post hoc (D-6) | S softening 79% (one failure) / 55% (three), or 73% / 30% without "in progress"-only cases; L at three failures 7%. Cause flip, family A: 37.8% [27.0, 48.6] (91/241) vs reverse 2/212; B 10.5% | Downgrade κ 0.83 on n = 24; the denominator uses strict (κ 0.09). Cause κ 0.82/0.84 on 40, mention denominator lenient (validated) | Workers misframed first (37/80 blamed their own code). Single coder who is also the designer |

Two corrections to the current text follow from the matrix:
- "The report followed the empty ledger" is true of the 20 losses, but 35 of 55 empty-ledger reports still named the failure. The accurate statement is that an empty ledger raised omission from about 2% to about 36%.
- Family B is not a failed replication of the *mechanism*. Its ledger is never empty, so the mechanism never triggers. It is a failed replication of the *generality* in the title.

## Alternative narratives

| | Narrative | What it buys | What a skeptic says | Title fit |
|---|---|---|---|---|
| (a) | **Ledger trade-off, narrowed.** In one 8B coordinator, logging issues first closes multi-failure gaps but misses lone failures that come early in context | Vivid. It matches the title. One actionable test: "check your issue step on a single failure" | "A prompt × position artefact of Qwen3-8B; Ministral doesn't show it" | Exact |
| (b) | **The pre-registered answer.** Transmission is not the bottleneck; loss happens at recording and in description | The only question asked in advance, with the best-validated numbers | "Descriptive, presence-only, and you validated the easy half." A near-null is a weak hook for engineers | Indirect |
| (c) | **Presence hides distortion.** A completeness check would pass these reports, yet they soften or misattribute failures | Strongest Track 4 relevance (failure laundering); Box 1 | "The boldest numbers rest on the weakest measurement (strict κ 0.09); softening halves without 'in progress'" | Poor |
| (d) | **The ledger as a detector with a threshold** (mine). A's ledger is precise but misses (0% clean-set false alarms, 54% lone recall). B's catches everything but raises false alarms (75% of approved changes, 26% of clean sets). The report inherits whichever error the ledger makes | Uses B instead of discarding it. Precision/recall is native to engineers, and it explains B's 0/120 | "Two models are not a threshold curve." Prereg §6 bars *interpreting* B's ledger, so this is allowed as description only. "B's reports inherit its false alarms" was not computed | Good |
| (e) | **Position decides visibility.** In a single issue pass, where a failure sits decides whether it is seen | Largest effect (+46 pts) | "Observational, 13 early sets, found after the results." It cannot lead without the swap run | Partial |

## Recommendation

Use **(b) as the frame and (a) as the headline**. That is the funnel the paper already has (written down → reaches the director → how it is described), with the emphasis moved.

1. The abstract and introduction state the pre-registered answer in one sentence (forwarding is near-lossless). The empty-ledger result follows immediately, with its scope in the same sentence: family A, lone failures, mostly early in context, post hoc. Then one clause on family B: its ledger flags almost everything, and it lost none.
2. Use (d) as **one descriptive sentence** explaining family B, without reinterpreting the gates.
3. (c) becomes one short exploratory subsection. Lead with cause flipping, which is the better-validated of the two. Give softening as a range with its denominator caveat. Take 79% / 55% out of the abstract.
4. Position goes in the main text as a labelled post hoc paragraph plus a small panel (D-9). The untested mechanisms get one line.
5. H1–H5 shrink to three sentences or a small table.
6. **The title stays and is read literally.** "When" names the conditions found: a lone failure, an issue-first step, an early position, this model.

**Track fit (framing, not a claim).** A single deviating worker among compliant peers has the statistical shape a lone misaligned agent's deviation would have, and it is exactly the case where the ledger step fails. One sentence in the introduction can make this link without claiming any adversary.

**What this gives up:** the reading of the result as a property of ledger steps in general, and softening as a headline number.
