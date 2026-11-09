"""Trace audit for report v4: list every number in report_v4.md that does not appear in report.md (v3),
and check each against the review outputs and the dated records. Prints the unmatched ones for manual review.

  python -I review/check_numbers_v4.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NUM = re.compile(r"(?<![\w.])[+−-]?\d+(?:[.,]\d+)*%?(?![\w])")


def nums(text: str) -> set[str]:
    return {m.group(0).lstrip("+−-").rstrip("%") for m in NUM.finditer(text)}


v3 = (ROOT / "report/report.md").read_text(encoding="utf-8")
v4 = (ROOT / "report/report_v4.md").read_text(encoding="utf-8")
sources = "\n".join((ROOT / p).read_text(encoding="utf-8") for p in (
    "review/stage1_checks_output.txt", "review/stage4_numbers_output.txt", "deviations.md",
    "results/posthoc/e1_result_2026-11-08.txt", "README.md"))
new = sorted(nums(v4) - nums(v3), key=lambda x: float(x.replace(",", "")))
src = nums(sources)
print(f"numbers in v4 not in v3: {len(new)}")
unmatched = [n for n in new if n not in src]
print("matched in sources:", " ".join(n for n in new if n in src))
print("UNMATCHED (review by hand):")
for n in unmatched:
    for m in re.finditer(rf"(?<![\w.]){re.escape(n)}", v4):
        s = v4[max(0, m.start() - 60):m.end() + 30].replace("\n", " ")
        print(f"  {n:>8}: …{s}…")
        break
