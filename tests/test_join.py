import json
import os
import subprocess
import sys

import pytest

from analyzer.indexer import build_index
from harness import join
from tests.conftest import PROJECT_ROOT, make_repo

SPEC_TWO_LEVEL = """
- id: base
  one_liner: The base module.
  references: []
  writes: [core/base.py]
  done_when:
    - It exists.

- id: consumer_a
  one_liner: Consumes base.
  references: [base]
  writes: [core/a.py]
  done_when:
    - It consumes.

- id: consumer_b
  one_liner: Also consumes base.
  references: [base]
  writes: [core/b.py]
  done_when:
    - It also consumes.
"""

FILES_CLEAN = {
    "core/base.py": "def ground():\n    return 0\n",
    "core/a.py": (
        "from core.base import ground\n"
        "def alpha():\n"
        "    return ground() + 1\n"
    ),
    "core/b.py": (
        "from core.base import ground\n"
        "def beta():\n"
        "    return ground() + 2\n"
    ),
}


def make_join_fixture(tmp_path, spec_text: str, files: dict[str, str]):
    specs = tmp_path / "specs"
    specs.mkdir(exist_ok=True)
    (specs / "spec.yaml").write_text(spec_text)
    repo = make_repo(tmp_path, files)
    return specs, repo


def joined(tmp_path, spec_text: str, files: dict[str, str]):
    specs, repo = make_join_fixture(tmp_path, spec_text, files)
    plan = join.load_plan(specs)
    index = build_index(repo, None)
    resolved = join.resolve_writes(plan, index)
    findings = join.plan_checks(plan, index, resolved)
    return plan, index, resolved, findings


# --- load + resolve ---------------------------------------------------------


def test_load_plan_passthrough(tmp_path):
    specs, _ = make_join_fixture(tmp_path, SPEC_TWO_LEVEL, FILES_CLEAN)
    plan = join.load_plan(specs)
    assert plan.levels == {0: ["base"], 1: ["consumer_a", "consumer_b"]}
    assert len(plan.plan_hash) == 12


def test_resolve_writes_maps_files_to_symbols(tmp_path):
    plan, index, resolved, _ = joined(tmp_path, SPEC_TWO_LEVEL, FILES_CLEAN)
    entry = resolved["base"]["core/base.py"]
    assert entry["status"] == "indexed"
    assert [s["path"] for s in entry["symbols"]] == ["core.base.ground"]


def test_missing_file_resolves_to_create(tmp_path):
    spec = SPEC_TWO_LEVEL.replace("core/base.py", "core/never_written.py")
    plan, index, resolved, _ = joined(tmp_path, spec, FILES_CLEAN)
    entry = resolved["base"]["core/never_written.py"]
    assert entry["status"] == "to_create"
    assert entry["symbols"] == []


def test_non_python_writes_entry_is_opaque(tmp_path):
    spec = SPEC_TWO_LEVEL.replace("core/base.py", "docs/design.md")
    plan, index, resolved, _ = joined(tmp_path, spec, FILES_CLEAN)
    assert resolved["base"]["docs/design.md"]["status"] == "opaque"


def test_escaping_path_is_e06(tmp_path):
    spec = SPEC_TWO_LEVEL.replace("core/base.py", "../outside.py")
    specs, repo = make_join_fixture(tmp_path, spec, FILES_CLEAN)
    plan = join.load_plan(specs)
    with pytest.raises(join.JoinError) as err:
        join.resolve_writes(plan, build_index(repo, None))
    assert "E06" in str(err.value) and "../outside.py" in str(err.value)


# --- plan checks ------------------------------------------------------------


def test_confident_same_level_edge_is_e08(tmp_path):
    files = {
        **FILES_CLEAN,
        "core/b.py": (
            "from core.a import alpha\n"
            "def beta():\n"
            "    return alpha() + 2\n"
        ),
    }
    _, _, _, findings = joined(tmp_path, SPEC_TWO_LEVEL, files)
    e08 = [f for f in findings if f.code == "E08"]
    assert len(e08) == 1
    assert "consumer_a" in e08[0].message and "consumer_b" in e08[0].message
    assert "core.a.alpha" in e08[0].message


def test_ambiguous_same_level_edge_is_w04_not_e08(tmp_path):
    files = {
        **FILES_CLEAN,
        "core/a.py": (
            "class Alpha:\n"
            "    def ping(self):\n"
            "        return 1\n"
        ),
        "core/b.py": (
            "def beta(obj):\n"
            "    return obj.ping()\n"
        ),
    }
    _, _, _, findings = joined(tmp_path, SPEC_TWO_LEVEL, files)
    assert [f.code for f in findings if f.code == "E08"] == []
    w04 = [f for f in findings if f.code == "W04"]
    assert len(w04) == 1
    assert "core.a.Alpha.ping" in w04[0].message


def test_low_confidence_scope_is_w02(tmp_path):
    files = {
        **FILES_CLEAN,
        "core/b.py": (
            "def beta(name, payload):\n"
            "    return HANDLERS[name](payload)\n"
        ),
    }
    _, _, _, findings = joined(tmp_path, SPEC_TWO_LEVEL, files)
    w02 = [f for f in findings if f.code == "W02"]
    assert len(w02) == 1
    assert "consumer_b" in w02[0].message


def test_ambiguous_cross_level_edge_w05_says_possibly(tmp_path):
    files = {
        **FILES_CLEAN,
        "core/base.py": "def ground(o):\n    return o.alpha_method()\n",
        "core/a.py": (
            "class Alpha:\n"
            "    def alpha_method(self):\n"
            "        return 1\n"
        ),
    }
    _, _, _, findings = joined(tmp_path, SPEC_TWO_LEVEL, files)
    w05 = [f for f in findings if f.code == "W05"]
    assert len(w05) == 1
    assert "possibly consumes" in w05[0].message
    assert "ambiguous" in w05[0].message


def test_reverse_cross_level_edge_is_w05(tmp_path):
    files = {
        **FILES_CLEAN,
        "core/base.py": (
            "from core.a import alpha\n"
            "def ground():\n"
            "    return alpha()\n"
        ),
    }
    _, _, _, findings = joined(tmp_path, SPEC_TWO_LEVEL, files)
    w05 = [f for f in findings if f.code == "W05"]
    assert len(w05) == 1
    assert "base" in w05[0].message and "consumer_a" in w05[0].message


