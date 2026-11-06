"""Balancing tests for sets.py. Run: python -m pytest -q tests/"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sets import CELLS, Deck, dumps_sets, generate_sets  # noqa: E402

PIDS = [f"P{i:02d}" for i in range(1, 46)]
CFG = {"workers_per_set": 9, "n_clean": 30, "n_low": 40, "n_high": 40, "n_auth": 20}
SEED = 20261106


@pytest.fixture(scope="module")
def sets():
    return generate_sets(PIDS, CFG, SEED)


def by_stratum(sets, stratum):
    return [s for s in sets if s["stratum"] == stratum]


def fail_cells(s):
    return [w["cell"] for w in s["workers"] if w["cell"] in CELLS]


def test_stratum_counts(sets):
    assert len(sets) == 130
    assert Counter(s["stratum"] for s in sets) == {"clean": 30, "low": 40, "high": 40, "auth": 20}
    assert len({s["set_id"] for s in sets}) == 130


def test_total_failures(sets):
    assert sum(len(fail_cells(s)) for s in sets) == 160
    assert Counter(c for s in sets for c in fail_cells(s)) == {c: 40 for c in CELLS}


def test_clean_sets_have_no_failures(sets):
    for s in by_stratum(sets, "clean"):
        assert all(w["cell"] == "clean" for w in s["workers"])
        assert s["amd_id"] is None


def test_low_pressure_one_failure_ten_per_cell(sets):
    low = by_stratum(sets, "low")
    assert all(len(fail_cells(s)) == 1 for s in low)
    assert Counter(fail_cells(s)[0] for s in low) == {c: 10 for c in CELLS}


def test_high_pressure_three_distinct_cells_missing_rotated(sets):
    high = by_stratum(sets, "high")
    missing = Counter()
    for s in high:
        cells = fail_cells(s)
        assert len(cells) == 3 and len(set(cells)) == 3
        missing[(set(CELLS) - set(cells)).pop()] += 1
    assert missing == {c: 10 for c in CELLS}


def test_authorised_sets(sets):
    for s in by_stratum(sets, "auth"):
        cells = Counter(w["cell"] for w in s["workers"])
        assert cells == {"AU": 1, "clean": 8}
        assert s["amd_id"].startswith("AMD-") and len(s["amd_id"]) == 8
    assert all(s["amd_id"] is None for s in sets if s["stratum"] != "auth")


def test_workers_and_problems_unique_within_set(sets):
    for s in sets:
        assert [w["worker_id"] for w in s["workers"]] == [f"worker_{i}" for i in range(1, 10)]
        assert [w["position"] for w in s["workers"]] == list(range(9))
        pids = [w["problem_id"] for w in s["workers"]]
        assert len(set(pids)) == 9


def test_problem_used_at_most_once_per_failure_cell(sets):
    for cell in CELLS + ("AU",):
        used = Counter(w["problem_id"] for s in sets for w in s["workers"] if w["cell"] == cell)
        assert max(used.values()) == 1, cell


def test_clean_usage_balanced(sets):
    used = Counter(w["problem_id"] for s in sets for w in s["workers"] if w["cell"] == "clean")
    assert sum(used.values()) == 30 * 9 + 40 * 8 + 40 * 6 + 20 * 8  # 990
    assert set(used) == set(PIDS)
    assert max(used.values()) - min(used.values()) <= 3, used


def test_failure_positions_spread(sets):
    pos = Counter(w["position"] for s in sets for w in s["workers"] if w["cell"] != "clean")
    assert set(pos) == set(range(9))  # every slot hosts some failure
    assert max(pos.values()) <= 2.5 * min(pos.values())  # 180 failures+AU over 9 slots, loose bound


def test_failure_positions_not_constant_within_stratum(sets):
    for stratum in ("low", "high", "auth"):
        layouts = {tuple(w["position"] for w in s["workers"] if w["cell"] != "clean")
                   for s in by_stratum(sets, stratum)}
        assert len(layouts) > 5, stratum


def test_deterministic_and_seed_sensitive(sets):
    assert dumps_sets(generate_sets(PIDS, CFG, SEED)) == dumps_sets(sets)
    assert dumps_sets(generate_sets(PIDS, CFG, SEED + 1)) != dumps_sets(sets)


def test_set_seeds_unique(sets):
    assert len({s["seed"] for s in sets}) == 130


def test_deck_skips_excluded_and_cycles():
    import random
    d = Deck(["a", "b", "c"], random.Random(0))
    draws = [d.draw(set()) for _ in range(6)]
    assert Counter(draws) == {"a": 2, "b": 2, "c": 2}
    assert d.draw({"a", "b"}) == "c"
    with pytest.raises(ValueError):
        d.draw({"a", "b", "c"})


def test_rejects_unbalanceable_config():
    with pytest.raises(ValueError):
        generate_sets(PIDS, {**CFG, "n_low": 41}, SEED)
