"""Append-only JSONL logs with resume keys, plus a content-addressed prompt store.

Every model call is one row in calls.jsonl with at least
(set_id, worker_id, arm, sample, family, framing, prompt_hash, output, model, seed, timestamp).
The resume key adds stage, turn and try. On restart a call whose key is already logged is
replayed from the log instead of re-sent, provided its prompt_hash matches; a mismatch raises.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# problem_id is in the key because a stage-B reserve reuses the worker_id and try numbers.
CALL_KEY = ("stage", "set_id", "worker_id", "problem_id", "arm", "sample", "family", "framing",
            "turn", "try")
CALL_REQUIRED = ("set_id", "worker_id", "arm", "sample", "family", "framing", "prompt_hash",
                 "output", "model", "seed", "timestamp")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class ResumeMismatch(RuntimeError):
    pass


class JsonlLog:
    """One JSONL file indexed by a tuple of key fields. Duplicate keys on load are an error."""

    def __init__(self, path: str | Path, key_fields: Iterable[str]) -> None:
        self.path = Path(path)
        self.key_fields = tuple(key_fields)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._index: dict[tuple[Any, ...], dict[str, Any]] = {}
        self._load()

    def key(self, row: dict[str, Any]) -> tuple[Any, ...]:
        missing = [k for k in self.key_fields if k not in row]
        if missing:
            raise KeyError(f"{self.path.name}: row lacks key fields {missing}")
        return tuple(row[k] for k in self.key_fields)

    def _load(self) -> None:
        if not self.path.exists():
            return
        raw = self.path.read_bytes()
        lines = raw.split(b"\n")
        good_bytes = 0
        for i, line in enumerate(lines):
            if not line.strip():
                good_bytes += len(line) + 1
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                if i == len(lines) - 1:  # torn final write from a killed job
                    print(f"[log] {self.path.name}: dropping torn final line ({len(line)} bytes)",
                          file=sys.stderr)
                    with open(self.path, "r+b") as f:
                        f.truncate(min(good_bytes, len(raw)))
                    break
                raise
            k = self.key(row)
            if k in self._index:
                raise ValueError(f"{self.path.name}: duplicate key {k} at line {i + 1}")
            self._index[k] = row
            good_bytes += len(line) + 1

    def get(self, key: tuple[Any, ...]) -> dict[str, Any] | None:
        return self._index.get(key)

    def __contains__(self, key: tuple[Any, ...]) -> bool:
        return key in self._index

    def rows(self) -> list[dict[str, Any]]:
        return list(self._index.values())

    def append(self, row: dict[str, Any]) -> None:
        k = self.key(row)
        if k in self._index:
            raise ValueError(f"{self.path.name}: key {k} already logged")
        line = json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
        self._index[k] = row


class CallLog(JsonlLog):
    def __init__(self, path: str | Path) -> None:
        super().__init__(path, CALL_KEY)

    def append(self, row: dict[str, Any]) -> None:
        missing = [k for k in CALL_REQUIRED if k not in row]
        if missing:
            raise KeyError(f"call row lacks required fields {missing}")
        super().append(row)

    def replay(self, key_row: dict[str, Any], prompt_hash: str) -> dict[str, Any] | None:
        hit = self.get(self.key(key_row))
        if hit is None:
            return None
        if hit["prompt_hash"] != prompt_hash:
            raise ResumeMismatch(f"logged call {self.key(key_row)} has prompt_hash "
                                 f"{hit['prompt_hash'][:12]} but the rendered prompt is {prompt_hash[:12]}")
        return hit


class PromptStore:
    """Rendered message lists, one file per prompt_hash, written once."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, prompt_hash: str, messages: list[dict[str, str]]) -> None:
        p = self.root / f"{prompt_hash}.json"
        if not p.exists():
            tmp = p.with_suffix(".tmp")
            tmp.write_text(json.dumps(messages, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, p)


class Logs:
    """All logs for one run directory."""

    def __init__(self, log_dir: str | Path) -> None:
        d = Path(log_dir)
        d.mkdir(parents=True, exist_ok=True)
        self.dir = d
        self.calls = CallLog(d / "calls.jsonl")
        self.episodes = JsonlLog(d / "episodes.jsonl", ("set_id", "worker_id", "problem_id", "try"))
        self.workers_final = JsonlLog(d / "workers_final.jsonl", ("set_id",))
        self.swaps = JsonlLog(d / "swaps.jsonl", ("stage", "set_id", "position", "seq"))
        self.manager_outputs = JsonlLog(d / "manager_outputs.jsonl",
                                        ("set_id", "family", "arm", "framing", "sample"))
        self.manifest = JsonlLog(d / "manifest.jsonl", ("run_id",))
        self.prompts = PromptStore(d / "prompts")
