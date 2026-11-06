"""Model calls through vLLM's OpenAI-compatible endpoint, with call-level logging and replay."""
from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
from openai import AsyncOpenAI

from common import messages_hash
from log import Logs, now_iso


class LLM:
    def __init__(self, family: str, fam_cfg: dict[str, Any], serving: dict[str, Any], logs: Logs,
                 sem: asyncio.Semaphore, extra_body: dict[str, Any] | None = None) -> None:
        self.family = family
        self.model = fam_cfg["model"]
        self.revision = fam_cfg["revision"]
        self.base_url = fam_cfg["base_url"]
        self.extra_body = extra_body if extra_body is not None else (fam_cfg.get("extra_body") or {})
        self.client = AsyncOpenAI(base_url=self.base_url, api_key=serving["api_key"],
                                  timeout=serving["request_timeout_s"],
                                  max_retries=serving["client_max_retries"])
        self.logs = logs
        self.sem = sem
        self.n_sent = 0
        self.n_replayed = 0

    async def served_models(self) -> list[str]:
        page = await self.client.models.list()
        return [m.id for m in page.data]

    async def count_tokens(self, text: str) -> int:
        """Token count with the served tokenizer (vLLM /tokenize), no special tokens."""
        root = self.base_url.rstrip("/").removesuffix("/v1")
        async with httpx.AsyncClient(timeout=60, trust_env=False) as c:
            r = await c.post(f"{root}/tokenize", json={"model": self.model, "prompt": text,
                                                         "add_special_tokens": False})
            r.raise_for_status()
            return int(r.json()["count"])

    async def chat(self, key: dict[str, Any], messages: list[dict[str, str]], *, seed: int,
                   temperature: float, max_tokens: int,
                   response_format: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return the logged call row (new or replayed). `key` holds the CALL_KEY fields."""
        row_key = {**key, "family": self.family}
        phash = messages_hash(messages)
        hit = self.logs.calls.replay(row_key, phash)
        if hit is not None:
            self.n_replayed += 1
            return hit
        self.logs.prompts.put(phash, messages)
        kwargs: dict[str, Any] = dict(model=self.model, messages=messages, temperature=temperature,
                                      max_tokens=max_tokens, seed=seed)
        if response_format is not None:
            kwargs["response_format"] = response_format
        if self.extra_body:
            kwargs["extra_body"] = self.extra_body
        async with self.sem:
            t0 = time.monotonic()
            resp = await self.client.chat.completions.create(**kwargs)
            latency = time.monotonic() - t0
        choice = resp.choices[0]
        usage = resp.usage
        cached = None
        if usage is not None and getattr(usage, "prompt_tokens_details", None) is not None:
            cached = getattr(usage.prompt_tokens_details, "cached_tokens", None)
        row = {
            **row_key,
            "prompt_hash": phash,
            "output": choice.message.content or "",
            "model": resp.model,
            "revision": self.revision,
            "seed": seed,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "structured": response_format is not None,
            "extra_body": self.extra_body,
            "finish_reason": choice.finish_reason,
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "cached_tokens": cached,
            "latency_s": round(latency, 3),
            "timestamp": now_iso(),
        }
        self.logs.calls.append(row)
        self.n_sent += 1
        return row
