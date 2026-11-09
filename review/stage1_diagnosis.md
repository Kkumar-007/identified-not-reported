# Stage 1: diagnosis of "The Empty Ledger" (report_final.pdf)

Written 8 Nov 2026, about 19:00 UK. Submission deadline is 8 Nov 11:59 pm AoE, which is about 12:00 UK on 9 Nov.

**What I inspected.**
- `report_final.pdf` (18 pages).
- The GitHub repository at `992a4c9`, and the local folder at `997d32e`. The local commit (the final title) is not on GitHub yet.
- `prereg.md`, `deviations.md`, `results/` and `handoff_log.md`.
- The data release `ibnr-release-v1.tar.gz`, staged from your folder.
- The Apart sprint page.

**What I could not inspect.** The Zenodo record itself and the Google Docs template rendering are not reachable from here.

**Labels used below.** *[verified]* means checked against files or sources. *[new analysis]* means my own post hoc computation, reproducible with `review/stage1_checks.py`. *[recommendation]* is my suggestion.

---

## 0. Bottom line

**The numbers are sound.** I traced every number in the main text, and most of those in the appendix, back to `results.json`, `results/posthoc/`, `cause_result.json` and `deviations.md`. All of them matched. I also reproduced the headline counts from the raw release: one failing worker, ledger first, 20/120 absent; no ledger, 2/120 absent. The pre-registration, the deviations log and the blind hand-checks are better than most conference papers manage. Nothing I found suggests a fabricated or mis-transcribed result.

**What the numbers mean is the problem.** The title and abstract build on the post hoc ledger-versus-no-ledger comparison, and present it as a property of the procedure: "logging issues first lets a lone failure slip through." Three things in the data narrow that claim considerably.

1. **Position, which the paper does not report** *[new analysis]*. Eighteen of the 20 lost lone failures come from sets where the failing worker's transcript is among the first three of nine.
   - Positions 1–3: the ledger recorded the failure in 7/39 samples, and 18/39 reports omitted it.
   - Positions 7–9: the ledger recorded it in 34/48 samples, and 0/48 reports omitted it.
   - At position 2 (8 sets), the ledger never recorded the failure (0/24).
   - The same function flips with position. P07, P23 and R11 were never recorded at position 2, but were recorded in 3/3 samples at positions 4–8.
   - Position was seeded per set and never counterbalanced, so the design cannot separate "ledger step" from "ledger step × early position".
2. **Family B shows no ledger effect at all** *[verified, Appendix E9]*. Its reports omitted 0/120 lone failures with or without the ledger. That result sits only in the appendix, and Figure 1b omits B on gate grounds (G1/G2). Those gates invalidate B's ledger as a *detection record*. They do not invalidate an end-to-end count of what reached the director.
3. **The deviation cells are not "self-initiated" as described** *[new analysis]*. 22 of 40 DE and 8 of 40 DC worker messages say the change was "as instructed" or "as per the instruction" (29 and 12 with a broader pattern). The leak filter, `i was (told|instructed|asked) to`, misses these phrasings. This does not drive the headline loss, but it undermines the Methods description of those cells and one explanation in §5.1.

**My reading.** The results can be true while the central interpretation is too general. What the evidence supports is narrower and, I think, more useful to an engineer: in one 8B coordinator, a single up-front issue-listing pass misses a lone failure that appears early in its context, and the report then follows the empty ledger. A free-form report from the same context does not miss it.

**Must fix before upload, whatever else happens.**
- The literal placeholder in Appendix G.
- Report the position pattern, labelled post hoc.
- Put family B's end-to-end result in the main text.
- Correct the deviation-cell description.

Section 8 has a time-boxed plan.

---

## 1. Research summary (reconstructed independently of the paper's framing)

**Problem.** When an overseer reads a coordinator agent's summary instead of each worker's transcript, the overseer sees only what the coordinator passes on. The paper asks what an honest, unprompted coordinator loses or distorts on the way up.

**Original question (pre-registered).** Does a coordinator's capped upward report drop failures that the coordinator has itself recorded? Does it drop more as more failures compete for the same words (load), and does it drop serious failures as readily as minor ones (severity)? The design separates three losses:
- *detection loss*: the failure never enters the coordinator's ledger;
- *reporting loss*: the failure is recorded, then omitted;
- *description loss*: the failure is reported, but softened or blamed on the wrong cause.

