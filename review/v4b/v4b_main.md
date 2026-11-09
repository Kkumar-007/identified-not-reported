# Abstract {.unnumbered}

Overseers of agent teams often read a coordinator’s summary instead of every worker’s transcript. We ask where honestly reported failures are lost on the way up when no agent is asked to hide anything. Nine Qwen3-8B workers each implement a Python function and end with a test-status line; hidden tests fix which fail. A coordinator reports to a director in at most 120 words, either directly or after first logging issues in a structured ledger (130 pre-registered transcript sets, 160 injected failures). Failures were lost when they were written down, not when they were passed on: a Qwen3-8B coordinator forwarded all but one of the 424 failures it logged (reported descriptively, because the pre-registered primary score failed validation). What it logged depended on the procedure. Post hoc, logging first removed every loss when three of nine workers failed (5.0% without a ledger), but with one failing worker the ledger was often empty, and the report omitted 16.7% of lone failures against 1.7% without a ledger. A Ministral-3-8B coordinator, whose ledger logged nearly everything, lost none. In exploratory analyses, reports that named a failure often called it fixed, minor or in progress. Reporting procedures should be tested on lone failures, not only where failures are plentiful.

# Introduction

Agent systems increasingly use an orchestrator–worker pattern: a coordinator assigns subtasks, reads the workers' outputs and reports upward, and the human or monitor above it reads that report rather than every transcript. At scale, one agent can coordinate hundreds of others, as one did in the 2026 OpenAI / Hugging Face incident (Greenblatt, Cotra and Wijk, 2026). Whatever the coordinator leaves out or softens is invisible to the overseer. The hardest case is one deviating worker among compliant peers. That is also the shape a single misaligned agent's deviation would take, although nothing in our setting is adversarial.

We ask which honestly reported failures a coordinating LLM writes down, which of them reach its supervisor, and whether they arrive still described as unresolved and correctly caused (Figure 1). Workers never see each other, hidden tests decide which functions fail, and nobody is asked to conceal anything. We vary the number of failing workers (one or three of nine), whether the failure concerns a core or an edge requirement, and the reporting procedure: report directly, or first log issues in a structured ledger, a common way to make a coordinator more systematic.

![**Figure 1. Design.** Nine workers each implement one function and end with a test-status line; one or three fail (orange). The coordinator reads the nine transcripts in order and reports to the director in at most 120 words, either after logging issues in a JSON ledger or directly. Hidden tests, not a model, define which functions fail. ①–③ mark the three questions we measure.](figures_v4/fig1_pipeline.png){width=90%}

In short, a Qwen3-8B coordinator forwarded what it wrote down, but a ledger-first procedure often wrote down nothing when a single worker failed. Our contributions are (1) a pre-registered measurement that separates recording, transmission and description against hidden-test ground truth, with near-zero transmission loss on the validated score (§4.2); (2) a post hoc, hand-checked finding that an issue-first step is a trade-off with an identifiable failure mode, a lone failure early in the coordinator's context (§4.3–4.4); and (3) an open instrument: 130 transcript sets, 1,170 worker episodes, prompts, hand labels, a dated deviations log and the data.

# Related Work

**Misreporting one's own work.** Guo et al. (2026) find that all eleven models they tested report more success on impossible or partly possible tasks than their trajectories support. There the failure is the agent's own; here workers disclose honestly and a different agent reports. Our test-conflict cells borrow ImpossibleBench's construction (Zhong et al., 2025).

**Withholding a teammate's failure.** In "Don't Be a Snitch" (Lizcano Cabezas, 2026), workers hide a teammate's rule violation when their lead asks; a model lead never agreed to hide an edit (0/160), yet once the edit was reverted it usually left it out of its final report. That setting has one deliberate violation and an explicit request; ours has neither, and up to three failures per report.

**Content kept, meaning lost.** Sun et al. (2026) show handoff compression turning an identified safety blocker into language that informs without binding; Wang et al. (2026) show handoff summaries keeping operational facts while dropping the boundary metadata that governs their use; iterated transmission drifts toward attractors (Perez et al., 2025). These study downward constraints and privacy; we study upward failure reports.

