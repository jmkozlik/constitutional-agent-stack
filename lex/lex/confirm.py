"""The confirm gate — the one part of lex that is law rather than plumbing.

The lex-operator skill says: *never self-ratify*, and *dispatch is never
automatic*. In lex v0 both were sentences in a prompt, and a prompt is a
request. Here they are a function every mutating tool call must pass through,
and the only thing that satisfies it is a human typing `y` at the terminal.

Deliberately absent — and asserted absent by tests/test_lex_confirm.py:

- **No bypass parameter.** The signature is `(question, detail)` and nothing
  else. There is no `assume_yes`, no `force`, no injectable answerer, so a
  caller cannot supply the answer in place of the human.
- **No environment override.** Nothing in this module reads `os.environ`.
- **No default-yes.** A bare Enter, an empty string, EOF and Ctrl-C are all
  refusals. Only the exact words `y` or `yes` (case-insensitive, stripped)
  approve.

The model cannot reach this function at all. What the model emits is tool
input; no field of tool input is read here, and no field of tool input
decides whether the gate runs — see `lex.tools.requires_confirmation`, which
fails closed on anything it does not recognise.
"""

import sys
from dataclasses import dataclass

# The complete set of affirmative answers. Anything else refuses.
AFFIRMATIVE = frozenset({"y", "yes"})

_RULE = "=" * 68


@dataclass(frozen=True)
class Decision:
    """A human's answer to one gate, kept whole so the transcript can quote
    what was typed rather than a boolean derived from it."""

    approved: bool
    answer: str

    def __bool__(self) -> bool:
        return self.approved


def confirm(question: str, detail: str = "") -> Decision:
    """Block until a human answers. Approve only on an explicit y/yes.

    `question` is the one-line ask; `detail` is the drafted action, printed
    verbatim underneath it — a ratification prompt is a question with the
    action attached, not a notification of something already applied.
    """
    out = sys.stdout
    out.write(f"\n{_RULE}\n")
    out.write(f"RATIFY: {question}\n")
    if detail:
        out.write(f"{'-' * 68}\n")
        for line in detail.rstrip("\n").splitlines():
            out.write(f"  {line}\n")
    out.write(f"{_RULE}\n")
    out.write(
        "Nothing has been done yet. Type y or yes to authorise it; anything\n"
        "else — including a bare Enter — refuses and the action does not run.\n"
    )
    out.flush()
    try:
        answer = input("ratify? [y/N] ")
    except (EOFError, KeyboardInterrupt):
        out.write("\n(no answer available — refused)\n")
        out.flush()
        return Decision(False, "<no answer>")
    approved = answer.strip().lower() in AFFIRMATIVE
    out.write("authorised.\n" if approved else "refused.\n")
    out.flush()
    return Decision(approved, answer)