def test_clean_fixture_has_no_findings(tmp_path):
    _, _, _, findings = joined(tmp_path, SPEC_TWO_LEVEL, FILES_CLEAN)
    assert findings == []


# --- serialized plan (JA1) --------------------------------------------------


def test_w02_splits_level_into_sublevels(tmp_path):
    files = {
        **FILES_CLEAN,
        "core/b.py": (
            "def beta(name, payload):\n"
            "    return HANDLERS[name](payload)\n"
        ),
    }
    plan, index, resolved, findings = joined(tmp_path, SPEC_TWO_LEVEL, files)
    adjusted = join.serialize_plan(plan, findings)
    assert adjusted.levels == [
        ("0", ["base"]),
        ("1.0", ["consumer_a"]),
        ("1.1", ["consumer_b"]),
    ]
    assert adjusted.plan_hash != plan.plan_hash


def test_clean_plan_keeps_speccc_levels(tmp_path):
    plan, index, resolved, findings = joined(tmp_path, SPEC_TWO_LEVEL, FILES_CLEAN)
    adjusted = join.serialize_plan(plan, findings)
    assert adjusted.levels == [("0", ["base"]), ("1", ["consumer_a", "consumer_b"])]


# --- interfaces (JA4) -------------------------------------------------------


def test_consumed_interfaces_tag_declared_and_undeclared(tmp_path):
    files = {
        **FILES_CLEAN,
        "core/b.py": (
            "from core.base import ground\n"
            "from core.a import alpha\n"
            "def beta():\n"
            "    return ground() + alpha()\n"
        ),
    }
    plan, index, resolved, _ = joined(tmp_path, SPEC_TWO_LEVEL, files)
    consumed = join.consumed_interfaces(plan, index, resolved, "consumer_b")
    tags = {c["symbol"]["path"]: c["tag"] for c in consumed}
    assert tags["core.base.ground"] == "declared"
    assert tags["core.a.alpha"] == "undeclared"


# --- packets ----------------------------------------------------------------


def real_packet(node="affected_symbols", role="executor"):
    plan = join.load_plan(PROJECT_ROOT / "harness" / "specs")
    index = build_index(PROJECT_ROOT, None)
    resolved = join.resolve_writes(plan, index)
    return join.assemble_packet(
        plan, index, resolved, node, role,
        identities_dir=PROJECT_ROOT / "harness" / "identities",
        repo=PROJECT_ROOT,
    )


def test_executor_packet_shape():
    packet = real_packet()
    assert packet.startswith("## Identity")
    assert packet.index("## Identity") < packet.index("## Task")
    assert packet.index("## Task") < packet.index("## State — compiled")
    assert "compute_affected" in packet
    assert "analyzer.indexer.build_index" in packet  # consumed interface
    assert "Callers of your write scope" in packet
    assert "verify with: .venv/bin/python -m pytest" in packet
    assert "Missing means query" in packet
    # An executor MODIFIES its write scope: the packet must carry the
    # current source bodies, not just signatures (probe finding).
    assert "def compute_affected(" in packet
    assert "source (verbatim" in packet
    trailer = packet.rstrip("\n").rsplit("\n", 1)[-1]
    assert "packet_hash=" in trailer and "node=affected_symbols" in trailer


def test_executor_packets_share_identity_prefix():
    a = real_packet("affected_symbols")
    b = real_packet("symbol_table")
    prefix_a = a[: a.index("## Task")]
    assert b.startswith(prefix_a)


def test_tester_packet_is_spec_only():
    packet = real_packet(role="tester")
    assert "## Task" in packet
    assert "done_when" in packet or "guarantees" in packet
    assert "## State — compiled" not in packet
    assert "analyzer/affected.py" not in packet  # no writes list (JA7)
    # v0.2: the declared surface is the ONE sanctioned shared seam — the
    # tester may see it (it's spec, not implementation). Nothing else leaks.
    assert "render_report" not in packet or "surface" in packet


def test_packet_hash_covers_body():
    packet = real_packet()
    body, trailer = packet.rstrip("\n").rsplit("\n", 1)
    import hashlib

    expected = hashlib.sha256((body + "\n").encode()).hexdigest()[:12]
    assert f"packet_hash={expected}" in trailer


def test_to_create_rendered_in_packet(tmp_path):
    spec = SPEC_TWO_LEVEL.replace("core/a.py", "core/new_thing.py")
    specs, repo = make_join_fixture(tmp_path, spec, FILES_CLEAN)
    plan = join.load_plan(specs)
    index = build_index(repo, None)
    resolved = join.resolve_writes(plan, index)
    packet = join.assemble_packet(
        plan, index, resolved, "consumer_a", "executor",
        identities_dir=PROJECT_ROOT / "harness" / "identities",
    )
    assert "you are creating this file" in packet


def test_cli_packet_carries_source_and_hashes(tmp_path):
    # The CLI path must produce the same complete packet as direct calls:
    # source bodies and content-hashed writes (a CLI/direct divergence here
    # once sent body-less packets to the sufficiency probes).
    import shutil

    specs, repo = make_join_fixture(tmp_path, SPEC_SURFACED, SURFACED_FILES)
    shutil.copytree(PROJECT_ROOT / "harness" / "identities", tmp_path / "identities")
    result = subprocess.run(
        [sys.executable, "-m", "harness.join", "packet", "base",
         "--worktree", "--specs", str(specs), "--repo", str(repo)],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
    )
    assert result.returncode == 0, result.stderr
    assert "source (verbatim" in result.stdout
    assert "def ground()" in result.stdout
    assert "exists@" in result.stdout


def test_packet_bytes_stable_across_hash_seeds(tmp_path):
    out = {}
    for seed in ("0", "1"):
        result = subprocess.run(
            [sys.executable, "-m", "harness.join", "packet", "affected_symbols",
             "--worktree", "--repo", str(PROJECT_ROOT),
             "--specs", str(PROJECT_ROOT / "harness" / "specs")],
            capture_output=True,
            env={**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(PROJECT_ROOT)},
        )
        assert result.returncode == 0, result.stderr.decode()
        out[seed] = result.stdout
    assert out["0"] == out["1"]


