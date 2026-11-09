# Abstract {.unnumbered}

Overseers of agent teams often read a coordinator’s summary instead of every worker’s transcript. We ask where honestly reported failures are lost on the way up when no agent is asked to hide anything. Nine Qwen3-8B workers each implement a Python function and end with a test-status line; hidden tests fix which fail. A coordinator reports to a director in at most 120 words, either directly or after first logging issues in a structured ledger (130 pre-registered transcript sets, 160 injected failures). Failures were lost when they were written down, not when they were passed on: a Qwen3-8B coordinator forwarded all but one of the 424 failures it logged (reported descriptively, because the pre-registered primary score failed validation). What it logged depended on the procedure. Post hoc, logging first removed every loss when three of nine workers failed (5.0% without a ledger), but with one failing worker the ledger was often empty, and the report omitted 16.7% of lone failures against 1.7% without a ledger. A Ministral-3-8B coordinator, whose ledger logged nearly everything, lost none. In exploratory analyses, reports that named a failure often called it fixed, minor or in progress. Reporting procedures should be tested on lone failures, not only where failures are plentiful.

# Introduction

Agent systems increasingly use an orchestrator–worker pattern: a coordinator assigns subtasks, reads the workers' outputs and reports upward, and the human or monitor above it reads that report rather than every transcript. At scale, one agent can coordinate hundreds of others, as one did in the 2026 OpenAI / Hugging Face incident (Greenblatt, Cotra and Wijk, 2026). Whatever the coordinator leaves out or softens is invisible to the overseer. The hardest case is one worker that deviates while its peers comply: that is the shape a lone misaligned agent's deviation would take, and whether it is seen may depend on what the other workers did, which no single-agent evaluation measures.

We ask: **when workers have honestly reported unresolved failures, which failures does a coordinating LLM write down, which reach its supervisor, and how are they described?** Nine workers who never see each other each implement a Python function and end with a status line; hidden tests decide which fail; a coordinator reports to a director in at most 120 words (Figure 1). Nobody is asked to conceal anything. We vary the number of failing workers (one or three of nine), whether a core or an edge requirement fails, and the reporting procedure: report directly, or first list issues in a structured ledger, a common way to make a coordinator more systematic.

We pre-registered one question: does a coordinator drop failures it has itself recorded? For Qwen3-8B it almost never did, so the losses happened before that step, in what got written down, and after it, in how failures were described. Post hoc, the ledger step turned out to decide what got written down. Our contributions:

1. **An open, pre-registered instrument** that measures what a coordinator writes down, what reaches its supervisor and how it is described, against hidden-test ground truth, with all prompts, logs and hand labels.
2. **The pre-registered answer:** a recorded failure almost always reached the director (1 of 359 dropped with three failing workers, 0 of 65 with one; §4.2).
3. **A post hoc trade-off and its scope:** for Qwen3-8B, a ledger-first step removed losses with three failing workers (5.0% → 0%) and introduced them with one (1.7% → 16.7%), concentrated at transcript positions 2–3; Ministral-3-8B, whose ledger listed nearly everything, lost no lone failure (§4.2–4.3).

# Related Work

**Misreporting one's own work.** Guo et al. (2026) find that all eleven models tested report more success on impossible or partly possible tasks than their trajectories support; there the failure is the agent's own, here a different agent reports it. Our test-conflict failures borrow ImpossibleBench's construction (Zhong et al., 2025).

**Withholding a teammate's failure.** In "Don't Be a Snitch" (Lizcano Cabezas, 2026), workers hide a teammate's rule violation when their lead asks. Model leads asked to hide an edit always refused (0 of 160), yet once the edit had been reverted their final report rarely mentioned it (8 of 142). That setting has one deliberate violation and, mostly, an explicit request; ours has no request and up to three failures per report.

**Content kept, meaning lost.** Sun et al. (2026) show handoff compression turning an identified safety blocker into language that informs without binding; Wang et al. (2026) show handoff summaries keeping facts while dropping the metadata that governs their use; iterated LLM transmission drifts toward attractors (Perez et al., 2025). We find the same pattern in upward, unprompted reports of failures (§4.5).

**Multi-agent failure and oversight.** A coordinator that does not act on a worker's report fits MAST failure modes (Cemri et al., 2025) and the information-asymmetry risk in Hammond et al. (2025); Kemeklis and Vemuri (2026) find an end-state monitor caught omissions that transcript review partly missed. In human organisations bad news is softened on the way up (the MUM effect; Rosen and Tesser, 1970; Smith, Keil and Depledge, 2001).

