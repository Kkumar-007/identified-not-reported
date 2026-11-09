"""Figures for report v4. Reads only analysis outputs; plots no number that is not in a results file.

  python -I review/figures_v4.py --repo . --outdir report

Inputs:
  results/analysis/results.json      detection, softening (downgrade), gates
  results/cause/cause_result.json    cause flipping (D-6)
  results/posthoc/e1_result.json     family A end-to-end absence, hand codes substituted (D-8)
  review/stage4_numbers.json         family B end-to-end absence; position bands and positions (D-9)
Outputs (report/): fig1_design_v4.png, fig2_funnel_v4.png, fig3_position_v4.png, figE1_detector_v4.png
Palette: dataviz reference slots 1-2 (blue = family A, orange = family B), validated light-mode pair;
shape is a second identity channel (circle = A, square = B). Red is used only for "failing" status, with an icon and a label.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

COL = {"A": "#2a78d6", "B": "#eb6834"}
MARK = {"A": "o", "B": "s"}
NAME = {"A": "Family A (Qwen3-8B)", "B": "Family B (Ministral-3-8B)"}
INK, MUTED, GRID, SURF = "#1f1f1e", "#6b6a64", "#e4e3de", "#fcfcfb"
FAIL, FAIL_BG = "#c43c3b", "#fbe9e8"
PANEL_BG, LINE = "#f3f2ee", "#b9b7ae"
plt.rcParams.update({"font.size": 8, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": INK, "font.family": "DejaVu Sans"})


def fmt(e: float) -> str:
    return f"{e * 100:.1f}%" if 0 < e < 0.2 or 0.99 < e < 1 else f"{e * 100:.0f}%"


# ---------------------------------------------------------------- Figure 1: design
def box(ax, x, y, w, h, text="", fc="white", ec=LINE, lw=1.0, fs=7.5, color=INK, weight="normal", ls="-", r=0.6,
        ha="center"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=lw, ls=ls))
    if text:
        tx = x + w / 2 if ha == "center" else x + 0.8
        ax.text(tx, y + h / 2, text, ha=ha, va="center", fontsize=fs, color=color, weight=weight, linespacing=1.25)


def arrow(ax, x0, y0, x1, y1, color=INK, lw=1.2, style="-|>", ms=9):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle=style, mutation_scale=ms, color=color, lw=lw,
                                 shrinkA=0, shrinkB=0))


def badge(ax, x, y, n):
    ax.add_patch(plt.Circle((x, y), 1.25, fc=INK, ec=SURF, lw=1.5, zorder=5))
    ax.text(x, y - 0.05, str(n), ha="center", va="center", fontsize=7.5, color="white", weight="bold", zorder=6)


def fig_design(out: Path) -> None:
    fig = plt.figure(figsize=(7.2, 3.0))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 41.7)
    ax.axis("off")
    # workers
    ax.text(14.5, 39.6, "Nine workers (Qwen3-8B)", ha="center", va="center", fontsize=8.5, weight="bold", color=INK)
    ax.text(14.5, 37.3, "one function each; each runs its tests\nand ends with a status line",
            ha="center", va="center", fontsize=6.6, color=MUTED, linespacing=1.2)
    failing = {2, 6}
    W, H, gx, gy = 8.4, 6.4, 0.6, 0.7
    for k in range(9):
        r, c = divmod(k, 3)
        x, y = 1.2 + c * (W + gx), 27.6 - r * (H + gy)
        f = (k + 1) in failing
        box(ax, x, y, W, H, fc=FAIL_BG if f else "white", ec=FAIL if f else LINE, lw=1.3 if f else 0.9)
        ax.text(x + W / 2, y + H - 1.8, f"worker_{k + 1}", ha="center", va="center", fontsize=6.6, color=INK)
        ax.text(x + W / 2, y + 1.8, "✗ failing" if f else "passing", ha="center", va="center", fontsize=6.6,
                color=FAIL if f else MUTED, weight="bold" if f else "normal")
    box(ax, 0.8, 0.8, 27.2, 9.4, ls=(0, (3, 2)), ec=MUTED, fc=SURF,
        text="Hidden tests decide which functions\nfail; no model decides. A failure is a\n"
             "contradictory test pair, or a hidden\ninstruction to deviate (core or edge)",
        fs=6.0, color=INK)
    ax.text(14.5, 11.6, "1 or 3 of 9 workers fail per set", ha="center", va="center", fontsize=6.6, color=FAIL,
            style="italic")
    arrow(ax, 28.8, 23.6, 33.6, 23.6)
    ax.text(31.2, 21.2, "9 tran-\nscripts", ha="center", va="center", fontsize=6.4, color=MUTED)

    # coordinator
    box(ax, 34.0, 3.0, 41.0, 35.4, fc=PANEL_BG, ec=LINE, r=1.0)
    ax.text(54.5, 35.9, "Coordinator (same model, two procedures)", ha="center", va="center", fontsize=8.5,
            weight="bold", color=INK)
    ax.text(54.5, 33.4, "A = Qwen3-8B or B = Ministral-3-8B · 3 samples each",
            ha="center", va="center", fontsize=6.4, color=MUTED)
    ax.text(36.0, 29.4, "Ledger first", ha="left", va="center", fontsize=7.6, weight="bold", color=INK)
    box(ax, 36.0, 19.6, 19.0, 8.0, fc="white",
        text='Turn 1: issue ledger (JSON)\n{"issues": [ … ]}\nempty list allowed', fs=6.6)
    arrow(ax, 55.4, 23.6, 58.6, 23.6)
    box(ax, 59.0, 19.6, 14.0, 8.0, fc="white", text="Turn 2: report\n≤ 120 words", fs=6.8)
    ax.text(36.0, 14.6, "No ledger", ha="left", va="center", fontsize=7.6, weight="bold", color=INK)
    box(ax, 59.0, 5.6, 14.0, 8.0, fc="white", text="Report\n≤ 120 words", fs=6.8)
    ax.text(47.5, 9.6, "the report is written\ndirectly from the transcripts", ha="center", va="center",
            fontsize=6.4, color=MUTED, linespacing=1.2)
    badge(ax, 55.0, 27.6, 1)

    # director
    box(ax, 84.0, 14.6, 14.8, 10.0, fc="white", ec=INK, lw=1.2, text="Director\nreads only\nthe report", fs=7.4)
    arrow(ax, 73.4, 23.6, 83.6, 20.8)
    arrow(ax, 73.4, 9.6, 83.6, 18.0)
    badge(ax, 78.6, 22.6, 2)
    badge(ax, 91.4, 26.4, 3)
    # key
    ax.text(77.0, 11.2, "Scored per injected failure:", ha="left", va="center", fontsize=6.5, color=INK, weight="bold")
    for i, t in enumerate(("written in the ledger?", "reaches the director?", "described as unresolved,\n"
                                                                             "with the right cause?")):
        yy = 8.6 - i * 2.5
        ax.add_patch(plt.Circle((78.0, yy), 0.9, fc=INK, ec=SURF, lw=1))
        ax.text(78.0, yy - 0.05, str(i + 1), ha="center", va="center", fontsize=6, color="white", weight="bold")
        ax.text(79.6, yy - (0.9 if i == 2 else 0), t, ha="left", va="center", fontsize=6.4, color=INK, linespacing=1.15)
    fig.savefig(out, dpi=250, facecolor=SURF)
    plt.close(fig)


# ---------------------------------------------------------------- Figure 2: funnel
def est(d: dict[str, Any] | None, key: str = "est") -> tuple[float, float, float] | None:
    if not d or d.get(key) is None:
        return None
    lo, hi = d.get("ci95") or (d[key], d[key])
    return d[key], lo, hi


def fig_funnel(R: dict, C: dict, E: dict, N: dict, out: Path) -> None:
    A, B = R["families"]["A"], R["families"]["B"]
    rd = C["relay_distortion"]
    Bn = N["B_end_to_end"]
    soft_excl = {"L/low": 0.57, "S/low": 0.73, "L/high": 0.06, "S/high": 0.30}  # deviations.md record, 7 Nov (post hoc)
    rows4 = [("1 failing · ledger first", "low", "L"), ("1 failing · no ledger", "low", "S"),
             ("3 failing · ledger first", "high", "L"), ("3 failing · no ledger", "high", "S")]
    P = {
        "a": ("a  Written in the ledger (family A)", "VALIDATED · judge-free count identical",
              [("1 of 9 failing", {"A": est(A["detection"]["lenient"]["low"])}),
               ("3 of 9 failing", {"A": est(A["detection"]["lenient"]["high"])})]),
        "b": ("b  Never reaches the director", "A: every absence hand-checked · B: judge only",
              [(lab, {"A": est(E[f"A_{st}_{arm}"]), "B": est(Bn[f"{st}_{arm}"])}) for lab, st, arm in rows4]),
        "c": ("c  Softened: called fixed, minor or in progress", "EXPLORATORY · share of named failures",
              [(lab, {"A": est(A["downgrade"][f"{arm}/{st}"]), "B": est(B["downgrade"][f"{arm}/{st}"])})
               for lab, st, arm in rows4]),
        "d": ("d  Cause flipped (test conflicts)", "EXPLORATORY · post hoc · worker blamed the test",
              [("Report blames\nonly the code", {"A": est(rd["A"], "rate"), "B": est(rd["B"], "rate")})]),
    }
    fig = plt.figure(figsize=(7.2, 4.6))
    gs = fig.add_gridspec(2, 2, height_ratios=[4, 4], hspace=0.62, wspace=0.62, left=0.17, right=0.97, top=0.86,
                          bottom=0.09)
    OFF = {"A": -0.19, "B": 0.19}
    for key, (r, c) in zip("abcd", ((0, 0), (0, 1), (1, 0), (1, 1))):
        title, sub, rows = P[key]
        ax = fig.add_subplot(gs[r, c])
        n = len(rows)
        for i, (lab, vals) in enumerate(rows):
            y = n - 1 - i
            for fam in ("A", "B"):
                v = vals.get(fam)
                if v is None:
                    continue
                e, lo, hi = v
                yy = y + (OFF[fam] if "B" in vals else 0)
                ax.plot([lo * 100, hi * 100], [yy, yy], color=COL[fam], lw=2, solid_capstyle="round", zorder=2)
                ax.plot(e * 100, yy, MARK[fam], ms=7, color=COL[fam], mec=SURF, mew=1.5, zorder=3)
                if e > 0.85:
                    ax.annotate(fmt(e), (min(lo, e) * 100, yy), xytext=(-6, 0), textcoords="offset points",
                                va="center", ha="right", fontsize=6.8, color=INK)
                else:
                    ax.annotate(fmt(e), (max(hi, e) * 100, yy), xytext=(5, 0), textcoords="offset points",
                                va="center", fontsize=6.8, color=INK)
            if key == "c":
                cond = ("L" if "ledger first" in lab else "S") + ("/low" if lab.startswith("1") else "/high")
                ax.plot(soft_excl[cond] * 100, y + OFF["A"], "o", ms=6, mfc=SURF, mec=COL["A"], mew=1.4, zorder=4)
        ax.set_yticks(range(n))
        ax.set_yticklabels([lab for lab, _ in rows][::-1], fontsize=7)
        pad = (4 - n) / 2 if key in "ad" else 0
        ax.set_ylim(-0.6 - pad, n - 0.4 + pad)
        ax.set_xlim(0, 100)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.set_xticklabels(["0", "25", "50", "75", "100%"], fontsize=7)
        ax.grid(axis="x", color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.tick_params(axis="y", length=0)
        ax.set_title(title, loc="left", fontsize=8.2, color=INK, pad=13, weight="bold", x=-0.02)
        ax.text(-0.02, 1.035, sub, transform=ax.transAxes, fontsize=6.6, color=MUTED, ha="left", va="bottom")
    handles = [plt.Line2D([], [], marker=MARK[f], color=COL[f], lw=2, ms=7, mec=SURF, label=NAME[f]) for f in "AB"]
    handles.append(plt.Line2D([], [], marker="o", ls="", ms=6, mfc=SURF, mec=COL["A"], mew=1.4,
                              label="A, softened excluding 'in progress' only"))
    fig.legend(handles=handles, loc="upper center", ncol=3, frameon=False, fontsize=7, bbox_to_anchor=(0.55, 0.995))
    fig.text(0.17, 0.012, "Lines: 95% cluster-bootstrap intervals over transcript sets. Family B's ledger failed two "
                          "validity gates, so panel a omits it.", fontsize=6.4, color=MUTED)
    fig.savefig(out, dpi=250, facecolor=SURF)
    plt.close(fig)


# ---------------------------------------------------------------- Figure 3: position (post hoc)
def fig_position(N: dict, out: Path) -> None:
    pos, bands = N["positions"], N["position_bands"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 2.35), gridspec_kw={"width_ratios": [1.45, 1], "wspace": 0.32})
    xs = list(range(1, 10))
    vals = [pos[str(p)]["rec"] / pos[str(p)]["n"] if pos[str(p)]["n"] else 0 for p in xs]
    a1.bar(xs, [v * 100 for v in vals], width=0.55, color=COL["A"], zorder=2)
    for p, v in zip(xs, vals):
        d = pos[str(p)]
        a1.text(p, v * 100 + 3, f"{d['rec']}/{d['n']}", ha="center", va="bottom", fontsize=6.6, color=INK)
    a1.set_xticks(xs)
    a1.set_xticklabels([f"{p}\nn={pos[str(p)]['sets']}" for p in xs],
                       fontsize=6.6)
    a1.set_ylim(0, 112)
    a1.set_yticks([0, 25, 50, 75, 100])
    a1.set_yticklabels(["0", "25", "50", "75", "100%"], fontsize=7)
    a1.set_xlabel("Failing worker's transcript position (of 9); n = sets, 3 samples each", fontsize=7, color=INK, labelpad=3)
    a1.set_title("a  Written in the ledger, by position", loc="left", fontsize=8.2, weight="bold", color=INK, pad=6)
    labels = {"early(1-3)": "positions 1–3", "mid(4-6)": "4–6", "late(7-9)": "7–9"}
    order = ["early(1-3)", "mid(4-6)", "late(7-9)"]
    w = 0.32
    for j, b in enumerate(order):
        d = bands[b]
        for k, (f, sty) in enumerate((("L_abs", "fill"), ("S_abs", "hollow"))):
            e, (lo, hi) = d[f]["est"], d[f]["ci95"]
            x = j + (k - 0.5) * (w + 0.06)
            if sty == "fill":
                a2.bar(x, e * 100, width=w, color=COL["A"], zorder=2)
            else:
                a2.bar(x, e * 100, width=w, color=SURF, ec=COL["A"], lw=1.3, zorder=2)
            a2.plot([x, x], [lo * 100, hi * 100], color=INK, lw=1, zorder=3)
            a2.text(x, hi * 100 + 2.5, f"{d[f]['k']}/{d[f]['n']}", ha="center", va="bottom", fontsize=6.4, color=INK)
    a2.set_xticks(range(3))
    a2.set_xticklabels([f"{labels[b]}\n{bands[b]['sets']} sets" for b in order], fontsize=6.6)
    a2.set_ylim(0, 100)
    a2.set_yticks([0, 25, 50, 75, 100])
    a2.set_yticklabels(["0", "25", "50", "75", "100%"], fontsize=7)
    a2.set_title("b  Absent from the report, by position band", loc="left", fontsize=8.2, weight="bold", color=INK,
                 pad=6)
    a2.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=COL["A"], label="ledger first"),
                       plt.Rectangle((0, 0), 1, 1, fc=SURF, ec=COL["A"], lw=1.3, label="no ledger")],
              loc="upper right", frameon=False, fontsize=6.8)
    for ax in (a1, a2):
        ax.grid(axis="y", color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.tick_params(axis="x", length=0)
    fig.savefig(out, dpi=250, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)


# ---------------------------------------------------------------- Figure E1: ledger as a detector (descriptive)
def fig_detector(N: dict, out: Path) -> None:
    D = N["detector"]
    rows = [("Lone failure written in the ledger\n(1 of 9 workers failing)", "recall_one"),
            ("Failures written in the ledger\n(3 of 9 workers failing)", "recall_three"),
            ("Approved changes flagged as issues", "au_flag"),
            ("Clean sets whose ledger claims a failure", "clean_false_alarm")]
    fig, ax = plt.subplots(figsize=(7.2, 2.2))
    for i, (lab, k) in enumerate(rows):
        y = len(rows) - 1 - i
        for fam, off in (("A", -0.17), ("B", 0.17)):
            d = D[fam][k]
            e, (lo, hi) = d["est"], d["ci95"]
            ax.plot([lo * 100, hi * 100], [y + off, y + off], color=COL[fam], lw=2, solid_capstyle="round", zorder=2)
            ax.plot(e * 100, y + off, MARK[fam], ms=7, color=COL[fam], mec=SURF, mew=1.5, zorder=3)
            ax.annotate(fmt(e), (max(hi, e) * 100, y + off), xytext=(5, 0), textcoords="offset points", va="center",
                        fontsize=6.8, color=INK)
    ax.axhline(1.5, color=GRID, lw=0.8)
    ax.text(101, 2.5, "higher is better", fontsize=6.4, color=MUTED, va="center", ha="left")
    ax.text(101, 0.5, "lower is better", fontsize=6.4, color=MUTED, va="center", ha="left")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows][::-1], fontsize=7)
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0", "25", "50", "75", "100%"], fontsize=7)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.legend(handles=[plt.Line2D([], [], marker=MARK[f], color=COL[f], lw=2, ms=7, mec=SURF, label=NAME[f])
                       for f in "AB"], loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False, fontsize=7)
    fig.savefig(out, dpi=250, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--outdir", type=Path, required=True)
    a = ap.parse_args()
    R = json.loads((a.repo / "results/analysis/results.json").read_text())
    C = json.loads((a.repo / "results/cause/cause_result.json").read_text())
    E = json.loads((a.repo / "results/posthoc/e1_result.json").read_text())
    N = json.loads((a.repo / "review/stage4_numbers.json").read_text())
    a.outdir.mkdir(exist_ok=True)
    fig_design(a.outdir / "fig1_design_v4.png")
    fig_funnel(R, C, E, N, a.outdir / "fig2_funnel_v4.png")
    fig_position(N, a.outdir / "fig3_position_v4.png")
    fig_detector(N, a.outdir / "figE1_detector_v4.png")
    print("wrote", *sorted(p.name for p in a.outdir.glob("fig*_v4.png")))


if __name__ == "__main__":
    main()