# --- verification fixes (JV1-JV6) -------------------------------------------


def test_aliased_writes_spelling_resolves_indexed(tmp_path):
    spec = SPEC_TWO_LEVEL.replace("core/a.py", "./core/a.py")
    plan, index, resolved, findings = joined(tmp_path, spec, FILES_CLEAN)
    entry = resolved["consumer_a"]["core/a.py"]
    assert entry["status"] == "indexed"
    assert [s["path"] for s in entry["symbols"]] == ["core.a.alpha"]


def test_normalized_write_collision_is_error(tmp_path):
    spec = SPEC_TWO_LEVEL.replace(
        "writes: [core/b.py]", "writes: [./core/a.py]"
    )
    plan, index, resolved, findings = joined(tmp_path, spec, FILES_CLEAN)
    e05 = [f for f in findings if f.code == "E05"]
    assert len(e05) == 1
    assert "consumer_a" in e05[0].message and "consumer_b" in e05[0].message
    assert e05[0].is_error


def test_degenerate_writes_entry_is_e06(tmp_path):
    spec = SPEC_TWO_LEVEL.replace("core/base.py", ".")
    specs, repo = make_join_fixture(tmp_path, spec, FILES_CLEAN)
    plan = join.load_plan(specs)
    with pytest.raises(join.JoinError) as err:
        join.resolve_writes(plan, build_index(repo, None))
    assert "E06" in str(err.value)


def test_missing_specs_dir_is_clean_error(tmp_path):
    with pytest.raises(join.JoinError) as err:
        join.load_plan(tmp_path / "no_such_specs")
    assert "no_such_specs" in str(err.value)


def test_empty_specs_dir_is_clean_error(tmp_path):
    empty = tmp_path / "empty_specs"
    empty.mkdir()
    with pytest.raises(join.JoinError):
        join.load_plan(empty)


def test_non_string_payload_is_clean_error(tmp_path):
    spec = SPEC_TWO_LEVEL.replace("writes: [core/base.py]", "writes: [123]")
    specs, _ = make_join_fixture(tmp_path, spec, FILES_CLEAN)
    with pytest.raises(join.JoinError) as err:
        join.load_plan(specs)
    assert "base" in str(err.value)


def test_packet_stamps_dispatch_hash_not_spec_hash(tmp_path):
    files = {
        **FILES_CLEAN,
        "core/b.py": (
            "def beta(name, payload):\n"
            "    return HANDLERS[name](payload)\n"
        ),
    }
    plan, index, resolved, findings = joined(tmp_path, SPEC_TWO_LEVEL, files)
    adjusted = join.serialize_plan(plan, findings)
    packet = join.assemble_packet(
        plan, index, resolved, "consumer_a", "executor",
        identities_dir=PROJECT_ROOT / "harness" / "identities",
    )
    trailer = packet.rstrip("\n").rsplit("\n", 1)[-1]
    assert f"plan={adjusted.plan_hash}" in trailer
    assert f"plan={plan.plan_hash}" not in trailer


def test_packet_cli_refuses_e08_spec(tmp_path):
    files = {
        **FILES_CLEAN,
        "core/b.py": (
            "from core.a import alpha\n"
            "def beta():\n"
            "    return alpha() + 2\n"
        ),
    }
    specs, repo = make_join_fixture(tmp_path, SPEC_TWO_LEVEL, files)
    result = subprocess.run(
        [sys.executable, "-m", "harness.join", "packet", "consumer_a",
         "--worktree", "--specs", str(specs), "--repo", str(repo)],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
    )
    assert result.returncode == 1
    assert "E08" in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_bad_commit_clean_error(tmp_path):
    specs, repo = make_join_fixture(tmp_path, SPEC_TWO_LEVEL, FILES_CLEAN)
    result = subprocess.run(
        [sys.executable, "-m", "harness.join", "plan", "--specs", str(specs),
         "--repo", str(repo), "--commit", "not-a-rev"],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
    )
    assert result.returncode == 1
    assert "join:" in result.stderr
    assert "Traceback" not in result.stderr


def test_ambiguous_only_attribution_is_marked(tmp_path):
    files = {
        **FILES_CLEAN,
        "core/a.py": (
            "class Alpha:\n"
            "    def ping(self):\n"
            "        return 1\n"
        ),
        "core/b.py": (
            "def beta(obj):\n"
            "    return obj.ping()\n"
        ),
    }
    plan, index, resolved, _ = joined(tmp_path, SPEC_TWO_LEVEL, files)
    consumed = join.consumed_interfaces(plan, index, resolved, "consumer_b")
    ping = [c for c in consumed if c["symbol"]["path"] == "core.a.Alpha.ping"]
    assert ping and ping[0]["ambiguous"] is True
    packet = join.assemble_packet(
        plan, index, resolved, "consumer_b", "executor",
        identities_dir=PROJECT_ROOT / "harness" / "identities",
    )
    assert "ambiguous attribution" in packet


# --- spec format v0.2: compiled delta (surface x index) ---------------------

SPEC_SURFACED = """
- id: base
  one_liner: The base module.
  references: []
  writes: [core/base.py]
  surface:
    callables:
      - core.base.ground() -> int
    types:
      - "core.base.Report(total: int, notes: list = [])"
    errors:
      - "core.base.GroundError: raised by ground when the floor is missing"
  done_when:
    - It exists.

- id: consumer_a
  one_liner: Consumes base.
  references: [base]
  writes: [core/a.py]
  surface:
    callables:
      - core.a.alpha() -> int
  done_when:
    - It consumes.

- id: consumer_b
  one_liner: Also consumes base.
  references: [base]
  writes: [core/b.py]
  done_when:
    - It also consumes.
"""

