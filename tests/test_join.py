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
    assert "verify with: python -m pytest" in packet
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
    assert "authored" in statuses["core.base.Report.total ∈ small | large  [authored]"]
    assert "authored" in statuses["core.base.record(path: str, line: int)  [authored]"]
    assert delta["kind"] == "empty"  # authored lines never count outstanding


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


# --- the real spec against this repo ---------------------------------------


def test_real_spec_resolves_against_this_repo():
    plan = join.load_plan(PROJECT_ROOT / "harness" / "specs")
    index = build_index(PROJECT_ROOT, None)
    resolved = join.resolve_writes(plan, index)
    assert set(resolved) == {
        "gitio",
        "symbol_table",
        "reference_map",
        "unresolved_sites",
        "affected_symbols",
        "analyzer_cli",
    }
    findings = join.plan_checks(plan, index, resolved)
    assert [f for f in findings if f.code == "E08"] == []
    # The known as-built reverse edge: indexer.py (symbol_table) consumes
    # refs.py (reference_map).
    assert any(f.code == "W05" for f in findings)
