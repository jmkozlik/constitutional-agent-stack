"""The law, asserted.

These tests are the reason lex v1 exists rather than lex v0 with a firmer
prompt: they establish, mechanically, that no code path in lex can approve a
mutating action on the model's say-so.

Three claims, each with its own test:
  1. only an explicit y/yes approves, and every other answer refuses;
  2. a refusal does not execute — the subprocess is never reached;
  3. there is no parameter, keyword, env var, or tool-input field that
     substitutes for the human.
"""

import ast
import inspect
import os
from pathlib import Path

import pytest

from lex import confirm as confirm_mod
from lex import tools as tools_mod
from lex.confirm import AFFIRMATIVE, Decision, confirm

LEX_DIR = Path(__file__).resolve().parent.parent / "lex"


@pytest.fixture
def answers(monkeypatch):
    """Stand in for the human at the terminal, one queued answer per prompt."""
    queue = []

    def fake_input(prompt=""):
        if not queue:
            raise EOFError
        return queue.pop(0)

    monkeypatch.setattr("builtins.input", fake_input)
    return queue


@pytest.fixture
def spy(monkeypatch):
    """Replace the subprocess layer so a test can prove it was never reached."""
    calls = []

    def fake_execute(argv, *, cwd, timeout=None):
        calls.append(argv)
        return {"argv": argv, "exit_code": 0, "stdout": "ran", "stderr": ""}

    monkeypatch.setattr(tools_mod, "execute", fake_execute)
    return calls


# --- claim 1: only y/yes approves -------------------------------------------


@pytest.mark.parametrize("answer", ["y", "Y", "yes", "YES", " yes ", "Yes"])
def test_affirmative_answers_approve(answers, answer):
    answers.append(answer)
    assert confirm("do the thing").approved is True


@pytest.mark.parametrize(
    "answer",
    [
        "",  # a bare Enter is NOT a default yes
        " ",
        "n",
        "no",
        "N",
        "sure",  # meaning yes, but not the word: refuse
        "ok",
        "yep",
        "yes please",
        "y y",
        "ratify",
        "true",
        "1",
        "--yes",
        "proceed",
    ],
)
def test_every_other_answer_refuses(answers, answer):
    answers.append(answer)
    decision = confirm("do the thing")
    assert decision.approved is False
    assert decision.answer == answer


def test_eof_refuses(answers):
    # queue left empty -> fake_input raises EOFError
    assert confirm("do the thing").approved is False


def test_affirmative_set_is_exactly_y_and_yes():
    assert AFFIRMATIVE == frozenset({"y", "yes"})


def test_decision_is_falsey_when_refused():
    assert not Decision(False, "n")
    assert Decision(True, "y")


# --- claim 2: a refusal does not execute ------------------------------------


GATED_CALLS = [
    ("dispatch_run", {"action": "prepare", "node": "index_assembly"}),
    ("dispatch_run", {"action": "harvest", "worktree": "/tmp/wt"}),
    ("dispatch_run", {"action": "teardown", "worktree": "/tmp/wt"}),
    ("fence", {"action": "apply", "worktree": "/tmp/wt"}),
    ("fence", {"action": "release", "worktree": "/tmp/wt"}),
]


@pytest.mark.parametrize("name,tool_input", GATED_CALLS)
def test_refused_gate_does_not_execute(answers, spy, tmp_path, name, tool_input):
    answers.append("n")
    result = tools_mod.run_tool(name, tool_input, repo=tmp_path)
    assert spy == [], "a refused gate must never reach the subprocess layer"
    assert result["refused"] is True
    assert result["gated"] is True
    assert "REFUSED" in result["message"]


@pytest.mark.parametrize("name,tool_input", GATED_CALLS)
def test_authorised_gate_executes(answers, spy, tmp_path, name, tool_input):
    answers.append("y")
    result = tools_mod.run_tool(name, tool_input, repo=tmp_path)
    assert len(spy) == 1, "an authorised gate must run exactly once"
    assert result.get("refused") is not True
    assert result["gated"] is True


def test_empty_answer_does_not_execute(answers, spy, tmp_path):
    answers.append("")
    tools_mod.run_tool("dispatch_run", {"action": "teardown", "worktree": "/x"},
                       repo=tmp_path)
    assert spy == []


def test_no_answer_at_all_does_not_execute(spy, tmp_path, monkeypatch):
    def no_terminal(prompt=""):
        raise EOFError

    monkeypatch.setattr("builtins.input", no_terminal)
    result = tools_mod.run_tool(
        "dispatch_run", {"action": "prepare", "node": "gitio"}, repo=tmp_path
    )
    assert spy == []
    assert result["refused"] is True


# --- claim 3: nothing substitutes for the human -----------------------------


def test_confirm_signature_has_no_bypass():
    params = inspect.signature(confirm).parameters
    assert list(params) == ["question", "detail"], (
        "confirm() takes the question and the drafted action and nothing "
        "else — a third parameter is a way to answer it in code"
    )
    assert params["question"].annotation is str
    assert params["detail"].default == ""


@pytest.mark.parametrize(
    "bypass",
    [
        {"confirm": True},
        {"yes": True},
        {"force": True},
        {"auto_approve": True},
        {"approved": True},
        {"assume_yes": True},
        {"ratified": True},
        {"skip_confirmation": True},
        {"_confirmed": "y"},
        {"answer": "y"},
    ],
)
def test_model_supplied_fields_cannot_skip_the_gate(answers, spy, tmp_path, bypass):
    """Whatever the model puts in tool_input, the gate still runs and 'n'
    still refuses. The gate decision is derived from the tool name and its
    action only."""
    answers.append("n")
    tool_input = {"action": "teardown", "worktree": "/tmp/wt", **bypass}
    assert tools_mod.requires_confirmation("dispatch_run", tool_input) is True
    result = tools_mod.run_tool("dispatch_run", tool_input, repo=tmp_path)
    assert spy == []
    assert result["refused"] is True


