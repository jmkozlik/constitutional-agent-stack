"""The terminal loop: slash verbs, the opening brief, and the exit file.

Two things worth naming, because they are choices and not accidents:

**The verb bodies are the repo's own command files, verbatim.** `/plan` sends
the body of `.claude/commands/plan.md`; `/run <node>` sends `run.md` with
`$ARGUMENTS` substituted. Nothing is paraphrased into Python, so editing the
command file changes what lex does.

**Standing state is delivered, not fetched.** lex has no file tool by design,
and `harness/LOOP.md` plus the latest report are the first read of every
session — so the harness hands them to lex in the opening turn, the way
`dispatch.prepare` hands an agent its packet. This is context, not a lever:
lex cannot re-read either file later, cannot read anything else, and cannot
write them back.
"""

import sys
from pathlib import Path

from lex import agent, transcript as transcript_mod
from lex.prompt import strip_frontmatter

COMMANDS = Path(".claude") / "commands"
VERBS = ("plan", "run", "status", "replay", "evals", "ledger")
MAX_CONTEXT_CHARS = 200_000

BANNER = """lex — the interactive interface to the harness.

verbs: /plan  /run <node> [--role executor|tester]  /status  /replay
       /evals  /ledger  /quit          (anything else is just conversation)
"""

ENVIRONMENT = """## Operational environment  [provenance: lex runtime, not law]

You are lex v1, running as a standalone terminal program against the
Anthropic API. Your conduct is the system prompt above, verbatim; this
section is environment only and does not add to it or override it.

- Repository: {repo} (you are running from it; every path you pass a tool is
  repo-relative).
- Your levers are the tools attached to this conversation: {tools}. They are
  the harness CLIs and nothing else. You have no file reader, no editor, no
  shell and no search. If the moment needs a lever that does not exist, say
  so and propose building it.
- **Mutating actions stop for the human in code, not on your goodwill.**
  `dispatch_run prepare|harvest|teardown` and `fence apply|release` block on
  an explicit y/n at the terminal before they run, and a refusal comes back
  to you as a tool result. You cannot answer that prompt, and there is no
  argument that skips it. Recommend and draft; the human adopts.
- The agent spawn is not yours. `dispatch_run prepare` returns a compiled
  prompt in its manifest; show it to the human, who spawns against it and
  brings the result back.
- A `REQUEST_MEM: <what and why>` line in your own text, or in any tool
  output, is put to the human inline and the answer is returned to you.
- On exit lex files this whole session verbatim to
  harness/reports/sessions/. It is a transcript, not a report — writing
  `harness/reports/NNN.md` stays a human act.

## Standing state  [provenance: delivered by the harness, read-only]

You cannot read files. These are handed to you because they are the first
read of every session. They are as of session start and do not update.

{state}
"""


def _verb_body(repo, verb: str) -> str:
    path = Path(repo) / COMMANDS / f"{verb}.md"
    if not path.is_file():
        return ""
    return strip_frontmatter(path.read_text(encoding="utf-8")).strip()


def _clip(text: str, label: str) -> str:
    if len(text) <= MAX_CONTEXT_CHARS:
        return text
    return text[:MAX_CONTEXT_CHARS] + f"\n… [lex truncated {label}]"


def standing_state(repo) -> str:
    repo = Path(repo)
    blocks = []
    loop = repo / "harness" / "LOOP.md"
    if loop.is_file():
        blocks.append(
            "### harness/LOOP.md (verbatim)\n\n"
            + _clip(loop.read_text(encoding="utf-8"), "LOOP.md")
        )
    else:
        blocks.append("### harness/LOOP.md — MISSING. Say so; do not proceed as"
                      " if you knew the standing state.")
    reports = sorted((repo / "harness" / "reports").glob("[0-9][0-9][0-9].md"))
    if reports:
        latest = reports[-1]
        blocks.append(
            f"### harness/reports/{latest.name} (latest report, verbatim)\n\n"
            + _clip(latest.read_text(encoding="utf-8"), latest.name)
        )
    else:
        blocks.append("### harness/reports/ — no numbered reports found.")
    return "\n\n".join(blocks)


def opening_turn(repo, *, tools) -> str:
    body = ENVIRONMENT.format(
        repo=Path(repo).resolve(),
        tools=", ".join(tools),
        state=standing_state(repo),
    )
    orientation = _verb_body(repo, "lex")
    if orientation:
        body += "\n\n## This turn\n\n" + orientation
    else:
        body += (
            "\n\n## This turn\n\nOrient the human: where the loop is, what is "
            "pending ratification, and what the next dispatch would be. Do not "
            "dispatch anything yet."
        )
    return body


def expand(repo, line: str) -> str:
    """A slash verb becomes its command file's body, verbatim."""
    verb, _, args = line[1:].partition(" ")
    verb = verb.strip().lower()
    if verb not in VERBS:
        return ""
    body = _verb_body(repo, verb)
    if not body:
        return (
            f"The human typed /{verb}, but .claude/commands/{verb}.md is "
            "missing, so lex cannot deliver its ratified text. Say so."
        )
    args = args.strip()
    if "$ARGUMENTS" in body:
        return body.replace("$ARGUMENTS", args or "(no arguments given)")
    return body if not args else f"{body}\n\nArguments: {args}"


def run(client, *, system: str, repo, model: str = agent.MODEL, commit: str = "",
        opening: str = "", out=None, provider=None) -> Path:
    """Drive the REPL until /quit or EOF, then file the session log."""
    out = out or sys.stdout
    log = transcript_mod.Transcript(repo, model=model, commit=commit)
    session = agent.Session(
        client, system=system, repo=repo, transcript=log, model=model, out=out,
        provider=provider,
    )
    from lex.tools import TOOL_NAMES

    out.write(BANNER + "\n")
    first = opening_turn(repo, tools=TOOL_NAMES)
    if opening:
        log.human(opening)
        expanded = expand(repo, opening) if opening.startswith("/") else opening
        first += (
            "\n\nThe human opened with "
            f"`{opening}`:\n\n{expanded or '(no such verb — say so)'}"
        )
    try:
        session.send(first)
        while True:
            try:
                line = input("\nlex> ").strip()
            except EOFError:
                out.write("\n")
                break
            if not line:
                continue
            if line.lower() in ("/quit", "/exit", "quit", "exit"):
                break
            if line.lower() in ("/help", "help", "?"):
                out.write(BANNER)
                continue
            log.human(line)
            content = expand(repo, line) if line.startswith("/") else line
            if not content:
                out.write(
                    f"lex: no such verb. {BANNER.splitlines()[2].strip()}\n"
                )
                continue
            session.send(content)
    except KeyboardInterrupt:
        out.write("\ninterrupted.\n")
        log.note("session interrupted by the human (Ctrl-C)")
    target = log.write()
    out.write(
        f"\nsession log: {target}\n"
        f"next free report number: {transcript_mod.next_report_number(repo)}\n"
    )
    return target
