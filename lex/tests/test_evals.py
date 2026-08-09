"""harness/evals.py — the reader over what the loop has already produced.

Four measures, all derived from artifacts on disk rather than from anyone's
recollection: miss depth per node, defects by catch layer, cost per
dispatch, finding recurrence.
"""

import json

from harness import evals


def write_record(dirpath, dispatch_id, **fields):
    dirpath.mkdir(parents=True, exist_ok=True)
    record = {
        "record": "dispatch",
        "dispatch_id": dispatch_id,
        "node": fields.pop("node", "some_node"),
        "role": fields.pop("role", "executor"),
        "commit": "0" * 40,
        "gate": "clean",
        **fields,
    }
    (dirpath / f"dispatch_record_{dispatch_id}.json").write_text(
        json.dumps(record, indent=2)
    )
    return record


def test_cost_per_dispatch_reads_records(tmp_path):
    ev = tmp_path / "evidence"
    write_record(ev / "a", "d1", node="alpha", wall_clock_seconds=600)
    write_record(ev / "b", "d2", node="beta", wall_clock_seconds=1200,
                 reads_out_of_packet=[{"path": "x.py"}], self_served_misses=1)
    report = evals.collect(evidence=ev, reports=tmp_path / "reports")
    costs = {c["dispatch_id"]: c for c in report["cost_per_dispatch"]}
    assert costs["d1"]["wall_clock_seconds"] == 600
    assert costs["d2"]["self_served_misses"] == 1
    assert report["totals"]["dispatches"] == 2


def test_miss_depth_per_node_counts_request_mem_lines(tmp_path):
    ev = tmp_path / "evidence"
    d = ev / "a"
    write_record(d, "d1", node="alpha")
    (d / "harvest-out").mkdir(parents=True)
    (d / "harvest-out" / "attestation.md").write_text(
        "REQUEST_MEM: the first thing\nsome prose\nREQUEST_MEM: the second\n"
    )
    report = evals.collect(evidence=ev, reports=tmp_path / "reports")
    depth = {m["node"]: m for m in report["miss_depth_per_node"]}
    assert depth["alpha"]["request_mem"] == 2
    assert depth["alpha"]["dispatches"] == 1


def test_defects_by_catch_layer(tmp_path):
    ev = tmp_path / "evidence"
    d = ev / "a"
    write_record(d, "d1", node="alpha")
    (d / "harvest-out").mkdir(parents=True)
    (d / "harvest-out" / "defects.md").write_text("## D-1 — thing\n## D-2 — other\n")
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "001.md").write_text(
        "| **F9** | **NEW, non-blocking** — found by the gate |\n"
        "| **F10** | **NEW** — red-team found it |\n"
    )
    report = evals.collect(evidence=ev, reports=reports)
    layers = report["defects_by_catch_layer"]
    assert layers["dispatch"] == 2      # the two filed defects
    assert layers["report"] == 2        # the two NEW findings in the ledger


def test_finding_recurrence_counts_reports_mentioning_each(tmp_path):
    ev = tmp_path / "evidence"
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "001.md").write_text("| **F3** | NEW |\n")
    (reports / "002.md").write_text("F3 still open; F4 filed\n")
    (reports / "003.md").write_text("F3 closed\n")
    report = evals.collect(evidence=ev, reports=reports)
    rec = {r["finding"]: r for r in report["finding_recurrence"]}
    assert rec["F3"]["reports"] == 3
    assert rec["F3"]["first"] == "001" and rec["F3"]["last"] == "003"
    assert rec["F4"]["reports"] == 1


def test_render_is_deterministic_and_reads_as_prose(tmp_path):
    ev = tmp_path / "evidence"
    write_record(ev / "a", "d1", node="alpha", wall_clock_seconds=60)
    report = evals.collect(evidence=ev, reports=tmp_path / "reports")
    first = evals.render(report)
    assert first == evals.render(evals.collect(evidence=ev, reports=tmp_path / "reports"))
    assert "miss depth per node" in first
    assert "cost per dispatch" in first


def test_collect_on_the_real_corpus_reports_every_dispatch():
    from tests.conftest import PROJECT_ROOT

    report = evals.collect(
        evidence=PROJECT_ROOT / "docs" / "evidence",
        reports=PROJECT_ROOT / "harness" / "reports",
    )
    ids = {c["dispatch_id"] for c in report["cost_per_dispatch"]}
    assert {"3a", "3b", "3t", "3d-1", "3d-1r", "3d-2"} <= ids
    # the loop's own history must be legible to its reader
    assert report["totals"]["reports"] >= 11
    assert any(r["finding"] == "F29" for r in report["finding_recurrence"])
