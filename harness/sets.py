"""Deterministic generation of the 130 transcript-set specs.

Strata: 30 clean (C01-C30), 40 low-pressure (L01-L40, one failure, 10 per cell),
40 high-pressure (H01-H40, three cells each; the missing cell rotates so each cell is
missing in exactly 10 sets), 20 authorised-change (A01-A20, one AU worker).

Balancing: each failure cell (and AU) draws problems from its own shuffled deck, so a problem
is used at most once per cell while the deck lasts (40 draws from 45 problems). Clean
positions draw from a cycling clean deck. No problem appears twice in a set. Failure positions
are sampled per set, and the problem-to-worker mapping is random, so worker order is shuffled.

Usage: python sets.py [--config config.yaml]  -> writes paths.sets_file and prints its sha256.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

from common import derive_seed, load_config, sha256_bytes

CELLS = ("AC", "AE", "DC", "DE")


class Deck:
    """Shuffled cycling deck; draw() skips cards in `exclude` without discarding them."""

    def __init__(self, items: list[str], rng: random.Random) -> None:
        self._items = list(items)
        self._rng = rng
        self._cards: list[str] = []
        self._refill()

    def _refill(self) -> None:
        batch = list(self._items)
        self._rng.shuffle(batch)
        self._cards.extend(batch)

    def draw(self, exclude: set[str]) -> str:
        if len(exclude) >= len(self._items):
            raise ValueError("cannot draw: every item is excluded")
        while True:
            for i, card in enumerate(self._cards):
                if card not in exclude:
                    return self._cards.pop(i)
            self._refill()


def _stratum_plan(n_clean: int, n_low: int, n_high: int, n_auth: int,
                  rng: random.Random) -> list[tuple[str, str, list[str]]]:
    if n_low % len(CELLS) or n_high % len(CELLS):
        raise ValueError("n_low and n_high must be multiples of 4 for exact cell balance")
    plan: list[tuple[str, str, list[str]]] = []
    plan += [(f"C{i + 1:02d}", "clean", []) for i in range(n_clean)]
    low_cells = [CELLS[i % 4] for i in range(n_low)]
    rng.shuffle(low_cells)
    plan += [(f"L{i + 1:02d}", "low", [c]) for i, c in enumerate(low_cells)]
    missing = [CELLS[i % 4] for i in range(n_high)]
    rng.shuffle(missing)
    plan += [(f"H{i + 1:02d}", "high", [c for c in CELLS if c != m]) for i, m in enumerate(missing)]
    plan += [(f"A{i + 1:02d}", "auth", ["AU"]) for i in range(n_auth)]
    return plan


def generate_sets(problem_ids: list[str], set_cfg: dict[str, Any], master_seed: int) -> list[dict[str, Any]]:
    k = set_cfg["workers_per_set"]
    if len(problem_ids) < k:
        raise ValueError("fewer problems than workers per set")
    rng = random.Random(derive_seed(master_seed, "sets"))
    plan = _stratum_plan(set_cfg["n_clean"], set_cfg["n_low"], set_cfg["n_high"], set_cfg["n_auth"], rng)
    decks = {c: Deck(problem_ids, rng) for c in CELLS + ("AU", "clean")}
    # Process sets in a shuffled order so deck position is not tied to stratum.
    order = list(range(len(plan)))
    rng.shuffle(order)
    built: dict[int, dict[str, Any]] = {}
    for idx in order:
        set_id, stratum, cells = plan[idx]
        set_seed = derive_seed(master_seed, "set", set_id)
        positions = rng.sample(range(k), len(cells))
        slot_cell = {pos: cell for pos, cell in zip(positions, cells)}
        used: set[str] = set()
        slot_problem: dict[int, str] = {}
        for pos in sorted(slot_cell, key=lambda p: CELLS.index(slot_cell[p]) if slot_cell[p] in CELLS else 9):
            pid = decks[slot_cell[pos]].draw(used)
            used.add(pid)
            slot_problem[pos] = pid
        for pos in range(k):
            if pos not in slot_problem:
                slot_cell[pos] = "clean"
                pid = decks["clean"].draw(used)
                used.add(pid)
                slot_problem[pos] = pid
        workers = [
            {"worker_id": f"worker_{pos + 1}", "position": pos, "problem_id": slot_problem[pos],
             "cell": slot_cell[pos]}
            for pos in range(k)
        ]
        rec: dict[str, Any] = {"set_id": set_id, "stratum": stratum, "seed": set_seed,
                               "master_seed": master_seed, "workers": workers}
        rec["amd_id"] = f"AMD-{set_seed % 10000:04d}" if stratum == "auth" else None
        built[idx] = rec
    return [built[i] for i in range(len(plan))]


def dumps_sets(sets: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(s, sort_keys=True, ensure_ascii=False) + "\n" for s in sets)


def load_sets(path: str | Path) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--force", action="store_true", help="overwrite an existing sets file")
    args = ap.parse_args()
    cfg = load_config(args.config)
    sets = generate_sets(cfg["data"]["problem_list"], cfg["sets"], cfg["seeds"]["master_seed"])
    text = dumps_sets(sets)
    out = Path(cfg["paths"]["sets_file"])
    if out.exists() and out.read_text(encoding="utf-8") != text and not args.force:
        raise SystemExit(f"{out} exists with different content; pass --force to overwrite")
    out.write_text(text, encoding="utf-8")
    counts: dict[str, int] = {}
    for s in sets:
        counts[s["stratum"]] = counts.get(s["stratum"], 0) + 1
    n_fail = sum(w["cell"] in CELLS for s in sets for w in s["workers"])
    print(f"wrote {len(sets)} sets {counts}, {n_fail} injected failures -> {out}")
    print(f"sha256 {sha256_bytes(text.encode('utf-8'))}")


if __name__ == "__main__":
    main()
