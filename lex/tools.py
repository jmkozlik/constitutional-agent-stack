"""lex's levers, and nothing else.

Every tool here shells out to an existing `python -m harness.*` CLI and hands
back stdout, stderr and the exit code. There is deliberately no file tool, no
editor, no shell escape and no search: if a lever does not exist for what the
moment needs, the operator has to say so and propose building it, which is
the whole point of the skill's one rule.

Two invariants this module is responsible for, both asserted in
tests/test_lex_tools.py:

1. **The gate is derived from the tool name and its action, never from the
   rest of the model's input.** `requires_confirmation` consults a hardcoded
   allowlist of read-only actions and gates everything else, so an unknown
   tool, a missing action, a misspelled action, or an extra `{"confirm":
   true}` field all fail *closed*.

2. **`run_tool` takes no injectable answerer.** It calls `confirm` directly.
   The only way past a gate is a human typing y at the terminal.
"""

import json
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from lex.confirm import confirm

# Tool output is fed straight back to the model; a compiled packet is large
# and a harvest can be larger. Cap each stream and say so rather than
# silently handing over a truncated artifact.
MAX_STREAM_CHARS = 40_000
DEFAULT_TIMEOUT = 900


class ToolError(Exception):
    pass


def interpreter(repo) -> str:
    """The repo's own interpreter when it has one (F22: a verify command that
    names an ambient interpreter is a defect), else the running one."""
    venv = Path(repo) / ".venv" / "bin" / "python"
    return str(venv) if venv.is_file() else sys.executable


