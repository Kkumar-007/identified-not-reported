"""Problem table: problems.csv (+ problems_check.csv entry points) joined with pinned MBPP+ v0.2.0."""
from __future__ import annotations

import csv
import gzip
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from common import sha256_file

CELLS_FAIL = ("AC", "AE", "DC", "DE")
ALL_CELLS = ("clean",) + CELLS_FAIL + ("AU",)


@dataclass(frozen=True)
class Problem:
    id: str
    source_id: str
    entry_point: str
    edge_type: str
    spec_text: str
    edge_requirement: str
    edge_test_1: str
    edge_test_2: str
    core_conflict_test: str
    edge_conflict_test: str
    core_deviation: str
    edge_deviation: str
    mbpp_asserts: tuple[str, ...]
    canonical_solution: str
    hidden_inputs: list[Any] = field(repr=False, hash=False, compare=False)

    # ---- W_INJ_DEV fill rules (prompts.md §1.3/1.4): only the first character is lower-cased.
    def dev_behaviour(self, cell: str, de_rule: str = "csv") -> str:
        if cell == "DE" and de_rule == "requirement":  # W_INJ_DEV v2 fill rule
            return f'does not implement the requirement "{self.edge_requirement}"'
        if cell == "DC":
            marker = " (stated reason:"
            if marker not in self.core_deviation:
                raise ValueError(f"{self.id}: core_deviation has no stated reason")
            return lower_first(self.core_deviation.split(marker, 1)[0])
        if cell == "DE":
            suffix = " to save time."
            if not self.edge_deviation.endswith(suffix):
                raise ValueError(f"{self.id}: edge_deviation does not end with {suffix!r}")
            return lower_first(self.edge_deviation[: -len(suffix)])
        raise ValueError(cell)

    def dev_reason(self, cell: str) -> str:
        if cell == "DC":
            inner = self.core_deviation.split("(stated reason: ", 1)[1]
            if not inner.endswith(")."):
                raise ValueError(f"{self.id}: core_deviation reason not closed by ').'")
            return inner[:-2]
        if cell == "DE":
            return "to save time"
        raise ValueError(cell)


def lower_first(s: str) -> str:
    return s[:1].lower() + s[1:]


def _read_csv(path: str) -> list[dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_problems(cfg: dict[str, Any]) -> dict[str, Problem]:
    paths = cfg["paths"]
    got = sha256_file(paths["mbppplus"])
    if got != cfg["data"]["mbppplus_sha256"]:
        raise ValueError(f"MBPP+ sha256 mismatch: {got}")
    with gzip.open(paths["mbppplus"], "rt", encoding="utf-8") as f:
        mbpp = {r["task_id"]: r for r in map(json.loads, f)}
    check = {r["id"]: r for r in _read_csv(paths["problems_check_csv"])}
    out: dict[str, Problem] = {}
    for r in _read_csv(paths["problems_csv"]):
        m = mbpp[r["source_id"]]
        c = check[r["id"]]
        if c["entry_point"] != m["entry_point"]:
            raise ValueError(f"{r['id']}: entry point mismatch")
        asserts = tuple(l.strip() for l in m["assertion"].splitlines() if l.strip())
        if len(asserts) != int(c["n_visible_mbpp_asserts"]):
            raise ValueError(f"{r['id']}: assert count {len(asserts)} != problems_check")
        hidden = list(m["base_input"]) + list(m["plus_input"])
        if len(hidden) != int(c["n_hidden_inputs"]):
            raise ValueError(f"{r['id']}: hidden input count mismatch")
        out[r["id"]] = Problem(
            id=r["id"], source_id=r["source_id"], entry_point=m["entry_point"],
            edge_type=c["edge_type"], spec_text=r["spec_text"],
            edge_requirement=r["edge_requirement"], edge_test_1=r["edge_test_1"],
            edge_test_2=r["edge_test_2"], core_conflict_test=r["core_conflict_test"],
            edge_conflict_test=r["edge_conflict_test"], core_deviation=r["core_deviation"],
            edge_deviation=r["edge_deviation"], mbpp_asserts=asserts,
            canonical_solution=m["canonical_solution"], hidden_inputs=hidden,
        )
    return out
