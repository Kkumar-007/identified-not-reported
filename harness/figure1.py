"""Figure 1: what happens to a failure the manager recorded (dropped / softened / cause flipped).

  python figure1.py --results ../results/analysis/results.json --cause ../results/cause/cause_result.json \
                    --out ../results/analysis/figure1_laundering.png [--soft-excl-in-progress A:S=0.30,A:L=0.06]

Reads only the analysis outputs; every plotted number is in results.json or cause_result.json, except the
optional hollow "excluding in-progress-only" points (post hoc, descriptive; deviations.md record, 7 Nov).
One shared 0-100% axis across panels, so the size contrast between panels is honest.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

COL = {"A": "#2a78d6", "B": "#eb6834"}          # dataviz default slots 1-2; validated light-mode pair
MARK = {"A": "o", "B": "s"}                      # secondary encoding: shape as well as colour
NAME = {"A": "Family A (Qwen3-8B)", "B": "Family B (Ministral-3-8B)"}
INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#e4e3de"
OFFSET = {"A": -0.14, "B": 0.14}


def est(d: dict[str, Any] | None) -> tuple[float, float, float] | None:
    if not d or d.get("est") is None:
        return None
    lo, hi = d.get("ci95") or (d["est"], d["est"])
    return d["est"], lo, hi


def panels(R: dict[str, Any], C: dict[str, Any], E: dict[str, Any]) -> list[tuple[str, list[tuple[str, dict[str, Any]]]]]:
    """v3 order: what is written down -> what reaches the director -> how it is described.

    Family B failed G1 and G2, so its ledger-conditioned and ledger-arm loss rates are not plotted
    (prereg section 6); its reports still enter the two exploratory panels.
    """
    A, B = R["families"]["A"], R["families"]["B"]
    rd = C["relay_distortion"]

    def both(fa: Any, fb: Any) -> dict[str, Any]:
        return {"A": est(fa), "B": est(fb)}

    recorded = [
        ("One failing worker of nine", both(A["detection"]["lenient"]["low"], None)),
        ("Three failing workers of nine", both(A["detection"]["lenient"]["high"], None)),
    ]
    absent = [
        ("One failing · ledger first", both(E["A_low_L"], None)),
        ("One failing · no ledger", both(E["A_low_S"], None)),
        ("Three failing · ledger first", both(E["A_high_L"], None)),
        ("Three failing · no ledger", both(E["A_high_S"], None)),
    ]
    dg = lambda F, k: F["downgrade"][k]
    softened = [
        ("One failing · ledger first", both(dg(A, "L/low"), dg(B, "L/low"))),
        ("One failing · no ledger", both(dg(A, "S/low"), dg(B, "S/low"))),
        ("Three failing · ledger first", both(dg(A, "L/high"), dg(B, "L/high"))),
        ("Three failing · no ledger", both(dg(A, "S/high"), dg(B, "S/high"))),
    ]
    flipped = [("Worker blamed test/spec;\nreport blames the code", both(rd["A"] | {"ci95": rd["A"]["ci95"], "est": rd["A"]["rate"]},
                                                                      rd["B"] | {"ci95": rd["B"]["ci95"], "est": rd["B"]["rate"]}))]
    return [
        ("a  Written in the ledger  ·  VALIDATED (lenient κ 0.79; judge-free count identical)  ·  family A", recorded),
        ("b  Never reaches the director (absent from the report)  ·  VALIDATED, absences hand-checked  ·  family A", absent),
        ("c  Softened: called fixed, minor or in progress  ·  EXPLORATORY (judge-coded)  ·  of reported failures", softened),
        ("d  Cause flipped  ·  EXPLORATORY (post hoc)  ·  admitted cells, both counts, both arms", flipped),
    ]


def parse_soft(s: str | None) -> dict[tuple[str, str], float]:
    out: dict[tuple[str, str], float] = {}
    for part in (s or "").split(","):
        if part.strip():
            k, v = part.split("=")
            fam, arm = k.split(":")
            out[(fam.strip(), arm.strip())] = float(v)
    return out


def draw(P: list[tuple[str, list[tuple[str, dict[str, Any]]]]], soft_excl: dict[tuple[str, str], float], out: Path) -> None:
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                         "xtick.color": MUTED, "ytick.color": INK})
    heights = [len(rows) for _, rows in P]
    fig, axes = plt.subplots(len(P), 1, figsize=(7.0, 0.62 * sum(heights) + 1.9), sharex=True,
                             gridspec_kw={"height_ratios": heights, "hspace": 0.55})
    for ax, (title, rows) in zip(axes, P):
        for i, (label, vals) in enumerate(rows):
            y = len(rows) - 1 - i
            for fam in ("A", "B"):
                v = vals.get(fam)
                if v is None:
                    continue
                e, lo, hi = v
                yy = y + OFFSET[fam]
                ax.plot([lo * 100, hi * 100], [yy, yy], color=COL[fam], lw=2, solid_capstyle="round", zorder=2)
                ax.plot(e * 100, yy, MARK[fam], ms=8, color=COL[fam], mec="#fcfcfb", mew=1.5, zorder=3)
                ax.annotate(f"{e * 100:.1f}%" if (e < 0.01 or e > 0.99) else f"{e * 100:.0f}%", (max(hi, e) * 100, yy),
                            xytext=(6, 0), textcoords="offset points", va="center", fontsize=8, color=INK)
            if "Softened" in title:
                cond = ("L" if "ledger first" in label else "S") + ("/low" if label.startswith("One") else "/high")
                if ("A", cond) in soft_excl:
                    yy = y + OFFSET["A"]
                    ax.plot(soft_excl[("A", cond)] * 100, yy, "o", ms=7, mfc="#fcfcfb", mec=COL["A"], mew=1.5, zorder=4)
        ax.set_yticks(range(len(rows)))
        ax.set_yticklabels([r[0] for r in rows][::-1])
        ax.set_ylim(-0.6, len(rows) - 0.4)
        ax.set_title(title, loc="left", fontsize=9.5, color=INK, pad=5)
        ax.grid(axis="x", color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.tick_params(axis="y", length=0)
    axes[-1].set_xlim(0, 100)
    axes[-1].set_xlabel("Percent (denominator in each panel title); bars are 95% cluster-bootstrap intervals over sets")
    handles = [plt.Line2D([], [], marker=MARK[f], color=COL[f], lw=2, ms=8, mec="#fcfcfb", label=NAME[f]) for f in ("A", "B")]
    if soft_excl:
        handles.append(plt.Line2D([], [], marker="o", ls="", ms=7, mfc="#fcfcfb", mec=COL["A"], mew=1.5,
                                  label="A, softened excl. 'in progress' only (post hoc)"))
    fig.legend(handles=handles, loc="upper center", ncol=len(handles), frameon=False, fontsize=8,
               bbox_to_anchor=(0.5, 0.955))
    fig.savefig(out, dpi=220, bbox_inches="tight", facecolor="#fcfcfb")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--cause", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--e1", type=Path, required=True, help="results/posthoc/e1_result.json (D-8, hand-checked absences)")
    ap.add_argument("--soft-excl-in-progress", default=None, help="e.g. A:L/low=0.57,A:S/low=0.73,A:L/high=0.06,A:S/high=0.30")
    a = ap.parse_args()
    R = json.loads(a.results.read_text())
    C = json.loads(a.cause.read_text())
    E = json.loads(a.e1.read_text())
    draw(panels(R, C, E), parse_soft(a.soft_excl_in_progress), a.out)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
