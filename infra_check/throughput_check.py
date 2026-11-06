"""DISPOSABLE pre-sprint infrastructure check. Not project code: delete after use.

Measures two numbers against a running vLLM OpenAI-compatible server:
  Phase A (shared prefix): one ~18k-token prefix, N parallel requests with unique
      suffixes and a fixed output length -> decode tokens/sec with a warm prefix cache.
  Phase B (distinct prefixes): N different ~18k-token prefixes, 1 output token each
      -> prefill tokens/sec on cache misses.
Then projects core-run GPU-hours from the token budget in BUDGET (assumptions; replace
with pilot measurements).

Usage:
  python throughput_check.py --model Qwen/Qwen3-8B --qwen-no-think
  python throughput_check.py --model mistralai/Ministral-3-8B-Instruct-2512-BF16
"""
from __future__ import annotations

import argparse
import asyncio
import random
import statistics
import time
from dataclasses import dataclass

from openai import AsyncOpenAI

WORDS = (
    "worker manager function returns list value edge case requirement hidden visible "
    "test passed failed status final input output integer string empty none raise"
).split()

# Token budget per the locked design. All token sizes are ASSUMPTIONS until the pilot.
BUDGET = {
    "sets": 130,
    "samples": 3,
    "mgr_prefix": 18_000,      # 9 worker transcripts + spec, shared by every call of a set
    "instr": 100,              # final instruction tokens
    "ledger_out": 800,         # L-arm turn 1 (uncapped; set max_tokens and log truncation)
    "report_out": 200,         # <=120 words
    "episodes": 1_170,
    "worker_prefill": 4_000,   # unique prefill per worker episode (multi-turn, cached)
    "worker_decode": 1_500,    # ~3 calls x 500 tokens
    "framing_calls": 480,
    "overhead": 1.5,           # model loads, restarts, retries, idle
}


@dataclass
class Result:
    latency: float
    prompt: int
    completion: int
    cached: int | None


def make_text(n_words: int, seed: int) -> str:
    """Pseudo-log text; the seed tag on line 1 makes prefixes diverge immediately."""
    rng = random.Random(seed)
    lines = [f"[log {seed}:{i}] " + " ".join(rng.choice(WORDS) for _ in range(12))
             for i in range(0, n_words, 12)]
    return "\n".join(lines)


async def call(client: AsyncOpenAI, model: str, prompt: str, max_tokens: int,
               extra: dict) -> Result:
    t0 = time.perf_counter()
    r = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.7,
        extra_body=extra,
    )
    dt = time.perf_counter() - t0
    details = getattr(r.usage, "prompt_tokens_details", None)
    cached = getattr(details, "cached_tokens", None) if details else None
    return Result(dt, r.usage.prompt_tokens, r.usage.completion_tokens, cached)


async def calibrate(client: AsyncOpenAI, model: str, target: int, extra: dict) -> int:
    """Return the word count that yields ~target prompt tokens."""
    probe_words = 2_000
    r = await call(client, model, make_text(probe_words, seed=999_999), 1, extra)
    per_word = r.prompt / probe_words
    return int(target / per_word)


def summarise(name: str, results: list[Result], wall: float) -> dict[str, float]:
    prompt = sum(r.prompt for r in results)
    comp = sum(r.completion for r in results)
    cached_vals = [r.cached for r in results if r.cached is not None]
    cached = sum(cached_vals) if cached_vals else None
    lat = sorted(r.latency for r in results)
    print(f"\n== {name}: {len(results)} requests, wall {wall:.1f}s")
    print(f"   prompt tokens {prompt:,} | completion tokens {comp:,} | "
          f"cached {'n/a' if cached is None else f'{cached:,}'}")
    print(f"   latency p50 {statistics.median(lat):.1f}s  max {lat[-1]:.1f}s")
    uncached = prompt - (cached or 0)
    return {"decode_tps": comp / wall, "prefill_tps": uncached / wall,
            "cache_frac": (cached / prompt) if cached is not None else float("nan")}


def project(prefill_tps: float, decode_tps: float) -> None:
    b = BUDGET
    s, k = b["samples"], b["sets"]
    per_set_prefill = b["mgr_prefix"] + 2 * s * b["instr"] + s * (b["ledger_out"] + b["instr"])
    per_set_decode = s * (b["ledger_out"] + b["report_out"]) + s * b["report_out"]
    parts = {
        "workers (A)": (b["episodes"] * b["worker_prefill"], b["episodes"] * b["worker_decode"]),
        "managers A, 130 sets": (k * per_set_prefill, k * per_set_decode),
        "managers B, 130 sets": (k * per_set_prefill, k * per_set_decode),
        "managers B, 60 sets": (60 * per_set_prefill, 60 * per_set_decode),
        "framing (S arm, A)": (b["framing_calls"] * (b["instr"] + 50),
                               b["framing_calls"] * b["report_out"]),
    }
    print("\n== Projection (conservative: prefill and decode treated as additive)")
    total = 0.0
    for name, (pf, dc) in parts.items():
        h = (pf / prefill_tps + dc / decode_tps) / 3600
        if name != "managers B, 60 sets":
            total += h
        print(f"   {name:24s} prefill {pf/1e6:5.2f}M  decode {dc/1e6:5.2f}M  -> {h:5.2f} GPU-h")
    print(f"   core incl. B@130 + framing: {total:.2f} GPU-h raw, "
          f"{total * b['overhead']:.2f} GPU-h with x{b['overhead']} overhead")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--base-url", default="http://localhost:8000/v1")
    ap.add_argument("--prefix-tokens", type=int, default=18_000)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--max-tokens", type=int, default=300)
    ap.add_argument("--qwen-no-think", action="store_true",
                    help="pass chat_template_kwargs enable_thinking=False (Qwen3 only)")
    args = ap.parse_args()

    client = AsyncOpenAI(base_url=args.base_url, api_key="EMPTY", timeout=600)
    base_extra: dict = {}
    if args.qwen_no_think:
        base_extra["chat_template_kwargs"] = {"enable_thinking": False}
    fixed_len = {**base_extra, "min_tokens": args.max_tokens, "ignore_eos": True}

    n_words = await calibrate(client, args.model, args.prefix_tokens, base_extra)
    shared = make_text(n_words, seed=0)

    # Phase A: warm the cache with one request, then N parallel on the same prefix.
    await call(client, args.model, shared + "\n\nRequest warmup: summarise the log.", 1, base_extra)
    t0 = time.perf_counter()
    res_a = await asyncio.gather(*[
        call(client, args.model, shared + f"\n\nRequest {i}: summarise the log in detail.",
             args.max_tokens, fixed_len) for i in range(args.n)])
    a = summarise("Phase A shared prefix", list(res_a), time.perf_counter() - t0)

    # Phase B: N distinct prefixes, 1 output token each (prefill-bound).
    t0 = time.perf_counter()
    res_b = await asyncio.gather(*[
        call(client, args.model, make_text(n_words, seed=i + 1) + "\n\nSummarise.", 1, base_extra)
        for i in range(args.n)])
    bres = summarise("Phase B distinct prefixes", list(res_b), time.perf_counter() - t0)

    print(f"\nPASTE THESE: model={args.model} decode_tps={a['decode_tps']:.0f} "
          f"prefill_tps={bres['prefill_tps']:.0f} phaseA_cache_frac={a['cache_frac']:.2f}")
    project(bres["prefill_tps"], a["decode_tps"])


if __name__ == "__main__":
    asyncio.run(main())
