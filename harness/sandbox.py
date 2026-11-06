"""Async wrapper that runs sandbox_runner.py in a subprocess with a wall-clock timeout."""
from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from common import REPO

RUNNER = REPO / "sandbox_runner.py"
VENDOR = REPO / "vendor_evalplus.py"


def unshare_available() -> bool:
    exe = shutil.which("unshare")
    if exe is None:
        return False
    r = subprocess.run([exe, "-rn", "true"], capture_output=True, timeout=10)
    return r.returncode == 0


class Sandbox:
    def __init__(self, wcfg: dict[str, Any], max_procs: int = 16) -> None:
        self.test_timeout_s = float(wcfg["test_timeout_s"])
        self.run_timeout_s = float(wcfg["run_timeout_s"])
        self.hidden_timeout_s = float(wcfg["hidden_input_timeout_s"])
        self.mem_mb = int(wcfg["sandbox_mem_mb"])
        mode = wcfg["use_unshare_net"]
        if mode == "auto":
            self.unshare = unshare_available()
        elif mode is True:
            if not unshare_available():
                raise RuntimeError("use_unshare_net: true but `unshare -rn` is not permitted here")
            self.unshare = True
        else:
            self.unshare = False
        self._sem = asyncio.Semaphore(max_procs)

    async def run(self, code: str, entry_point: str, tests: list[dict[str, str]],
                  hidden: dict[str, Any] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": code, "entry_point": entry_point, "tests": tests,
            "test_timeout_s": self.test_timeout_s, "mem_mb": self.mem_mb,
        }
        if hidden is not None:
            payload["hidden"] = {**hidden, "timeout_s": self.hidden_timeout_s, "vendor_path": str(VENDOR)}
        async with self._sem:
            with tempfile.TemporaryDirectory(prefix="ibnr_sbx_") as tmp:
                inp, outp = Path(tmp) / "in.json", Path(tmp) / "out.json"
                inp.write_text(json.dumps(payload), encoding="utf-8")
                cmd = [sys.executable, "-I", str(RUNNER), str(inp), str(outp)]
                if self.unshare:
                    cmd = ["unshare", "-rn"] + cmd
                proc = await asyncio.create_subprocess_exec(
                    *cmd, cwd=tmp, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                    env={"PATH": "/usr/bin:/bin", "HOME": tmp, "PYTHONHASHSEED": "0"})
                try:
                    _, err = await asyncio.wait_for(proc.communicate(), timeout=self.run_timeout_s)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                    return self._all_failed(tests, f"raised TimeoutError: test run exceeded "
                                                   f"{self.run_timeout_s:g} seconds", hidden, "wall_timeout")
                if not outp.exists():
                    tail = err.decode("utf-8", "replace")[-400:]
                    return self._all_failed(tests, "raised MemoryError: test process crashed"
                                            if "MemoryError" in tail else
                                            "raised RuntimeError: test process crashed", hidden,
                                            f"crash rc={proc.returncode}: {tail}")
                res = json.loads(outp.read_text(encoding="utf-8"))
                res["harness_error"] = None
                return res

    @staticmethod
    def _all_failed(tests: list[dict[str, str]], detail: str, hidden: dict[str, Any] | None,
                    why: str) -> dict[str, Any]:
        res: dict[str, Any] = {"load_error": detail, "harness_error": why,
                               "tests": [{"name": t["name"], "passed": False, "detail": detail} for t in tests]}
        if hidden is not None:
            n = len(hidden["inputs"])
            res["hidden_inputs"] = {"n": n, "n_failed": n, "failed_idx": list(range(n)),
                                    "examples": [], "canonical_errors": 0}
        return res
