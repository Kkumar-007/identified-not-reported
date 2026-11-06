"""Extract prompt blocks from prompts.md (v1) and render them with string.Template.

Each prompt is the first fenced ``text`` block under a heading ``### <ID> · v1``.
Blocks are written to prompts/v1/<ID>.txt plus a manifest of sha256 hashes.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from string import Template

from common import sha256_bytes

MODEL_FACING = [
    "W_SYS", "W_TASK", "W_RESULT", "W_INJ_DEV", "M_SYS", "M_PREFIX", "M_TRANSCRIPT",
    "L_LEDGER", "REPORT", "CAP", "STRESS", "FRAME_R", "FRAME_P", "AMENDMENT",
]
JUDGE = ["J_ITEM_SYS", "J_ITEM_USER", "J_OPT", "J_FALSE"]
OPTIONAL = ["W_INJ_AU"]  # exists only from v4; required when worker.au_cite_instruction is true

_HEADING = re.compile(r"^### ([A-Z][A-Z0-9_]*) · (v\d+)\b")
_FENCE_OPEN = re.compile(r"^(`{3,})text\s*$")

# M_TRANSCRIPT contains a literal "..." standing for the repeated turn pair, so it is rendered
# in code. This guard fails loudly if the block in prompts.md ever changes.
_M_TRANSCRIPT_EXPECTED = (
    '<worker id="${worker_id}" function="${function_name}">\n[${worker_id}]\n${worker_message}\n'
    "[test results]\n${harness_result}\n...\n[${worker_id}]\n${final_message}\n</worker>"
)


def extract_blocks(md_text: str, version: str) -> dict[str, str]:
    """For each block ID, the block at the highest version <= `version` (v2 run: v2 where it
    exists, otherwise v1)."""
    want = int(version.lstrip("v"))
    lines = md_text.splitlines()
    found: dict[str, tuple[int, str]] = {}
    i = 0
    while i < len(lines):
        m = _HEADING.match(lines[i])
        if not m:
            i += 1
            continue
        pid, ver = m.group(1), int(m.group(2).lstrip("v"))
        j = i + 1
        while j < len(lines) and not _FENCE_OPEN.match(lines[j]) and not lines[j].startswith("### "):
            j += 1
        if j >= len(lines) or lines[j].startswith("### "):
            i = j
            continue
        fence = _FENCE_OPEN.match(lines[j]).group(1)
        k = j + 1
        while k < len(lines) and lines[k].rstrip() != fence:
            k += 1
        if k >= len(lines):
            raise ValueError(f"unterminated block for {pid} v{ver}")
        body = "\n".join(lines[j + 1 : k])
        if ver <= want:
            if pid in found and found[pid][0] == ver:
                raise ValueError(f"duplicate block {pid} v{ver}")
            if pid not in found or ver > found[pid][0]:
                found[pid] = (ver, body)
        i = k + 1
    return {pid: body for pid, (_, body) in found.items()}


def block_versions(md_text: str, version: str) -> dict[str, int]:
    want = int(version.lstrip("v"))
    out: dict[str, int] = {}
    for line in md_text.splitlines():
        m = _HEADING.match(line)
        if m:
            v = int(m.group(2).lstrip("v"))
            if v <= want:
                out[m.group(1)] = max(v, out.get(m.group(1), 0))
    return out


class Prompts:
    def __init__(self, prompts_md: str | Path, out_dir: str | Path, version: str = "v1") -> None:
        text = Path(prompts_md).read_text(encoding="utf-8")
        self.version = version
        self.md_sha256 = sha256_bytes(text.encode("utf-8"))
        self.blocks = extract_blocks(text, version)
        self.versions = block_versions(text, version)
        missing = [p for p in MODEL_FACING + JUDGE if p not in self.blocks]
        if missing:
            raise ValueError(f"prompts.md is missing blocks: {missing}")
        if self.blocks["M_TRANSCRIPT"] != _M_TRANSCRIPT_EXPECTED:
            raise ValueError("M_TRANSCRIPT block changed; update the renderer in prompts.py")
        self._write(Path(out_dir))

    def _write(self, out_dir: Path) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest = {"prompts_md_sha256": self.md_sha256, "version": self.version,
                    "block_versions": self.versions, "blocks": {}}
        for pid, body in sorted(self.blocks.items()):
            (out_dir / f"{pid}.txt").write_text(body, encoding="utf-8")
            manifest["blocks"][pid] = sha256_bytes(body.encode("utf-8"))
        (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    def raw(self, pid: str) -> str:
        return self.blocks[pid]

    def render(self, pid: str, **kw: str) -> str:
        return Template(self.blocks[pid]).substitute(**kw)

    def render_transcript(
        self, worker_id: str, function_name: str, turns: list[tuple[str, str]], final_message: str
    ) -> str:
        parts = [f'<worker id="{worker_id}" function="{function_name}">']
        for worker_message, harness_result in turns:
            parts += [f"[{worker_id}]", worker_message, "[test results]", harness_result]
        parts += [f"[{worker_id}]", final_message, "</worker>"]
        return "\n".join(parts)


def check_word_caps(p: Prompts, word_cap: int, stress_cap: int) -> None:
    for pid, cap in (("REPORT", word_cap), ("CAP", word_cap), ("FRAME_R", word_cap),
                     ("FRAME_P", word_cap), ("STRESS", stress_cap)):
        if f"at most {cap} words" not in p.raw(pid):
            raise ValueError(f"{pid} does not say 'at most {cap} words'; config and prompts disagree")
    rep = p.raw("REPORT")
    for pid in ("FRAME_R", "FRAME_P"):
        if not p.raw(pid).endswith(" " + rep):
            raise ValueError(f"{pid} is not '<sentence> ' + REPORT")
    if not p.raw("CAP").startswith(rep + " "):
        raise ValueError("CAP is not REPORT + ' ' + <sentence>")


def framing_sentence(p: Prompts, pid: str) -> str:
    return p.raw(pid)[: -(len(p.raw("REPORT")) + 1)]


def check_test_runs(p: Prompts, max_test_runs: int) -> None:
    """W_SYS must state the same run budget the harness enforces."""
    phrase = "You can run the tests once." if max_test_runs == 1 else f"at most {max_test_runs} times"
    if phrase not in p.raw("W_SYS"):
        raise ValueError(f"W_SYS does not say {phrase!r} but worker.max_test_runs = {max_test_runs}")
