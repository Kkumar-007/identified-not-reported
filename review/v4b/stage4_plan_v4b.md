# Stage 4: structure plan for report_v4 (approved narrative: (b) frame + (a) headline)

Written 8 Nov 2026, about 22:00 UK. The narrative is in `review/stage23_narrative.md`, approved 21:48 UK. The title is unchanged.

## Abstract outline (≤ 250 words, six moves)
1. **Problem** (1 sentence). Overseers read a coordinator's summary, not every worker's transcript.
2. **Setup** (2 sentences).
   - Nine Qwen3-8B workers each end with a test-status line, and hidden tests decide what fails.
   - A coordinator reports in ≤ 120 words, either directly or after first logging issues in a ledger.
   - 130 pre-registered transcript sets, 160 injected failures, two 8B coordinator models.
3. **Pre-registered answer** (1 sentence). A failure written in the ledger almost always reached the director (1 of 359 dropped; 0 of 65).
4. **Headline, post hoc** (2–3 sentences).
   - With three failing workers, logging first removed the 5% loss.
   - With one, the ledger was often empty, and 20/120 lone failures went missing, against 2/120 without a ledger.
   - 18 of the 20 losses came from the first three transcripts; position was not controlled.
   - Ministral-8B, whose ledger listed every failure but also flagged approved changes, lost none.
5. **Exploratory** (1 sentence). Reported failures were often called fixed, minor or in progress, and 38% of correctly diagnosed test conflicts were relayed as code bugs.
6. **Scope and takeaway** (2 sentences).
   - The strict score failed validation, so everything is descriptive; one small model; easy tasks.
   - Give overseers worker status directly, and test any summarising step on a lone failure.

**Out of the abstract:** 79%/55% softening, "98%", H-labels, and gate names.

## Introduction outline (about 0.8 page plus Figure 1)
- ¶1 **The problem.** The orchestrator–worker pattern; the overseer sees the summary; scale (Greenblatt et al.).
  - One framing sentence: a lone deviating worker among compliant peers has the shape a single misaligned agent's deviation would take. This study has no adversary.
- ¶2 **Design in plain words**, pointing to Figure 1. Three questions, matching the three measurement points:
  1. written down?
  2. reaches the director?
  3. described faithfully?
- ¶3 **Findings in funnel order.**
  - Forwarding is near-lossless (the pre-registered result).
  - What gets written down depends on the procedure: the trade-off, scoped to family A, lone failures and early position.
  - Family B lost nothing, but its ledger cannot tell approved changes from failures.
  - Description is distorted (exploratory).
- ¶4 **Three contributions.**
  1. A pre-registered, hidden-test measurement of recording, transmission and description.
  2. Post hoc: an issue-first step is a trade-off with an identifiable failure mode.
  3. An open instrument and data release.

## Figures
- **Figure 1 (new, main, about 0.3 page): the pipeline.**
  - Nine workers (one failing), each sending a transcript with a status line.
  - The coordinator, with two paths: ledger first (JSON ledger → report) or no ledger (report directly).
  - The director, receiving a report of ≤ 120 words.
  - Hidden tests give the ground truth on the side; a blind judge plus hand-checks do the scoring.
  - Three numbered measurement points ①②③.
- **Figure 2 (revised results, 2×2, about 0.55 page).**
  - (a) Written down: family A, one vs three failing; family B noted as 100% but failing gates G1/G2.
  - (b) Absent from the report: **families A and B**, ledger first vs none, one vs three failing. A's absences are hand-checked; B's are judge only.
  - (c) **Position (post hoc, D-9):** family A, one failing worker, transcript position early/mid/late. Shows recorded in the ledger, absent with the ledger, and absent without it.
  - (d) Described (exploratory): softened (no ledger, three failing; with the "in progress" exclusion as a hollow marker) and cause flipped, A vs B.
  - Labels on the panels say which are validated, post hoc or exploratory.
- **Appendix figures** (for readability; they use no main-text space):
  - A1: positions 1–9 in detail.
  - A2: recording by failure type with one failing worker, plus approved changes.
  - A3: cause flow from worker framing to report framing (E4 counts).

## Main text vs appendix (8 pages)
| Section | Pages | Change |
|---|---|---|
| Abstract | 0.4 | Rewritten to the outline |
| Introduction + Fig 1 | 1.1 | Rewritten; contributions reordered |
| Related work | 0.45 | Trimmed by about 20%; the "not claimed as new" line kept |
| Methods | 1.2 | Plain names for cells and arms; codes defined once; F2 fix |
| Results + Fig 2, Tables 1–2 | 2.9 | Funnel order: validity → written down → forwarded → trade-off (A and B) → position → description; H1–H5 in three sentences |
| Discussion + Limitations | 0.9 | Takeaway first; mechanisms in one paragraph; F2 limitation |
| Conclusion, Code and Data, Author | 0.3 | |

**Moved to the appendix:**
- Box 1 → Appendix E.
- The G1 matched-load detail → one sentence in the main text, with detail in the appendix.
- The "why the ledger might lose" paragraph → compressed.

**Label policy in the main text:**
- "ledger first" and "no ledger" in prose; L/S only in tables.
- Gates named in Table 1 only.
- H1–H5 named only in the pre-registered-contrasts paragraph.
- Cells in plain words: core/edge test conflict, core/edge change. Codes appear in parentheses once.
- No J_* prompt names.
