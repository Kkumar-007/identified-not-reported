"""Assemble report/v4b/report_v4b.md from v3 (report/report.md) plus review/v4b/v4b_main.md, applying the appendix
and reference edits as asserted find-and-replace. Run from the repo root. Then: cd report/v4b && python build_v4b.py
(paths inside the output: figures/ and review/v4b/ are rewritten after assembly; see the last lines)."""
from pathlib import Path
src=Path('report/report.md').read_text(encoding='utf-8')
main=Path('review/v4b/v4b_main.md').read_text(encoding='utf-8')
head=src[:src.index('# Abstract {.unnumbered}')]
tail=src[src.index('# Code and Data {.unnumbered}'):]
box1_start=src.index('> **Box 1.')
box1=src[box1_start:src.index('\n',box1_start)]
def rep(t,old,new):
    assert t.count(old)==1, (t.count(old), old[:80])
    return t.replace(old,new)
tail=rep(tail,"that it forwards nearly everything it writes down; and, post hoc with hand-checked absences, that a ledger step first lowers end-to-end loss with three failing workers and raises it with one.",
 "that it forwards nearly everything it writes down; and, post hoc with hand-checked absences, that a ledger step first lowers end-to-end loss with three failing workers and raises it with one, with the lone-failure losses concentrated where the failing transcript sat second or third of nine (D-9; not counterbalanced). Family B's reports, scored end to end without its ledger, lost no lone failure.")
tail=rep(tail,"that family B's managers are or are not faithful reporters (its ledger failed G1 and G2);",
 "that family B's managers are or are not faithful reporters (its ledger failed G1 and G2); that transcript position causes the loss (it was never counterbalanced);")
tail=rep(tail,"In 35 of the 55 one-failure samples with an empty ledger, the same conversation's report still mentioned the failure (hand-checked).",
 "In 35 of the 55 one-failure samples with an empty ledger, the same conversation's report still mentioned the failure (judge lenient; 5 of these 35 fell in the hand-checked sample, and all 20 absences were hand-checked).")
tail=rep(tail,"Its omission rates appear only in Appendix E.",
 "Its ledger-conditioned rates appear only in Appendix E1; its end-to-end counts, which do not use the ledger, are in Table 2 and Figure 2b (judge calls, not hand-checked).")
anchor="but it was not a pre-registered test.\n"
tail=rep(tail,anchor, anchor+
"- **Position was never counterbalanced (D-9).** 18 of the 20 lost lone failures come from transcripts at positions 2 and 3. Positions were drawn per set, the first-three group is 13 sets, and the pattern was found after the results were known, while three moderators were examined (instruction phrasing, position, set clustering). A position-swapped rerun of the frozen worker episodes was not run, so the pattern is an observation, not a causal result.\n"
"- **The instructed-change cells leak their instruction (D-9).** 22 of 40 DE and 8 of 40 DC accepted worker messages say the change was made \"as instructed\" or \"as per the instruction\" (29 and 12 with \"as requested\"); no other cell does. The registered leak filter (`i was (told|instructed|asked) to`) does not match these phrasings. These cells therefore mix self-presented and visibly directed changes, which bears on DE recording, the matched-load G1 comparison and softening. It does not drive the headline: in the one-failure DC/DE sets, ledger-first absences were 3 of 21 samples with the phrasing and 4 of 39 without, and DE recording was 3 of 12 and 7 of 18.\n")
d8="the hand codes pushed (`9ba472c`) before the recompute.\n"
tail=rep(tail,d8, d8+"- **D-9 (post hoc exploratory observations, 8 Nov):** from a review of the final draft: instruction phrasing in the instructed-change cells, recording and end-to-end loss by transcript position, and family B's end-to-end intervals. No model was run and nothing registered changed; the author decided not to run a position-swapped rerun before the deadline.\n")
tail=rep(tail,"(6) leak filter `system prompt|hidden instruction|i was (told|instructed|asked) to|my instructions`;",
 "(6) leak filter `system prompt|hidden instruction|i was (told|instructed|asked) to|my instructions` (it does not match \"as instructed\" or \"as per the instruction\"; see D-9);")