def execute(argv: list, *, cwd, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Run one harness command. Module-level on purpose: tests replace this
    attribute, so nothing in the calling convention can be mistaken for a way
    around the gate."""
    try:
        proc = subprocess.run(
            argv, cwd=str(cwd), capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return {
            "argv": argv,
            "exit_code": None,
            "stdout": "",
            "stderr": f"lex: command exceeded {timeout}s and was killed",
        }
    except OSError as exc:
        return {"argv": argv, "exit_code": None, "stdout": "", "stderr": f"lex: {exc}"}
    return {
        "argv": argv,
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


# --- tool definitions -------------------------------------------------------


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    properties: dict
    required: tuple = ()
    # Actions that only read. Anything not listed is gated. An empty set on a
    # tool that has an `action` axis means every action is gated.
    read_only_actions: frozenset = frozenset()
    # True for tools with no action axis that never mutate the tree.
    read_only: bool = False
    extra_schema: dict = field(default_factory=dict)

    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.properties,
                "required": list(self.required),
                **self.extra_schema,
            },
        }


_S = {"type": "string"}


def _s(desc: str) -> dict:
    return {"type": "string", "description": desc}


TOOLS = {
    t.name: t
    for t in [
        Tool(
            name="speccc",
            description=(
                "Compile the spec: `python -m harness.speccc <specs>`. Reports node "
                "count, atoms, levels, max width, the spec plan hash, the raw "
                "parallelism plan, and every W-grade warning. Read-only.\n\n"
                "Its raw levels are NOT the dispatch-safe plan — use join_plan for "
                "anything you intend to dispatch against."
            ),
            properties={"specs": _s("specs dir; default harness/specs")},
            read_only=True,
        ),
        Tool(
            name="join_plan",
            description=(
                "`python -m harness.join plan` — resolve the spec against the symbol "
                "index and print the DISPATCH-SAFE plan: levels after W02/W04 "
                "serialization, each node's compiled delta, and every finding "
                "(E05/E08/W02/W04/W05 plus speccc's warnings). Read-only. Exit 1 "
                "means at least one E-grade finding, not a crash."
            ),
            properties={
                "specs": _s("specs dir; default harness/specs"),
                "commit": _s("rev to compile against; default the worktree"),
            },
            read_only=True,
        ),
        Tool(
            name="join_packet",
            description=(
                "`python -m harness.join packet <node> --role <role>` — assemble one "
                "context packet and return it on stdout. Read-only; writes nothing. "
                "Use it to show the human what a dispatch would carry before asking "
                "for approval. Output is capped, so a long packet comes back "
                "truncated with a marker."
            ),
            properties={
                "node": _s("node id"),
                "role": {"type": "string", "enum": ["executor", "tester"]},
                "specs": _s("specs dir; default harness/specs"),
                "commit": _s("rev; default HEAD"),
                "worktree": {
                    "type": "boolean",
                    "description": "compile from the uncommitted worktree (stamped not replayable)",
                },
            },
            required=("node",),
            read_only=True,
        ),
        Tool(
            name="join_replay",
            description=(
                "`python -m harness.join replay <node> --commit C --shipped F` — "
                "rebuild a packet at its pinned commit and its pinned join version "
                "and compare byte-for-byte with the shipped file. Verdicts are "
                "disjoint: IDENTICAL (exit 0), DIVERGED (exit 1), CHECK-ERROR "
                "(exit 2). Read-only."
            ),
            properties={
                "node": _s("node id"),
                "role": {"type": "string", "enum": ["executor", "tester"]},
                "commit": _s("the commit the packet was shipped at"),
                "shipped": _s("path to the shipped packet, repo-relative"),
            },
            required=("node", "commit", "shipped"),
            read_only=True,
        ),
        Tool(
            name="join_record",
            description=(
                "`python -m harness.join record` — compose a dispatch record from the "
                "real artifacts (packet trailer, fence bytes, recomputed plan hashes) "
                "and cross-check them against the stated dispatch. Prints the record "
                "on stdout; it is not written to disk from here. Read-only. Exit 1 "
                "means the packet trailer disagrees with the dispatch you described."
            ),
            properties={
                "node": _s("node id"),
                "role": {"type": "string", "enum": ["executor", "tester"]},
                "commit": _s("the dispatch commit"),
                "specs": _s("specs dir; default harness/specs"),
                "packet": _s("path to the shipped packet"),
                "fence": _s("path to the fence.json used"),
                "dispatch_id": _s("dispatch id, e.g. 3d-1"),
                "started": _s("ISO 8601 start"),
                "finished": _s("ISO 8601 finish"),
                "tokens_out": {"type": "integer"},
                "tokens_in": {"type": "integer"},
            },
            required=(
                "node",
                "commit",
                "packet",
                "fence",
                "dispatch_id",
                "started",
                "finished",
            ),
            read_only=True,
        ),
        Tool(
            name="fence",
            description=(
                "`python -m harness.fence <action>` — the wall.\n"
                "  build   compile a node's fence and print it (read-only)\n"
                "  check   the diff gate: every changed path must be inside the "
                "fence (read-only; exit 1 = RUN FAILS)\n"
                "  apply   chmod out-of-scope tracked files read-only in a worktree\n"
                "  release restore the modes apply recorded\n"
                "apply and release change files on disk, so both stop for the "
                "human. dispatch_run prepare already builds and applies the fence "
                "for you — reach for apply/release only to repair one by hand."
            ),
            properties={
                "action": {
                    "type": "string",
                    "enum": ["build", "check", "apply", "release"],
                },
                "node": _s("node id (build only)"),
                "role": {"type": "string", "enum": ["executor", "tester"]},
                "specs": _s("specs dir; default harness/specs (build only)"),
                "commit": _s("rev (build only)"),
                "packet_hash": _s("packet hash to stamp into the fence (build only)"),
                "worktree": _s("worktree dir (apply/release/check)"),
            },
            required=("action",),
            read_only_actions=frozenset({"build", "check"}),
        ),
        Tool(
            name="dispatch_run",
            description=(
                "`python -m harness.dispatch <action>` — the deterministic hands.\n"
                "  canary   feed the write-fence hook the probes it must refuse and "
                "report whether the wall is live (read-only; proves the hook script, "
                "not its registration)\n"
                "  prepare  cut a fenced git worktree at a commit, compile and "
                "deliver the packet, and return the manifest plus the compiled spawn "
                "prompt\n"
                "  harvest  collect artifacts, run the diff gate, emit the dispatch "
                "record\n"
                "  teardown release the fence and REMOVE the worktree — destructive, "
                "harvest first\n"
                "prepare, harvest and teardown all stop for the human before they "
                "run. The agent spawn is not here and is not yours: prepare hands "
                "you a prompt, and a human runs it."
            ),
            properties={
                "action": {
                    "type": "string",
                    "enum": ["canary", "prepare", "harvest", "teardown"],
                },
                "node": _s("node id (prepare)"),
                "role": {"type": "string", "enum": ["executor", "tester"]},
                "specs": _s("specs dir; default harness/specs (prepare)"),
                "commit": _s("rev to cut the worktree at (prepare)"),
                "dispatch_id": _s("dispatch id; defaults to the node (prepare)"),
                "root": _s("dispatch root dir (prepare)"),
                "handoff": _s("file whose text lands in the packet handoff (prepare)"),
                "worktree": _s("worktree dir (canary/harvest/teardown)"),
                "evidence": _s("evidence dir to harvest into (harvest)"),
                "started": _s("ISO 8601 start (harvest)"),
                "finished": _s("ISO 8601 finish (harvest)"),
            },
            required=("action",),
            read_only_actions=frozenset({"canary"}),
        ),
        Tool(
            name="evals",
            description=(
                "The reproducible half of the standing gate: `join plan` at HEAD, "
                "then `join replay` over every shipped packet on record under "
                "docs/evidence/ whose dispatch record names it unambiguously. "
                "Read-only.\n\n"
                "It does NOT run the three-probe packet-sufficiency protocol. That "
                "gate lives in docs/evidence/step3t/gate.js, which is a JS runner "
                "and not a harness CLI, so lex has no lever for it — say so rather "
                "than reporting eval numbers as if the probes had run."
            ),
            properties={"specs": _s("specs dir; default harness/specs")},
            read_only=True,
        ),
    ]
}

TOOL_NAMES = tuple(TOOLS)


def schemas() -> list:
    return [TOOLS[name].schema() for name in TOOL_NAMES]


# --- the gate decision ------------------------------------------------------


def requires_confirmation(name: str, tool_input) -> bool:
    """Does this call need a human? Fails closed on everything unfamiliar.

    Nothing here reads a caller-supplied approval: an input carrying
    `{"confirm": true}`, `{"force": true}` or any other invented field is
    treated exactly like one that does not.
    """
    tool = TOOLS.get(name)
    if tool is None:
        return True  # unknown tool: gate it
    if tool.read_only:
        return False
    if not isinstance(tool_input, dict):
        return True
    action = tool_input.get("action")
    if not isinstance(action, str):
        return True  # no action named: gate it
    return action not in tool.read_only_actions


def _gate_detail(name: str, tool_input: dict, argv: list) -> str:
    return (
        f"tool:    {name}\n"
        f"input:   {json.dumps(tool_input, sort_keys=True)}\n"
        f"command: {' '.join(shlex.quote(a) for a in argv)}"
    )


def _gate_question(name: str, tool_input: dict) -> str:
    action = tool_input.get("action") if isinstance(tool_input, dict) else None
    subject = f"{name} {action}" if action else name
    if name == "dispatch_run" and action == "teardown":
        return f"run {subject}? This DESTROYS the worktree — harvest first."
    return f"run {subject}? It changes files on disk."


# --- argv construction ------------------------------------------------------


def _opt(argv: list, flag: str, value):
    if value is None or value == "":
        return
    argv.extend([flag, str(value)])


def build_argv(name: str, tool_input: dict, *, repo) -> list:
    """The exact command a tool call becomes. Pure — no side effects — so the
    gate can print it before anything runs."""
    if name not in TOOLS:
        raise ToolError(f"unknown tool {name!r}")
    if not isinstance(tool_input, dict):
        raise ToolError(f"{name}: tool input must be an object")
    py = interpreter(repo)
    specs = tool_input.get("specs") or "harness/specs"
    role = tool_input.get("role") or "executor"

    if name == "speccc":
        return [py, "-m", "harness.speccc", specs]

    if name == "join_plan":
        argv = [py, "-m", "harness.join", "plan", "--specs", specs, "--repo", "."]
        _opt(argv, "--commit", tool_input.get("commit"))
        return argv

    if name == "join_packet":
        argv = [
            py, "-m", "harness.join", "packet", _need(tool_input, "node", name),
            "--role", role, "--specs", specs, "--repo", ".",
        ]
        if tool_input.get("worktree"):
            argv.append("--worktree")
        else:
            _opt(argv, "--commit", tool_input.get("commit"))
        return argv

    if name == "join_replay":
        return [
            py, "-m", "harness.join", "replay", _need(tool_input, "node", name),
            "--role", role, "--repo", ".",
            "--commit", _need(tool_input, "commit", name),
            "--shipped", _need(tool_input, "shipped", name),
        ]

    if name == "join_record":
        argv = [
            py, "-m", "harness.join", "record", _need(tool_input, "node", name),
            "--role", role, "--repo", ".", "--specs", specs,
            "--commit", _need(tool_input, "commit", name),
            "--packet", _need(tool_input, "packet", name),
            "--fence", _need(tool_input, "fence", name),
            "--dispatch-id", _need(tool_input, "dispatch_id", name),
            "--started", _need(tool_input, "started", name),
            "--finished", _need(tool_input, "finished", name),
        ]
        _opt(argv, "--tokens-out", tool_input.get("tokens_out"))
        _opt(argv, "--tokens-in", tool_input.get("tokens_in"))
        return argv

    if name == "fence":
        action = _need(tool_input, "action", name)
        if action == "build":
            argv = [
                py, "-m", "harness.fence", "build", _need(tool_input, "node", name),
                "--specs", specs, "--repo", ".", "--role", role,
            ]
            _opt(argv, "--commit", tool_input.get("commit"))
            _opt(argv, "--packet-hash", tool_input.get("packet_hash"))
            return argv
        if action in ("apply", "release", "check"):
            return [
                py, "-m", "harness.fence", action,
                _need(tool_input, "worktree", name),
            ]
        raise ToolError(f"fence: unknown action {action!r}")

    if name == "dispatch_run":
        action = _need(tool_input, "action", name)
        if action == "prepare":
            argv = [
                py, "-m", "harness.dispatch", "prepare",
                _need(tool_input, "node", name),
                "--role", role, "--repo", ".", "--specs", specs,
                "--interpreter", py,
            ]
            _opt(argv, "--commit", tool_input.get("commit"))
            _opt(argv, "--id", tool_input.get("dispatch_id"))
            _opt(argv, "--root", tool_input.get("root"))
            _opt(argv, "--handoff", tool_input.get("handoff"))
            return argv
        if action == "harvest":
            argv = [
                py, "-m", "harness.dispatch", "harvest",
                _need(tool_input, "worktree", name),
            ]
            _opt(argv, "--evidence", tool_input.get("evidence"))
            _opt(argv, "--started", tool_input.get("started"))
            _opt(argv, "--finished", tool_input.get("finished"))
            return argv
        if action in ("canary", "teardown"):
            return [
                py, "-m", "harness.dispatch", action,
                _need(tool_input, "worktree", name),
            ]
        raise ToolError(f"dispatch_run: unknown action {action!r}")

    if name == "evals":
        return [py, "-m", "harness.join", "plan", "--specs", specs, "--repo", "."]

    raise ToolError(f"unknown tool {name!r}")  # pragma: no cover


def _need(tool_input: dict, key: str, name: str):
    value = tool_input.get(key)
    if value is None or value == "":
        raise ToolError(f"{name}: '{key}' is required")
    return value


# --- rendering --------------------------------------------------------------


def _clip(text: str) -> str:
    if len(text) <= MAX_STREAM_CHARS:
        return text
    return (
        text[:MAX_STREAM_CHARS]
        + f"\n… [lex truncated {len(text) - MAX_STREAM_CHARS} chars]"
    )


def render(result: dict) -> str:
    """One command's outcome, in the shape the model reads it."""
    if result.get("refused"):
        return result["message"]
    argv = " ".join(shlex.quote(a) for a in result.get("argv", []))
    parts = [f"$ {argv}", f"exit: {result.get('exit_code')}"]
    stdout, stderr = result.get("stdout", ""), result.get("stderr", "")
    parts.append("--- stdout ---\n" + (_clip(stdout) if stdout else "(empty)"))
    parts.append("--- stderr ---\n" + (_clip(stderr) if stderr else "(empty)"))
    return "\n".join(parts)


# --- evals ------------------------------------------------------------------


def _replay_targets(repo) -> tuple:
    """Shipped packets on record, paired with the dispatch record that pins
    their commit. A record with no packet beside it, or with several, is
    reported as ambiguous rather than guessed at."""
    evidence = Path(repo) / "docs" / "evidence"
    targets, ambiguous = [], []
    for record_path in sorted(evidence.glob("*/dispatch_record_*.json")):
        try:
            record = json.loads(record_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            ambiguous.append((record_path.name, f"unreadable: {exc}"))
            continue
        packets = sorted(
            p for p in record_path.parent.glob("packet*.md") if p.is_file()
        )
        rel = record_path.parent.relative_to(Path(repo))
        if len(packets) != 1:
            ambiguous.append(
                (str(rel), f"{len(packets)} packet files — replay one by hand")
            )
            continue
        if not record.get("node") or not record.get("commit"):
            ambiguous.append((str(rel), "record names no node/commit"))
            continue
        targets.append((record, packets[0].relative_to(Path(repo))))
    return targets, ambiguous


# Flip to False in the same commit that settles F36, and the qualifier
# disappears from every report that quotes this tool.
F36_OPEN = True


def run_evals(tool_input: dict, *, repo) -> dict:
    """join plan + replay over every unambiguous shipped packet on record."""
    specs = tool_input.get("specs") or "harness/specs"
    py = interpreter(repo)
    sections = []

    plan = execute(build_argv("join_plan", {"specs": specs}, repo=repo), cwd=repo)
    sections.append("### plan\n" + render(plan))

    # The reader over the loop's own artifacts (harness.evals): miss depth
    # per node, defects by catch layer, cost per dispatch, finding
    # recurrence. A harness command, so it is a legal lever.
    measured = execute([py, "-m", "harness.evals"], cwd=repo)
    sections.append("### measures\n" + render(measured))

    targets, ambiguous = _replay_targets(repo)
    verdicts = []
    for record, packet in targets:
        argv = [
            py, "-m", "harness.join", "replay", record["node"],
            "--role", record.get("role", "executor"), "--repo", ".",
            "--commit", record["commit"], "--shipped", str(packet),
        ]
        result = execute(argv, cwd=repo)
        verdict = {0: "IDENTICAL", 1: "DIVERGED", 2: "CHECK-ERROR"}.get(
            result["exit_code"], f"exit {result['exit_code']}"
        )
        # F36 is open: a packet carrying an injected handoff is not
        # reproducible from (spec, commit, join version), so an IDENTICAL
        # here does not yet mean what reports have been taking it to mean.
        # Ruled: no replay line is cited as IDENTICAL until the handoff's
        # relationship to the packet hash is settled. Enforced here rather
        # than left to whoever is writing the report.
        if verdict == "IDENTICAL" and F36_OPEN:
            verdict = "IDENTICAL* (NOT CITABLE — F36 open)"
        verdicts.append(verdict)
        sections.append(
            f"### replay {record['dispatch_id']} "
            f"({record['node']}/{record.get('role', 'executor')} @ "
            f"{record['commit'][:12]}) -> {verdict}\n" + render(result)
        )

    tally = {v: verdicts.count(v) for v in sorted(set(verdicts))}
    header = [
        "evals: the reproducible half of the standing gate.",
        f"replay: {len(verdicts)} packets on record — "
        + (", ".join(f"{n} {v}" for v, n in tally.items()) or "none found"),
    ]
    if ambiguous:
        header.append("not replayed (ambiguous, stated rather than guessed):")
        header += [f"  - {where}: {why}" for where, why in ambiguous]
    if F36_OPEN:
        header.append(
            "F36 OPEN: replay verdicts above are marked NOT CITABLE. A packet "
            "carrying an injected handoff is not rebuildable from the commit, "
            "so IDENTICAL does not currently mean what reports have read it "
            "to mean. Do not quote these as IDENTICAL until F36 is ruled."
        )
    header.append(
        "NOT RUN HERE: the three-probe packet-sufficiency protocol "
        "(docs/evidence/step3t/gate.js). lex has no lever for it — it is a JS "
        "runner, not a harness CLI. Do not report gate numbers from this tool."
    )
    body = "\n".join(header) + "\n\n" + "\n\n".join(sections)
    worst = max(
        (0 if v == "IDENTICAL" else 1 for v in verdicts), default=0
    ) or (1 if plan["exit_code"] not in (0, None) else 0)
    return {
        "argv": ["evals"],
        "exit_code": worst,
        "stdout": body,
        "stderr": "",
        "composite": True,
    }


# --- the entry point --------------------------------------------------------


def run_tool(name: str, tool_input, *, repo) -> dict:
    """Run one tool call, stopping for a human first when the call mutates.

    Note the signature: `(name, tool_input, repo)`. There is no approver
    argument, no options object, and no keyword that answers the gate — the
    only channel is stdin, and the only affirmative answers are y and yes.
    """
    if name not in TOOLS:
        return {
            "refused": True,
            "message": (
                f"lex has no tool named {name!r}. Its levers are: "
                f"{', '.join(TOOL_NAMES)}. If the moment needs one that does not "
                "exist, that is a finding to file, not something to improvise."
            ),
        }
    try:
        argv = build_argv(name, tool_input, repo=repo)
    except ToolError as exc:
        return {"refused": True, "message": f"lex: {exc}", "invalid": True}

    if requires_confirmation(name, tool_input):
        decision = confirm(
            _gate_question(name, tool_input), _gate_detail(name, tool_input, argv)
        )
        if not decision.approved:
            return {
                "refused": True,
                "answer": decision.answer,
                "gated": True,
                "message": (
                    f"REFUSED by the human at the ratification prompt (answer: "
                    f"{decision.answer!r}). {name} was NOT run and nothing on disk "
                    "changed. Do not retry it, do not route around it, and do not "
                    "describe it as done — report the refusal and ask what they "
                    "want instead."
                ),
            }
        result = (
            run_evals(tool_input, repo=repo)
            if name == "evals"
            else execute(argv, cwd=repo)
        )
        return {**result, "gated": True, "answer": decision.answer}

    if name == "evals":
        return run_evals(tool_input, repo=repo)
    return execute(argv, cwd=repo)