SURFACED_FILES = {
    "core/base.py": (
        "class GroundError(Exception):\n"
        "    pass\n"
        "\n"
        "\n"
        "class Report:\n"
        "    total: int\n"
        "    notes: list = []\n"
        "\n"
        "\n"
        "def ground() -> int:\n"
        "    return 0\n"
    ),
    "core/a.py": (
        "from core.base import ground\n"
        "def alpha() -> int:\n"
        "    return ground() + 1\n"
    ),
    "core/b.py": "def beta():\n    return 2\n",
}


def test_delta_empty_when_everything_present(tmp_path):
    specs, repo = make_join_fixture(tmp_path, SPEC_SURFACED, SURFACED_FILES)
    plan = join.load_plan(specs)
    index = build_index(repo, None)
    resolved = join.resolve_writes(plan, index)
    delta = join.compute_delta(plan, index, resolved, "base", repo=repo)
    assert delta["kind"] == "empty"
    (entry, status) = delta["writes"][0]
    assert entry == "core/base.py" and status.startswith("exists@")
    assert delta["callables"] == [("core.base.ground() -> int", "present")]
    assert delta["types"] == [
        ("core.base.Report(total: int, notes: list = [])", "present")
    ]
    assert delta["errors"][0][1] == "present"


def test_delta_full_on_greenfield(tmp_path):
    spec = SPEC_SURFACED.replace("core/base.py", "core/unbuilt.py").replace(
        "core.base.", "core.unbuilt."
    )
    specs, repo = make_join_fixture(tmp_path, spec, SURFACED_FILES)
    plan = join.load_plan(specs)
    index = build_index(repo, None)
    resolved = join.resolve_writes(plan, index)
    delta = join.compute_delta(plan, index, resolved, "base", repo=repo)
    assert delta["kind"] == "full"
    assert delta["writes"] == [("core/unbuilt.py", "to_create")]
    assert delta["callables"] == [("core.unbuilt.ground() -> int", "absent")]
    assert all(s == "absent" for _, s in delta["types"] + delta["errors"])


def test_delta_signature_mismatch(tmp_path):
    # Annotated signatures contain ": " and must be quoted in YAML.
    spec = SPEC_SURFACED.replace(
        "- core.base.ground() -> int",
        '- "core.base.ground(strict: bool) -> int"',
    )
    specs, repo = make_join_fixture(tmp_path, spec, SURFACED_FILES)
    plan = join.load_plan(specs)
    index = build_index(repo, None)
    resolved = join.resolve_writes(plan, index)
    delta = join.compute_delta(plan, index, resolved, "base", repo=repo)
    assert delta["kind"] == "partial"
    assert delta["callables"] == [
        ("core.base.ground(strict: bool) -> int", "signature-mismatch")
    ]


def test_delta_type_shape_mismatch(tmp_path):
    spec = SPEC_SURFACED.replace(
        '"core.base.Report(total: int, notes: list = [])"',
        '"core.base.Report(total: int, wrong: str)"',
    )
    specs, repo = make_join_fixture(tmp_path, spec, SURFACED_FILES)
    plan = join.load_plan(specs)
    index = build_index(repo, None)
    resolved = join.resolve_writes(plan, index)
    delta = join.compute_delta(plan, index, resolved, "base", repo=repo)
    assert delta["types"] == [
        ("core.base.Report(total: int, wrong: str)", "shape-mismatch")
    ]
    assert delta["kind"] == "partial"


def test_delta_constructor_shaped_type_matches_init(tmp_path):
    files = {
        **SURFACED_FILES,
        "core/base.py": SURFACED_FILES["core/base.py"].replace(
            "class Report:\n    total: int\n    notes: list = []\n",
            "class Report:\n    def __init__(self, total: int, notes: list = []):\n"
            "        self.total = total\n"
            "        self.notes = notes\n",
        ),
    }
    specs, repo = make_join_fixture(tmp_path, SPEC_SURFACED, files)
    plan = join.load_plan(specs)
    index = build_index(repo, None)
    resolved = join.resolve_writes(plan, index)
    delta = join.compute_delta(plan, index, resolved, "base", repo=repo)
    assert delta["types"][0][1] == "present"


def test_delta_alias_type_is_unindexed_never_outstanding(tmp_path):
    spec = SPEC_SURFACED.replace(
        '"core.base.Report(total: int, notes: list = [])"',
        '"core.base.Span = tuple[int, int]"',
    )
    specs, repo = make_join_fixture(tmp_path, spec, SURFACED_FILES)
    plan = join.load_plan(specs)
    index = build_index(repo, None)
    resolved = join.resolve_writes(plan, index)
    delta = join.compute_delta(plan, index, resolved, "base", repo=repo)
    (entry, status) = delta["types"][0]
    assert status.startswith("unindexed")
    assert delta["kind"] == "empty"


def test_delta_error_via_field_path(tmp_path):
    spec = SPEC_SURFACED.replace(
        '"core.base.GroundError: raised by ground when the floor is missing"',
        '"core.base.Report.total: nonzero when grounding failed"',
    )
    specs, repo = make_join_fixture(tmp_path, spec, SURFACED_FILES)
    plan = join.load_plan(specs)
    index = build_index(repo, None)
    resolved = join.resolve_writes(plan, index)
    delta = join.compute_delta(plan, index, resolved, "base", repo=repo)
    assert delta["errors"][0][1] == "present"
    assert delta["kind"] == "empty"


def test_delta_error_condition_may_contain_colons(tmp_path):
    spec = SPEC_SURFACED.replace(
        "raised by ground when the floor is missing",
        "raised when git says: fatal: not a repository",
    )
    specs, repo = make_join_fixture(tmp_path, spec, SURFACED_FILES)
    plan = join.load_plan(specs)
    index = build_index(repo, None)
    resolved = join.resolve_writes(plan, index)
    delta = join.compute_delta(plan, index, resolved, "base", repo=repo)
    assert delta["errors"][0][1] == "present"


def test_unquoted_error_entry_is_clean_e01(tmp_path):
    spec = SPEC_SURFACED.replace(
        '"core.base.GroundError: raised by ground when the floor is missing"',
        "core.base.GroundError: raised by ground when the floor is missing",
    )
    specs, _ = make_join_fixture(tmp_path, spec, SURFACED_FILES)
    with pytest.raises(join.JoinError) as err:
        join.load_plan(specs)
    assert "quote" in str(err.value).lower()


