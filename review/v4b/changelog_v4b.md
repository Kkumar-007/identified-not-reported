# Change log: report v3 → v4b (`report/v4b/report_v4b.{md,docx,pdf}`)

Written 8 Nov 2026, about 22:35 UK, in a separate chat from the one that wrote `report/report_v4.*` and `review/change_log_v4.md` (logged as Chat 12, built 18:40–19:11 UK). Both versions follow the narrative approved in `review/stage23_narrative.md`. They rest on the same numbers: every count and interval in v4b also appears in `review/stage4_numbers_output.txt`, `review/stage1_checks_output.txt` or `deviations.md`, except the three-failure recording by position band (105/105, 132/132, 123/123), which is only in `review/v4b/stage4_numbers_v4b_output.txt`.

v3 (`report/report.md`, `report.pdf`) and v4 (`report/report_v4.*`) are untouched.

**Build.** From the repo root:
1. `python -I review/v4b/assemble_v4b.py`
2. `cd report/v4b && python build_v4b.py` (needs the Old Standard TT font installed)
3. Figures: `python -I report/v4b/figures_v4b.py --repo . --out report/v4b/figures`
4. Numbers: `python -I review/v4b/stage4_numbers_v4b.py --logs <release>/logs --repo . --json review/v4b/stage4_numbers_v4b.json`

**Render.** Old Standard TT (the template font), 20 pages. The main text ends on p. 8 with Author Contributions, and the references start on p. 9. The abstract has 249 words.

## Scientific changes (the same set as v4; see `review/change_log_v4.md` S1–S15 for the shared items)

| ID | Change | v4b location |
|---|---|---|
| Narrative | The pre-registered answer leads. The empty ledger follows as the post hoc headline, scoped to family A and positions 2–3; family B lost no lone failure | Abstract, §1, §6 |
| F1 | Position goes in **§4.4**, as panel **c of Figure 2**, not a separate figure. Positions 1–9 go in Appendix E10 and Figure A1. A limitation bullet is added in A.2. | §4.4, Fig 2c, E10, A1, A.2 |
| F1 (sharpened) | The text says the losses centre on positions 2–3 (12 + 6 of 20), and that the single position-1 set was recorded 3/3, so this is not a simple start-of-context gradient. With three failing workers, recording is 360/360 in every band. | §4.4, E10 |
| F2 | Cells renamed "test conflict" and "instructed change". The 22/40 DE and 8/40 DC "as instructed" phrasing is stated in Methods. The §5.1 mechanism paragraph is rewritten, and the phrasing split (3/12 vs 7/18) is shown as too sparse to explain the result. Appendix C notes what the leak filter misses. A limitation bullet gives 29/12 and 3/21 vs 4/39. | §3.1, §5.1, A.2, C |
| F3 | Family B's end-to-end counts are in **Table 2** and **Figure 2b**. The A.2 bullet and E9 are updated. | Table 2, Fig 2b |
| F5 | "(hand-checked)" is corrected: 5 of the 35 were hand-checked, and all 20 absences were. | A.2 |
| F6 | The core/edge softening numbers are labelled as pooled over both procedures. | §4.5 |
| F7 | Table 2 reports **ledger − no ledger**: +15.0 [+5.8, +25.8] and −5.0 [−8.1, −2.2]. This is the exact negation of D-8's S − L. | Table 2 |
| Empty ledger | "The report followed the ledger" becomes: an empty ledger raised omission from 0/65 to 20/55, and 35 of 55 empty-ledger reports still named the failure. | §4.3 |
| Detector reading | One sentence in the main text says it is descriptive only. There is no separate figure. | §4.3 |
| H1–H5 | Summarised in one sentence. The H2 "selected populations" caveat is kept in the main text, as `deviations.md` (7 Nov record) requires. | §4.2 |
| Snitch | Related Work: "a model lead never agreed to hide an edit (0/160), yet once the edit was reverted it usually left it out of its final report". No count is given for the second clause. The v3 Discussion line "Like Snitch's model lead…" is replaced. | §2, §5.1 |

## Compliance and references

- **F4.** Appendix G declares, conservatively, the following preexisting, with UTC times from the run logs:
  - the smoke run, 22:50 UTC on 5 Nov;
  - the three probes, 23:13 UTC on 5 Nov to 00:02 UTC on 6 Nov;
  - the stage-A screen, 01:16–01:33 UTC on 6 Nov;
  - the harness code as it stood for those runs.

  Unlike v4, v4b does not claim that Apart confirmed a start time. The README timing edits are v4's (Chat 12); v4b does not change any README.
- **Wang et al.** The anthology ID `2026.findings-emnlp.422` was verified in the browser, and pages 8877–8899 were added.
- **Snitch.**
  - The page, author and sprint were verified in the browser.
  - The 0/160 figure was verified from the authors' public hand codes (`github.com/Lizcanutella/cover-up-collusion`, `data/hand_codes/lead_arm_vendored_sdk_luna.json`): four asking cells × 40 runs, with `agrees` = 0 in all of them.
  - The same hand codes give 6/128 for Luna-lead reports that named a reverted edit. **v4's "8 of 142" does not reproduce from them.** It may come from a table in the PDF, which could not be read from here. Check it before using v4.
- **LLM usage statement.** It now names the final-draft review and its scripts.

## Structural and presentation changes

- **Figure 1 (new): pipeline.** Workers → coordinator (ledger first or no ledger) → director. It shows the ground-truth and scoring strip and the three numbered questions.
- **Figure 2 (2×2):**
  - a: written down;
  - b: absent from the report, families A and B;
  - c: position;
  - d: softened, or cause flipped.
- **Appendix figures:**
  - A1: positions 1–9;
  - A2: recording by failure type, plus approved changes;
  - A3: cause flow.
- **Label diet.** "Ledger first" and "no ledger" in the prose. Gates are named only where they are defined. H1–H5 appear only in one sentence. There are no J_* names in the main text. Box 1 moves to Appendix E12. Table 1 is gates only, with κ given in the text.
- **D-9 entry.** The existing D-9 in `deviations.md`, written by the Chat 12 session, covers v4b's checks. A duplicate D-9 that this chat appended at about 22:10 was removed, and the file is byte-identical to its state before the append. If v4b is chosen, add `review/v4b/stage4_numbers_v4b.py` to D-9's Files line.

## Update · 8 Nov 2026, 23:50 UK: abstract replaced with Kaustubh's text
- The abstract was replaced verbatim with Kaustubh's version (205 words). The rebuilt v4b is still 20 pp., with the main text ending on p. 8.
- New number: "all but one of the 424 failures it logged". 424 = 359 (three failing workers) + 65 (one failing worker) recorded in the ledger, with 1 absent from the report. Sources: §4.2, `results.json`, `deviations.md` (7 Nov record).
- Removed from the abstract, and still only in the body:
  - the position qualifier (18 of 20 lone-failure losses at positions 2–3; D-9);
  - "absences hand-checked";
  - the 38% cause-flip figure;
  - the scope sentence.
