"""Manager calls for one set: ledger arm L (two turns, one conversation) and spontaneous arm S,
`samples` each, for one family and one framing. CAP (D3) and STRESS (D6) are extra L turn-2
variants that reuse the same turn-1 ledger. Framing applies to S only (H5).

Scheduling per set: L turn 1 x3 and S x3 are submitted together; each L turn 2 follows its own
turn 1. Several sets run at once (manager.sets_in_flight) so >= 20 requests stay in flight.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from common import derive_seed
from llm import LLM
from log import Logs, now_iso
from problems import Problem
from prompts import Prompts
from worker import render_amendment

ARMS = ("L", "S", "CAP", "STRESS")
TURN2_PROMPT = {"L": "REPORT", "CAP": "CAP", "STRESS": "STRESS"}
FRAMING_PROMPT = {"neutral": "REPORT", "responsible": "FRAME_R", "placebo": "FRAME_P"}
WORKER_IDS = [f"worker_{i}" for i in range(1, 10)]


def ledger_schema() -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False, "required": ["issues"],
        "properties": {"issues": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["worker_id", "function", "requirement", "evidence_quote", "severity"],
            "properties": {
                "worker_id": {"type": "string", "enum": WORKER_IDS},
                "function": {"type": "string"}, "requirement": {"type": "string"},
                "evidence_quote": {"type": "string"},
                "severity": {"type": "string", "enum": ["high", "medium", "low"]},
            }}}},
    }


def validate_ledger(text: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        return None, f"json: {e.msg}"
    if not isinstance(obj, dict) or set(obj) != {"issues"} or not isinstance(obj["issues"], list):
        return None, "schema: top level must be exactly {\"issues\": [...]}"
    keys = {"worker_id", "function", "requirement", "evidence_quote", "severity"}
    for i, e in enumerate(obj["issues"]):
        if not isinstance(e, dict) or set(e) != keys:
            return None, f"schema: entry {i} has wrong fields"
        if e["worker_id"] not in WORKER_IDS or e["severity"] not in ("high", "medium", "low"):
            return None, f"schema: entry {i} has a bad enum value"
        if not all(isinstance(e[k], str) for k in keys):
            return None, f"schema: entry {i} has a non-string field"
    return obj, None


@dataclass
class ManagerContext:
    system: str
    user_prefix: str      # M_PREFIX rendered + "\n": the arm instruction follows directly


def build_context(pr: Prompts, problems: dict[str, Problem], final: dict[str, Any],
                  episodes: dict[str, dict[str, Any]]) -> ManagerContext:
    """`episodes` maps worker_id -> accepted episode record."""
    positions = sorted(final["positions"], key=lambda x: x["position"])
    spec_lines, transcripts = [], []
    amendment = None
    for pos in positions:
        p = problems[pos["problem_id"]]
        spec_lines.append(f"{pos['worker_id']} · {p.entry_point}: {p.spec_text} {p.edge_requirement}")
        ep = episodes[pos["worker_id"]]
        mv = ep["manager_view"]
        transcripts.append(pr.render_transcript(pos["worker_id"], p.entry_point,
                                                [tuple(t) for t in mv["turns"]], mv["final_message"]))
        if pos["cell"] == "AU":
            amendment = render_amendment(pr, p, final["amd_id"])
    system = pr.render("M_SYS", spec_block="\n".join(spec_lines),
                       amendments_block=amendment if amendment is not None else "None.")
    prefix = pr.render("M_PREFIX", transcripts="\n\n".join(transcripts))
    if not prefix.endswith("</transcripts>\n"):
        raise ValueError("M_PREFIX no longer ends with '</transcripts>\\n'")
    return ManagerContext(system=system, user_prefix=prefix + "\n")


class SetManager:
    def __init__(self, cfg: dict[str, Any], pr: Prompts, llm: LLM, logs: Logs, family: str) -> None:
        self.mc = cfg["manager"]
        self.pr = pr
        self.llm = llm
        self.logs = logs
        self.family = family

    def _key(self, set_id: str, arm: str, framing: str, sample: int, turn: int, try_idx: int) -> dict[str, Any]:
        return {"stage": "manager", "set_id": set_id, "worker_id": None, "problem_id": None, "arm": arm,
                "sample": sample, "framing": framing, "turn": turn, "try": try_idx}

    def _seed(self, set_seed: int, arm: str, framing: str, sample: int, turn: int) -> int:
        return derive_seed(set_seed, "manager", self.family, arm, framing, sample, turn)

    async def _ledger(self, set_spec: dict[str, Any], ctx: ManagerContext, sample: int) -> dict[str, Any]:
        msgs = [{"role": "system", "content": ctx.system},
                {"role": "user", "content": ctx.user_prefix + self.pr.raw("L_LEDGER")}]
        rf = None
        if self.mc["ledger_structured_output"]:
            rf = {"type": "json_schema", "json_schema": {"name": "ledger", "schema": ledger_schema(),
                                                          "strict": True}}
        base = self._seed(set_spec["seed"], "L", "neutral", sample, 1)
        errors: list[str] = []
        for t in range(self.mc["ledger_max_tries"]):
            row = await self.llm.chat(self._key(set_spec["set_id"], "L", "neutral", sample, 1, t), msgs,
                                      seed=base + t, temperature=self.mc["temperature"],
                                      max_tokens=self.mc["max_tokens_ledger"], response_format=rf)
            obj, err = validate_ledger(row["output"])
            if obj is not None:
                return {"messages": msgs, "raw": row["output"], "ledger": obj, "tries": t + 1,
                        "errors": errors}
            errors.append(err or "unknown")
        return {"messages": msgs, "raw": row["output"], "ledger": None, "tries": len(errors),
                "errors": errors}

    async def _report(self, set_spec: dict[str, Any], msgs: list[dict[str, str]], arm: str, framing: str,
                      sample: int, turn: int) -> dict[str, Any]:
        row = await self.llm.chat(self._key(set_spec["set_id"], arm, framing, sample, turn, 0), msgs,
                                  seed=self._seed(set_spec["seed"], arm, framing, sample, turn),
                                  temperature=self.mc["temperature"], max_tokens=self.mc["max_tokens_report"])
        return row

    def _record(self, set_id: str, arm: str, framing: str, sample: int, **fields: Any) -> None:
        key = (set_id, self.family, arm, framing, sample)
        if key in self.logs.manager_outputs:
            return
        self.logs.manager_outputs.append({"set_id": set_id, "family": self.family, "arm": arm,
                                          "framing": framing, "sample": sample, **fields,
                                          "timestamp": now_iso()})

    async def _l_chain(self, set_spec: dict[str, Any], ctx: ManagerContext, sample: int,
                       turn2_arms: list[str]) -> None:
        led = await self._ledger(set_spec, ctx, sample)
        sid = set_spec["set_id"]
        if led["ledger"] is None:  # no valid ledger after all tries: no turn 2, recorded as such
            for arm in turn2_arms:
                self._record(sid, arm, "neutral", sample, ledger=None, ledger_raw=led["raw"],
                             ledger_tries=led["tries"], ledger_errors=led["errors"], report=None,
                             report_words=None, finish_reason=None)
            return
        base = led["messages"] + [{"role": "assistant", "content": led["raw"]}]

        async def turn2(arm: str) -> None:
            msgs = base + [{"role": "user", "content": self.pr.raw(TURN2_PROMPT[arm])}]
            row = await self._report(set_spec, msgs, arm, "neutral", sample, 2)
            self._record(sid, arm, "neutral", sample, ledger=led["ledger"], ledger_raw=led["raw"],
                         ledger_tries=led["tries"], ledger_errors=led["errors"], report=row["output"],
                         report_words=len(row["output"].split()), finish_reason=row["finish_reason"])

        await asyncio.gather(*(turn2(a) for a in turn2_arms))

    async def _s(self, set_spec: dict[str, Any], ctx: ManagerContext, sample: int, framing: str) -> None:
        msgs = [{"role": "system", "content": ctx.system},
                {"role": "user", "content": ctx.user_prefix + self.pr.raw(FRAMING_PROMPT[framing])}]
        row = await self._report(set_spec, msgs, "S", framing, sample, 1)
        self._record(set_spec["set_id"], "S", framing, sample, ledger=None, ledger_raw=None,
                     ledger_tries=None, ledger_errors=None, report=row["output"],
                     report_words=len(row["output"].split()), finish_reason=row["finish_reason"])

    async def run_set(self, set_spec: dict[str, Any], ctx: ManagerContext, arms: list[str],
                      framing: str) -> None:
        bad = [a for a in arms if a not in ARMS]
        if bad:
            raise ValueError(f"unknown arms {bad}")
        if framing != "neutral" and arms != ["S"]:
            raise ValueError("non-neutral framing is defined for the S arm only (H5); pass --arms S")
        turn2 = [a for a in ("L", "CAP", "STRESS") if a in arms]
        jobs = []
        for s in range(self.mc["samples"]):
            if turn2:
                jobs.append(self._l_chain(set_spec, ctx, s, turn2))
            if "S" in arms:
                jobs.append(self._s(set_spec, ctx, s, framing))
        await asyncio.gather(*jobs)
