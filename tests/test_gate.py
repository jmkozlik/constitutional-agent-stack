"""harness/gate.py — the ported gate, and its instrument continuity.

F26 made protocol identity load-bearing: the "identical three-probe
protocol" had been depending on memory between rounds. A port is exactly
where that could silently restart, so the archived protocol is the
authority and these tests hold the port to it.
"""

import json
import re

import pytest

from harness import gate
from tests.conftest import PROJECT_ROOT

ARCHIVE = PROJECT_ROOT / "docs" / "evidence" / "step3t" / "gate.js"


def archived(pattern, flags=re.S):
    return re.search(pattern, ARCHIVE.read_text(), flags)


def test_preamble_matches_the_archived_protocol():
    # The instrument-continuity clause, mechanised: if the archive and the
    # port ever diverge, this fails rather than the gate quietly measuring
    # something else under the same name.
    original = archived(r"const PROBE_PREAMBLE = `(.*?)`\n").group(1)
    assert gate.PROBE_PREAMBLE == original.strip()


def test_the_three_probes_and_their_extras_match_the_archive():
    found = re.findall(
        r"\{ key: '([^']+)', text: PACKETS\.\w+, extra: '([^']*)' \}",
        ARCHIVE.read_text(),
    )
    assert [key for key, _ in found] == [key for key, *_ in gate.PROBES]
    for (key, extra), (_, _, _, ported) in zip(found, gate.PROBES):
        assert ported == extra.replace("\\'", "'"), key


def test_verdict_enum_matches_the_archive():
    enum = archived(r"verdict: \{ type: 'string', enum: \[(.*?)\]")
    values = [v.strip().strip("'") for v in enum.group(1).split(",")]
    assert list(gate.VERDICTS) == values


def test_prompt_carries_the_packet_between_the_archived_markers():
    prompt = gate.build_prompt("PACKET BODY", "do the thing")
    assert gate.PROBE_PREAMBLE in prompt
    assert "=== PACKET BEGINS ===\nPACKET BODY\n=== PACKET ENDS ===" in prompt
    assert "do the thing" in prompt


def test_call_rejects_an_unknown_verdict(monkeypatch):
    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {"choices": [{"message": {"content": '{"verdict": "great"}'}}]}

    import httpx

    monkeypatch.setattr(httpx, "post", lambda *a, **k: Response())
    with pytest.raises(gate.GateError) as err:
        gate._call("p", model="m", api_key="k", base_url="u")
    assert "unknown verdict" in str(err.value)


def test_call_extracts_json_wrapped_in_prose(monkeypatch):
    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {"choices": [{"message": {"content":
                    'Here you go:\n{"verdict": "insufficient", "missing": [], '
                    '"notes": "n"}\nhope that helps'}}]}

    import httpx

    monkeypatch.setattr(httpx, "post", lambda *a, **k: Response())
    assert gate._call("p", model="m", api_key="k", base_url="u")["verdict"] == \
        "insufficient"


def test_run_without_a_key_is_an_error(monkeypatch):
    for var in ("XAI_API_KEY", "GROK_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(gate.GateError) as err:
        gate.run(repo=PROJECT_ROOT, api_key=None)
    assert "XAI_API_KEY" in str(err.value)


def test_render_reads_as_a_verdict_table():
    text = gate.render({
        "protocol": "p", "model": "m",
        "probes": [{"probe": "executor:symbol_table",
                    "verdict": "sufficient_with_gaps",
                    "missing": ["a thing"]}],
    })
    assert "executor:symbol_table" in text and "sufficient_with_gaps" in text


def test_prompt_is_byte_identical_to_the_archived_construction():
    # The instrument-continuity clause at its strongest: not "same verdicts"
    # (stochastic even on one model) but the same bytes measured. gate.js
    # builds PREAMBLE + '\n' + extra + markers and appends nothing, because
    # its schema parameter is out-of-band; the port must match exactly.
    packet = "PACKET BODY\nline two"
    for key, _, _, extra in gate.PROBES:
        expected = (
            gate.PROBE_PREAMBLE + "\n" + extra
            + "\n\n=== PACKET BEGINS ===\n" + packet + "\n=== PACKET ENDS ==="
        )
        assert gate.build_prompt(packet, extra) == expected, key


def test_shape_enforcement_stays_out_of_band():
    # The JSON instruction must not leak into the measured prompt.
    prompt = gate.build_prompt("P", "E")
    assert "JSON" not in prompt and "json" not in prompt
    assert "verdict" not in prompt