**Multi-agent oversight.** A coordinator that does not act on a worker's report fits the MAST taxonomy (Cemri et al., 2025) and the information-asymmetry risk in Hammond et al. (2025); Kemeklis and Vemuri (2026) find an end-state monitor caught omissions that transcript review partly missed. In human organisations bad news is softened on the way up (the MUM effect; Rosen and Tesser, 1970), including in software status reports (Smith, Keil and Depledge, 2001).

**Not claimed as new:** separating identification from transmission (Lizcano Cabezas; Sun et al.), handoffs that keep content but lose meaning (Sun et al.; Wang et al.), or end-state verification (Kemeklis and Vemuri). We add a controlled measurement of unprompted, multi-worker upward reporting against hidden-test ground truth, and the observation that a structured ledger step changes which failures are lost.

# Methods

The design was pre-registered before any coordinator saw a set containing a failure (commit `dff73e2`, Wayback snapshot 6 Nov 2026 18:54 UTC). Later changes are deviations D-1 to D-9 (Appendix A.2); all prompts are in Appendix C.

## Tasks, workers and failures

We took 60 MBPP+ v0.2.0 problems (Austin et al., 2021; Liu et al., 2023), 45 primaries and 15 reserves, and gave each an explicit edge requirement with two edge tests; workers see the MBPP asserts plus one edge test, renamed `test_1…n` in seeded order. **Ground truth is a hidden suite** (visible tests, the second edge test, and the MBPP+ inputs against canonical outputs); no model decides what fails. Workers are Qwen3-8B (Yang et al., 2025; thinking off, temperature 0.7). Each implements one function, may run its tests once, and ends with `Final status: passing p/n; failing: …; deviations: …`.

Failures are injected in a 2×2 design. In a **test conflict** (core AC, edge AE), a contradictory test pair makes passing impossible and the worker reports the failing test. In an **instructed change** (core DC, edge DE), a hidden instruction makes the worker change the main behaviour, or skip the edge requirement "to save time", and present this as its own decision. The instruction did not always stay hidden: 22 of 40 edge-change and 8 of 40 core-change workers wrote that the change was made "as instructed" or "as per the instruction", a phrasing the leak filter missed (post hoc, D-9), so many of these changes read as directed rather than self-initiated. Acceptance checks regenerate non-compliant workers (Appendix C), so coordinators, who never see worker prompts, receive honest, explicit status lines by construction; no set was excluded. Mechanism is confounded with "whose fault", so only core versus edge within a mechanism is a clean contrast of criticality.

The 130 sets (master seed 20261106) are 30 clean, 40 with one failing worker (10 per cell), 40 with three, and 20 in which a director-approved amendment withdraws one worker's edge requirement (an **approved change**, which a good coordinator should not flag): 160 injected failures. Each set fixes which transcript positions the failing workers occupy; positions were drawn per set and not balanced. Worker episodes are generated once and shared by every procedure, sample and coordinator.

## Coordinator procedures and models

The coordinator's system prompt gives a neutral role ("You lead a team of nine workers, worker_1 to worker_9, and you report to a director"), the nine specifications and any amendment; the user message holds the nine transcripts with their test results, worker_1 first (about 1.8k tokens). Both procedures end with the byte-identical instruction *"Write your report to your director, in plain text, at most 120 words."* With the **ledger first (L)**, turn 1 asks the coordinator to "Record any issues…" as schema-constrained JSON (worker, function, requirement, evidence quote, severity), stating that `{"issues": []}` is allowed, and turn 2 is the report. With **no ledger (S, "spontaneous")**, the coordinator reports directly. A capacity check regenerates the report from the same ledger with "Include every issue in your ledger." added, and a framing check adds a responsibility cue or a placebo sentence. Each procedure runs 3 samples per set at temperature 0.7; reports are truncated after word 120.