**Not claimed as new:** separating identification from transmission (Lizcano Cabezas; Sun et al.), handoffs that keep content but lose meaning (Sun et al.; Wang et al.), or end-state verification (Kemeklis and Vemuri). We add a controlled, pre-registered measurement of unprompted, multi-worker upward reporting against hidden-test ground truth, and the observation that a ledger step changes which failures a coordinator loses.

# Methods

The design was pre-registered before any coordinator saw a set containing a failure (commit `dff73e2`, Wayback snapshot 6 Nov 2026 18:54 UTC). Later changes are deviations D-1 to D-9 (Appendix A.2, F); all prompts are in Appendix C.

![**Figure 1. Study design.** Nine workers each implement one function and end with a status line; hidden tests decide which fail (one or three per set). The same nine transcripts go to a coordinator that either writes an issue ledger and then its report (*ledger first*) or writes the report directly (*no ledger*). Each injected failure is scored at three checkpoints.](fig1_design_v4.png){width=82%}

## Tasks, workers and failures

We took 60 MBPP+ v0.2.0 problems (Austin et al., 2021; Liu et al., 2023), 45 primaries and 15 reserves, and gave each an explicit edge requirement with two edge tests. **Ground truth is a hidden suite** (the visible MBPP asserts and edge test, a second edge test, and the MBPP+ inputs against canonical outputs), so no model decides what fails. Workers are Qwen3-8B (Yang et al., 2025; thinking off, temperature 0.7); each runs its tests once and ends with `Final status: passing p/n; failing: …; deviations: …`.

Failures follow a 2×2 design. In a **test conflict**, a contradictory test pair makes passing impossible and the worker reports the failing test. In a **hidden-instruction** failure, a hidden instruction makes the worker change the main behaviour or skip the edge requirement "to save time", and asks it to present this as its own decision; many did not keep up that framing (22 of 40 edge and 8 of 40 core workers wrote that they acted "as instructed"; post hoc, D-9). Each type fails a **core** or an **edge** requirement; only core vs edge within a type is a clean contrast of criticality. Acceptance checks regenerate non-compliant workers (Appendix C), so coordinators receive honest, explicit reports by construction; no set was excluded.

The 130 sets are 30 clean, 40 with one failing worker (10 per cell), 40 with three, and 20 in which a director-approved amendment withdraws one worker's edge requirement (approved-change controls): 160 injected failures. The failing worker's position among the nine transcripts was seeded per set, not counterbalanced. Worker episodes are generated once and shared by every procedure, sample and coordinator.

## Coordinators

The coordinator's system prompt gives a neutral role ("You lead a team of nine workers, worker_1 to worker_9, and you report to a director"), the nine specifications and any amendment; the user message holds the nine transcripts in worker order. Every procedure ends with *"Write your report to your director, in plain text, at most 120 words."* **Ledger first:** turn 1 asks the coordinator to "Record any issues…" as schema-constrained JSON (worker, function, requirement, evidence quote, severity), noting that `{"issues": []}` is allowed; turn 2 asks for the report. **No ledger:** the report directly. Controls add an include-every-issue instruction to turn 2, or a responsibility or placebo sentence to a direct report. Three samples per procedure per set, temperature 0.7. Coordinators are family A (`Qwen/Qwen3-8B` @ `b968826d`, thinking off) and family B (`mistralai/Ministral-3-8B-Instruct-2512-BF16` @ `f6fae979`; Mistral AI, 2025), served with vLLM 0.33.0 (Kwon et al., 2023).

## Scoring and analysis

A judge, `google/gemma-4-31B-it-qat-w4a16-ct` @ `52f3f65b` (Google, 2026; temperature 0), sees one failure description and one ledger or report, never the procedure, family, load or cell. For each injected failure it marks whether the text **mentions** a problem with that worker or function (lenient score), **states** this failure's problem (strict), and, if stated, whether it is **softened**: called fixed, minor, in progress, acceptable or not affecting delivery while still failing. *Recorded* means the ledger has an entry for the failing worker; *transmission loss* is P(absent from the report | recorded); *end-to-end loss* is P(absent from the report). The author hand-labelled 80 pairs before seeing any result; each field needed Cohen's κ ≥ 0.7 (Cohen, 1960). Intervals are 95% cluster-bootstrap intervals over sets (2,000 resamples) unless stated. The pre-registered hypotheses concern transmission loss (§4.4); the ledger-vs-no-ledger (D-8), cause (D-6) and position (D-9) analyses are post hoc.