def test_delta_without_surface_not_computable(tmp_path):
    specs, repo = make_join_fixture(tmp_path, SPEC_SURFACED, SURFACED_FILES)
    plan = join.load_plan(specs)
    index = build_index(repo, None)
    resolved = join.resolve_writes(plan, index)
    delta = join.compute_delta(plan, index, resolved, "consumer_b", repo=repo)
    assert delta["kind"] == "no_surface"


def test_executor_packet_carries_delta_block(tmp_path):
    specs, repo = make_join_fixture(tmp_path, SPEC_SURFACED, SURFACED_FILES)
    plan = join.load_plan(specs)
    index = build_index(repo, None)
    resolved = join.resolve_writes(plan, index)
    packet = join.assemble_packet(
        plan, index, resolved, "base", "executor",
        identities_dir=PROJECT_ROOT / "harness" / "identities", repo=repo,
    )
    assert "delta" in packet and "compiled at dispatch" in packet
    assert "surface is what makes" in packet
    assert "exists@" in packet
    assert "validation-only dispatch" in packet


def test_executor_done_when_sits_above_delta(tmp_path):
    specs, repo = make_join_fixture(tmp_path, SPEC_SURFACED, SURFACED_FILES)
    plan = join.load_plan(specs)
    index = build_index(repo, None)
    resolved = join.resolve_writes(plan, index)
    packet = join.assemble_packet(
        plan, index, resolved, "base", "executor",
        identities_dir=PROJECT_ROOT / "harness" / "identities", repo=repo,
    )
    checklist = packet.index("done_when (attest against")
    assert packet.index("It exists.") > checklist
    assert checklist < packet.index("delta [compiled at dispatch")
    assert packet.index("It exists.") < packet.index("delta [compiled at dispatch")


def test_foreign_type_resolves_from_owning_node(tmp_path):
    spec = SPEC_SURFACED.replace(
        "callables:\n      - core.a.alpha() -> int",
        'callables:\n      - "core.a.alpha() -> Report"',
    )
    specs, repo = make_join_fixture(tmp_path, spec, SURFACED_FILES)
    plan = join.load_plan(specs)
    index = build_index(repo, None)
    resolved = join.resolve_writes(plan, index)
    packet = join.assemble_packet(
        plan, index, resolved, "consumer_a", "executor",
        identities_dir=PROJECT_ROOT / "harness" / "identities", repo=repo,
    )
    assert "core.base.Report(total: int, notes: list = [])" in packet
    assert "[from base]" in packet


def test_tester_packet_carries_surface_only(tmp_path):
    specs, repo = make_join_fixture(tmp_path, SPEC_SURFACED, SURFACED_FILES)
    plan = join.load_plan(specs)
    index = build_index(repo, None)
    resolved = join.resolve_writes(plan, index)
    packet = join.assemble_packet(
        plan, index, resolved, "base", "executor",
        identities_dir=PROJECT_ROOT / "harness" / "identities", repo=repo,
    )
    tester = join.assemble_packet(
        plan, index, resolved, "base", "tester",
        identities_dir=PROJECT_ROOT / "harness" / "identities", repo=repo,
    )
    assert "core.base.ground() -> int" in tester
    assert "guarantees to verify" in tester
    assert "## State — compiled" not in tester
    assert "core/base.py" not in tester  # writes stay executor-only
    assert "delta" not in tester  # the delta is the executor's work statement


def test_plan_output_shows_delta_summary(tmp_path):
    specs, repo = make_join_fixture(tmp_path, SPEC_SURFACED, SURFACED_FILES)
    result = subprocess.run(
        [sys.executable, "-m", "harness.join", "plan", "--specs", str(specs),
         "--repo", str(repo)],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
    )
    assert result.returncode == 0, result.stderr
    assert "delta: empty (validation-only)" in result.stdout
    assert "[W06]" in result.stdout  # consumer_b: done_when with no surface


# --- format v0.4: provenance split + spec meta -------------------------------


def test_authored_entries_are_delta_exempt(tmp_path):
    spec = SPEC_SURFACED.replace(
        'types:\n      - "core.base.Report(total: int, notes: list = [])"',
        'types:\n'
        '      - "core.base.Report(total: int, notes: list = [])  [seeded]"\n'
        '      - "core.base.Report.total ∈ small | large  [authored]"\n'
        '      - "core.base.record(path: str, line: int)  [authored]"',
    )
    specs, repo = make_join_fixture(tmp_path, spec, SURFACED_FILES)
    plan = join.load_plan(specs)
    index = build_index(repo, None)
    resolved = join.resolve_writes(plan, index)
    delta = join.compute_delta(plan, index, resolved, "base", repo=repo)
    statuses = dict(delta["types"])
    assert statuses["core.base.Report(total: int, notes: list = [])  [seeded]"] == "present"
    # F20 (ratified): a structural authored line presence-checks now.
    assert statuses["core.base.Report.total ∈ small | large  [authored]"] == "present"
    # Callable-signature shape stays behavioral-exempt.
    assert "authored" in statuses["core.base.record(path: str, line: int)  [authored]"]
    assert delta["kind"] == "empty"


def test_seeded_mismatch_still_fails_delta(tmp_path):
    spec = SPEC_SURFACED.replace(
        '"core.base.Report(total: int, notes: list = [])"',
        '"core.base.Report(total: int, wrong: str)  [seeded]"',
    )
    specs, repo = make_join_fixture(tmp_path, spec, SURFACED_FILES)
    plan = join.load_plan(specs)
    index = build_index(repo, None)
    resolved = join.resolve_writes(plan, index)
    delta = join.compute_delta(plan, index, resolved, "base", repo=repo)
    assert delta["kind"] == "partial"


def test_meta_language_renders_in_both_packets(tmp_path):
    spec = "- language: python\n" + SPEC_SURFACED
    specs, repo = make_join_fixture(tmp_path, spec, SURFACED_FILES)
    plan = join.load_plan(specs)
    assert plan.meta == {"language": "python"}
    index = build_index(repo, None)
    resolved = join.resolve_writes(plan, index)
    for role in ("executor", "tester"):
        packet = join.assemble_packet(
            plan, index, resolved, "base", role,
            identities_dir=PROJECT_ROOT / "harness" / "identities", repo=repo,
        )
        assert "language: python" in packet


