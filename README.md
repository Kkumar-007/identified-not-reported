# Identified but Not Reported

Solo entry to Apart Research's Swarm Alignment Hackathon (Track 4, Multi-Agent Oversight and Control). Kaustubh Kumar, University of Edinburgh.

Paper: *The Empty Ledger: When Logging Issues First Lets a Lone Failure Slip Through* (`report/`). The repository keeps its working name, "Identified but Not Reported".

- `report/`: the submission report (`report.md` source, `report.docx` in the template's styles, `report.pdf` preview, `build.py`). Every number in it comes from `results/analysis/results.json`, `results/cause/cause_result.json` or the dated records in `deviations.md`.
- `results/`: analysis outputs (`analysis/results.{json,md}`, Figure 1), CAUSE outputs, hand labels and codebooks.
- `prereg.md`: the pre-registration (authority for the analysis). `deviations.md`: every later change.
- `harness/`: experiment code (see `harness/README.md`), frozen config, set specs, and worker-only probe, smoke and screen logs.
- `prompts.md`, `problem_set.md`, `problems.csv`, `problems_check.csv`, `design_decisions.md`, `related_work.md`, `infra.md`, `report_skeleton.md`, `handoff_log.md`: design and planning documents.

**Prior work (sprint rule).** This project does not build on any earlier project or code of the author's; no code in this repository was written before the sprint. It builds on published work by others, cited in the report's §2: Guo et al. (ICML 2026), Lizcano Cabezas, "Don't Be a Snitch" (Apart AI Collusion Research Sprint, Oct 2026), Kemeklis & Vemuri, "Omission Attacks" (Apart AI Control Hackathon 2026), Sun et al. (2026, arXiv:2608.24569), and ImpossibleBench (Zhong et al., 2025) for the admitted-failure construction. The only preexisting material is planning documents, listed below.

**Timing and preexisting material (sprint rule).** All code in `harness/`, every run in `harness/logs_*` and `prereg.md` were produced after the sprint started. Declared as preexisting planning material: the problem set and its CSVs, the prompt drafts, the infra throughput check and the planning documents (`design_decisions.md`, `related_work.md`, `infra.md`, `report_skeleton.md`, `project_description_v2.md`, and Chats 1–5 in `handoff_log.md`). Changes made to them during the sprint are marked in their status lines or changelogs.

**Redaction.** The cluster username is replaced by `UUN_REDACTED` in run manifests, in the published data release and, from the commit that adds `release/`, in the tracked documents. A University staff member's name in the planning documents is replaced by their role. Earlier commits still contain the username in log paths: history was not rewritten, so that the push times of the pre-registration, hand-label, D-6 and D-8 commits stay verifiable.

**Data.** All run logs, judge calls, rendered prompts, scores and the hand-label key: [doi:10.5281/zenodo.24047673](https://doi.org/10.5281/zenodo.24047673). See `release/README_DATA.md` for contents, the reproduction commands and the redaction record; `release/ibnr-release-v1.tar.gz.sha256` gives the archive checksum. On this release, `harness/analysis.py` reproduces `results/analysis/results.json` byte for byte.

## Pre-registration commit

`prereg.md` became binding with commit [`dff73e2`](https://github.com/Kkumar-007/identified-not-reported/commit/dff73e25188796ebfc62d5a4afe8346603c49c35) (full hash `dff73e25188796ebfc62d5a4afe8346603c49c35`). The push time is GitHub's record of that push. Third-party timestamp: [Wayback Machine snapshot of the commit page](https://web.archive.org/web/20261106185455/https://github.com/Kkumar-007/identified-not-reported/commit/dff73e25188796ebfc62d5a4afe8346603c49c35). Every later change to outcomes, thresholds, sample sizes, exclusions or analysis is listed in `deviations.md`.