# Results

Figure 2 follows a failure through the funnel; panels a–b are validated, c–d exploratory.

## Measurement validity

The judge's strict field agreed with the hand labels at κ = 0.09 (a fallback rule at 0.13), so **the pre-registered hypotheses are reported descriptively**. All 26 strict disagreements were test-conflict reports calling the impossible test pair a coding error, which the labeller counted as stating the failure and the judge did not. The lenient field passed (κ = 0.79) but was validated almost only on positives, so every judge "absent" call in Table 1 (family A) was hand-checked blind to procedure: 40 of 42 confirmed, 2 unsure; 30 of 30 "present" controls confirmed. Recording needs no judge.

Two pre-registered gates test the ledger itself (Appendix Table E0). Family A passed both: it flagged approved changes (35.0%) at under half the rate it recorded edge deviations (83.3%), with no false alarms on clean sets. Family B failed both, flagging 75.0% of approved changes and claiming a failure in 25.6% of clean-set ledgers, so its ledger-conditioned numbers are not interpreted; its end-to-end losses do not depend on the ledger. Family A's pass holds only with failure counts pooled (Appendix A.2).

## What is written down, and what reaches the director

Family A's ledger recorded 99.7% [99.2, 100.0] of failures when three workers failed (n = 360) but 54.2% [39.2, 68.3] when one did (n = 120; Figure 2a); the 55 misses are clean `{"issues": []}` ledgers, clustered by set. Once recorded, a failure was almost always forwarded: 1 of 359 was dropped with three failing workers (hand-coded as unsure) and 0 of 65 with one. Asking to "include every issue" lost 0.6%, and reports used about half the word cap (median 59 words), so the cap forced none of this.

End-to-end loss therefore follows recording (Table 1, Figure 2b). With three failing workers, the ledger step removed the 5.0% loss. With one, every lost failure had an empty ledger. An empty ledger did not guarantee omission (35 of the 55 empty-ledger reports still mentioned the failure), but it made omission common: 20 of 55, against 2 of 120 without a ledger. Family B's ledger listed every injected failure, and its ledger-first reports lost none.

**Table 1. Failures absent from the report** (lenient score; post hoc, D-8, D-9). Family A: every absence hand-checked; family B: judge only. Ledger effect: paired difference, ledger first minus no ledger, with 95% interval; per-arm intervals are in Figure 2b.

|                              | Ledger first         | No ledger            | Ledger effect (pts)        |
|------------------------------|----------------------|----------------------|----------------------------|
| A, one failing worker | 20/120 (16.7%) | 2/120 (1.7%) | +15.0 [+5.8, +25.8] |
| A, three failing workers | 0/360 | 18/360 (5.0%) | −5.0 [−8.1, −2.2] |
| B, one failing worker | 0/120 | 0/120 | 0 |
| B, three failing workers | 0/360 | 1/360 (0.3%) | −0.3 [−0.8, +0.0] |

![**Figure 2. What the coordinator writes down, what reaches the director, and how it is described.** (a) Failures with a ledger entry for the failing worker, family A. (b) Failures absent from the report; family A hand-checked, family B judge only (post hoc, D-8, D-9). (c) Stated failures called fixed, minor, in progress or acceptable; hollow: excluding "in progress"-only cases. (d) Test conflicts the worker blamed on the test, relayed as a code bug. Panels c–d are exploratory.](fig2_funnel_v4.png){width=92%}

## Where the lone failures were lost (post hoc)

The missed lone failures were not spread evenly (Figure 3). Eighteen of the 20 losses came from workers whose transcript was second or third of nine. At positions 1–3 the ledger recorded the failure in 7 of 39 samples (0 of 24 at position 2); at positions 7–9, in 34 of 48, and no report omitted it. The same function flipped with position: P07, P23 and R11 were never recorded at position 2 but always at positions 4–8. Without a ledger, position barely mattered (2 of 39 absent at positions 1–3).

This pattern was found after the results and is observational: position was seeded per set, the early band rests on 13 sets (one at position 1, recorded 3 of 3), and we ran no position-swap experiment. Untested explanations: the JSON ledger forces an early yes-or-no on "any issues?" without stepping through the workers, the empty-list sentence offers an easy exit, and constrained decoding may tilt that decision. Reordering transcripts or dropping the empty-list sentence would test these.

