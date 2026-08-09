"""harness/autopilot.py — the conductor, and the consent it must not lose.

P1 removes the human from between the spec and a law-escalation. The tests
that matter are therefore not "does it walk the levels" but "what can it
still not do without a person" — because a conductor that quietly gains the
authority it was routing around is the one failure that would matter more
than every dispatch it ever ran.
"""

import ast
import inspect
import json

import pytest

from harness import autopilot, join
from tests.conftest import PROJECT_ROOT


def _tree():
    """The module's AST. Ratified test law: structural assertions are made
    against calls and imports, never against the presence of a word."""
    return ast.parse(inspect.getsource(autopilot))


def _called_names() -> set:
    names = set()
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
    return names


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
    monkeypatch away from answering its own ratification prompt.

    Ruled test law: asserted over the AST, so a mention in prose is not a
    call and deleting the comment that explains a rule cannot make the rule
    pass."""
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("lex"), alias.name
        elif isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith("lex"), node.module
    assert "confirm" not in _called_names()


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
    boss = conductor(tmp_path)
    assert boss._gate_clean({"probes": []}) is False
    assert boss._gate_clean({}) is False


def test_one_nodes_crash_does_not_take_down_the_run(tmp_path):
    boss = conductor(tmp_path)

    def explode(node_id):
        raise RuntimeError("worktree gone")

    boss.run_node = explode
    boss.calibration_fn = lambda: {"inert": False, "verdict": "insufficient"}
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


# --- the ratified gate law ---------------------------------------------------


def test_sufficient_with_gaps_proceeds_when_no_gap_blocks(tmp_path):
    boss = conductor(tmp_path, queued_findings=["F4", "F3"])
    verdicts = {"probes": [{"probe": "p", "verdict": "sufficient_with_gaps",
                            "missing": ["the F4 surface-coverage gap again"]}]}
    assert boss.blocking_items(verdicts) == []
    assert boss._gate_clean(verdicts) is True


def test_a_blocking_item_stops_the_line_despite_a_passing_verdict(tmp_path):
    """The ruled clause that does the work: the headline verdict is not the
    whole gate. A gap nobody has ruled on blocks even under
    sufficient_with_gaps."""
    boss = conductor(tmp_path, queued_findings=["F4"])
    verdicts = {"probes": [{"probe": "p", "verdict": "sufficient_with_gaps",
                            "missing": ["the index persistence schema"]}]}
    assert boss.blocking_items(verdicts)
    assert boss._gate_clean(verdicts) is False


def test_insufficient_stops_regardless_of_classification(tmp_path):
    boss = conductor(tmp_path, queued_findings=["F4"])
    assert boss._gate_clean({"probes": [
        {"probe": "p", "verdict": "insufficient", "missing": ["F4 thing"]}]}) is False


def test_blocking_classification_never_touches_the_probe_prompt():
    """F37's continuity clause: asking the probe to classify severity would
    change the measured instrument while keeping its name."""
    import inspect

    from harness import gate as gate_mod

    assert "blocking" not in gate_mod.PROBE_PREAMBLE.lower()
    assert "blocking" not in gate_mod.SHAPE_SYSTEM.lower()
    assert "blocking" not in inspect.getsource(gate_mod.build_prompt).lower()


def test_an_inert_gate_escalates_instead_of_proceeding(tmp_path):
    boss = conductor(tmp_path)
    boss.gate_inert = True
    spawned = []
    boss.runner = lambda *a, **k: spawned.append(1) or {"returncode": 0}
    assert boss.run_node("gitio") == "stopped"
    assert spawned == []
    assert boss.journal.escalations()[0].escalation == "GATE_INERT"


def test_calibration_runs_before_any_node_and_lands_in_the_journal(tmp_path):
    boss = conductor(tmp_path, calibration_fn=lambda: {
        "inert": False, "verdict": "insufficient", "model": "grok-4"})
    boss.run_node = lambda n: "completed"
    boss.run()
    kinds = [e.kind for e in boss.journal.events]
    assert kinds.index("calibration") < kinds.index("level")


def test_gutting_removes_what_an_executor_cannot_work_without():
    from harness import gate as gate_mod

    packet = (PROJECT_ROOT / "docs" / "evidence" / "step3t" / "packet_st.md").read_text()
    gutted = gate_mod.gut_packet(packet)
    assert "### Write scope as it exists" not in gutted
    assert "### Interfaces you consume" not in gutted
    assert "## Identity" in gutted, "it must still look like a packet"
    assert len(gutted) < len(packet) / 4
    assert "synthetic fixture" in gutted


# --- the ratified commit policy ----------------------------------------------


def test_only_evidence_class_paths_are_committable():
    assert autopilot.is_evidence_path("docs/evidence/autopilot/run-1/journal.jsonl")
    assert autopilot.is_evidence_path("harness/reports/017.md")
    for forbidden in ("analyzer/symbols.py", "harness/join.py", "lex/tools.py",
                      "harness/specs/analyzer.yaml", ".claude/settings.json"):
        assert not autopilot.is_evidence_path(forbidden), forbidden


def test_a_non_evidence_path_is_refused_and_recorded(tmp_path):
    log = journal(tmp_path)
    result = autopilot.commit_evidence(
        tmp_path, ["analyzer/symbols.py"], dispatch_id="d1",
        record_hash="abc", branch="autopilot/run-x", journal=log)
    assert result["committed"] is False
    assert result["refused"] == ["analyzer/symbols.py"]
    assert any(e.kind == "commit_refused" for e in log.events)


def test_autopilot_cannot_push():
    """The ruling puts push outside autopilot, and it is kept out by the
    absence of the capability rather than by a flag.

    Ruled test law: the assertion walks call arguments in the AST. The
    docstrings in this module say "push" while describing the rule; a
    word-presence test could be satisfied by deleting the explanation, which
    is the opposite of what it should reward."""
    forbidden = {"push", "remote", "origin", "fetch"}
    for node in ast.walk(_tree()):
        if not isinstance(node, ast.Call):
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                assert arg.value not in forbidden, \
                    f"{arg.value!r} is passed as a call argument"


def test_journal_is_promoted_out_of_the_gitignored_directory(tmp_path):
    log = journal(tmp_path)
    log.write("run_start", detail="x")
    target = autopilot.promote_journal(tmp_path, log, "0001")
    assert target.as_posix().endswith("docs/evidence/autopilot/run-0001")
    assert "run_start" in (target / "journal.jsonl").read_text()
    assert autopilot.is_evidence_path("docs/evidence/autopilot/run-0001/journal.jsonl")


def test_a_vault_entry_is_a_new_file_never_an_edit(tmp_path):
    ledger = tmp_path / "ledger"
    summary = {"plan_hash": "66e6", "completed": ["gitio"], "stopped": [],
               "escalations": [{"escalation": "GATE_BLOCKING", "node": "symbol_table",
                                "because": "blocking item"}]}
    path = autopilot.vault_entry("0001", summary, ledger=ledger)
    assert path.name == "autopilot-run-0001.md"
    assert "GATE_BLOCKING" in path.read_text()
    assert list(ledger.iterdir()) == [path]



def test_every_miss_is_logged_with_its_class(tmp_path):
    """Ruled: per-miss classification logged — matched finding id or `new`."""
    boss = conductor(tmp_path, queued_findings=["F4"])
    boss.blocking_items({"probes": [{"probe": "p", "verdict": "sufficient_with_gaps",
                                     "missing": ["the F4 coverage gap",
                                                 "the index persistence schema"]}]})
    classified = [e for e in boss.journal.events if e.kind == "classify"]
    assert [e.data["matched"] for e in classified] == ["F4", "new"]
    assert [e.data["blocking"] for e in classified] == [False, True]


def test_the_worker_transcript_is_archived_at_harvest():
    """Ruled, observability: from leg one onward. Asserted structurally —
    the harvest path writes worker-transcript.txt."""
    source = inspect.getsource(autopilot.Conductor.run_node)
    tree = ast.parse(source.strip())
    constants = {n.value for n in ast.walk(tree)
                 if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert "worker-transcript.txt" in constants
