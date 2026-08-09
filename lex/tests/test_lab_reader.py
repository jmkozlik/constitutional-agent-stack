"""lab/reader.py — the read layer, and the design law made mechanical.

docs/lab-brief.md, THE ONE DESIGN LAW: *"EVERY NUMBER IS A CITATION. No
stat, verdict, or chart point may render without a provenance affordance…
A number the UI cannot cite does not render."*

A law that lives in the frontend's good intentions is the same class of
mistake as a law that lives in a prompt — F3, restated. So the API cannot
emit a bare number at all: values leave the read layer wrapped with their
source or wrapped as explicitly unavailable, and the test below walks the
payload asserting there is no third option.
"""

import json

import pytest

from lab import cite, reader
from tests.conftest import PROJECT_ROOT


def test_cited_carries_the_file_and_field_it_came_from():
    value = cite.cited(42, path="docs/evidence/step3b/dispatch_record_3b.json",
                       field="tokens.output")
    assert value["v"] == 42
    assert value["cite"]["path"].endswith("dispatch_record_3b.json")
    assert value["cite"]["field"] == "tokens.output"


def test_unavailable_names_the_file_that_would_have_carried_it():
    # The brief: tokens "(or 'unavailable', never blank)". A blank cell reads
    # as zero; this reads as what it is.
    value = cite.unavailable("not recorded in dispatch_record_3d-1.json")
    assert value["v"] is None
    assert "dispatch_record_3d-1.json" in value["unavailable"]
    assert "cite" not in value


def test_a_derived_number_cites_every_field_it_was_derived_from():
    # Wall-clock is often not stored; it is finished - started. A derived
    # number is still a number, so it carries both sources and says how.
    value = cite.derived(
        1105, path="runs/x.json", fields=["started", "finished"],
        how="finished - started",
    )
    assert value["v"] == 1105
    assert value["cite"]["fields"] == ["started", "finished"]
    assert value["cite"]["how"] == "finished - started"


def test_every_number_in_the_runs_payload_is_cited():
    """The law, enforced by walking the real payload.

    If a future field is added as a bare int, this fails — which is the
    point. The UI is then free to render every leaf the same way, because
    the shape guarantees the provenance is there.
    """
    rows = reader.runs(PROJECT_ROOT)
    assert rows, "expected the repo's own dispatch records"

    def walk(obj, trail):
        if isinstance(obj, dict):
            if "v" in obj and ("cite" in obj or "unavailable" in obj):
                return                      # a wrapped value: legal
            for key, value in obj.items():
                walk(value, f"{trail}.{key}")
        elif isinstance(obj, list):
            for i, value in enumerate(obj):
                walk(value, f"{trail}[{i}]")
        elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
            raise AssertionError(f"uncited number at {trail}: {obj!r}")

    for row in rows:
        walk(row, row["id"]["v"])


def test_every_citation_points_at_a_file_that_exists():
    # A citation the reader cannot resolve is worse than no citation: it
    # looks like provenance and goes nowhere.
    for row in reader.runs(PROJECT_ROOT):
        for value in row.values():
            path = (value.get("cite") or {}).get("path") if isinstance(value, dict) else None
            if path:
                assert (PROJECT_ROOT / path).exists(), path


def test_missing_token_counts_are_unavailable_not_zero():
    rows = {row["id"]["v"]: row for row in reader.runs(PROJECT_ROOT)}
    # 3t recorded the keys with null values; 3d-1 never recorded them.
    for run in ("3t", "3d-1"):
        assert rows[run]["tokens_out"]["v"] is None
        assert "unavailable" in rows[run]["tokens_out"]


def test_absent_read_telemetry_is_not_reported_as_zero_reads():
    """3a predates the read fence (F29). Zero would be a claim that the
    agent read nothing outside its packet; the truth is nobody was
    counting."""
    rows = {row["id"]["v"]: row for row in reader.runs(PROJECT_ROOT)}
    assert rows["3a"]["reads_out_of_packet"]["v"] is None
    assert rows["3d-1r"]["reads_out_of_packet"]["v"] > 0
    assert rows["3d-1r"]["reads_out_of_packet"]["cite"]["field"] == \
        "reads_out_of_packet"


def test_wall_clock_is_derived_when_it_was_not_stored():
    rows = {row["id"]["v"]: row for row in reader.runs(PROJECT_ROOT)}
    derived = rows["3d-1"]["wall_clock"]
    assert derived["v"] == pytest.approx(18 * 60 + 25, abs=1)
    assert derived["cite"]["fields"] == ["started", "finished"]


def test_rows_are_sorted_and_carry_a_stable_id():
    rows = reader.runs(PROJECT_ROOT)
    ids = [row["id"]["v"] for row in rows]
    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids)


def test_run_detail_returns_the_whole_record_and_its_path():
    detail = reader.run_detail(PROJECT_ROOT, "3d-1r")
    assert detail["path"].endswith("dispatch_record_3d-1r.json")
    assert detail["record"]["dispatch_id"] == "3d-1r"
    assert any(a.endswith(".md") for a in detail["artifacts"])
    assert detail["fence_allowed"]


def test_unknown_run_is_an_error_not_an_empty_row():
    with pytest.raises(reader.ReaderError):
        reader.run_detail(PROJECT_ROOT, "no-such-dispatch")


def test_empty_repo_reports_where_records_would_live(tmp_path):
    # The brief: empty states name the file that would populate them.
    (tmp_path / "harness").mkdir()
    assert reader.runs(tmp_path) == []
    assert "runs/" in reader.runs_empty_reason(tmp_path)


def test_status_reports_provider_model_and_plan_hash(monkeypatch):
    monkeypatch.setenv("LEX_PROVIDER", "xai")
    monkeypatch.setenv("LEX_MODEL", "grok-4")
    status = reader.status(PROJECT_ROOT)
    assert status["provider"]["v"] == "xai"
    assert status["model"]["v"] == "grok-4"
    assert status["commit"]["v"]
    # the F36 badge is a real state read from the code, not a hardcoded word
    assert status["f36"]["v"] in ("open", "landed")
    assert status["f36"]["cite"]["path"].endswith("tools.py")


def test_status_provider_falls_back_to_the_key_that_is_present(monkeypatch):
    for var in ("LEX_PROVIDER", "ANTHROPIC_API_KEY", "XAI_API_KEY",
                "GROK_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    status = reader.status(PROJECT_ROOT)
    assert status["provider"]["v"] is None
    assert "no API key" in status["provider"]["unavailable"]
