"""The agent loop, the prompt transfer, the verbs, and the session log.

No live API calls: the client is a fake whose `messages.stream(...)` replays
scripted turns and records the params it was handed.
"""

import io
import json
from pathlib import Path

import pytest

from lex import agent, prompt, repl, request_mem
from lex import tools as tools_mod
from lex.transcript import Transcript

REPO = Path(__file__).resolve().parent.parent


# --- the fake client --------------------------------------------------------


class Block:
    def __init__(self, **fields):
        self.__dict__.update(fields)


class Message:
    def __init__(self, content, stop_reason="end_turn"):
        self.content = content
        self.stop_reason = stop_reason
        self.stop_details = None


class FakeStream:
    def __init__(self, message):
        self.message = message

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __iter__(self):
        return iter(())

    def get_final_message(self):
        return self.message


class FakeMessages:
    def __init__(self, turns):
        self.turns = list(turns)
        self.params = []

    def stream(self, **params):
        self.params.append(params)
        if not self.turns:
            raise AssertionError("the loop asked for more turns than were scripted")
        return FakeStream(self.turns.pop(0))


class FakeClient:
    def __init__(self, turns):
        self.messages = FakeMessages(turns)


def text(body):
    return Block(type="text", text=body)


def tool_use(name, tool_input, ident="tu_1"):
    return Block(type="tool_use", name=name, input=tool_input, id=ident)


@pytest.fixture
def session_factory(tmp_path):
    def make(turns, *, repo=None):
        client = FakeClient(turns)
        log = Transcript(repo or tmp_path, model=agent.MODEL)
        session = agent.Session(
            client, system="SKILL BODY", repo=repo or tmp_path,
            transcript=log, out=io.StringIO(),
        )
        return client, session, log

    return make


# --- request shape ----------------------------------------------------------


def test_request_uses_opus_5_the_skill_verbatim_and_only_harness_tools(
    session_factory,
):
    client, session, _ = session_factory([Message([text("hi")])])
    session.send("go")
    params = client.messages.params[0]
    assert params["model"] == "claude-opus-5"
    assert params["system"][0]["text"] == "SKILL BODY"
    assert {t["name"] for t in params["tools"]} == set(tools_mod.TOOL_NAMES)
    assert params["thinking"]["type"] == "adaptive"


def test_conversation_accumulates_across_turns(session_factory):
    client, session, _ = session_factory(
        [Message([text("one")]), Message([text("two")])]
    )
    session.send("first")
    session.send("second")
    assert [m["role"] for m in session.messages] == [
        "user", "assistant", "user", "assistant"
    ]
    assert client.messages.params[1]["messages"] is session.messages


# --- the tool loop ----------------------------------------------------------


def test_tool_result_is_fed_back(session_factory, monkeypatch, tmp_path):
    monkeypatch.setattr(
        tools_mod, "execute",
        lambda argv, *, cwd, timeout=None: {
            "argv": argv, "exit_code": 0, "stdout": "PLAN OK", "stderr": ""
        },
    )
    _, session, log = session_factory(
        [Message([tool_use("join_plan", {})]), Message([text("that is the plan")])]
    )
    session.send("/plan")
    results = session.messages[2]["content"]
    assert results[0]["type"] == "tool_result"
    assert "PLAN OK" in results[0]["content"]
    assert log.tool_calls == 1


def test_a_refused_gate_comes_back_as_a_tool_result_and_the_loop_continues(
    session_factory, monkeypatch, tmp_path
):
    calls = []
    monkeypatch.setattr(
        tools_mod, "execute",
        lambda argv, *, cwd, timeout=None: calls.append(argv) or {
            "argv": argv, "exit_code": 0, "stdout": "", "stderr": ""
        },
    )
    monkeypatch.setattr("builtins.input", lambda prompt="": "n")
    _, session, log = session_factory(
        [
            Message([tool_use("dispatch_run", {"action": "prepare", "node": "gitio"})]),
            Message([text("understood — not dispatched")]),
        ]
    )
    session.send("/run gitio")
    body = session.messages[2]["content"][0]["content"]
    assert "REFUSED" in body and "NOT run" in body
    assert calls == []
    assert log.gates == [
        {
            "tool": "dispatch_run",
            "input": {"action": "prepare", "node": "gitio"},
            "answer": "n",
            "approved": False,
        }
    ]


def test_the_loop_stops_at_the_round_guard(session_factory, monkeypatch):
    monkeypatch.setattr(
        tools_mod, "execute",
        lambda argv, *, cwd, timeout=None: {
            "argv": argv, "exit_code": 0, "stdout": "", "stderr": ""
        },
    )
    turns = [Message([tool_use("join_plan", {})]) for _ in range(agent.MAX_TOOL_ROUNDS + 1)]
    _, session, log = session_factory(turns)
    session.send("loop")
    assert any("runtime guard" in e.get("text", "") for e in log.entries)


def test_a_refusal_stop_reason_ends_the_turn(session_factory):
    _, session, log = session_factory([Message([], stop_reason="refusal")])
    session.send("go")
    assert any("declined this turn" in e.get("text", "") for e in log.entries)


# --- REQUEST_MEM ------------------------------------------------------------


def test_scan_finds_request_mem_lines():
    body = (
        "attestation\nREQUEST_MEM: is `repo` a git repo?\n"
        "more\n  REQUEST_MEM:   are revs git revisions?  \n"
        "REQUEST_MEM: is `repo` a git repo?\n"
    )
    assert request_mem.scan(body) == [
        "is `repo` a git repo?",
        "are revs git revisions?",
    ]
    assert request_mem.scan("nothing here") == []


