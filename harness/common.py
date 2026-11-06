"""Shared helpers: config loading, seed derivation, hashing."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parent


def _expand(obj: Any) -> Any:
    if isinstance(obj, str):
        return os.path.expandvars(obj)
    if isinstance(obj, dict):
        return {k: _expand(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand(v) for v in obj]
    return obj


def apply_override(cfg: dict[str, Any], spec: str) -> None:
    """`a.b.c=<yaml value>`, e.g. worker.enable_thinking=true or data.stage_b_pool=[R01,R03]."""
    if "=" not in spec:
        raise ValueError(f"override must be key=value: {spec!r}")
    key, raw = spec.split("=", 1)
    parts = key.strip().split(".")
    node = cfg
    for p in parts[:-1]:
        if p not in node or not isinstance(node[p], dict):
            raise KeyError(f"override path {key!r}: no section {p!r}")
        node = node[p]
    if parts[-1] not in node:
        raise KeyError(f"override path {key!r}: unknown key {parts[-1]!r}")
    node[parts[-1]] = yaml.safe_load(raw)


# Worker settings each prompt version requires (prompts.md); a mismatch is a config error.
VERSION_SETTINGS: dict[str, dict[str, Any]] = {
    "v1": {"injection_placement": "system", "de_fill_rule": "csv", "max_test_runs": 4,
           "au_spec_omits_requirement": False, "au_cite_instruction": False},
    "v2": {"injection_placement": "task", "de_fill_rule": "requirement", "max_test_runs": 4,
           "au_spec_omits_requirement": False, "au_cite_instruction": False},
    "v3": {"injection_placement": "task", "de_fill_rule": "requirement", "max_test_runs": 1,
           "au_spec_omits_requirement": True, "au_cite_instruction": False},
    "v4": {"injection_placement": "task", "de_fill_rule": "requirement", "max_test_runs": 1,
           "au_spec_omits_requirement": True, "au_cite_instruction": True},
}


def check_version_settings(cfg: dict[str, Any]) -> None:
    want = VERSION_SETTINGS.get(cfg["prompts_version"])
    if want is None:
        raise ValueError(f"unknown prompts_version {cfg['prompts_version']!r}")
    bad = {k: (cfg["worker"].get(k), v) for k, v in want.items() if cfg["worker"].get(k) != v}
    if bad:
        raise ValueError(f"worker settings do not match prompts {cfg['prompts_version']}: "
                         f"{ {k: f'{a!r} (needs {b!r})' for k, (a, b) in bad.items()} }")


def load_config(path: str | Path = REPO / "config.yaml", overrides: list[str] | None = None) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        cfg = _expand(yaml.safe_load(f))
    for spec in overrides or []:
        apply_override(cfg, spec)
    cfg["paths"]["prompts_dir"] = f"prompts/{cfg['prompts_version']}"
    check_version_settings(cfg)
    for key, rel in cfg["paths"].items():
        if "$" in rel:
            if key == "log_dir":  # may be supplied with --log-dir instead
                cfg["paths"][key] = None
                continue
            raise ValueError(f"paths.{key} has an unset environment variable: {rel!r}")
        p = Path(rel)
        cfg["paths"][key] = str(p if p.is_absolute() else REPO / p)
    return cfg


def derive_seed(*parts: Any) -> int:
    """Deterministic 31-bit seed from any sequence of parts (stable across Python versions)."""
    h = hashlib.sha256("\x1f".join(str(p) for p in parts).encode("utf-8")).hexdigest()
    return int(h[:8], 16) & 0x7FFFFFFF


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str | Path) -> str:
    with open(path, "rb") as f:
        return sha256_bytes(f.read())


def messages_hash(messages: list[dict[str, str]]) -> str:
    """prompt_hash = sha256 of the fully rendered message list (prompts.md conventions)."""
    canon = json.dumps(messages, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return sha256_bytes(canon.encode("utf-8"))
