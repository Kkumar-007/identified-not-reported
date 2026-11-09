# Change log: report v3 (`report/report.md`, `report.pdf`) → v4 (`report/report_v4.md`, `.docx`, `.pdf`)

8 Nov 2026, 19:10 UK. v3 is untouched (sha256 `611acb6e…` md, `bec0f055…` pdf). The title is unchanged.
**Build:** `python -I review/make_report_v4.py`, then `cd report && python build_v4.py`.
- `make_report_v4.py` takes v3's title block, references and appendix.
- It swaps in the main text from `review/v4_main.md`.
- It applies each appendix and reference edit as an asserted find-and-replace, listed in the script.

**Page check (LibreOffice render):** 21 pages. The main text ends on p. 8, after Author Contributions, and the references start on p. 9. The abstract has 248 words. The main text is 2,886 words without captions (v3: 3,362).

**Number check.** `review/check_numbers_v4.py` lists every number in v4 that is not in v3 and matches it against:
- `review/stage1_checks_output.txt`
- `review/stage4_numbers_output.txt`
- `deviations.md`
- `results/posthoc/e1_result_2026-11-08.txt`
- `README.md`

Six items are unmatched, and all are expected:
- two section numbers and one figure width;
- Snitch's "8 of 142", read from the Snitch report PDF in a browser on 8 Nov;
- Wang et al. pp. 8877–8899, from the ACL Anthology page.

Output: `review/check_numbers_v4_output.txt`.

## Scientific changes (claims, numbers, analysis)

| # | Stage 1 ID | Change | Where | Source |
|---|---|---|---|---|
| S1 | narrative | The thesis is reframed: the pre-registered answer (transmission is near-lossless) comes first, and the empty-ledger result follows as the post hoc headline, with its scope (family A, positions 2–3, B lost no lone failure). It runs through the abstract, introduction, contributions and conclusion | Abstract, §1, §6 | Stage 2+3 (`review/stage23_narrative.md`, approved) |
| S2 | F1 | New post hoc section §4.3 and Figure 3 on transcript position. New Appendix E11 table, with per-position counts, early-minus-late bootstrap and same-function flips. The untested mechanisms move here from the Discussion. A limitation bullet is added in A.2. A.1 scope is narrowed | §4.3, Fig 3, E11, A.1, A.2 | `stage1_checks_output.txt` §2–3; `stage4_numbers_output.txt` §0–2 |
| S3 | F1 | **D-9 added to `deviations.md`**: position, instruction phrasing, family B end-to-end and the L − S re-expression. It records the forking paths and that the swap rerun was not run. D-9 is listed in A.2 and in the F chronology, and the text says D-1 to D-9 | `deviations.md`, A.2, F, §3 | — |
| S4 | F3 | Family B's end-to-end losses move into the main text: Table 1 rows, Figure 2b squares, the §4.2 text and the abstract. The text explains why gates G1/G2 do not apply to them (they are not conditioned on the ledger). The A.2 family B bullet is updated | Table 1, Fig 2b, §4.1–4.2 | `stage4_numbers_output.txt` §4 (same counts as E9) |
| S5 | F2 | The deviation cells are renamed "hidden-instruction" failures. Methods says 22/40 DE and 8/40 DC workers wrote "as instructed", and the "self-initiated" framing is removed. The §5.1 explanation via "the worker gave a reason" is removed. A limitation bullet gives 29/12 (broad pattern) and 3/21 vs 4/39 (no effect on the headline) | §3.1, §5, A.2 | `stage1_checks_output.txt` §1; `stage4_numbers_output.txt` §7 |
| S6 | F7 | The Table 1 effect column is now the **ledger effect, L − S** (+15.0 [+5.8, +25.8]; −5.0 [−8.1, −2.2]). It is exactly the negation of D-8's S − L, with the same bootstrap. Per-arm intervals moved to Figure 2b to keep table rows to one line | Table 1 | `stage4_numbers_output.txt` §3 |
| S7 | — | The §4.2 statement "the report then follows the ledger" is corrected to: an empty ledger raised omission to 20 of 55, against 2 of 120 without a ledger, and 35 of 55 empty-ledger reports still mentioned the failure | §4.2 | `stage4_numbers_output.txt` §5 |
| S8 | F5 | A.2 no longer says "(hand-checked)" for the 35 mentions. It now says 5 of the 35 were hand-checked and all 20 absences were | A.2 | `stage4_numbers_output.txt` §5 |
| S9 | F6 | The core/edge softening numbers are labelled as pooled over both procedures | §4.5 | `results.json` downgrade `high/core`, `high/edge` (n 247/215) |
| S10 | — | The softening numbers leave the abstract and appear in §4.5 as a range with both caveats. Cause flipping leads §4.5 | Abstract, §4.5 | unchanged numbers |
| S11 | Snitch | Related work: model leads refused to hide an edit (0 of 160) yet named a reverted edit in only 8 of 142 final reports. **This corrects v3's Discussion line "Like Snitch's model lead, the coordinator forwarded nearly every failure it had written down", which misdescribed Snitch.** That line is removed | §2, §5 | Snitch report PDF, §4.3 (read in the browser) |
| S12 | — | The H1–H5 paragraph is reduced to H1 plus a descriptive summary. The lenient H3–H5 numbers move to Appendix E7, so no number is lost | §4.4, E7 | v3 §4.4 numbers |
| S13 | — | Family A's matched-load G1 caveat moves from the main text to A.2 (unchanged there). The main text keeps a one-line pointer | §4.1, A.2 | v3 |
| S14 | — | New Appendix E10 and Figure E10: each family's ledger as a detector (recall vs false alarms). It is descriptive, B is marked gate-failed, and the main text has one sentence ("Two models, two ledgers") | E10, §5 | `results.json` (echoed in `stage4_numbers_output.txt` §6) |
| S15 | — | Track-4 framing sentence in §1: "the shape a lone misaligned agent's deviation would take". No adversary is claimed | §1 | — |

