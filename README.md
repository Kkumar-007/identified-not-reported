# Identified but Not Reported

Entry to Apart Research's Swarm Alignment Hackathon (Track 4, Multi-Agent Oversight and Control). Kaustubh Kumar, University of Edinburgh.

Paper: *The Empty Ledger: When Logging Issues First Lets a Lone Failure Slip Through* (`report/`). The repository keeps its working name, "Identified but Not Reported".

- `report/`: the submitted report, `report_final.pdf` (source `report_final.md`; `report_final.docx` in the template's styles). `make_final.py` derives `report_final.md` from the v4 draft `report_v4.md`, and `build_final.py` builds the docx and PDF. `report.md` and `build.py` are the earlier v3 draft; its built files are no longer tracked. Every number in the report comes from `results/analysis/results.json`, `results/cause/cause_result.json` or the dated records in `deviations.md`.
- `results/`: analysis outputs (`analysis/results.{json,md}`, Figure 1), CAUSE outputs, hand labels and codebooks.
- `review/`: scripts, outputs and change log for the D-9 post hoc checks on the final draft.
- `prereg.md`: the pre-registration (authority for the analysis). `deviations.md`: every later change.
- `harness/`: experiment code (see `harness/README.md`), frozen config, set specs, and worker-only probe, smoke and screen logs.
- `prompts.md`, `problem_set.md`, `problems.csv`, `problems_check.csv`, `design_decisions.md`, `related_work.md`, `infra.md`, `report_skeleton.md`, `handoff_log.md`: design and planning documents.

**Prior work (sprint rule).** This project does not build on any earlier project of the author's. Part of the harness, and some runs made with it, may predate the sprint's start; they are declared as preexisting below. It builds on published work by others, cited in the report's §2: Guo et al. (ICML 2026), Lizcano Cabezas, "Don't Be a Snitch" (Apart AI Collusion Research Sprint, Oct 2026), Kemeklis & Vemuri, "Omission Attacks" (Apart AI Control Hackathon 2026), Sun et al. (2026, arXiv:2608.24569), and ImpossibleBench (Zhong et al., 2025) for the admitted-failure construction. The preexisting material is listed below.

**Timing and preexisting material (sprint rule).** We did not record the sprint start time that Apart confirmed to us, so we take the conservative reading. Declared as **preexisting**:

- the planning material: the problem set and its CSVs, the prompt drafts (`prompts.md` v1), the infra throughput check, and the planning documents (`design_decisions.md`, `related_work.md`, `infra.md`, `report_skeleton.md`, `project_description_v2.md`, and Chats 1–5 in `handoff_log.md`);
- the harness code as it stood before the first commit, and the runs made with it, all on workers except one plumbing check:
  - the smoke run (job 3700609, 5 Nov 22:51 UTC);
  - three worker-prompt probes (jobs 3700646, 3700662 and 3700665, 5 Nov 23:13 UTC to 6 Nov 00:02 UTC). Job 3700646 also holds the coordinator plumbing check on clean set C01, which is disclosed in `prereg.md` §0;
  - the stage-A problem screen (job 3700718, 6 Nov 01:16–01:32 UTC).

  No commit exists before `dff73e2`, so that code is identified only by the config hashes in those runs' manifests (`harness/logs_*`).

**Produced on 6–8 Nov, the sprint's published dates**, from the pre-registration commit `dff73e2` (6 Nov 18:48 UTC) onward:

- the pre-registration;
- the scoring, judge, gate, pilot and analysis code, and every later harness change;
- the pilot and main runs;
- the hand labels;
- every post hoc check;
- the report.

No manager saw a set containing a failure before `dff73e2`. Changes to the planning material during the sprint are marked in its status lines or changelogs.

**Redaction.** The cluster username is replaced by `UUN_REDACTED` in run manifests, in the published data release and, from the commit that adds `release/`, in the tracked documents. A University staff member's name in the planning documents is replaced by their role. Earlier commits still contain the username in log paths: history was not rewritten, so that the push times of the pre-registration, hand-label, D-6 and D-8 commits stay verifiable.

**Data.** All run logs, judge calls, rendered prompts, scores and the hand-label key: [doi:10.5281/zenodo.24047673](https://doi.org/10.5281/zenodo.24047673). See `release/README_DATA.md` for contents, the reproduction commands and the redaction record; `release/ibnr-release-v1.tar.gz.sha256` gives the archive checksum. On this release, `harness/analysis.py` reproduces `results/analysis/results.json` byte for byte.

## Pre-registration commit

`prereg.md` became binding with commit [`dff73e2`](https://github.com/Kkumar-007/identified-not-reported/commit/dff73e25188796ebfc62d5a4afe8346603c49c35) (full hash `dff73e25188796ebfc62d5a4afe8346603c49c35`). The push time is GitHub's record of that push. Third-party timestamp: [Wayback Machine snapshot of the commit page](https://web.archive.org/web/20261106185455/https://github.com/Kkumar-007/identified-not-reported/commit/dff73e25188796ebfc62d5a4afe8346603c49c35). Every later change to outcomes, thresholds, sample sizes, exclusions or analysis is listed in `deviations.md`.