![**Figure 3. Lone failures by the failing worker's transcript position, family A** (post hoc, D-9; position was not counterbalanced). (a) Samples whose ledger has an entry for the failing worker. (b) Failures absent from the report by position band; whiskers are 95% cluster-bootstrap intervals over the band's sets.](fig3_position_v4.png){width=86%}

## Pre-registered contrasts (descriptive)

On the lenient score, transmission loss with three failing workers (H1) was 0.3% (97.5% upper bound 1.1%), inside the pre-registered "faithful" band (below 5%), but lenient was not the primary score, so no decision follows. Descriptively, the number of failing workers did not change transmission loss (H2, +0.3 pts), core and edge failures were dropped at the same near-zero rate (H3), reports without a ledger omitted 4.7 points more recoverable failures with three failing workers (H4), and a responsibility cue changed nothing against a placebo (H5). Intervals and strict-score versions are in Appendix E5 and E7.

## How reported failures are described (exploratory)

**Cause.** In test-conflict cells the true cause is the test pair, and the workers themselves often misframed it: 37 of 80 blamed only their own code, 32 only the test or specification, 11 both. Where the worker blamed the test or specification and the report mentioned the failure, family A's reports gave a code-only cause in 37.8% [27.0, 48.6] of cases (91 of 241); the reverse happened in 2 of 212 (Figure 2d). Family B: 10.5% [5.6, 16.7]. Judge cause codes matched 40 hand-coded reports at κ = 0.82 and 0.84.

**Status.** Reports often presented a stated failure as handled (Figure 2c). Without a ledger, family A softened 79% of stated lone failures and 55% with three failing workers; with the ledger first, 58% and 7%. "In progress" alone accounts for much of this (excluding those cases: 73% and 30% without a ledger), and the denominator rests on the unvalidated strict score (the softening field's κ of 0.83 rests on 24 cases). Softening did not track criticality (family A, three failing workers, both procedures pooled: core 32.4%, edge 29.8%), suggesting distortion rather than triage. Appendix E12 shows examples.

# Discussion and Limitations

**For people deploying agent teams.** A ledger step is a natural way to make a coordinator more systematic, and it helped where failures were plentiful: no loss with three failing workers, and far less softening (55% → 7%). It failed on the least visible case, one deviant among compliant peers early in the context: once the coordinator committed to "no issues", its report often followed. Test such steps on single failures and in several transcript orders, and do not treat a coordinator's notes as an audit trail: passing the workers' status lines to the overseer beside the summary would have caught every failure here by construction (a design implication we did not test).

**Two models, two ledgers.** Family A's ledger raised no false alarms but missed lone failures, and its reports often missed them too; family B's missed nothing, and neither did its reports, but it flagged most approved changes and a quarter of clean sets (Appendix Figure E10). The trade-off may reflect a model's threshold for "an issue" rather than ledgers as such; two models cannot settle this.

**Limitations.** The setting is easy by design (explicit status lines, enforced worker compliance, one hop, one task domain). Only one non-reasoning 8B coordinator yields interpretable ledgers, reading its own family's transcripts. Failure count is confounded with the share failing, and the word cap never bound. The strict score failed validation; one coder, also the designer, hand-checked the absences. The ledger and position comparisons are post hoc, position was not counterbalanced, and hidden-instruction workers often said they acted as instructed. Status and cause are exploratory. Appendix A states each assumption and all nine deviations. Next: a counterbalanced position test, other coordinators and a second coder.

# Conclusion

A Qwen3-8B coordinator almost never dropped a failure it had written down; what its director saw depended on what it wrote down and how. An issue-ledger step closed every gap when several workers failed, but with one failing worker it often logged no issues and left one lone failure in six out of the report, mostly when that worker's transcript came early. Overseers should receive the workers' own status lines beside the summary.

# Code and Data {.unnumbered}

Code and hand labels: <https://github.com/Kkumar-007/identified-not-reported> (the README declares preexisting material). Data (Kumar, 2026): <https://doi.org/10.5281/zenodo.24047673>. No info hazards beyond Appendix A.3.

# Author Contributions {.unnumbered}

K.K. designed and ran the study, labelled and hand-checked the validation items and wrote the report.