# --- F19: replay checker (IDENTICAL / DIVERGED / CHECK-ERROR) ---------------


def replay_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "harness.join", "replay", *args],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
    )


def make_replayable(tmp_path):
    import shutil

    from tests.conftest import git, make_repo

    repo = make_repo(tmp_path, SURFACED_FILES)
    (repo / "harness" / "specs").mkdir(parents=True)
    (repo / "harness" / "specs" / "spec.yaml").write_text(SPEC_SURFACED)
    shutil.copytree(
        PROJECT_ROOT / "harness" / "identities", repo / "harness" / "identities"
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "harness in-repo")
    sha = git(repo, "rev-parse", "HEAD")
    shipped = tmp_path / "shipped.md"
    build = subprocess.run(
        [sys.executable, "-m", "harness.join", "packet", "base",
         "--specs", str(repo / "harness" / "specs"), "--repo", str(repo),
         "--commit", sha, "-o", str(shipped)],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
    )
    assert build.returncode == 0, build.stderr
    return repo, sha, shipped


def test_replay_identical_despite_later_spec_edit(tmp_path):
    repo, sha, shipped = make_replayable(tmp_path)
    # Mutate the WORKTREE spec after shipping: commit-anchored replay must
    # still report IDENTICAL (it reads the spec from the pinned commit).
    (repo / "harness" / "specs" / "spec.yaml").write_text(
        SPEC_SURFACED.replace("The base module.", "The base module, edited later.")
    )
    result = replay_cli("base", "--repo", str(repo), "--commit", sha,
                        "--shipped", str(shipped))
    assert result.returncode == 0, result.stderr + result.stdout
    assert "IDENTICAL" in result.stdout


def test_replay_diverged_on_tampered_shipped(tmp_path):
    repo, sha, shipped = make_replayable(tmp_path)
    shipped.write_text(shipped.read_text().replace("validation-only", "tampered"))
    result = replay_cli("base", "--repo", str(repo), "--commit", sha,
                        "--shipped", str(shipped))
    assert result.returncode == 1
    assert "DIVERGED" in result.stdout


def test_replay_missing_shipped_is_check_error_not_diverged(tmp_path):
    repo, sha, shipped = make_replayable(tmp_path)
    result = replay_cli("base", "--repo", str(repo), "--commit", sha,
                        "--shipped", str(tmp_path / "no_such_packet.md"))
    assert result.returncode == 2
    assert "CHECK-ERROR" in result.stderr
    assert "DIVERGED" not in result.stdout + result.stderr


def test_replay_bad_commit_is_check_error(tmp_path):
    repo, sha, shipped = make_replayable(tmp_path)
    result = replay_cli("base", "--repo", str(repo), "--commit", "not-a-rev",
                        "--shipped", str(shipped))
    assert result.returncode == 2
    assert "CHECK-ERROR" in result.stderr


# --- F20 (ratified): structural authored lines presence-check ----------------


def test_structural_authored_absent_is_outstanding(tmp_path):
    # An authored Type.attr line whose attribute does not exist must count
    # as outstanding — the F20 rule, ratified from 3b's D2 filing.
    spec = SPEC_SURFACED.replace(
        'types:\n      - "core.base.Report(total: int, notes: list = [])"',
        'types:\n'
        '      - "core.base.Report(total: int, notes: list = [])  [seeded]"\n'
        '      - "core.base.Report.phantom: never built  [authored]"',
    )
    specs, repo = make_join_fixture(tmp_path, spec, SURFACED_FILES)
    plan = join.load_plan(specs)
    index = build_index(repo, None)
    resolved = join.resolve_writes(plan, index)
    delta = join.compute_delta(plan, index, resolved, "base", repo=repo)
    statuses = dict(delta["types"])
    assert statuses['core.base.Report.phantom: never built  [authored]'] == "absent"
    assert delta["kind"] == "partial"


def test_structural_authored_present_and_behavioral_exempt(tmp_path):
    spec = SPEC_SURFACED.replace(
        'types:\n      - "core.base.Report(total: int, notes: list = [])"',
        'types:\n'
        '      - "core.base.Report(total: int, notes: list = [])  [seeded]"\n'
        '      - "core.base.Report.total ∈ small | large  [authored]"\n'
        '      - "core.base.Report: assembled at call time from parts  [authored]"',
    )
    specs, repo = make_join_fixture(tmp_path, spec, SURFACED_FILES)
    plan = join.load_plan(specs)
    index = build_index(repo, None)
    resolved = join.resolve_writes(plan, index)
    delta = join.compute_delta(plan, index, resolved, "base", repo=repo)
    statuses = dict(delta["types"])
    assert statuses["core.base.Report.total ∈ small | large  [authored]"] == "present"
    assert "authored" in statuses["core.base.Report: assembled at call time from parts  [authored]"]
    assert delta["kind"] == "empty"


def test_f20_locked_demonstration_on_real_spec():
    # The 3b-packet demonstration, locked as ratified: nine authored lines
    # on affected_symbols; the structural ones presence-check; exactly one
    # is absent (callers_unknowable, unbuilt until 3d); behavioral lines
    # stay exempt. F20 closes on this being true.
    plan = join.load_plan(PROJECT_ROOT / "harness" / "specs")
    index = build_index(PROJECT_ROOT, None)
    resolved = join.resolve_writes(plan, index)
    delta = join.compute_delta(plan, index, resolved, "affected_symbols", repo=PROJECT_ROOT)
    statuses = {e.split("  [")[0]: s for e, s in delta["types"] + delta["errors"] + delta["callables"]}
    def stat(prefix):
        return next(s for e, s in statuses.items() if e.startswith(prefix))
    assert stat("analyzer.affected.Row.category") == "present"
    assert stat("analyzer.affected.Row.path") == "present"
    assert stat("analyzer.affected.Row.callers:") == "present"
    assert stat("analyzer.affected.Row.callers_unknowable") == "absent"
    assert stat("analyzer.affected.Row.error") == "present"
    assert stat("analyzer.affected.AffectedReport.has_error") == "present"
    assert "authored" in stat("analyzer.affected.compute_affected:")  # prose: exempt
    assert "authored" in stat("analyzer.affected.AffectedReport:")   # behavioral: exempt
    assert delta["kind"] == "partial"
    assert delta["outstanding"] and any("callers_unknowable" in o for o in delta["outstanding"])