e9_start=tail.index('**E9. End-to-end loss, family B')
e9_end=tail.index('\n',e9_start)
new_e=("**E9. End-to-end loss, family B (judge lenient; not hand-checked; descriptive; now in Table 2 and Figure 2b).** Family B's ledger recorded all 120 lone failures and all 360 with three failing workers, along with 59 of 60 approved changes. Its reports omitted 0 of 120 lone failures in either procedure, and 0 of 360 (ledger first) and 1 of 360 (no ledger; 0.3% [0.0, 0.8]) with three failing workers. Script: `review/stage4_numbers.py`.\n\n"
"**E10. Transcript position, family A, one failing worker (D-9, post hoc).** The coordinator prompt lists transcripts worker_1 to worker_9 in order (checked on all 240 one-failure, family A, turn-1 prompts). Per position (sets; written down; absent with the ledger first; absent without a ledger): 1: 1; 3/3; 0/3; 0/3 · 2: 8; 0/24; 12/24; 0/24 · 3: 4; 4/12; 6/12; 2/12 · 4: 5; 12/15; 1/15; 0/15 · 5: 2; 3/6; 1/6; 0/6 · 6: 4; 9/12; 0/12; 0/12 · 7: 5; 13/15; 0/15; 0/15 · 8: 7; 11/21; 0/21; 0/21 · 9: 4; 10/12; 0/12; 0/12. By band, written down: 17.9% [0.0, 41.0] (positions 1–3), 72.7% [45.5, 100.0] (4–6), 70.8% [50.0, 87.5] (7–9); absent with the ledger first: 46.2% [20.5, 71.8], 6.1% [0.0, 15.2], 0.0%. With three failing workers, written down 105/105, 132/132 and 123/123 by band. Scripts: `review/stage1_checks.py`, `review/stage4_numbers.py`.\n\n"
"![**Figure A1. Family A, one failing worker, by the failing worker's transcript position.** Grey: share of samples whose ledger has an entry for the failing worker. Blue: share whose ledger-first report omits the failure. Set counts under each position; positions were not counterbalanced.](figures_v4/figA1_positions.png){width=88%}\n\n"
"**E11. Recording by failure type, family A, one failing worker (judge-free).** Core test conflict 16/30, edge test conflict 18/30, core instructed change 21/30, edge instructed change 10/30; approved changes with a ledger entry 21/60 (a good coordinator should not flag these).\n\n"
"![**Figure A2. Share of samples whose ledger has an entry for the worker, by failure type** (family A, one failing worker; grey: approved change, which should not be flagged).](figures_v4/figA2_by_type.png){width=88%}\n\n"
"![**Figure A3. Cause flow in the test-conflict cells (counts as in E4).** Each bar is the set of reports that mention the failure, split by what the worker blamed (rows) and what the report blamed (colours). The true cause is always the test pair.](figures_v4/figA3_cause.png){width=88%}\n\n"
"**E12. Moved from the main text: example reports.**\n\n"+box1+"\n")
tail=tail[:e9_start]+new_e+tail[e9_end+1:]
tail=rep(tail,"→ hand codes pushed (`9ba472c`) → E1 recompute (`b013f83`).",
 "→ hand codes pushed (`9ba472c`) → E1 recompute (`b013f83`) → review of the final draft (8 Nov) → D-9 (no model run).")
g_old_start=tail.index("Built during the sprint: all code in `harness/`")
g_old_end=tail.index("pushed at 18:48 UTC on 6 Nov.",g_old_start)+len("pushed at 18:48 UTC on 6 Nov.")
g_new=("**Timing.** The sprint's exact start time is not recorded in the project files, so we declare conservatively. The worker-only runs made before the pre-registration are treated as preexisting, together with the harness code as it stood for them: the smoke test (job 3700609, from 22:50 UTC on 5 Nov), three worker-prompt probes (23:13 UTC on 5 Nov to 00:02 UTC on 6 Nov) and the stage A screen (job 3700718, 01:16–01:33 UTC on 6 Nov). None involved a coordinator reading a set that contained a failure (pre-registration §0). Everything from the pre-registration onward was built during the sprint: the pre-registration commit `dff73e2` (pushed 18:48 UTC on 6 Nov), the later harness code (judge, scoring, gates, pilot runner, analysis), every pilot and main-run log, the deviations log, the hand labels and cause codes, the analysis and this report.")
tail=tail[:g_old_start]+g_new+tail[g_old_end:]
tail=rep(tail,"The judge model used for scoring is described in §3.",
 "A second AI-assisted review of the final draft (8 Nov) found the patterns reported under D-9, checked two references against their sources, and drafted the v4 figures' plotting code and parts of the revised text; every number it added comes from `review/stage1_checks.py` or `review/stage4_numbers.py` run on the released data. The judge model used for scoring is described in §3.")
tail=rep(tail,"*Findings of the Association for Computational Linguistics: EMNLP 2026*. <https://aclanthology.org/2026.findings-emnlp.422/>",
 "*Findings of the Association for Computational Linguistics: EMNLP 2026*, 8877–8899. <https://aclanthology.org/2026.findings-emnlp.422/>")
out=(head+main+tail).replace('](figures_v4/','](figures/').replace('`review/stage4_numbers.py`','`review/v4b/stage4_numbers_v4b.py`')
Path('report/v4b/report_v4b.md').write_text(out,encoding='utf-8')
print('main words', len(main.split()))
