"""Executed in a subprocess by sandbox.py:  python -I sandbox_runner.py <in.json> <out.json>

Runs one worker function against a list of test lines and, optionally, against MBPP+ hidden
inputs compared with the canonical solution (evalplus semantics: exact ==, or float closeness
with atol 1e-6 / rtol 1e-7 when the expected output is a float or a list/tuple of floats).

This is a hygiene sandbox, not a security boundary: resource limits, a per-call timer, a
temporary cwd, and network/process calls stubbed out. sandbox.py adds `unshare -rn` when the
kernel allows it. The threat model is an 8B model writing stdlib code, not an adversary.
"""
from __future__ import annotations

import ast
import contextlib
import copy
import importlib.util
import io
import json
import math
import resource
import signal
import sys
from typing import Any

REPR_MAX = 200


class _Timeout(Exception):
    pass


def _alarm(_sig: int, _frame: Any) -> None:
    raise _Timeout()


@contextlib.contextmanager
def time_limit(seconds: float):
    signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


@contextlib.contextmanager
def quiet():
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        yield


def _blocked(*_a: Any, **_k: Any) -> Any:
    raise PermissionError("network and process access are disabled in the test harness")


def harden(mem_mb: int) -> None:
    lim = mem_mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (lim, lim))
    resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))
    import os
    import socket
    import subprocess
    for name in ("socket", "create_connection", "socketpair", "getaddrinfo", "create_server"):
        setattr(socket, name, _blocked)
    for name in ("system", "popen", "fork", "forkpty", "execv", "execve", "execvp", "spawnv", "kill"):
        if hasattr(os, name):
            setattr(os, name, _blocked)
    subprocess.Popen = _blocked  # type: ignore[assignment,misc]
    subprocess.run = _blocked  # type: ignore[assignment]


def short_repr(x: Any) -> str:
    try:
        r = repr(x)
    except BaseException as e:  # noqa: BLE001 - report, never hide
        r = f"<unrepresentable {type(e).__name__}>"
    return r if len(r) <= REPR_MAX else r[: REPR_MAX - 3] + "..."


def exc_detail(e: BaseException, timeout_s: float) -> str:
    if isinstance(e, _Timeout):
        return f"raised TimeoutError: no result within {timeout_s:g} seconds"
    msg = str(e)
    if isinstance(e, SyntaxError) and e.lineno:
        msg = f"{e.msg} (line {e.lineno})"
    name = type(e).__name__
    return f"raised {name}: {msg}" if msg else f"raised {name}"


class _PytestShim:
    """Only used for test lines that are neither a plain assert nor a single pytest.raises."""

    @staticmethod
    @contextlib.contextmanager
    def raises(exc: type[BaseException]):
        try:
            yield
        except exc:
            return
        raise AssertionError(f"DID NOT RAISE {exc.__name__}")


def _is_pytest_raises(node: ast.AST) -> bool:
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "raises" and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "pytest")


def _outer_call(tree: ast.AST, entry: str) -> ast.Call | None:
    for node in ast.walk(tree):  # breadth-first: the outermost call is found first
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == entry:
            return node
    return None


class _Swap(ast.NodeTransformer):
    def __init__(self, target: ast.Call) -> None:
        self.target = target

    def visit_Call(self, node: ast.Call) -> ast.AST:
        if node is self.target:
            return ast.copy_location(ast.Name(id="__ret__", ctx=ast.Load()), node)
        return self.generic_visit(node)


def run_test(src: str, ns_base: dict[str, Any], entry: str, timeout_s: float) -> tuple[bool, str]:
    ns = dict(ns_base)
    ns["pytest"] = _PytestShim
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return False, exc_detail(e, timeout_s)
    stmt = tree.body[0] if len(tree.body) == 1 else None

    # Form 1: with pytest.raises(E): <expr>
    if isinstance(stmt, ast.With) and len(stmt.items) == 1 and _is_pytest_raises(stmt.items[0].context_expr) \
            and len(stmt.body) == 1 and isinstance(stmt.body[0], ast.Expr):
        exc_type = eval(compile(ast.Expression(stmt.items[0].context_expr.args[0]), "<test>", "eval"), ns)
        call = compile(ast.Expression(stmt.body[0].value), "<test>", "eval")
        try:
            with quiet(), time_limit(timeout_s):
                value = eval(call, ns)
        except BaseException as e:  # noqa: BLE001 - classified below
            if isinstance(e, exc_type) and not isinstance(e, _Timeout):
                return True, ""
            return False, exc_detail(e, timeout_s)
        return False, f"no exception raised; returned {short_repr(value)}"

    # Form 2: assert <expr containing a call to entry>
    if isinstance(stmt, ast.Assert):
        target = _outer_call(stmt, entry)
        if target is not None:
            call = compile(ast.Expression(copy.deepcopy(target)), "<test>", "eval")
            # the call is compiled from a copy above; the swap edits the original tree in place
            swapped = ast.fix_missing_locations(_Swap(target).visit(tree))
            check = compile(swapped, "<test>", "exec")
            try:
                with quiet(), time_limit(timeout_s):
                    value = eval(call, ns)
            except BaseException as e:  # noqa: BLE001
                return False, exc_detail(e, timeout_s)
            ns["__ret__"] = value
            try:
                with quiet(), time_limit(timeout_s):
                    exec(check, ns)
            except AssertionError:
                return False, f"returned {short_repr(value)}"
            except BaseException as e:  # noqa: BLE001
                return False, exc_detail(e, timeout_s)
            return True, ""

    # Fallback: execute as written.
    try:
        with quiet(), time_limit(timeout_s):
            exec(compile(tree, "<test>", "exec"), ns)
    except BaseException as e:  # noqa: BLE001
        return False, exc_detail(e, timeout_s)
    return True, ""