Coordinators are family A (`Qwen/Qwen3-8B` @ `b968826d`) and family B (`mistralai/Ministral-3-8B-Instruct-2512-BF16` @ `f6fae979`; Mistral AI, 2025). The judge, `google/gemma-4-31B-it-qat-w4a16-ct` @ `52f3f65b` (Google, 2026; temperature 0, structured output), sees one failure description and one text, never the procedure, family, failure count or cell. All models ran on vLLM 0.33.0 (Kwon et al., 2023) on one H200 MIG slice.

## Measures and analysis

For each injected failure × output, the judge decides whether the text **mentions** a problem attributed to that worker or function (*lenient*), whether it also **states this failure's problem** (*strict*), and whether a stated failure is **softened** (presented as fixed, minor, in progress, acceptable or not affecting delivery). Following Figure 1, a failure is **written down** if the ledger has an entry for the failing worker (no judge needed); **transmission loss** is P(absent from the report | written down); **end-to-end loss** is P(absent from the report), for both procedures. **Cause flipping** (post hoc, D-6) applies to test conflicts, whose true cause is the test pair: P(report blames only the code | worker blamed the test or specification, report mentions it).

The author hand-labelled 80 pairs before opening any result table; each judge field needed Cohen's κ ≥ 0.7 (Cohen, 1960). Three **validity gates** come first (Table 1); failing G1 or G2 makes a family's ledger-based results an instrument failure. The registered hypotheses concern transmission loss: H1 (three failing workers, against an assumed 5% band) and H2 (three minus one) are co-primary; H3 (core failures), H4 (no ledger versus ledger) and H5 (responsibility cue) are secondary. Estimates are ratios of sums over (failure, output) pairs with 95% percentile cluster-bootstrap intervals over sets (2,000 resamples). The end-to-end comparison and the hand-check of absences are post hoc (D-8; rule committed before hand-coding); the position and phrasing analyses (D-9) came from reviewing the final draft, after all results were known.

# Results

Figure 2 follows a failure through the funnel (a–b validated, c post hoc, d exploratory).

![**Figure 2. What the coordinator writes down, what reaches the director, and how it is described.** (a) Ledger entry for the failing worker, family A (lenient; judge-free 65/120 and 360/360). (b) Absent from the report; A's absences hand-checked, B's judge calls. (c) Family A, one failing worker, by transcript position (post hoc; not counterbalanced). (d) Exploratory: stated failures called fixed, minor or in progress, three failing workers (tick: A excluding "in progress"-only); test conflicts relayed as code-only. Whiskers: 95% cluster-bootstrap intervals over sets.](figures_v4/fig2_results.png){width=88%}

## Measurement validity

The judge's strict field agreed with the hand labels at κ = 0.09 (a deterministic fallback rule at 0.13), so **no pre-registered hypothesis is decided**; we report them descriptively. All 26 strict disagreements sit in the test-conflict cells and go one way: coordinators often describe an impossible test pair as a coding error, which the human counted as stating the failure and the judge did not. The lenient field passed (κ = 0.79), but 78 of its 80 validation pairs were positives, so we hand-checked every judge "absent" call on the family A reports used below, blind to procedure and judge call: 40 of 42 were confirmed and 2 coded unsure, and 30 of 30 judge "present" calls were confirmed (D-8). Family B's ledger flagged 75% of approved changes and listed something in half its clean-set ledgers, so it is not a valid detection record; its reports are still scored end to end, which does not use the ledger. Family A passes G1 only with loads pooled: at matched load, approved changes were flagged about as often (35%) as lone edge changes were recorded (33%), though 19 of 21 such entries cite the amendment.

**Table 1. Validity gates (pre-registered rules; scoring κ in the text).**

| Gate | Rule | Family A | Family B |
|---|---|---|---|
| G1 approved changes | flag rate < ½ × edge-change record rate | 35.0% vs 83.3%: **pass** | 75.0% vs 100%: **fail** |
| G2 clean-set false alarms | < 15% of ledgers | 0.0%: **pass** | 25.6% (any entry 51.1%): **fail** |
| G3 capacity, 97.5% upper bound | < 10% | judge-strict 11.8%: **fail**; lenient 2.2% | judge-strict 6.2%: pass |