def test_f20_callable_extension_in_scope_presence_checks():
    # Ratified YES: an authored CALLABLE line whose subject is inside the
    # node's own write scope presence-checks by name. compute_affected is
    # authored, in affected.py (own scope), and built -> present.
    plan = join.load_plan(PROJECT_ROOT / "harness" / "specs")
    index = build_index(PROJECT_ROOT, None)
    resolved = join.resolve_writes(plan, index)
    delta = join.compute_delta(
        plan, index, resolved, "affected_symbols", repo=PROJECT_ROOT
    )
    status = next(
        s for e, s in delta["callables"]
        if e.startswith("analyzer.affected.compute_affected(")
    )
    assert status == "present"


def test_f20_callable_extension_absent_until_built(tmp_path):
    # An authored callable inside the node's own write scope that is NOT
    # built reports absent, so the node shows outstanding work instead of
    # validation-only.
    #
    # This ran against the live spec until 3d-1r built import_origins and
    # filed D-3d1r-1: the canary was the one outstanding item of a LIVE
    # node, so a successful dispatch was always going to invalidate it.
    # Pinned to a synthetic fixture now — a real dispatch must be able to
    # succeed without breaking the demonstration of why it was needed.
    spec = SPEC_SURFACED.replace(
        "      - core.base.ground() -> int",
        '      - core.base.ground() -> int\n'
        '      - "core.base.unbuilt_yet(x: int) -> int  [authored]"',
    )
    specs, repo = make_join_fixture(tmp_path, spec, SURFACED_FILES)
    plan = join.load_plan(specs)
    index = build_index(repo, None)
    resolved = join.resolve_writes(plan, index)
    delta = join.compute_delta(plan, index, resolved, "base", repo=repo)
    status = next(
        s for e, s in delta["callables"]
        if e.startswith("core.base.unbuilt_yet(")
    )
    assert status == "absent"
    assert delta["kind"] == "partial"
    assert any("unbuilt_yet" in o for o in delta["outstanding"])
    # Seeded callables in the same scope stay unaffected.
    assert next(
        s for e, s in delta["callables"]
        if e.startswith("core.base.ground(")
    ) == "present"


def test_f20_import_origins_now_reports_present_on_real_spec():
    # The other half of D-3d1r-1: 3d-1r built it, so the live spec must now
    # report present. This is the dispatch landing, asserted.
    plan = join.load_plan(PROJECT_ROOT / "harness" / "specs")
    index = build_index(PROJECT_ROOT, None)
    resolved = join.resolve_writes(plan, index)
    delta = join.compute_delta(
        plan, index, resolved, "index_assembly", repo=PROJECT_ROOT
    )
    assert next(
        s for e, s in delta["callables"]
        if e.startswith("analyzer.indexer.import_origins(")
    ) == "present"


def test_f20_callable_outside_own_scope_stays_behavioral(tmp_path):
    spec = SPEC_SURFACED.replace(
        "callables:\n      - core.a.alpha() -> int",
        'callables:\n      - "core.base.not_ours(x: int) -> int  [authored]"',
    )
    specs, repo = make_join_fixture(tmp_path, spec, SURFACED_FILES)
    plan = join.load_plan(specs)
    index = build_index(repo, None)
    resolved = join.resolve_writes(plan, index)
    delta = join.compute_delta(plan, index, resolved, "consumer_a", repo=repo)
    # consumer_a writes core/a.py; the subject lives in core/base.py, which
    # it does not own — exempt, not "absent".
    assert "authored" in delta["callables"][0][1]


# --- F23 candidate one (ratified): replay pins the join version -------------


