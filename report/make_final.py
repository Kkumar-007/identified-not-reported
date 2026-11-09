"""Build report_final.md from report_v4.md (the chosen version, with Kaustubh's 23:50 abstract) by exact,
asserted replacements. Changes: clearer abstract; Author Contributions removed; new LLM Usage statement;
new Appendix G text; Snitch 'always refused' -> 'never agreed to' (0/160 is the hand-coded 'agrees' count).

  python -I make_final.py
"""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
src = (HERE / "report_v4.md").read_text(encoding="utf-8")

OLD_ABSTRACT = src.split("# Abstract {.unnumbered}\n\n", 1)[1].split("\n\n# Introduction", 1)[0]
NEW_ABSTRACT = (
    "Overseers of agent teams often read a coordinator's summary instead of every worker's transcript. "
    "We ask where honestly reported failures are lost on the way up when no agent is asked to hide anything. "
    "Nine Qwen3-8B workers each implement a Python function and end with a test-status line; hidden tests decide "
    "which functions fail. A coordinator reports to a director in at most 120 words, either directly or after first "
    "logging issues in a structured ledger (130 pre-registered transcript sets, 160 injected failures). "
    "Our pre-registered question was whether a coordinator drops failures it has logged. A Qwen3-8B coordinator "
    "almost never did: it forwarded 423 of the 424 failures it logged (reported descriptively: the pre-registered "
    "primary score failed validation against hand labels). With a ledger, failures were lost at the "
    "logging step, not in forwarding. Post hoc, with three of nine workers failing, logging first removed every loss "
    "(0% vs 5.0% without a ledger). With one failing worker, the coordinator often logged no issues, and its "
    "ledger-first reports omitted 16.7% of lone failures, against 1.7% without a ledger; 18 of these 20 "
    "omissions came when the failing worker's transcript was second or third of nine. A Ministral-3-8B coordinator, "
    "whose ledger listed nearly everything, including most approved changes, lost no lone failure with either "
    "procedure. In exploratory analyses, reports that did name a failure often called it fixed, minor or in "
    "progress. Reporting procedures should be tested on lone failures, not only where failures are plentiful."
).replace("'", "’")  # match the curly apostrophes of the v4 abstract

OLD_G = src.split("## G. Prior work and pre-sprint material {.unnumbered}\n\n", 1)[1].split("\n\n# LLM Usage", 1)[0]
NEW_G = (
    "The following materials were prepared before the sprint began and are therefore declared as preexisting: the "
    "problem set and its accompanying files (`problems.csv`, `problems_check.csv`, and `problem_set.md`); the "
    "initial prompt drafts (`prompts.md` v1); the infrastructure throughput check; and the planning documents "
    "(`design_decisions.md`, `related_work.md`, `infra.md`, `report_skeleton.md`, `project_description_v2.md`, and "
    "Chats 1–5 of `handoff_log.md`). Because they predate the first commit, we also declare as preexisting the "
    "harness code as it stood before `dff73e2` and the runs made with it, between 22:50 UTC on 5 November and 01:32 "
    "UTC on 6 November: the worker-only smoke run (job 3700609), three worker-prompt probes (jobs 3700646, 3700662 "
    "and 3700665; job 3700646 also holds the coordinator plumbing check on clean set C01 disclosed in the "
    "pre-registration) and the stage-A problem screen (job 3700718). All subsequent work was conducted within the "
    "sprint's published dates of 6–8 November, beginning with the pre-registration commit `dff73e2` (pushed at "
    "18:48 UTC on 6 November). This includes every subsequent harness change (scoring, judge, validity gates, pilot "
    "and analysis), the pilot and main experimental runs, the deviations log, the hand labels and cause codes, the "
    "post hoc checks, and this report."
)

OLD_LLM = src.split("# LLM Usage Statement {.unnumbered}\n\n", 1)[1].rstrip("\n")
NEW_LLM = ("Claude Code (Opus 5.5) was used for coding assistance, experimental design iteration and drafting portions "
           "of this report. All claims were verified against raw experimental data.")

EDITS = [
    ("abstract", OLD_ABSTRACT, NEW_ABSTRACT),
    ("author contributions removed",
     "# Author Contributions {.unnumbered}\n\nK.K. designed and ran the study, labelled and "
     "hand-checked the validation items and wrote the report.\n\n", ""),
    ("Snitch: 0/160 is 'never agreed', not 'always refused'",
     "Model leads asked to hide an edit always refused (0 of 160), yet",
     "Model leads asked to hide an edit never agreed to (0 of 160), yet"),
    ("appendix G", OLD_G, NEW_G),
    ("LLM usage", OLD_LLM, NEW_LLM),
]

out = src
for label, old, new in EDITS:
    n = out.count(old)
    assert n == 1, f"{label}: found {n} times"
    out = out.replace(old, new)
assert "Author Contributions" not in out
(HERE / "report_final.md").write_text(out, encoding="utf-8")
print(f"wrote report_final.md ({len(EDITS)} edits); abstract {len(NEW_ABSTRACT.split())} words")
