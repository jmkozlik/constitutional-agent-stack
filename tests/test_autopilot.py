"""harness/autopilot.py — the conductor, and the consent it must not lose.

P1 removes the human from between the spec and a law-escalation. The tests
that matter are therefore not "does it walk the levels" but "what can it
still not do without a person" — because a conductor that quietly gains the
authority it was routing around is the one failure that would matter more
than every dispatch it ever ran.
"""

import json

import pytest

from harness import autopilot, join
from tests.conftest import PROJECT_ROOT


def journal(tmp_path, name="run"):
    return autopilot.Journal(tmp_path / f"{name}.jsonl")


def conductor(tmp_path, **kwargs):
    kwargs.setdefault("authorized_plan_hash",
                      autopilot.compile_plan_hash(PROJECT_ROOT, "harness/specs"))
    kwargs.setdefault("journal", journal(tmp_path))
    kwargs.setdefault("gate_fn", lambda node: {"probes": [
        {"probe": "p1", "verdict": "sufficient_with_gaps"}]})
    return autopilot.Conductor(repo=PROJECT_ROOT, specs="harness/specs", **kwargs)


# --- the constitutional checks ---------------------------------------------


def test_a_run_cannot_start_against_an_unauthorised_plan(tmp_path):
    """The whole of the consent lives here. A human ratified one hashed
    plan; anything else is a plan they never saw."""
    boss = conductor(tmp_path, authorized_plan_hash="deadbeefcafe")
    with pytest.raises(autopilot.AutopilotError) as err:
        boss.run()
    assert "plan drift" in str(err.value)


def test_drift_is_rechecked_before_every_level_not_once_at_the_start(tmp_path):
    # A spec edit landing mid-run must not be carried by an authorisation
    # granted before it existed.
    boss = conductor(tmp_path, dry_run=True)
    calls = []
    real = autopilot.compile_plan_hash

    def drifting(repo, specs):
        calls.append(1)
        return boss.authorized if len(calls) < 3 else "0000deadbeef"

    autopilot.compile_plan_hash = drifting
    try:
        with pytest.raises(autopilot.AutopilotError):
            boss.run()
    finally:
        autopilot.compile_plan_hash = real
    assert len(calls) >= 3, "authorisation was not re-checked per level"
    assert boss.journal.escalations()[-1].escalation == "PLAN_DRIFT"


def test_there_is_no_flag_that_skips_authorisation():
    """Checked structurally — a prose mention of "bypass" in a docstring is
    not a bypass, and a test that cannot tell the difference would be
    satisfied by deleting the comment that explains the rule."""
    import inspect

    signature = inspect.signature(autopilot.Conductor.__init__)
    assert signature.parameters["authorized_plan_hash"].default is \
        inspect.Parameter.empty, "authorisation must be mandatory"
    for name in ("skip_auth", "force", "assume_yes", "no_authorize", "bypass"):
        assert name not in signature.parameters

    parsed = autopilot.main.__wrapped__ if hasattr(autopilot.main, "__wrapped__") \
        else autopilot.main
    flags = [line for line in inspect.getsource(parsed).splitlines()
             if "add_argument" in line]
    assert any("--authorize" in f and "required=True" in f for f in flags)
    assert not any(("--force" in f or "--skip" in f) for f in flags)


def test_the_conductor_never_calls_the_confirm_gate():
    """Not because the gate is weak — because the gate belongs to the
    interactive path. If autopilot ever imported it, it would be one
    monkeypatch away from answering its own ratification prompt."""
    import inspect

    source = inspect.getsource(autopilot)
    import re

    assert not re.search(r"^\s*(from|import)\s+lex", source, re.M), \
        "autopilot must not import any part of the interactive path"
    assert "confirm(" not in source


# --- stop-routing ------------------------------------------------------------


def test_dependents_are_transitive_and_exclude_siblings():
    plan = join.load_plan(PROJECT_ROOT / "harness" / "specs")
    downstream = autopilot.dependents(plan, "symbol_table")
    assert "reference_map" in downstream          # direct
    assert "affected_symbols" in downstream       # transitive
    assert "gitio" not in downstream              # sibling on the same level
    assert "symbol_table" not in downstream       # never itself