def test_gate_fails_closed(tmp_path):
    """Anything unrecognised is gated, not waved through."""
    assert tools_mod.requires_confirmation("dispatch_run", {}) is True
    assert tools_mod.requires_confirmation("dispatch_run", {"action": None}) is True
    assert tools_mod.requires_confirmation("dispatch_run", {"action": "PREPARE"}) is True
    assert tools_mod.requires_confirmation("dispatch_run", {"action": "prepar"}) is True
    assert tools_mod.requires_confirmation("fence", {"action": "appply"}) is True
    assert tools_mod.requires_confirmation("dispatch_run", "prepare") is True
    assert tools_mod.requires_confirmation("no_such_tool", {"action": "x"}) is True
    # ...and only the named read-only actions are ungated.
    assert tools_mod.requires_confirmation("dispatch_run", {"action": "canary"}) is False
    assert tools_mod.requires_confirmation("fence", {"action": "check"}) is False


def test_every_mutating_action_is_gated():
    """The enum in each schema, minus the declared read-only actions, is
    exactly the set that stops for a human — no action can be added to a tool
    without landing on one side of the line."""
    for name in ("dispatch_run", "fence"):
        tool = tools_mod.TOOLS[name]
        actions = set(tool.properties["action"]["enum"])
        gated = {a for a in actions if requires(name, a)}
        assert gated == actions - tool.read_only_actions
        assert gated, f"{name} declares no gated action"
    assert tools_mod.TOOLS["dispatch_run"].read_only_actions == frozenset({"canary"})
    assert {"prepare", "harvest", "teardown"} <= set(
        tools_mod.TOOLS["dispatch_run"].properties["action"]["enum"]
    )


def requires(name, action):
    return tools_mod.requires_confirmation(name, {"action": action})


def test_confirm_module_reads_no_environment():
    """No env var can pre-answer a gate. Asserted against the source, so a
    later os.environ lookup fails this test rather than shipping quietly."""
    source = (LEX_DIR / "confirm.py").read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in ("environ", "getenv"):
            pytest.fail("confirm.py must not consult the environment")
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "os", "confirm.py must not import os"
        if isinstance(node, ast.ImportFrom):
            assert node.module != "os", "confirm.py must not import from os"


def test_no_auto_yes_identifier_anywhere_in_lex():
    """Prose may name these to say they are absent; code may not use them.
    So the check walks the AST — identifiers, arguments, keywords, attributes
    and string literals — rather than the file text."""
    forbidden = {
        "auto_yes", "assume_yes", "skip_confirm", "skip_confirmation",
        "no_confirm", "force_yes", "auto_approve", "auto_ratify",
        "LEX_YES", "LEX_AUTO_APPROVE", "LEX_RATIFY", "--yes",
    }
    for path in sorted(LEX_DIR.glob("*.py")):
        tree = ast.parse(path.read_text())
        docstring_nodes = set()
        for node in ast.walk(tree):
            if isinstance(
                node,
                (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                first = node.body[0] if node.body else None
                if (
                    isinstance(first, ast.Expr)
                    and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)
                ):
                    docstring_nodes.add(id(first.value))
        used = set()
        for node in ast.walk(tree):
            if id(node) in docstring_nodes:
                continue
            if isinstance(node, ast.Name):
                used.add(node.id)
            elif isinstance(node, ast.arg):
                used.add(node.arg)
            elif isinstance(node, ast.keyword) and node.arg:
                used.add(node.arg)
            elif isinstance(node, ast.Attribute):
                used.add(node.attr)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                used.add(node.value)
        leaked = {
            needle
            for needle in forbidden
            if needle in used or any(needle in u for u in used if isinstance(u, str))
        }
        assert not leaked, f"{path.name} uses {leaked}"


def test_run_tool_has_no_approver_parameter():
    """run_tool takes the call and the repo. There is no seam an approval can
    be threaded through — the only channel is stdin."""
    params = inspect.signature(tools_mod.run_tool).parameters
    assert list(params) == ["name", "tool_input", "repo"]
    assert params["repo"].kind is inspect.Parameter.KEYWORD_ONLY


def test_gate_is_not_disabled_by_a_non_tty(answers, spy, tmp_path, monkeypatch):
    """Refusing when stdin is not a terminal is the safe direction, and lex
    must not branch on it at all."""
    monkeypatch.setattr("sys.stdin", type("S", (), {"isatty": lambda self: False})())
    answers.append("n")
    result = tools_mod.run_tool(
        "fence", {"action": "apply", "worktree": "/x"}, repo=tmp_path
    )
    assert spy == []
    assert result["refused"] is True


def test_environment_does_not_leak_an_approval(answers, spy, tmp_path, monkeypatch):
    for var in ("LEX_YES", "LEX_AUTO_APPROVE", "CI", "LEX_RATIFY", "LEX_FENCE"):
        monkeypatch.setenv(var, "1")
    answers.append("n")
    result = tools_mod.run_tool(
        "dispatch_run", {"action": "prepare", "node": "gitio"}, repo=tmp_path
    )
    assert spy == []
    assert result["refused"] is True
    assert os.environ["LEX_YES"] == "1"  # the vars were really set
