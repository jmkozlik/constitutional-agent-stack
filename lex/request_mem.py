"""REQUEST_MEM as an inline question to the human.

The packet's ratified v0 shape is a report line `REQUEST_MEM: <what and why>`.
A dispatched agent emits those into its artifacts and its final report; the
operator emits them when it hits something only the human knows. Both reach
lex as text — harvested artifact text on a tool result, or the operator's own
turn — so lex scans both, asks the human each one inline, and returns the
answer to the model.

There is no guessing branch: an unanswered line comes back as
`(no answer given)`, which is a fact the model can act on, not a blank the
model can fill in for itself.
"""

import re
import sys

MARKER = "REQUEST_MEM"
_LINE = re.compile(rf"^\s*{MARKER}\s*:\s*(?P<body>.+?)\s*$", re.MULTILINE)

_RULE = "-" * 68


def scan(text: str) -> list:
    """Every REQUEST_MEM body in `text`, in order, de-duplicated."""
    if not text or MARKER not in text:
        return []
    seen, out = set(), []
    for match in _LINE.finditer(text):
        body = match.group("body")
        if body not in seen:
            seen.add(body)
            out.append(body)
    return out


def ask(request: str, *, source: str = "") -> str:
    """Put one request to the human and return what they typed."""
    out = sys.stdout
    out.write(f"\n{_RULE}\n")
    out.write(f"REQUEST_MEM{f' (from {source})' if source else ''}\n")
    out.write(f"  {request}\n")
    out.write(f"{_RULE}\n")
    out.write("Answer, or press Enter to send it back unanswered.\n")
    out.flush()
    try:
        answer = input("answer> ")
    except (EOFError, KeyboardInterrupt):
        out.write("\n(no answer available)\n")
        return "(no answer given)"
    answer = answer.strip()
    return answer or "(no answer given)"


def collect(text: str, *, source: str = "") -> list:
    """Scan, ask each, and return [(request, answer)]."""
    return [(request, ask(request, source=source)) for request in scan(text)]


def render(pairs: list) -> str:
    """The answers, in the shape the model gets them back."""
    if not pairs:
        return ""
    lines = ["", "REQUEST_MEM answers from the operator's human:"]
    for request, answer in pairs:
        lines.append(f"  Q: {request}")
        lines.append(f"  A: {answer}")
    return "\n".join(lines) + "\n"