def test_request_mem_in_tool_output_is_asked_and_answered(
    session_factory, monkeypatch
):
    monkeypatch.setattr(
        tools_mod, "execute",
        lambda argv, *, cwd, timeout=None: {
            "argv": argv, "exit_code": 0,
            "stdout": "REQUEST_MEM: is repo a git repo?", "stderr": "",
        },
    )
    monkeypatch.setattr("builtins.input", lambda prompt="": "yes, always a git repo")
    _, session, log = session_factory(
        [Message([tool_use("join_plan", {})]), Message([text("noted")])]
    )
    session.send("/plan")
    body = session.messages[2]["content"][0]["content"]
    assert "REQUEST_MEM answers from the operator's human" in body
    assert "yes, always a git repo" in body
    assert log.request_mems[0]["source"] == "tool:join_plan"


def test_request_mem_in_the_operators_own_text_is_asked(session_factory, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt="": "option B")
    _, session, log = session_factory(
        [
            Message([text("REQUEST_MEM: which candidate ruling?")]),
            Message([text("proceeding on B")]),
        ]
    )
    session.send("status")
    follow_up = session.messages[2]
    assert follow_up["role"] == "user"
    assert "option B" in follow_up["content"]
    assert log.request_mems[0]["source"] == "lex"


def test_unanswered_request_mem_is_marked_not_filled_in(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt="": "")
    assert request_mem.ask("what is X?") == "(no answer given)"


# --- the system prompt ------------------------------------------------------


def test_system_prompt_is_the_skill_body_verbatim():
    skill = (REPO / prompt.SKILL).read_text(encoding="utf-8")
    body = prompt.load_system_prompt(REPO)
    assert body in skill, "the prompt must be a slice of the skill, not a rewrite"
    assert not body.startswith("---")
    assert "name: lex-operator" not in body
    for line in (
        "**Your levers are the harness commands. Nothing else.**",
        "**Never self-ratify.**",
        "Dispatch is never automatic.",
    ):
        assert line in body


def test_strip_frontmatter_leaves_a_plain_file_alone():
    assert prompt.strip_frontmatter("# title\nbody\n") == "# title\nbody\n"
    assert prompt.strip_frontmatter("---\na: b\n---\n# t\n") == "# t\n"
    # An unterminated fence is not frontmatter.
    assert prompt.strip_frontmatter("---\na: b\n") == "---\na: b\n"


def test_missing_skill_is_an_error_not_a_default(tmp_path):
    with pytest.raises(prompt.PromptError):
        prompt.load_system_prompt(tmp_path)


# --- verbs and the opening turn ---------------------------------------------


@pytest.mark.parametrize("verb", repl.VERBS)
def test_every_verb_expands_to_its_command_file_verbatim(verb):
    """The verb bodies are the repo's command files, not prose in Python."""
    body = repl.expand(REPO, f"/{verb}")
    source = prompt.strip_frontmatter(
        (REPO / repl.COMMANDS / f"{verb}.md").read_text()
    ).strip()
    assert body == source.replace("$ARGUMENTS", "(no arguments given)")


def test_run_verb_carries_its_arguments():
    body = repl.expand(REPO, "/run index_assembly --role tester")
    assert "index_assembly --role tester" in body
    assert "$ARGUMENTS" not in body


def test_unknown_verb_expands_to_nothing():
    assert repl.expand(REPO, "/deploy") == ""


def test_opening_turn_delivers_standing_state_and_names_the_gate():
    body = repl.opening_turn(REPO, tools=tools_mod.TOOL_NAMES)
    assert "harness/LOOP.md" in body
    assert "LOOP — standing state" in body  # LOOP.md's own first line
    latest = sorted((REPO / "harness" / "reports").glob("[0-9][0-9][0-9].md"))[-1]
    assert f"harness/reports/{latest.name}" in body
    assert latest.read_text(encoding="utf-8")[:200] in body
    assert "explicit y/n at the terminal" in body
    assert "there is no\n  argument that skips it" in body
    assert "dispatch_run" in body


def test_standing_state_says_so_when_the_files_are_absent(tmp_path):
    (tmp_path / "harness" / "reports").mkdir(parents=True)
    body = repl.standing_state(tmp_path)
    assert "MISSING" in body
    assert "no numbered reports" in body


# --- the session log --------------------------------------------------------


def test_session_log_is_a_transcript_not_a_report(tmp_path):
    reports = tmp_path / "harness" / "reports"
    reports.mkdir(parents=True)
    (reports / "009.md").write_text("# report 009")
    log = Transcript(tmp_path, model="claude-opus-5", commit="deadbeef")
    log.human("/plan")
    log.operator("here is the plan")
    log.tool("join_plan", {}, {"argv": ["py"], "exit_code": 0, "stdout": "ok",
                               "stderr": ""})
    log.tool(
        "dispatch_run", {"action": "teardown"},
        {"refused": True, "gated": True, "answer": "n", "message": "REFUSED"},
    )
    log.request_mem([("is repo a git repo?", "yes")], source="tool:join_plan")
    target = log.write()

    assert target.parent == tmp_path / "harness" / "reports" / "sessions"
    assert target.name.startswith("lex-")
    body = target.read_text()
    assert "not a ratified report" in body
    assert "next free report number is **010**" in body
    assert "REFUSED" in body and "`n`" in body
    assert "is repo a git repo?" in body
    assert "here is the plan" in body
    # It must not masquerade as a numbered report.
    assert not (reports / "010.md").exists()
    assert list(reports.glob("[0-9][0-9][0-9].md")) == [reports / "009.md"]


def test_next_report_number_walks_the_real_reports_dir():
    from lex.transcript import next_report_number

    existing = sorted((REPO / "harness" / "reports").glob("[0-9][0-9][0-9].md"))
    expected = f"{int(existing[-1].stem) + 1:03d}"
    assert next_report_number(REPO) == expected