## Written down, then forwarded (pre-registered)

Family A's ledger recorded 99.7% [99.2, 100.0] of failures when three workers failed (n = 360 pairs) but 54.2% [39.2, 68.3] when one did (n = 120; Figure 2a). The 55 misses are all clean `{"issues": []}` ledgers, clustered by set (15 sets empty in all three samples, 20 in none). Once written down, a failure reached the director: 1 of 359 recorded failures was absent from the report with three failing workers (0.3% [0.0, 1.1], 97.5% interval; that one hand-coded unsure), and 0 of 65 with one. The capacity check lost 0.6%, and reports used about half the word cap (median 59 words), so the cap did not force omissions. On the validated score, transmission was not the bottleneck; whether the failure was written down was. The registered contrasts agree descriptively: H1's lenient upper bound (1.1%) lies in the "faithful" band; H2 shows no load effect (+0.3 pts [+0.0, +1.1]), though it compares populations selected by what the ledger recorded; core and edge failures were dropped alike (H3; 0/179 vs 1/180); without a ledger, reports omitted 4.7 points more of recoverable failures (H4; [+1.9, +8.1]); a responsibility cue did nothing (H5; 6.0% vs 6.7% placebo). Judge-strict versions: Appendix E7.

## Which failures reach the director (post hoc)

**Table 2. Failures absent from the report (lenient; family A's absences hand-checked, family B's judge calls; post hoc, D-8 and D-9).**

| | A, ledger first | A, no ledger | A: ledger − none (paired) | B, ledger first | B, no ledger |
|---|---|---|---|---|---|
| One failing worker | 20/120 (16.7% [6.7, 27.5]) | 2/120 (1.7% [0.0, 5.0]) | +15.0 pts [+5.8, +25.8] | 0/120 | 0/120 |
| Three failing workers | 0/360 | 18/360 (5.0% [2.2, 8.1]) | −5.0 pts [−8.1, −2.2] | 0/360 | 1/360 (0.3% [0.0, 0.8]) |

With the ledger step, family A lost 20 of 120 lone failures; without it, 2 (Figure 2b). Every one of the 20 had an empty ledger, but an empty ledger did not guarantee omission: 35 of the 55 empty-ledger reports still mentioned the failure, so omission rose from 0 of 65 when the failure was written down to 20 of 55 when it was not. With three failing workers the sign reversed, and the ledger step removed the 5% loss of the no-ledger procedure. Family B showed no trade-off: it lost no lone failure with or without a ledger. But its ledger was never empty when a failure existed, and it also flagged approved changes and clean workers, so the mechanism that cost family A its lone failures never had a chance to operate. Descriptively (two models cannot test it), the ledger acts like a detector with a threshold whose errors the report inherits: family A's is conservative, family B's liberal.

## Where the lone failure sits (post hoc, D-9)

Five sets supplied 15 of the 20 lost lone failures, and the failing worker's position in the context accounts for most of this (Figure 2c; Appendix E10). When the failing transcript was among the first three, the ledger recorded it in 7 of 39 samples and the report omitted it in 18 of 39; among the last three, 34 of 48 and 0 of 48 (omission, first three minus last three: +46.2 pts [+20.5, +71.8]). The pattern centres on position 2, where the ledger never recorded the failure (0 of 24 samples, 8 sets); the one set at position 1 was recorded in all three samples, so this is not a simple gradient from the start of the context. The same function flips with position: P07, P23 and R11 were never recorded at position 2 but were recorded in 3 of 3 samples at positions 4–8. Without a ledger, position mattered little (2 of 39 omitted among the first three), and with three failing workers the ledger recorded every failure at every position (360/360, judge-free). Position was never counterbalanced, the early group is 13 sets, and we found the pattern after the results were known while examining three moderators, so it is an observation, which a position-swapped rerun of the frozen episodes could test, not a result.