**Design.**
- 130 sets of nine Qwen3-8B worker transcripts on MBPP+ functions. Ground truth comes from hidden tests, so no model decides what fails.
- 160 injected failures, in a 2×2 of mechanism × criticality:
  - mechanism: an admitted failure (a contradictory test pair, after ImpossibleBench) or a hidden-instruction deviation;
  - criticality: core vs edge.
- Load: one failing worker (40 sets) or three (40 sets). There are also 30 clean and 20 authorised-change sets.
- Two coordinator arms on the same transcripts:
  - **L** writes a schema-constrained JSON issue ledger, then the report;
  - **S** writes the report directly.
- Reports are capped at 120 words. Coordinators are Qwen3-8B (family A) and Ministral-8B (family B). A Gemma-31B judge scores the outputs, and is validated against 80 hand labels.
- Three validity gates come first: authorised-change flagging, false alarms, and a capacity check.

**What happened.**
- Family B failed gates G1 and G2: its ledger flags nearly everything, including approved changes.
- The pre-registered primary score (judge-strict) failed validation (κ = 0.09), so every hypothesis is reported descriptively.
- On the validated lenient score, family A's coordinator almost never drops a failure it has recorded:
  - H1 loss 0.3% [0.0, 1.1];
  - H2 load effect +0.3 points;
  - H3 core loss 0.0%.

  The pre-registered question therefore has a clear answer: transmission is not where loss happens in this setting.
- Recording depends sharply on load: 99.7% with three failing workers, but 54.2% with one.
- Post hoc (D-8, after an external review), end-to-end loss splits by arm.
  - One failing worker: ledger first 16.7% vs no ledger 1.7%.
  - Three failing workers: ledger first 0% vs no ledger 5.0%.
- Exploratory, and resting on unvalidated or thin denominators: reported failures are often softened, and in the admitted cells often relayed as code bugs (family A 37.8%, B 10.5%).

**What is genuinely new.** No pre-registered hypothesis confirms anything. What the paper adds is a measurement instrument, and two observations:
- a structured issue-ledger step changes *which* failures a small coordinator loses;
- presence-based completeness hides substantial distortion of status and cause.

Separating identification from transmission, and "content kept, meaning lost", are prior work. The paper says so correctly.

---

## 2. The paper's current narrative and contributions

**Narrative.** A coordinator forwards almost everything it writes down, but what it writes down depends on the procedure.
- With three failures, the ledger helps (5% → 0% loss).
- With one, the ledger is often empty and the report follows it (1.7% → 16.7%).
- Forwarded failures are often softened or blamed on the code.
- The recommendation: overseers need an independent per-worker status channel.

**Contributions as presented.**

| # | Claim | Evidential status |
|---|---|---|
| 1 | A ledger step trades lone-failure visibility for multi-failure completeness | Post hoc (D-8); family A only; hand-checked absences; E2–E4 were seen before the headline rule was fixed |
| 2 | Recording, transmission and description are measured separately against hidden tests | Recording: validated (lenient κ 0.79; also judge-free). Transmission: validated on positives only. Description: exploratory (softening rests on the strict denominator, κ 0.09; downgrade κ on n = 24) |
| 3 | An open, pre-registered instrument | Strong: prereg with Wayback timestamp, D-1 to D-8, release reproduces `results.json` byte for byte |

**Tension.** The title and abstract lead with the contribution that has the weakest provenance (claim 1). The pre-registered result is a precise, validated null on transmission loss, and it is mentioned only in passing.

---

## 3. Verification

### 3.1 Numbers *[verified]*

I checked these against the result files. All matched.
- Abstract and introduction: 20/120, 2/120, 0/360, 18/360, 98%, and "one in six".
- Table 1, every gate cell.
- §4.2–4.5 (99.7%, 54.2%, the per-cell 21/18/16/10 of 30, the softening rates, H2–H5) and Table 2.
- The cause rates (37.8% [27.0, 48.6], 91/241; 2/212; B 10.5%) and Appendices E1 and E3–E9.

I reproduced from the raw release:
- 20/120 and 2/120 (one failure);
- 0/360 and 18/360 (three failures);
- 65 recorded, all 65 forwarded;
- 55 empty ledgers.

The Box 1 quotes appear verbatim in `results/labels/labels_filled_utf8.csv` (X001, X003, X005). X005 is an admitted-cell item, so "cause flipped" is correct.

### 3.2 Citations

