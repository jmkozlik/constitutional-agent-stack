"""lex's tool surface: exactly the harness levers, and the argv they become."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from lex import tools as tools_mod
from lex.tools import TOOL_NAMES, build_argv, render, run_tool, schemas

REPO = Path(__file__).resolve().parent.parent

EXPECTED_TOOLS = {
    "speccc",
    "join_plan",
    "join_packet",
    "join_replay",
    "join_record",
    "fence",
    "dispatch_run",
    "evals",
}


@pytest.fixture
def spy(monkeypatch):
    calls = []

    def fake_execute(argv, *, cwd, timeout=None):
        calls.append(argv)
        return {"argv": argv, "exit_code": 0, "stdout": "out", "stderr": ""}

    monkeypatch.setattr(tools_mod, "execute", fake_execute)
    return calls


def test_tool_set_is_exactly_the_ratified_levers():
    assert set(TOOL_NAMES) == EXPECTED_TOOLS


def test_there_is_no_file_or_shell_tool():
    """The skill's one rule, in the tool list: no reader, no editor, no shell,
    no search. A tool named for any of them is the failure mode."""
    banned = {
        "read", "write", "edit", "bash", "shell", "exec", "run", "python",
        "grep", "glob", "search", "ls", "cat", "spawn", "task", "agent",
    }
    for name in TOOL_NAMES:
        assert name not in banned
        assert not any(name.startswith(f"{b}_") for b in banned)


def test_schemas_are_well_formed():
    for schema in schemas():
        assert schema["name"] in EXPECTED_TOOLS
        assert len(schema["description"]) > 40
        body = schema["input_schema"]
        assert body["type"] == "object"
        for key in body["required"]:
            assert key in body["properties"], f"{schema['name']}: {key}"


def _tail(argv):
    """Drop the interpreter so assertions read like the command line."""
    assert argv[1] == "-m"
    return argv[2:]


def test_every_command_is_a_harness_module(tmp_path):
    calls = [
        ("speccc", {}),
        ("join_plan", {}),
        ("join_packet", {"node": "gitio"}),
        ("join_replay", {"node": "gitio", "commit": "abc", "shipped": "p.md"}),
        ("fence", {"action": "build", "node": "gitio"}),
        ("fence", {"action": "check", "worktree": "/w"}),
        ("dispatch_run", {"action": "canary", "worktree": "/w"}),
        ("evals", {}),
    ]
    for name, tool_input in calls:
        argv = build_argv(name, tool_input, repo=tmp_path)
        assert argv[1] == "-m"
        assert argv[2].startswith("harness."), f"{name} -> {argv}"


def test_argv_shapes(tmp_path):
    assert _tail(build_argv("speccc", {}, repo=tmp_path)) == [
        "harness.speccc", "harness/specs"
    ]
    assert _tail(build_argv("join_plan", {"commit": "HEAD"}, repo=tmp_path)) == [
        "harness.join", "plan", "--specs", "harness/specs", "--repo", ".",
        "--commit", "HEAD",
    ]
    assert _tail(
        build_argv("join_packet", {"node": "gitio", "role": "tester"}, repo=tmp_path)
    ) == [
        "harness.join", "packet", "gitio", "--role", "tester",
        "--specs", "harness/specs", "--repo", ".",
    ]
    assert "--worktree" in build_argv(
        "join_packet", {"node": "gitio", "worktree": True}, repo=tmp_path
    )
    assert _tail(
        build_argv("dispatch_run", {"action": "teardown", "worktree": "/w"},
                   repo=tmp_path)
    ) == ["harness.dispatch", "teardown", "/w"]


def test_join_packet_cannot_write_a_file(tmp_path):
    """-o/--output is not exposed: a packet comes back on stdout, so no tool
    call can leave a file behind."""
    argv = build_argv("join_packet", {"node": "gitio", "specs": "s"}, repo=tmp_path)
    assert "-o" not in argv and "--output" not in argv
    assert "output" not in tools_mod.TOOLS["join_packet"].properties


def test_join_record_cannot_write_a_file(tmp_path):
    argv = build_argv(
        "join_record",
        {
            "node": "gitio", "commit": "abc", "packet": "p.md", "fence": "f.json",
            "dispatch_id": "3x", "started": "2026-01-01T00:00:00",
            "finished": "2026-01-01T00:01:00",
        },
        repo=tmp_path,
    )
    assert "-o" not in argv and "--output" not in argv


def test_fence_build_cannot_target_a_worktree(tmp_path):
    argv = build_argv("fence", {"action": "build", "node": "gitio"}, repo=tmp_path)
    assert "-t" not in argv and "--target" not in argv
    assert "target" not in tools_mod.TOOLS["fence"].properties


def test_missing_required_input_is_reported_not_guessed(tmp_path):
    result = run_tool("join_packet", {}, repo=tmp_path)
    assert result["refused"] is True
    assert "'node' is required" in result["message"]


def test_unknown_tool_is_a_finding_not_an_improvisation(tmp_path):
    result = run_tool("read_file", {"path": "x"}, repo=tmp_path)
    assert result["refused"] is True
    assert "no tool named" in result["message"]
    assert "finding" in result["message"]


def test_read_only_tools_run_without_a_gate(spy, tmp_path, monkeypatch):
    def explode(prompt=""):
        raise AssertionError("a read-only tool must not prompt the human")

    monkeypatch.setattr("builtins.input", explode)
    for name, tool_input in [
        ("speccc", {}),
        ("join_plan", {}),
        ("join_packet", {"node": "gitio"}),
        ("fence", {"action": "build", "node": "gitio"}),
        ("dispatch_run", {"action": "canary", "worktree": "/w"}),
    ]:
        result = run_tool(name, tool_input, repo=tmp_path)
        assert result.get("refused") is not True, name
    assert len(spy) == 5


def test_interpreter_prefers_the_repo_venv(tmp_path):
    assert tools_mod.interpreter(tmp_path) == sys.executable
    venv = tmp_path / ".venv" / "bin"
    venv.mkdir(parents=True)
    (venv / "python").write_text("#!/bin/sh\n")
    assert tools_mod.interpreter(tmp_path) == str(venv / "python")


def test_render_shows_the_command_and_both_streams():
    body = render(
        {"argv": ["py", "-m", "harness.join", "plan"], "exit_code": 1,
         "stdout": "levels", "stderr": "warned"}
    )
    assert "$ py -m harness.join plan" in body
    assert "exit: 1" in body
    assert "levels" in body and "warned" in body


def test_render_clips_a_long_stream(monkeypatch):
    monkeypatch.setattr(tools_mod, "MAX_STREAM_CHARS", 10)
    body = render({"argv": ["x"], "exit_code": 0, "stdout": "y" * 50, "stderr": ""})
    assert "lex truncated 40 chars" in body


def test_execute_captures_exit_code_and_streams(tmp_path):
    result = tools_mod.execute(
        [sys.executable, "-c", "import sys; print('o'); print('e', file=sys.stderr); sys.exit(3)"],
        cwd=tmp_path,
    )
    assert result["exit_code"] == 3
    assert result["stdout"].strip() == "o"
    assert result["stderr"].strip() == "e"


def test_execute_reports_a_missing_binary(tmp_path):
    result = tools_mod.execute(["definitely-not-a-binary-xyz"], cwd=tmp_path)
    assert result["exit_code"] is None
    assert "lex:" in result["stderr"]


# --- evals ------------------------------------------------------------------


def test_evals_pairs_records_with_packets_and_states_the_ambiguous(tmp_path):
    evidence = tmp_path / "docs" / "evidence"
    good = evidence / "stepA"
    good.mkdir(parents=True)
    (good / "dispatch_record_A.json").write_text(
        json.dumps({"dispatch_id": "A", "node": "gitio", "role": "executor",
                    "commit": "a" * 40})
    )
    (good / "packet.md").write_text("packet")
    twin = evidence / "stepB"
    twin.mkdir(parents=True)
    (twin / "dispatch_record_B.json").write_text(
        json.dumps({"dispatch_id": "B", "node": "gitio", "commit": "b" * 40})
    )
    (twin / "packet_one.md").write_text("p")
    (twin / "packet_two.md").write_text("p")

    targets, ambiguous = tools_mod._replay_targets(tmp_path)
    assert [t[0]["dispatch_id"] for t in targets] == ["A"]
    assert ambiguous and "stepB" in ambiguous[0][0]


def test_evals_says_what_it_does_not_run(spy, tmp_path):
    result = tools_mod.run_evals({}, repo=tmp_path)
    assert "NOT RUN HERE" in result["stdout"]
    assert "gate.js" in result["stdout"]
    assert "three-probe" in tools_mod.TOOLS["evals"].description


def test_evals_is_read_only(monkeypatch, spy, tmp_path):
    def explode(prompt=""):
        raise AssertionError("evals must not prompt the human")

    monkeypatch.setattr("builtins.input", explode)
    run_tool("evals", {}, repo=tmp_path)


# --- the levers actually exist ---------------------------------------------


@pytest.mark.parametrize(
    "name,tool_input",
    [
        ("speccc", {}),
        ("join_plan", {}),
        ("fence", {"action": "build", "node": "gitio"}),
    ],
)
def test_commands_run_for_real_against_this_repo(name, tool_input):
    """Not mocked: the argv lex builds is a command the harness answers."""
    argv = build_argv(name, tool_input, repo=REPO)
    proc = subprocess.run(argv, cwd=REPO, capture_output=True, text=True, timeout=300)
    assert proc.returncode in (0, 1), proc.stderr[-2000:]
    assert proc.stdout.strip(), f"{name} produced nothing on stdout"