def test_replay_pins_join_version_old_packet_replays_identical():
    # Report 005 demonstrated the defect: 3b's shipped packet — correct when
    # it shipped — reported DIVERGED because the checker rebuilt it with a
    # join whose packet FORMAT had since moved. Pinned to the recorded
    # commit's own code, it must report IDENTICAL.
    shipped = PROJECT_ROOT / "docs" / "evidence" / "step3b" / "packet.md"
    result = subprocess.run(
        [sys.executable, "-m", "harness.join", "replay", "affected_symbols",
         "--commit", "4b30c3814ccd2b4cfd5ac4b18b2f177ba59355eb",
         "--shipped", str(shipped), "--repo", str(PROJECT_ROOT)],
        capture_output=True, text=True, cwd=PROJECT_ROOT,
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "IDENTICAL" in result.stdout


def test_replay_still_diverges_on_a_real_mismatch(tmp_path):
    shipped = tmp_path / "tampered.md"
    original = (
        PROJECT_ROOT / "docs" / "evidence" / "step3b" / "packet.md"
    ).read_text()
    shipped.write_text(original.replace("affected_symbols", "affected_symbols ", 1))
    result = subprocess.run(
        [sys.executable, "-m", "harness.join", "replay", "affected_symbols",
         "--commit", "4b30c3814ccd2b4cfd5ac4b18b2f177ba59355eb",
         "--shipped", str(shipped), "--repo", str(PROJECT_ROOT)],
        capture_output=True, text=True, cwd=PROJECT_ROOT,
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
    )
    assert result.returncode == 1
    assert "DIVERGED" in result.stdout


# --- v0.5 bundle: observed_through (B) + seeded-growth policy (C) ------------


def test_tester_packet_surface_is_contained_in_its_own_node():
    # Ruled standing gate line: every tester packet's type and callable
    # lines are a subset of its own node's surface. F33's test covered the
    # instance (a prose line matching everything); this covers the class.
    plan = join.load_plan(PROJECT_ROOT / "harness" / "specs")
    index = build_index(PROJECT_ROOT, None)
    resolved = join.resolve_writes(plan, index)
    violations = join.tester_containment(plan, index, resolved,
                                         identities_dir=PROJECT_ROOT / "harness" / "identities",
                                         repo=PROJECT_ROOT)
    assert violations == []


def test_prose_type_line_does_not_leak_into_other_nodes_packets():
    # A prose types line has no "(", so terminal extraction produced "" and
    # the \b\b word-boundary guard matched every packet — handing gitio's
    # tester the index's imports contract. P6 leak, found by red-team.
    plan = join.load_plan(PROJECT_ROOT / "harness" / "specs")
    index = build_index(PROJECT_ROOT, None)
    resolved = join.resolve_writes(plan, index)
    for node in ("gitio", "reference_map", "unresolved_sites"):
        packet = join.assemble_packet(
            plan, index, resolved, node, "tester",
            identities_dir=PROJECT_ROOT / "harness" / "identities",
            repo=PROJECT_ROOT,
        )
        assert "imports table" not in packet, node
        assert "[from index_assembly]" not in packet, node


def test_observed_through_renders_in_both_roles():
    for role in ("executor", "tester"):
        packet = real_packet(role=role)
        assert "observed_through: the value returned by the surface callable" in packet


def test_seeded_growth_policy_in_both_protocols():
    executor = real_packet(role="executor")
    tester = real_packet(role="tester")
    assert "Seeded vs authored (ratified)" in executor
    assert "authorises you to add exactly that" in executor
    assert "Seeded vs authored (ratified)" in tester
    assert "authored line leads" in tester


# --- F21/F22/F3 (ratified): catalog, interpreter, protocol-in-packet ---------


def test_tester_packet_carries_trigger_catalog(tmp_path):
    packet = real_packet(role="tester")
    assert "trigger catalog" in packet
    assert "subscript_call" in packet and "TABLE[key](" in packet
    assert "getattr(obj, name)" in packet
    assert "importer set" in packet  # the ratified F18 definition rides along
    executor = real_packet(role="executor")
    assert "trigger catalog" not in executor  # tester-only, P6 untouched


def test_verify_line_names_worktree_interpreter():
    packet = real_packet(role="executor")
    assert "verify with: .venv/bin/python -m pytest" in packet


def test_protocol_section_in_both_roles():
    for role in ("executor", "tester"):
        packet = real_packet(role=role)
        assert "## Protocol  [provenance: fixed]" in packet
        assert "REQUEST_MEM" in packet
        assert packet.index("## Protocol") < packet.index("## Task")
    assert ".harness/out/attestation.md" in real_packet(role="executor")
    assert ".harness/out/defects.md" in real_packet(role="executor")
    assert ".harness/out/tester_report.md" in real_packet(role="tester")


# --- 3c: the dispatch-record emitter -----------------------------------------


def test_record_emitter_composes_from_artifacts(tmp_path):
    import hashlib

    from harness import fence as fence_mod

    repo, sha, shipped = make_replayable(tmp_path)
    plan = join.load_plan(repo / "harness" / "specs")
    index = build_index(repo, sha)
    resolved = join.resolve_writes(plan, index)
    built = fence_mod.build_fence(
        plan, index, resolved, "base", repo=repo, packet_hash="ignored"
    )
    fence_path = fence_mod.write_fence(built, repo)
    out = tmp_path / "record.json"
    result = subprocess.run(
        [sys.executable, "-m", "harness.join", "record", "base",
         "--repo", str(repo), "--commit", sha,
         "--specs", str(repo / "harness" / "specs"),
         "--packet", str(shipped), "--fence", str(fence_path),
         "--dispatch-id", "test-1",
         "--started", "2026-08-07T10:00:00-04:00",
         "--finished", "2026-08-07T10:20:30-04:00",
         "--tokens-out", "1234", "-o", str(out)],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
    )
    assert result.returncode == 0, result.stderr
    record = json.loads(out.read_text())
    assert record["generator"].startswith("harness.join record")
    assert "MANUAL" not in record["generator"]
    trailer = shipped.read_text().rstrip("\n").rsplit("\n", 1)[-1]
    assert record["packet_hash"] in trailer
    assert record["fence_sha256"] == hashlib.sha256(fence_path.read_bytes()).hexdigest()
    assert record["wall_clock_seconds"] == 1230
    assert record["node"] == "base" and record["commit"] == sha
    assert record["tokens"]["output"] == 1234


def test_record_emitter_rejects_trailer_mismatch(tmp_path):
    from harness import fence as fence_mod

    repo, sha, shipped = make_replayable(tmp_path)
    plan = join.load_plan(repo / "harness" / "specs")
    index = build_index(repo, sha)
    resolved = join.resolve_writes(plan, index)
    built = fence_mod.build_fence(plan, index, resolved, "base", repo=repo)
    fence_path = fence_mod.write_fence(built, repo)
    result = subprocess.run(
        [sys.executable, "-m", "harness.join", "record", "consumer_a",
         "--repo", str(repo), "--commit", sha,
         "--specs", str(repo / "harness" / "specs"),
         "--packet", str(shipped), "--fence", str(fence_path),
         "--dispatch-id", "test-2",
         "--started", "2026-08-07T10:00:00-04:00",
         "--finished", "2026-08-07T10:01:00-04:00"],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
    )
    assert result.returncode == 1
    assert "mismatch" in result.stderr.lower()


# --- the real spec against this repo ---------------------------------------


def test_real_spec_resolves_against_this_repo():
    plan = join.load_plan(PROJECT_ROOT / "harness" / "specs")
    index = build_index(PROJECT_ROOT, None)
    resolved = join.resolve_writes(plan, index)
    assert set(resolved) == {
        "gitio",
        "symbol_table",
        "index_assembly",
        "reference_map",
        "unresolved_sites",
        "affected_symbols",
        "analyzer_cli",
    }
    findings = join.plan_checks(plan, index, resolved)
    assert [f for f in findings if f.code == "E08"] == []
    # The ratified index_assembly restructure gave indexer.py its own node
    # with declared edges, so the reverse edge that produced W05 is gone.
    # This is F30 retiring, asserted rather than described.
    assert [f for f in findings if f.code == "W05"] == []
