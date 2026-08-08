"""harness/dispatch.py — the deterministic hands.

Everything a dispatch does EXCEPT the model call: worktree, fence, packet
delivery, the compiled prompt, harvest, gate, record, teardown. The
non-deterministic half (spawning the agent) stays with the operator, so
the hands are testable and the same for every caller — CLI or interface.
"""

import json
import subprocess
import sys

import pytest

from harness import dispatch, join
from tests.conftest import PROJECT_ROOT, git
from tests.test_join import SPEC_SURFACED, SURFACED_FILES, make_join_fixture


def prepared(tmp_path, node="base", role="executor"):
    specs, repo = make_join_fixture(tmp_path, SPEC_SURFACED, SURFACED_FILES)
    (tmp_path / "identities").mkdir(exist_ok=True)
    for r in ("executor", "tester"):
        (tmp_path / "identities" / f"{r}.md").write_text(
            (PROJECT_ROOT / "harness" / "identities" / f"{r}.md").read_text()
        )
    ctx = dispatch.prepare(
        node, role=role, repo=repo, specs=specs,
        commit=git(repo, "rev-parse", "HEAD"),
        dispatch_id="t1", root=tmp_path / "dispatches",
    )
    return ctx, repo


def test_prepare_lands_a_fenced_worktree_with_the_packet(tmp_path):
    ctx, repo = prepared(tmp_path)
    try:
        worktree = ctx["worktree"]
        assert (worktree / ".harness" / "packet.md").exists()
        assert (worktree / ".harness" / "fence.json").exists()
        assert (worktree / ".harness" / "out").is_dir()
        assert (worktree / ".harness" / "scratch").is_dir()
        # the packet delivered is the packet the manifest claims
        trailer = (worktree / ".harness" / "packet.md").read_text().rstrip("\n").rsplit("\n", 1)[-1]
        assert ctx["packet_hash"] in trailer
        assert len(ctx["fence_sha256"]) == 64
        # out-of-scope files are read-only
        assert not (worktree / "core" / "b.py").stat().st_mode & 0o200
    finally:
        dispatch.teardown(ctx)


def test_prepare_compiles_the_prompt_and_carries_no_law(tmp_path):
    ctx, repo = prepared(tmp_path)
    try:
        prompt = ctx["prompt"]
        # operational only: it points at the packet and the environment
        assert str(ctx["worktree"] / ".harness" / "packet.md") in prompt
        assert "interpreter" in prompt.lower()
        # F3: the prompt carries no contract — that lives in the packet
        for law in ("done_when", "attestation.md", "REQUEST_MEM:", "write scope"):
            assert law not in prompt
    finally:
        dispatch.teardown(ctx)


def test_prepare_is_deterministic(tmp_path):
    # Same repo, same commit, two dispatches: every compiled value must
    # match. Only the dispatch id (and so the paths) may differ.
    specs, repo = make_join_fixture(tmp_path, SPEC_SURFACED, SURFACED_FILES)
    (tmp_path / "identities").mkdir(exist_ok=True)
    for r in ("executor", "tester"):
        (tmp_path / "identities" / f"{r}.md").write_text(
            (PROJECT_ROOT / "harness" / "identities" / f"{r}.md").read_text()
        )
    sha = git(repo, "rev-parse", "HEAD")

    def once(did):
        return dispatch.prepare(
            "base", role="executor", repo=repo, specs=specs, commit=sha,
            dispatch_id=did, root=tmp_path / "dispatches",
        )

    ctx1 = once("d1")
    ctx2 = once("d2")
    try:
        for key in ("packet_hash", "fence_sha256", "spec_plan_hash",
                    "dispatch_plan_hash", "commit", "delta"):
            assert ctx1[key] == ctx2[key], key
    finally:
        dispatch.teardown(ctx1)
        dispatch.teardown(ctx2)