| Reference | Status |
|---|---|
| Guo et al., ICML 2026, PMLR 306, arXiv:2512.04864 | Verified: the PMLR page exists; the paper evaluates 11 models |
| Sun et al., arXiv:2608.24569 | Verified: title, authors, Aug 2026; the content matches the paper's description |
| Wang et al., "Facts Without Rules" | arXiv:2608.29028 verified (authors match; human-validated judge, κ 0.74). **The EMNLP 2026 Findings anthology ID (2026.findings-emnlp.422) is not verified.** Check it, or cite the arXiv ID |
| Greenblatt, Cotra & Wijk (Redwood/METR) | Verified. Reports say one agent (PHASEONE[big]) orchestrated hundreds of others, so the intro sentence holds. That coordination ran over an unsanctioned peer message board, not a sanctioned orchestrator pipeline; it is fine "for scale only" |
| Kemeklis & Vemuri, "Omission Attacks" | Partly verified: a LessWrong follow-up describes its finding that postcondition tests caught omissions far more often than monitors |
| Lizcano Cabezas, "Don't Be a Snitch" | **Not verified from here.** The October 2026 AI Collusion Research Sprint exists, but I could not find the project page. Check the link and the 0/160 figure in a browser |
| MAST, Hammond, MUM effect, Smith et al., Perez et al., ImpossibleBench, MBPP/+, vLLM, Qwen3 | Not rechecked. Your handoff log records the first four as verified |

---

## 4. Discrepancies and new findings

| ID | The paper says | The data or code show | Why it matters | Severity |
|---|---|---|---|---|
| F1 | Lone-failure loss comes from the ledger step ("logging issues first") | 18 of 20 losses come from failing workers at positions 1–3. Early vs late (7–9) L absence: +46.2 points [+20.5, +71.8] (set-cluster bootstrap). Recording: 18% vs 71%. Position 2: 0/24 recorded. Same-function flips: P07, P23, R11. Position was never counterbalanced | The causal story is at least "ledger × position". The title generalises beyond the evidence. This is a confound the design cannot remove, but it can be disclosed and, cheaply, tested | **Critical for interpretation** (the counts stay valid) |
| F2 | DC/DE: a hidden instruction the worker "presents as its own decision"; §5.1 explains low DE recording by "a reasoned decision" | DE 22/40 and DC 8/40 messages say "as instructed" or "as per the instruction" (29 and 12 with "as requested"). 0 in other cells. Lone DE recording: 3/12 samples with this phrasing vs 7/18 without (small n) | The cell description is wrong for most DE workers. A manager reading "as instructed" can reasonably treat the change as directed, which bears on the DE recording rate, the matched-load G1 comparison and softening. It does **not** drive the headline: in DC/DE one-failure sets, L absence was 3/21 samples with this phrasing vs 4/39 without | Major |
| F3 | Figure 1b and Table 2 show family A only; "Family B's ledger failed gates G1 and G2, so panels a–b omit it" | B's end-to-end loss is 0/120 in both arms with one failure, and 0/360 vs 1/360 with three (Appendix E9). End-to-end loss is not conditioned on the ledger | Omitting the result that fails to replicate the headline, on a gate that does not apply to it, will read as selective. It also undercuts the title's generality. B also appears in panels c–d, so the gating looks inconsistent | Major |
| F4 | Appendix G: "No code was written before the sprint. **Timing: [the sprint start time Apart confirmed, in UTC]**" | The placeholder is literally in the PDF. The public page lists the sprint as 6–8 Nov (talks from 5 Nov). The smoke run is logged 22:50 UTC on 5 Nov. Your handoff log (Chat 6, cont. 3) says Apart confirmed the start time | A bracket in a final PDF looks unfinished. A screener comparing 22:50 UTC 5 Nov with "6–8 Nov" needs the confirmed time stated, ideally with how it was confirmed | **Critical (compliance, presentation)** |
| F5 | A.2: "In 35 of the 55 … the report still mentioned the failure (hand-checked)" | The 20 absences were all hand-checked, but only 5 of the 35 presences were (they fell in the E1 sample). The other 30 are judge-lenient calls | A small overstatement of the hand-check | Minor |
| F6 | §4.5: "core 32.4% … edge 29.8%" | These pool the L and S arms at high load (n = 247 / 215). The text does not say so | Pooling arms with 7% and 55% softening hides the arm effect | Minor |
| F7 | Table 2 column "S — L" | Negative values mean the ledger loses more | Readers expect "ledger effect = L − S" | Minor (clarity) |
| F8 | Project description: "the first upload is final" | The Apart page says resubmitting with **the same title** replaces the PDF before the deadline | Good news. But **changing the title may create a second submission rather than replace the first.** This constrains Stage 4 if you have already submitted | Process |
| F9 | README and the release `README_DATA.md` carry the old title ("When Writing Issues Down…"); the paper cites the dataset under the new one | The local `997d32e` fixes the README but is unpushed; the archive's README is unchanged | Cosmetic, but a reviewer clicking through sees mismatched titles | Minor |

