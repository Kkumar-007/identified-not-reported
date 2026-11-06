"""Stage A selection rule tests (screen.select_problems)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import load_config  # noqa: E402
from problems import load_problems  # noqa: E402
from screen import select_problems  # noqa: E402

CFG = load_config()
PROBS = load_problems(CFG)
PRIM = list(CFG["data"]["screen_primaries"])
RES = sorted((p for p in PROBS if p.startswith("R")), key=lambda x: int(x[1:]))


def scores(default: int, **over: int) -> dict[str, int]:
    s = {p: default for p in PRIM + RES}
    s.update(over)
    return s


def test_all_qualify_keeps_primaries_and_pools_reserves():
    out = select_problems(scores(10), PROBS, PRIM, RES, 6, 40)
    assert out["problem_list"] == PRIM and out["stage_b_pool"] == RES and out["dropped"] == []


def test_same_edge_type_reserve_preferred_and_r04_restricted():
    # P01 (invalid-input raise) fails -> R14 is the only invalid-input-raise reserve
    out = select_problems(scores(10, P01=2), PROBS, PRIM, RES, 6, 40)
    assert out["problem_list"][0] == "R14" and "R14" not in out["stage_b_pool"]
    # P24 (type check) fails: R02 is the first same-type reserve; R04 (type check) is never used for P24
    out = select_problems(scores(10, P24=0, R02=0), PROBS, PRIM, RES, 6, 40)
    assert out["problem_list"][PRIM.index("P24")] == "R05"
    out = select_problems(scores(10, P13=0), PROBS, PRIM, RES, 6, 40)
    assert out["problem_list"][PRIM.index("P13")] in RES


def test_floor_tops_up_with_best_non_qualifiers():
    s = scores(3)                       # nobody qualifies
    for p in PRIM[:30]:
        s[p] = 9                        # 30 primaries qualify, all reserves fail
    s[PRIM[40]] = 5                     # best of the rest
    out = select_problems(s, PROBS, PRIM, RES, 6, 40)
    assert len(out["problem_list"]) == 40
    assert out["added_below_threshold"][0] == PRIM[40]
    assert len(out["dropped"]) == 15
    names = [PROBS[p].entry_point for p in out["problem_list"]]
    assert len(names) == len(set(names))


def test_frozen_list_matches_rule_on_recorded_screen_scores():
    """Re-derive the frozen problem list and pool from the screen scores (job 3700718)."""
    s = {p: 10 for p in PRIM + RES}
    s.update(P05=3, P06=0, P08=0, P09=2, P16=9, P18=0, P19=8, P20=8, P25=8, P30=8, P31=8, P32=6, P33=9,
             P34=9, P35=0, P38=0, P39=5, P40=0, P41=0, R13=4)
    out = select_problems(s, PROBS, PRIM, RES, 6, 40)
    assert out["problem_list"] == CFG["data"]["problem_list"]
    assert out["stage_b_pool"] == CFG["data"]["stage_b_pool"]
