"""lex v1 — a standalone terminal operator for the harness.

Not a Claude Code session in a hat: an agent loop on the Anthropic API whose
system prompt is the lex-operator skill verbatim and whose only tools are
subprocess wrappers around the harness CLIs.

The one thing that moved from prose to code: every mutating dispatch action
and every ratification point passes through `lex.confirm.confirm`, which
blocks on a human typing y at the terminal. There is no parameter, flag, or
environment variable that answers it.

Run: python -m lex
"""

__all__ = ["agent", "confirm", "prompt", "repl", "request_mem", "tools", "transcript"]