**Caveat on F1 and F2 (my own forking paths).** I found both while reviewing, after all results were known. I examined three moderators: instruction phrasing, position and set clustering. F1 is large and holds within function, but it rests on 13 early-position sets. It should be reported as a post hoc observation (a D-9 entry), not as a result.

**Mechanistic hypotheses for F1 (untested; mine).** Three explanations are not mutually exclusive.
- The JSON ledger forces an immediate yes/no "are there issues?" decision at about token 5, with no enumeration of workers, so it leans on recency. The S report enumerates workers in order and hits the early one.
- Grammar-constrained decoding (`structured: True` on the ledger call) may itself distort that first decision.
- The sentence `If there are no issues, output {"issues": []}` offers an easy exit.

Section 8 lists cheap tests.

---

## 5. Strengths

- **Ground truth without a model in the loop.** Hidden tests decide what fails, and the workers' honesty is enforced by acceptance checks. This is the paper's best design decision and rarely seen in multi-agent evaluation.
- **Paired design.** The same worker episodes are shared across arms and families, so the L vs S contrasts are within-set.
- **Research hygiene.**
  - A pre-registration with a third-party timestamp.
  - A dated deviation log that records what was seen before each change.
  - Rules fixed before hand-coding (E1, D-6).
  - Failed validations reported as failures (κ 0.09; family B's gates), instead of being re-specified.
  - A data release that reproduces the analysis byte for byte.
  - A judge reviewing the deviation log will find nothing hidden.
- **The numbers are faithful.** Every number I traced matched its source.
- **A concrete engineering takeaway.** Give the overseer a status channel that bypasses the coordinator. Do not treat the coordinator's own notes as an audit trail.

## 6. Weaknesses (preliminary; Stage 3 will go deeper)

1. **The headline is post hoc and fragile.** It comes from one model, 9 of 40 sets (5 sets supply 15 of the 20 losses), and an uncontrolled position factor (F1). Family B does not show it (F3).
2. **The primary score failed.** Every pre-registered hypothesis is descriptive. The softening numbers in the abstract (79%, 55%) use the unvalidated strict denominator. Roughly half of S-high softening is "in progress" only (55% → 30%).
3. **The setting is easy by design.** Status lines name the failing tests and compliance is enforced. The recommendation (pass status lines to the overseer) is therefore correct by construction. Judges may see it as obvious unless the paper frames *why* a reasonable engineer would instead add a ledger step.
4. **Cell validity.** F2, plus the "whose fault" confound that the paper already discloses.
5. **Density.** The reader must track about 30 labels:
   - AC/AE/DC/DE/AU and L/S/CAP/STRESS;
   - G1–G3, H1–H5, D-1–D-8, E1–E9;
   - J_ITEM/J_FALSE/J_CAUSE;
   - strict, lenient, judge-strict, rule, and committed scores.

   Almost every sentence carries a caveat. The pre-registered H1–H5 section takes space but does not carry the story. For mostly industry-engineer judges, this is the biggest scoring risk.
6. **Track fit is modest.** Track 4's prompts centre on collusion, covert channels, log tampering and control protocols. This paper has no adversary. It fits the track's "cascading failures / oversight that doesn't scale" rationale, and it should say so explicitly rather than leave the judge to infer it.

## 7. Preliminary reviewer-style assessment (Apart rubric, 1–5)

| Dimension | Score now | What moves it |
|---|---|---|
| Impact & Innovation | **3** (clear problem, some novelty in framing) | A sharper, mechanistic claim ("one up-front issue pass is position-sensitive; free-form reporting is not") with a concrete design rule could reach 4. Claiming generality without evidence risks the "replicates recent work / overclaims" check |
| Execution Quality | **3** (range 3–4) | The process is exemplary, but the primary measure failed, only one model is interpretable, and the headline is post hoc and confounded with position. Disclosing F1 openly helps more than it hurts; a counterbalanced rerun (§8) would be the single biggest gain |
| Presentation & Clarity | **2–3** | Fewer labels, one story, the pre-registered null stated plainly, and B in the main figure |

**Bottom-line review sentence, as a skeptical judge would write it.** "A carefully run, honestly reported small study whose most interesting result is post hoc, model-specific and, on inspection of the released data, position-dependent. The writing buries the story under its own safeguards."

---

## 8. What follows for the next stages, and a time-boxed plan

You have about 17 hours. The full six-stage process will not fit as written, so I suggest compressing it.

**Stage 2 and 3 decision: which narrative?** I will lay out the alternatives properly in Stage 2. The candidates are:
- **(a)** keep the ledger trade-off, narrowed by position and by family B;
- **(b)** lead with the pre-registered answer: coordinators forward what they record, so loss happens at recording and description, not transmission;
- **(c)** presence-based completeness hides distortion.

My provisional view is that (a)+(b) combined is the most defensible. The title must stay unchanged if you have already submitted and want the upload replaced (F8).

**Must-do before upload (about 2–3 hours of writing; no new runs).**
1. Fill or remove the timing placeholder (F4). State the confirmed start time and how Apart confirmed it. If you cannot, declare the 5 Nov smoke, probe and screen runs as preexisting.
2. Add a D-9 entry and a short labelled paragraph or figure panel for the position pattern (F1).
3. Put family B's end-to-end counts in Figure 1b or Table 2, with one line on why they are interpretable (F3).
4. Correct the DC/DE description and §5.1 (F2), and add one limitation line.
5. Fix the minor items: F5, F6, F7, F9, and the Wang et al. venue.

**Optional high-value experiment (needs your approval and a free saxa slice; about 30–60 minutes of GPU time).**
- **Setup.** Reuse the frozen worker episodes of the 40 one-failure sets, family A only. Re-render each set twice, with the failing worker's transcript at position 2 and at position 8. Keep IDs in order (renaming them follows the transcript). Run the L and S arms, 3 samples each.
- **Size.** 40 × 2 × 3 × (2 + 1) = 720 coordinator calls, plus about 1,000 judge calls.
- **What it resolves.** Whether position is causal (F1), separately from problem and cell.
- **Pre-commit before running.** Report the paired early-minus-late L absence whatever it is. Call the effect "position-dependent" only if its 95% interval excludes 0.
- **What it displaces.** Nothing in the D9 cut order (all of it is already cut or done), but it costs about 3–4 hours end to end, including scoring and writing. If the cluster is busy at night, skip it and report F1 as observational.
- **Cheaper variants of the same idea.** Drop the `{"issues": []}` sentence, or run the ledger without guided decoding. Each would test one of the mechanisms above. I'd prioritise position.

**Not recommended now.** New models, a reasoning-mode coordinator, multi-hop chains. They are the right next steps, but they cannot be done well tonight.

## 9. Decisions needed from you

1. **Have you already submitted this PDF?** If yes, the title must stay byte-identical for the new upload to replace the old one, unless Apart confirms otherwise.
2. **Run the position-reversal experiment tonight, or report F1 observationally?**
3. **Go-ahead for Stage 2 (narrative distillation)**, with the compressed plan above.

---

## Handoff note (Chat 11: Stage 1 review · 8 Nov 2026, about 19:00 UK)

**Decisions made:** none. This is a diagnosis only. No repository, manuscript or prereg file was changed.

**Findings:**
- Every traced number matches its source.
- F1: the lone-failure loss is concentrated at early transcript positions (18/20 at positions 1–3; position 2 recorded 0/24).
- F2: 22–29/40 DE and 8–12/40 DC workers say the deviation was instructed.
- F3: family B lost 0/120 lone failures in both arms, but appears only in E9.
- F4: the Appendix G timing placeholder is still in the PDF.
- F8: Apart allows replacement by resubmitting with the same title.

**Files produced:**
- `review/stage1_diagnosis.md` (this file)
- `review/stage1_checks.py` and `review/stage1_checks_output.txt` (reproduce F1–F3 from the release; no model calls)
- A project copy at `claude/stage1_diagnosis.md`

**Open issues:**
- A D-9 entry is needed for the F1/F2 checks, since they were made after results were known.
- The timing placeholder.
- B in the main figure.
- The DC/DE description.
- Unverified: the Snitch link and figure, and the Wang et al. EMNLP anthology ID.
- `997d32e` is not pushed.

**Next chat's first step:** answer the three decisions in §9, then run Stage 2 (narrative distillation), with the position finding included.