def is_floats(x: Any) -> bool:
    if isinstance(x, float):
        return True
    if isinstance(x, (list, tuple)) and x:
        return all(isinstance(i, float) for i in x)
    return False


def outputs_match(out: Any, exp: Any) -> bool:
    try:
        if out == exp:
            return True
    except BaseException:  # noqa: BLE001 - a raising __eq__ is a mismatch
        return False
    if not is_floats(exp) or type(out) is not type(exp):
        return False
    if isinstance(exp, float):
        return math.isclose(out, exp, rel_tol=1e-7, abs_tol=1e-6)
    return len(out) == len(exp) and all(
        isinstance(o, float) and math.isclose(o, e, rel_tol=1e-7, abs_tol=1e-6) for o, e in zip(out, exp))


def load_function(code: str, entry: str, timeout_s: float) -> tuple[dict[str, Any], str | None]:
    ns: dict[str, Any] = {"__name__": "worker_module"}
    try:
        with quiet(), time_limit(timeout_s):
            exec(compile(code, "<worker>", "exec"), ns)
    except BaseException as e:  # noqa: BLE001
        return ns, exc_detail(e, timeout_s)
    if not callable(ns.get(entry)):
        return ns, f"raised NameError: name '{entry}' is not defined"
    return ns, None


def run_hidden(payload: dict[str, Any], ns_worker: dict[str, Any] | None) -> dict[str, Any]:
    h = payload["hidden"]
    spec = importlib.util.spec_from_file_location("vendor_evalplus", h["vendor_path"])
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    inputs = mod.mbpp_deserialize_inputs(h["task_id"], h["inputs"])
    entry, t = payload["entry_point"], h["timeout_s"]
    ns_c: dict[str, Any] = {"__name__": "canonical"}
    exec(compile(h["canonical"], "<canonical>", "exec"), ns_c)
    canon = ns_c[entry]
    failed: list[int] = []
    examples: list[dict[str, str]] = []
    canonical_errors = 0
    for i, inp in enumerate(inputs):
        try:
            with quiet(), time_limit(t):
                exp = canon(*copy.deepcopy(inp))
        except BaseException:  # noqa: BLE001 - counted and reported
            canonical_errors += 1
            continue
        if ns_worker is None:
            ok, detail = False, "function did not load"
        else:
            try:
                with quiet(), time_limit(t):
                    out = ns_worker[entry](*copy.deepcopy(inp))
                ok = outputs_match(out, exp)
                detail = "" if ok else f"returned {short_repr(out)}; expected {short_repr(exp)}"
            except BaseException as e:  # noqa: BLE001
                ok, detail = False, exc_detail(e, t)
        if not ok:
            failed.append(i)
            if len(examples) < 3:
                examples.append({"input": short_repr(inp), "detail": detail})
    return {"n": len(inputs) - canonical_errors, "n_failed": len(failed), "failed_idx": failed,
            "examples": examples, "canonical_errors": canonical_errors}


def main() -> None:
    with open(sys.argv[1], encoding="utf-8") as f:
        payload = json.load(f)
    harden(payload["mem_mb"])
    entry, t = payload["entry_point"], payload["test_timeout_s"]
    ns, load_error = load_function(payload["code"], entry, t)
    results = []
    for test in payload["tests"]:
        if load_error is not None:
            passed, detail = False, load_error
        else:
            passed, detail = run_test(test["src"], ns, entry, t)
        results.append({"name": test["name"], "passed": passed, "detail": detail})
    out: dict[str, Any] = {"load_error": load_error, "tests": results}
    if payload.get("hidden"):
        out["hidden_inputs"] = run_hidden(payload, None if load_error else ns)
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump(out, f)


if __name__ == "__main__":
    main()
