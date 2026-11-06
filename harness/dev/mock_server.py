"""DEV ONLY. A scripted stand-in for vLLM's OpenAI-compatible server, for testing harness plumbing
without a GPU. Its outputs are NOT model behaviour and must never enter an analysis. Every
response carries model = "MOCK::<id>" so mock rows are unmistakable in the logs.

Scripted worker: turn 1 sends code; turn 2 sends a final message whose status line echoes the
last test results. Code per cell (inferred from the prompt the way a model would see it):
  - deviation cells / authorised change: the MBPP+ canonical solution (it lacks the edge rule);
  - DC additionally overrides the core-conflict call, so a core assert fails;
  - everything else: canonical + hard-coded edge behaviour from the two edge tests.
Scripted manager: ledger = one entry per worker whose status line lists failing tests;
report = one sentence per such worker, cut to the word cap named in the prompt.

  python dev/mock_server.py --port 8000 --model Qwen/Qwen3-8B
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import load_config  # noqa: E402
from problems import Problem, load_problems  # noqa: E402

STATUS_RE = re.compile(r"Final status: passing (\d+)/(\d+); failing: ([^;]+); deviations: (.+)")
RAN_RE = re.compile(r"Ran (\d+) tests: (\d+) passed, (\d+) failed\.")


def _override(test_src: str, entry: str) -> tuple[str, str, str] | None:
    node = ast.parse(test_src).body[0]
    if isinstance(node, ast.With):
        call, kind, val = node.body[0].value, "raise", ast.unparse(node.items[0].context_expr.args[0])
    elif isinstance(node, ast.Assert) and isinstance(node.test, ast.Compare) \
            and isinstance(node.test.ops[0], ast.Eq):
        call, kind, val = node.test.left, "return", ast.unparse(node.test.comparators[0])
    else:
        return None
    if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == entry) \
            or call.keywords or any(isinstance(n, (ast.GeneratorExp, ast.Call)) for a in call.args for n in ast.walk(a)):
        return None
    return "(" + "".join(ast.unparse(a) + ", " for a in call.args) + ")", kind, val


# Edge rules the generic override cannot express (the expected value is not the call's return).
HAND_WRITTEN = {
    "dict_filter": "def dict_filter(dict1, n):\n"
                   "    kept = [(k, v) for k, v in dict1.items() if v >= n]\n"
                   "    return dict(sorted(kept, key=lambda kv: kv[1], reverse=True))\n",
}


def oracle_code(p: Problem, tests: list[str]) -> str:
    if p.entry_point in HAND_WRITTEN and tests and p.core_conflict_test not in tests:
        return HAND_WRITTEN[p.entry_point]
    rows = [o for o in (_override(t, p.entry_point) for t in tests) if o is not None]
    ov = ",\n    ".join(f"({a}, {k!r}, {v})" for a, k, v in rows)
    return (f"{p.canonical_solution.strip()}\n\n_canon = {p.entry_point}\n_ov = [\n    {ov}\n]\n\n"
            f"def {p.entry_point}(*a, **k):\n    for args, kind, val in _ov:\n"
            f"        if not k and list(a) == list(args):\n"
            f"            if kind == 'raise':\n                raise val('invalid input')\n"
            f"            return val\n    return _canon(*a, **k)\n")


class Mock:
    def __init__(self, model: str) -> None:
        cfg = load_config()
        self.model = model
        probs = sorted(load_problems(cfg).values(), key=lambda p: p.id, reverse=True)
        self.by_entry = {p.entry_point: p for p in probs}  # P wins over R on a name clash (remove_odd)

    def worker(self, msgs: list[dict[str, str]]) -> str:
        system, task = msgs[0]["content"], msgs[1]["content"]
        p = self.by_entry[re.search(r"^Function: (\S+)", task, re.M).group(1)]
        dev = re.search(r"write your function so that it (.*?)\. Your reason: (.*?)\. (?:Keep|Some)", system + "\n" + task)
        amd = re.search(r"Amendment (AMD-\d{4})", task)
        if len(msgs) == 2:
            if dev or amd:
                tests = [p.core_conflict_test] if dev and dev.group(2) != "to save time" else []
                code = oracle_code(p, tests) if tests else p.canonical_solution.strip() + "\n"
            else:
                code = oracle_code(p, [p.edge_test_1, p.edge_test_2])
            return f"Here is my implementation.\n\n```python\n{code}```"
        last = msgs[-1]["content"]
        n, ok, _ = map(int, RAN_RE.search(last).groups())
        failing = re.findall(r"^FAILED (test_\d+):", last, re.M)
        deviations = "none"
        if dev:
            deviations = f"it {dev.group(1)}, my own decision, {dev.group(2)}"
        elif amd:
            deviations = f"the withdrawn requirement is not implemented, per Amendment {amd.group(1)}"
        note = f"{', '.join(failing)} still fail." if failing else "All acceptance tests pass."
        return (f"I implemented {p.entry_point}. {note}\n\nFinal status: passing {ok}/{n}; "
                f"failing: {', '.join(failing) or 'none'}; deviations: {deviations}")

    @staticmethod
    def _failing_workers(user: str) -> list[tuple[str, str, str]]:
        out = []
        for wid, fn, body in re.findall(r'<worker id="(worker_\d)" function="(\w+)">(.*?)</worker>', user, re.S):
            m = list(STATUS_RE.finditer(body))
            if m and m[-1].group(3).strip() != "none":
                out.append((wid, fn, m[-1].group(0)))
        return out

    def ledger(self, msgs: list[dict[str, str]]) -> str:
        issues = [{"worker_id": w, "function": f, "requirement": "its acceptance tests",
                   "evidence_quote": q, "severity": "high"} for w, f, q in self._failing_workers(msgs[1]["content"])]
        return json.dumps({"issues": issues})

    def report(self, msgs: list[dict[str, str]]) -> str:
        cap = int(re.search(r"at most (\d+) words", msgs[-1]["content"]).group(1))
        fails = self._failing_workers(msgs[1]["content"])
        words = (f"{9 - len(fails)} of 9 functions pass their tests. " + " ".join(
            f"{w} ({f}) has failing tests: {q.split('failing: ')[1].split(';')[0]}." for w, f, q in fails)).split()
        return " ".join(words[:cap])

    def complete(self, body: dict[str, Any]) -> str:
        msgs = body["messages"]
        if body.get("response_format"):
            return self.ledger(msgs)
        if msgs[0]["content"].startswith("You lead a team"):
            return self.report(msgs)
        return self.worker(msgs)


def make_handler(mock: Mock) -> type[BaseHTTPRequestHandler]:
    class H(BaseHTTPRequestHandler):
        def log_message(self, *_a: Any) -> None:
            return

        def _send(self, obj: dict[str, Any]) -> None:
            data = json.dumps(obj).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            if self.path.rstrip("/") in ("/v1/models", "/health"):
                self._send({"object": "list", "data": [{"id": mock.model, "object": "model"}]})
            else:
                self.send_error(404)

        def do_POST(self) -> None:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path == "/tokenize":
                self._send({"count": len(re.findall(r"\w+|[^\w\s]", body["prompt"]))})
                return
            if self.path != "/v1/chat/completions":
                self.send_error(404)
                return
            text = mock.complete(body)
            n_in = sum(len(m["content"]) for m in body["messages"]) // 4
            self._send({"id": "mock", "object": "chat.completion", "created": 0, "model": f"MOCK::{mock.model}",
                        "choices": [{"index": 0, "finish_reason": "stop",
                                     "message": {"role": "assistant", "content": text}}],
                        "usage": {"prompt_tokens": n_in, "completion_tokens": len(text) // 4,
                                  "total_tokens": n_in + len(text) // 4}})
    return H


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--model", required=True)
    a = ap.parse_args()
    ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(Mock(a.model))).serve_forever()


if __name__ == "__main__":
    main()
