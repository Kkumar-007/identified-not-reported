# Stage 4 plan: report v4 ("The Empty Ledger")

8 Nov 2026, about 19:05 UK. The narrative was approved (Stage 2+3, `review/stage23_narrative.md`): (b) is the frame and (a) the headline. The title is unchanged.
New numbers come from `review/stage4_numbers.py` and its output, and from `review/stage1_checks_output.txt`.

## Abstract outline (≤ 250 words, 7 moves)
1. **Problem.** Overseers read a coordinator's summary, not every worker's transcript.
2. **Setup.**
   - Nine Qwen3-8B workers, with ground truth from hidden tests.
   - 130 pre-registered sets and 160 injected failures.
   - The coordinator writes a report of at most 120 words, either directly or after first writing an issue ledger.
3. **Pre-registered answer.** Failures written in the ledger were almost always forwarded, so transmission was not the bottleneck.
4. **Headline (post hoc), with its scope.**
   - Three failing workers: ledger first 0/360 missing, against 5.0% with no ledger.
   - One failing worker: the ledger was often empty, and 20/120 lone failures were missing (16.7%), against 2/120 (1.7%).
   - 18 of the 20 losses came from workers whose transcript was second or third of nine.
   - Family B's ledger listed nearly everything, including approved changes. It lost none.
5. **Exploratory.**
   - 38% of correctly diagnosed test conflicts were relayed as code bugs.
   - Named failures were often called fixed, minor or in progress (a range, with its caveat).
6. **Caveats.** The strict score failed validation, so everything is descriptive. The headline is post hoc and holds for one model.
7. **Takeaway.** Give the overseer the workers' own status lines beside the summary. Treat the coordinator's notes as a lossy filter, not an audit trail.

## Introduction outline (about 0.6 page)
1. **Problem.**
   - The orchestrator–worker pattern, with the overseer reading the summary.
   - Scale (the Hugging Face incident).
   - One framing sentence: a single deviating worker among compliant peers has the shape a lone misaligned agent's deviation would take. No adversary is claimed.
2. **Question and design** in plain words: honest workers, hidden tests, and two reporting procedures.
3. **Findings, in funnel order.**
   - Forwarding is near-lossless (pre-registered).
   - What gets written down depends on the procedure: the empty ledger, the position, family B (post hoc).
   - Description distorts (exploratory).
4. **Contributions, three short items.**
   - An open, pre-registered instrument.
   - The pre-registered answer: loss happens at recording and description, not transmission.
   - The ledger-first trade-off and its scope (post hoc).

## Figures
- **Fig 1 (new, design).** Nine workers, each running hidden tests and ending with a status line, with the failing workers marked. They feed one coordinator, which follows one of two procedures:
  - (ledger first) an issue ledger, then the report;
  - (no ledger) the report directly.

  The report goes to the director. Three numbered checkpoints: ① written in the ledger? ② reaches the director? ③ described as unresolved, with the right cause? This replaces about a third of the Methods prose.
- **Fig 2 (revised Figure 1, the funnel).**
  - (a) Written in the ledger, family A.
  - (b) Absent from the report. Family A is hand-checked. **Family B is added** (judge lenient, not hand-checked; not conditioned on the ledger, so gates G1/G2 do not apply).
  - (c) Softened; (d) cause flipped. Both exploratory.
- **Fig 3 (new, post hoc).** Family A, one failing worker.
  - Left: share written in the ledger, by the failing worker's position (1–9), with the set count under each position.
  - Right: absent from the report by position band, ledger first vs no ledger.
- **Appendix Fig E1 (new).** Each family's ledger as a detector: recall with one and with three failing workers, approved changes flagged, and clean-set false alarms. This backs the one descriptive sentence on family B.

## Main text vs appendix (target ≤ 8.0 pages; v3 ends on p. 8 after Author Contributions, so there is no slack)

| Section | v4 plan | Page change (approx.) |
|---|---|---|
| Abstract | Rewritten to the outline | 0 |
| 1 Introduction | Shorter contributions, plus the framing sentence | −0.1 |
| 2 Related work | Each paragraph tightened; positioning kept | −0.15 |
| 3 Methods | Fig 1 added; prose cut; plain names; F2 correction | +0.25 figure, −0.3 prose |
| 4.1 Measurement validity | Table 1 without the κ row (κ moved to text); shorter paragraph | −0.1 |
| 4.2 Written down and reaching the director | Fig 2; Table 2 gains family B rows and a ledger-effect column (L − S) | +0.1 |
| 4.3 Where the lone failures were lost (post hoc) | **New**: position paragraph and Fig 3; the untested mechanisms move here | +0.45 |
| 4.4 Pre-registered contrasts | Three sentences | −0.1 |
| 4.5 Description (exploratory) | Cause first, softening as a range, pooled arms labelled (F6); **Box 1 moves to Appendix E** | −0.15 |
| 5 Discussion and limitations | Mechanism paragraph merged into 4.3; one F2 line | −0.1 |
| 6 Conclusion | Rewritten to the thesis | 0 |

**Notation cuts in the main text:**
- Arms are "ledger first" and "no ledger" (no L/S/CAP/STRESS in prose).
- Cells are "test-conflict" and "hidden-instruction" failures, core or edge (codes only in Table 1 and the appendix).
- Gates are named by what they test.
- H1–H5 appear only in §4.4.
- D-n numbers appear only as pointers to the appendix.
- Scores are called "mentioned" (lenient), "stated" (strict) and "softened" (downgrade).