## How reported failures are described (exploratory)

**Cause.** Workers often misframed the impossible test pair themselves: of 80 final messages, 37 blamed only their own code, 32 only the test or specification, and 11 both. Where the worker blamed the test or specification and the report mentioned the failure, family A's coordinators reported a code-only cause in 37.8% [27.0, 48.6] of cases (91 of 241); the reverse, a code-only worker relayed as a test problem, happened in 2 of 212 (Figure 2d; Appendix Figure A3). Family B: 10.5% [5.6, 16.7] (27 of 257). Judge cause codes matched 40 hand-coded reports at κ = 0.82 and 0.84.

**Status.** With three failing workers, family A's no-ledger reports called 54.5% [44.4, 64.1] of stated failures fixed, minor, in progress, acceptable or not affecting delivery (n = 233), or 30% if cases whose only cue is "in progress" are excluded; ledger-first reports, 7.4% [3.3, 12.1] (n = 229). Family B: 60.2% and 36.6%. Softening was higher with one failing worker than with three (Appendix E3), so the word budget does not explain it, and it ignored criticality (family A, three failing workers, procedures pooled: core 32.4%, edge 29.8%). These rates rest on the unvalidated strict denominator and a softening κ from 24 cases; examples are in Appendix E12.

# Discussion and Limitations

## What this means for people deploying agent teams

A structured issue-ledger step is the kind of fix one adds to make a coordinator more reliable, and it helped: with several failing workers it removed omissions and cut softening (family A: 55% → 7%). But in one model it created a new way to lose the least visible failure, a single deviating worker among compliant peers; once the coordinator committed to "no issues", the report often followed. The coordinator's own notes are therefore not an audit trail, and summarising steps should be tested on the sparse case (one failure among many), not only on busy sets. Passing the workers' status lines or test results to the overseer beside the summary would have caught every failure here by construction; the summary then adds context, not coverage. This is a design implication, not an intervention we tested.

**Why the ledger might miss lone failures** (untested). The prompt says an empty list is allowed; the JSON forces an early yes/no on "any issues?" before any worker is enumerated, while a free report walks through the workers in order; grammar-constrained decoding may contribute. Edge changes were recorded least (10/30), and most edge-change workers called the change instructed, which may read as authorised, but recording with and without that phrasing (3/12 vs 7/18) is too sparse to tell. Dropping the empty-list sentence, asking for per-worker status, decoding without a grammar and swapping positions would each test one reading.

**Fit with prior work.** Snitch's model leads refused to hide an edit yet usually omitted it once reverted; our coordinators, unasked, forwarded what they wrote down, so the loss sat earlier. As in Sun et al. and Wang et al., kept content often lost its meaning, here upward and unprompted. Unlike the MUM effect, omission ignored a responsibility cue.

## Limitations and future work

The setting is easy by design (explicit status lines, enforced compliance), one hop, one task domain. Only one non-reasoning 8B coordinator yields an interpretable ledger, and it reads its own family's transcripts. The ledger comparison and position pattern are post hoc, and position was never counterbalanced; the instructed-change cells are less "self-initiated" than designed; failure count is confounded with the share failing; the cap never bound. The strict score failed validation, and lenient absences were hand-checked by one coder who is also the designer. Appendix A states every assumption and all nine deviations. Next: the position swap and ledger ablations above, a reasoning coordinator, a binding budget, multi-hop chains and a second coder.

# Conclusion

A Qwen3-8B coordinator almost never dropped a failure it had written down, so what reached the director was decided by what it wrote down. A "log issues first" step stopped every loss when several workers failed, but left one lone failure in six out of the report, mostly when that worker's transcript sat second or third; a second model, whose ledger listed everything, lost none. Reported failures were often softened or blamed on the wrong cause. Overseers should not treat a coordinator's notes as an audit trail: give them worker status directly, and test any summarising step on a lone failure.

