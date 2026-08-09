"""The session log lex files on exit.

Deliberately NOT `harness/reports/NNN.md`. A numbered report is the ratified
artifact — key tuple, evidence, flags, monotonic findings ledger — and it is
the operator's authored claim about a round. lex has the transcript and
nothing else; emitting a numbered report from it would be lex adopting its
own report, which is exactly the self-ratification the skill forbids. So the
smallest honest thing is a transcript, provenance-marked, parked one
directory below the reports it feeds, with the next free number stated so the
human knows where it goes.

Files land at harness/reports/sessions/lex-<UTC timestamp>.md.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

SESSIONS = Path("harness") / "reports" / "sessions"
_NNN = re.compile(r"^(\d{3})\.md$")


def next_report_number(repo) -> str:
    reports = Path(repo) / "harness" / "reports"
    numbers = [
        int(m.group(1))
        for path in reports.glob("*.md")
        if (m := _NNN.match(path.name))
    ]
    return f"{max(numbers) + 1:03d}" if numbers else "001"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Transcript:
    """Append-only record of one session. Nothing is summarised on the way in
    — the whole point is that what gets filed is what happened."""

    def __init__(self, repo=".", *, model: str = "", commit: str = ""):
        self.repo = Path(repo)
        self.model = model
        self.commit = commit
        self.started = _now()
        self.entries: list = []
        self.tool_calls = 0
        self.gates: list = []
        self.request_mems: list = []

    def _add(self, kind: str, **fields):
        self.entries.append({"at": _now(), "kind": kind, **fields})

    def human(self, text: str):
        self._add("human", text=text)

    def operator(self, text: str):
        self._add("operator", text=text)

    def thinking(self, text: str):
        if text.strip():
            self._add("thinking", text=text)

    def note(self, text: str):
        self._add("note", text=text)

    def tool(self, name: str, tool_input, result: dict):
        self.tool_calls += 1
        if result.get("gated"):
            self.gates.append(
                {
                    "tool": name,
                    "input": tool_input,
                    "answer": result.get("answer", ""),
                    "approved": not result.get("refused"),
                }
            )
        self._add(
            "tool",
            name=name,
            input=tool_input,
            argv=result.get("argv"),
            exit_code=result.get("exit_code"),
            refused=bool(result.get("refused")),
            gated=bool(result.get("gated")),
            answer=result.get("answer"),
            stdout=result.get("stdout", ""),
            stderr=result.get("stderr", ""),
            message=result.get("message", ""),
        )

    def request_mem(self, pairs: list, *, source: str):
        for question, answer in pairs:
            self.request_mems.append(
                {"source": source, "question": question, "answer": answer}
            )
            self._add("request_mem", source=source, question=question, answer=answer)

    # --- rendering ----------------------------------------------------------

    def render(self) -> str:
        nxt = next_report_number(self.repo)
        refusals = [g for g in self.gates if not g["approved"]]
        lines = [
            f"# lex session log — {self.started}",
            "",
            "**Provenance: transcript, agent-authored, not a ratified report.**",
            "lex files this instead of `harness/reports/NNN.md` on purpose: a",
            "numbered report is the operator's authored claim to the ratifier —",
            "key tuple, evidence, flags, monotonic findings ledger — and lex",
            "writing one from its own transcript would be lex adopting its own",
            f"report. The next free report number is **{nxt}**; turning this log",
            "into `harness/reports/{}.md` is a human's job.".format(nxt),
            "",
            "## session",
            "",
            "| key | value |",
            "|---|---|",
            f"| started (UTC) | {self.started} |",
            f"| ended (UTC) | {_now()} |",
            f"| model | {self.model or '(unrecorded)'} |",
            f"| commit at start | {self.commit or '(unrecorded)'} |",
            f"| tool calls | {self.tool_calls} |",
            f"| ratification prompts | {len(self.gates)} "
            f"({len(refusals)} refused) |",
            f"| REQUEST_MEM exchanges | {len(self.request_mems)} |",
            "",
        ]

        if self.gates:
            lines += ["## ratification prompts (verbatim answers)", ""]
            for gate in self.gates:
                verdict = "AUTHORISED" if gate["approved"] else "REFUSED"
                lines.append(
                    f"- **{verdict}** `{gate['tool']}` "
                    f"{json.dumps(gate['input'], sort_keys=True)} — human typed "
                    f"`{gate['answer']}`"
                )
            lines.append("")

        if self.request_mems:
            lines += ["## REQUEST_MEM", ""]
            for item in self.request_mems:
                lines.append(f"- from {item['source']}")
                lines.append(f"  - Q: {item['question']}")
                lines.append(f"  - A: {item['answer']}")
            lines.append("")

        lines += ["## turns (verbatim)", ""]
        for entry in self.entries:
            lines += self._render_entry(entry)
        return "\n".join(lines).rstrip("\n") + "\n"

    @staticmethod
    def _render_entry(entry: dict) -> list:
        kind, at = entry["kind"], entry["at"]
        if kind in ("human", "operator", "thinking", "note"):
            label = {
                "human": "human",
                "operator": "lex",
                "thinking": "lex (thinking summary)",
                "note": "lex runtime",
            }[kind]
            return [f"### {at} — {label}", "", "```", entry["text"].rstrip(), "```", ""]
        if kind == "request_mem":
            return [
                f"### {at} — REQUEST_MEM ({entry['source']})",
                "",
                f"- Q: {entry['question']}",
                f"- A: {entry['answer']}",
                "",
            ]
        out = [
            f"### {at} — tool `{entry['name']}`",
            "",
            f"input: `{json.dumps(entry['input'], sort_keys=True)}`",
            "",
        ]
        if entry["gated"]:
            verdict = "REFUSED" if entry["refused"] else "AUTHORISED"
            out += [f"gate: **{verdict}** (human typed `{entry['answer']}`)", ""]
        if entry["refused"]:
            out += ["```", entry["message"].rstrip(), "```", ""]
            return out
        argv = " ".join(entry["argv"] or [])
        out += [
            "```",
            f"$ {argv}",
            f"exit: {entry['exit_code']}",
            "--- stdout ---",
            entry["stdout"].rstrip() or "(empty)",
            "--- stderr ---",
            entry["stderr"].rstrip() or "(empty)",
            "```",
            "",
        ]
        return out

    def write(self) -> Path:
        target_dir = self.repo / SESSIONS
        target_dir.mkdir(parents=True, exist_ok=True)
        stamp = self.started.replace(":", "").replace("-", "")
        target = target_dir / f"lex-{stamp}.md"
        target.write_text(self.render(), encoding="utf-8")
        return target
