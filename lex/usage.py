"""What the session spent, counted by lex itself.

Ordered with the second leg: lex prints its own token usage, so cost per
dispatch becomes a harness number rather than something only the vendor's
console knows. `harness.evals` already reports cost per dispatch from the
records; this is the other half — the interface's own consumption.

Two decisions worth naming.

**The vendors do not agree on what "prompt tokens" means.** Anthropic's
`input_tokens` EXCLUDES cache reads and creations; OpenAI/xAI's
`prompt_tokens` INCLUDES the cached portion, with the cached count broken
out underneath. Normalising means subtracting on the xAI side, or every
cached turn is counted twice.

**There is no price table.** Rates change, differ by tier, and I would be
writing them from memory — an invented cost is worse than no cost, and it
would be cited in a report as though it were measured. Tokens are the
datapoint; whoever knows the rate can multiply.
"""

from dataclasses import dataclass


def from_anthropic(raw) -> dict:
    return {
        "input": getattr(raw, "input_tokens", 0) or 0,
        "output": getattr(raw, "output_tokens", 0) or 0,
        "cache_read": getattr(raw, "cache_read_input_tokens", 0) or 0,
        "cache_write": getattr(raw, "cache_creation_input_tokens", 0) or 0,
    }


def from_openai(raw: dict) -> dict:
    raw = raw or {}
    prompt = raw.get("prompt_tokens") or 0
    cached = ((raw.get("prompt_tokens_details") or {}).get("cached_tokens")) or 0
    # cached is a SUBSET of prompt here, unlike Anthropic. Subtract it so the
    # "input" column means the same thing on both vendors.
    return {
        "input": max(prompt - cached, 0),
        "output": raw.get("completion_tokens") or 0,
        "cache_read": cached,
        "cache_write": 0,
    }


@dataclass
class Usage:
    """Running totals for one lex session."""

    turns: int = 0
    unreported: int = 0
    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write: int = 0

    def record(self, source) -> None:
        """Count one assistant turn, from a message, a usage dict, or None."""
        self.turns += 1
        counted = self._normalise(source)
        if counted is None:
            # Not zero: a turn whose usage the vendor withheld is still a
            # turn that cost something. Counting it as free would make the
            # total read authoritative while being short.
            self.unreported += 1
            return
        self.input += counted["input"]
        self.output += counted["output"]
        self.cache_read += counted["cache_read"]
        self.cache_write += counted["cache_write"]

    @staticmethod
    def _normalise(source):
        if source is None:
            return None
        raw = getattr(source, "usage", source)
        if raw is None:
            return None
        if isinstance(raw, dict):
            if "prompt_tokens" in raw or "completion_tokens" in raw:
                return from_openai(raw)
            if not any(k in raw for k in ("input", "output")):
                return None
            return {
                "input": raw.get("input", 0),
                "output": raw.get("output", 0),
                "cache_read": raw.get("cache_read", 0),
                "cache_write": raw.get("cache_write", 0),
            }
        if hasattr(raw, "input_tokens"):
            return from_anthropic(raw)
        return None

    def as_dict(self) -> dict:
        return {
            "turns": self.turns, "unreported": self.unreported,
            "input": self.input, "output": self.output,
            "cache_read": self.cache_read, "cache_write": self.cache_write,
        }

    def render(self, model: str = "") -> str:
        head = f"tokens{f' — {model}' if model else ''}: "
        parts = [
            f"{self.turns} turn{'s' if self.turns != 1 else ''}",
            f"in {self.input:,}",
            f"out {self.output:,}",
        ]
        if self.cache_read:
            parts.append(f"cache read {self.cache_read:,}")
        if self.cache_write:
            parts.append(f"cache write {self.cache_write:,}")
        line = head + ", ".join(parts)
        tail = []
        if self.unreported:
            tail.append(
                f"{self.unreported} turn"
                f"{'s' if self.unreported != 1 else ''} with no usage reported "
                "— the total below is short by that much"
            )
        if self.cache_read or self.cache_write:
            tail.append("counts are normalised across vendors: cache reads are "
                        "never included in the input column")
        tail.append("no price table is asserted here — these are tokens, not "
                    "dollars")
        if not (self.cache_read or self.cache_write or self.unreported):
            return line
        return line + "\n" + "\n".join(f"  ({note})" for note in tail)