def test_prepare_tester_role_fences_all_tracked_writes(tmp_path):
    ctx, repo = prepared(tmp_path, role="tester")
    try:
        fence = json.loads((ctx["worktree"] / ".harness" / "fence.json").read_text())
        assert fence["allowed"] == {}
        assert fence["role"] == "tester"
    finally:
        dispatch.teardown(ctx)


def test_harvest_collects_artifacts_stores_code_inert_and_gates(tmp_path):
    ctx, repo = prepared(tmp_path)
    try:
        out = ctx["worktree"] / ".harness" / "out"
        (out / "attestation.md").write_text("# Attestation\n\nATTEST\n")
        (out / "tests").mkdir()
        (out / "tests" / "test_x.py").write_text("def test_x():\n    assert True\n")
        (ctx["worktree"] / ".harness" / "scratch" / "probe.py").write_text("x = 1\n")
        evidence = tmp_path / "evidence"
        result = dispatch.harvest(ctx, evidence=evidence)
        assert result["gate"] == "clean"
        assert (evidence / "harvest-out" / "attestation.md").exists()
        # harvested code is stored inert — evidence is never indexable source
        assert (evidence / "harvest-out" / "tests" / "test_x.py.txt").exists()
        assert not (evidence / "harvest-out" / "tests" / "test_x.py").exists()
        assert (evidence / "harvest-scratch" / "probe.py.txt").exists()
        record = json.loads((evidence / "dispatch_record_t1.json").read_text())
        assert record["generator"].startswith("harness.dispatch")
        assert record["packet_hash"] == ctx["packet_hash"]
        assert record["role"] == "executor"
    finally:
        dispatch.teardown(ctx)


def test_harvest_reports_a_gate_violation(tmp_path):
    ctx, repo = prepared(tmp_path)
    try:
        target = ctx["worktree"] / "core" / "b.py"
        target.chmod(0o644)
        target.write_text("def beta():\n    return 99\n")
        result = dispatch.harvest(ctx, evidence=tmp_path / "evidence2")
        assert result["gate"] == "violated"
        assert "core/b.py" in result["violations"]
    finally:
        dispatch.teardown(ctx)


def test_teardown_releases_modes_and_removes_the_worktree(tmp_path):
    ctx, repo = prepared(tmp_path)
    worktree = ctx["worktree"]
    dispatch.teardown(ctx)
    assert not worktree.exists()
    listed = subprocess.run(
        ["git", "-C", str(repo), "worktree", "list"],
        capture_output=True, text=True,
    ).stdout
    assert str(worktree) not in listed


def test_cli_prepare_emits_manifest_json(tmp_path):
    specs, repo = make_join_fixture(tmp_path, SPEC_SURFACED, SURFACED_FILES)
    (tmp_path / "identities").mkdir(exist_ok=True)
    for r in ("executor", "tester"):
        (tmp_path / "identities" / f"{r}.md").write_text(
            (PROJECT_ROOT / "harness" / "identities" / f"{r}.md").read_text()
        )
    result = subprocess.run(
        [sys.executable, "-m", "harness.dispatch", "prepare", "base",
         "--repo", str(repo), "--specs", str(specs),
         "--commit", git(repo, "rev-parse", "HEAD"),
         "--id", "t2", "--root", str(tmp_path / "d2")],
        capture_output=True, text=True, cwd=PROJECT_ROOT,
        env={"PATH": __import__("os").environ["PATH"],
             "PYTHONPATH": str(PROJECT_ROOT)},
    )
    assert result.returncode == 0, result.stderr
    manifest = json.loads(result.stdout)
    assert manifest["node"] == "base"
    assert manifest["packet_hash"]
    subprocess.run(
        [sys.executable, "-m", "harness.dispatch", "teardown",
         manifest["worktree"]],
        capture_output=True, cwd=PROJECT_ROOT,
        env={"PATH": __import__("os").environ["PATH"],
             "PYTHONPATH": str(PROJECT_ROOT)},
    )
