"""Dollar-cost model for LLM usage.

Costs are reported primarily in tokens (model-agnostic). Dollar figures are
computed under a representative frontier-model price point (Claude Sonnet 5
standard API pricing as of 2026-07: $3 / $15 per million input / output
tokens; prompt-cache reads 0.1x input, cache writes 1.25x input for the
5-minute TTL).
"""
from __future__ import annotations

from dataclasses import dataclass

PRICE_IN_PER_MTOK = 3.00
PRICE_OUT_PER_MTOK = 15.00
CACHE_READ_MULT = 0.10
CACHE_WRITE_MULT = 1.25

# Per-model pricing table (USD per Mtok in/out) for multi-provider arms.
# VERIFY against current provider price pages before running a paid arm;
# the GPT entries are placeholders from mid-2025 public pricing.
MODEL_PRICES = {
    "claude-sonnet": (3.00, 15.00),
    "claude-haiku": (1.00, 5.00),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
}


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    def add(self, other: "Usage") -> "Usage":
        return Usage(
            self.input_tokens + other.input_tokens,
            self.output_tokens + other.output_tokens,
            self.cache_read_tokens + other.cache_read_tokens,
            self.cache_write_tokens + other.cache_write_tokens,
        )

    @property
    def total_tokens(self) -> int:
        return (self.input_tokens + self.output_tokens
                + self.cache_read_tokens + self.cache_write_tokens)

    def dollars(self) -> float:
        return (
            self.input_tokens * PRICE_IN_PER_MTOK
            + self.cache_read_tokens * PRICE_IN_PER_MTOK * CACHE_READ_MULT
            + self.cache_write_tokens * PRICE_IN_PER_MTOK * CACHE_WRITE_MULT
            + self.output_tokens * PRICE_OUT_PER_MTOK
        ) / 1_000_000

    def as_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_write_tokens": self.cache_write_tokens,
            "usd": round(self.dollars(), 6),
        }