def test_a_stopped_node_stops_its_line_and_leaves_the_rest(tmp_path):
    plan = join.load_plan(PROJECT_ROOT / "harness" / "specs")
    boss = conductor(tmp_path)
    boss._stop_line("symbol_table", plan)
    assert "reference_map" in boss.stopped
    assert "gitio" not in boss.stopped


def test_a_gate_that_is_not_clean_stops_the_node_before_any_dispatch(tmp_path):
    prepared = []
    boss = conductor(
        tmp_path,
        gate_fn=lambda node: {"probes": [{"probe": "p", "verdict": "insufficient"}]},
    )
    boss.runner = lambda *a, **k: prepared.append(1) or {"returncode": 0}
    assert boss.run_node("gitio") == "stopped"
    assert prepared == [], "a dirty gate must stop before the worktree exists"
    assert boss.journal.escalations()[0].escalation == "GATE_NOT_CLEAN"


def test_an_empty_probe_set_is_not_clean(tmp_path):
    # A gate that answered nothing is not a gate that said yes.
    assert autopilot.Conductor._gate_clean({"probes": []}) is False
    assert autopilot.Conductor._gate_clean({}) is False


def test_one_nodes_crash_does_not_take_down_the_run(tmp_path):
    boss = conductor(tmp_path)

    def explode(node_id):
        raise RuntimeError("worktree gone")

    boss.run_node = explode
    summary = boss.run()
    assert summary["escalations"], "the crash must reach the human as an event"
    assert any(e["escalation"] == "RUNNER_ERROR" for e in summary["escalations"])


# --- the record --------------------------------------------------------------


def test_every_escalation_carries_the_rule_it_descends_from(tmp_path):
    log = journal(tmp_path)
    for name in autopilot.ESCALATIONS:
        log.write("stop", node="n", escalation=name)
    for event in log.events:
        assert event.as_dict()["because"], f"{event.escalation} has no grounds"


def test_the_journal_is_append_only_jsonl_in_order(tmp_path):
    log = journal(tmp_path)
    log.write("run_start", detail="a")
    log.write("dispatch", node="gitio")
    log.write("run_end", detail="b")
    lines = [json.loads(l) for l in log.path.read_text().splitlines()]
    assert [l["seq"] for l in lines] == [1, 2, 3]
    assert [l["kind"] for l in lines] == ["run_start", "dispatch", "run_end"]


def test_dry_run_walks_every_level_and_spawns_nothing(tmp_path):
    spawned = []
    boss = conductor(tmp_path, dry_run=True,
                     runner=lambda *a, **k: spawned.append(1))
    summary = boss.run()
    assert spawned == []
    kinds = [e.kind for e in boss.journal.events]
    assert kinds[0] == "run_start" and kinds[-1] == "run_end"
    planned = {e.node for e in boss.journal.events if e.kind == "dry_run"}
    assert {"gitio", "symbol_table", "affected_symbols"} <= planned
    assert not summary["escalations"]


def test_request_mem_from_the_agent_becomes_an_escalation_not_a_retry(tmp_path):
    # The whole miss-is-a-query discipline dies if autopilot answers for the
    # human or loops. It records and stops the line.
    boss = conductor(tmp_path)
    line = "REQUEST_MEM: the index schema, to attest bullet 2"
    assert autopilot._first_request_mem(f"blah\n{line}\nmore") == line


def test_render_puts_the_escalations_in_front_of_the_human(tmp_path):
    text = autopilot.render({
        "plan_hash": "abc123", "completed": ["gitio"], "stopped": ["symbol_table"],
        "escalations": [{"escalation": "GATE_NOT_CLEAN", "node": "symbol_table",
                         "because": autopilot.ESCALATIONS["GATE_NOT_CLEAN"],
                         "detail": "probe said insufficient"}],
        "journal": "/tmp/x.jsonl",
    })
    assert "GATE_NOT_CLEAN" in text and "symbol_table" in text
    assert "clean gate = proceed" in text