## Compliance and reference changes

| # | Stage 1 ID | Change | Where |
|---|---|---|---|
| C1 | F4 | The Appendix G placeholder is replaced with a conservative declaration, because no start time was available. The following are declared preexisting, with job IDs and UTC times from the run logs: the harness code before the first commit; the 5 Nov smoke run; the three probes, including the C01 coordinator plumbing check; and the 6 Nov stage-A screen. Everything from `dff73e2` (6 Nov 18:48 UTC) onward falls in the published 6–8 Nov sprint window. The same declaration is made in the root `README.md` (Prior work and Timing paragraphs) and in `harness/README.md` | G; `README.md`; `harness/README.md` |
| C2 | F9 | `release/README_DATA.md` gets the final title. A note says the copy inside the archive carries the earlier working title. The archive itself was **not** rebuilt, so its sha256 still matches Zenodo | `release/README_DATA.md` |
| C3 | ref | Wang et al.: the anthology ID `2026.findings-emnlp.422` was verified, and pages 8877–8899 were added | References |
| C4 | ref | Snitch: the link, title, author and sprint were verified, and 0/160 was confirmed in the report PDF | References, §2 |
| C5 | — | The LLM usage statement mentions the final-draft review (D-9 and the figures), and the number sources include the `review/` outputs | LLM statement |

## Structural and presentation changes

- **New Figure 1 (design diagram).** Workers and hidden tests → a coordinator (ledger first or no ledger) → the director, with three checkpoints. It replaces about a third of the Methods prose.
- **Figure 2 (was Figure 1).** It is now a 2×2 dot-plot. Family B is added to panel b, and panel titles are plain-language.
- **Figure 3 (new).** Position.
- **Figure E10 (new).** Each family's ledger as a detector.
- **Generation.** All figures are generated by `review/figures_v4.py` from the results files and `review/stage4_numbers.json`. The palette was validated with the dataviz validator.
- **Gate table.** It moves to Appendix Table E0. The main text summarises it in three sentences.
- **Box 1.** It moves to Appendix E12.
- **Labels cut from the main text:**
  - cells are "test conflict" and "hidden instruction", core or edge;
  - procedures are "ledger first" and "no ledger";
  - scores are "mentions", "states" and "softened";
  - gates are named by purpose;
  - H1–H5 appear only in §4.4;
  - the codes are defined once, in an appendix notation line.
- **Text cuts.**
  - The "Fit with prior work" paragraph is cut. Its Snitch point now sits, corrected, in Related Work.
  - The Discussion is trimmed.
  - Limitations become compact prose.
  - The Code and Data line is shortened.
- **Build.**
  - `report/build_v4.py` is a copy of `build.py` with v4 file names and `--columns=40`. Pandoc 2.9 otherwise gave the short-row Table 1 no column widths, and LibreOffice dropped three of its columns.
  - Section numbering is unchanged.

## Not changed

- The title.
- Every v3 number, other than the re-expression (S6) and the relocations (S12, S13).
- Prereg, prompts, analysis code, `results/`, and the release archive.
- No model was run.

## Update · 8 Nov 2026, 23:50 UK: abstract replaced with Kaustubh's text (Chat 13)
- The abstract was replaced verbatim, 248 → 205 words, in `report/report_v4.md` and in `review/v4_main.md`, so `make_report_v4.py` reproduces it.
- The report was rebuilt with Old Standard TT, the template font: `report_v4.docx`, `report_v4_oldstandard.pdf`, and `report_v4.pdf`, which is now the same Old Standard render and replaces the DejaVu Serif one. 20 pp.; the main text ends on p. 8.
- New number: "all but one of the 424 failures it logged" = 359 + 65 recorded, 1 absent (§4.2, `results.json`).
- Removed from the abstract, and still only in the body:
  - the position qualifier (18 of 20 losses at positions 2–3; D-9);
  - "absences hand-checked";
  - the 38% cause-flip figure.
