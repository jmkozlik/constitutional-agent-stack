"""The write-fence: compiler plumbing that turns a node's write scope
into an enforced wall (fence.json + chmod + diff gate + PreToolUse hook)."""

import json
import os
import stat
import subprocess
import sys

from analyzer.indexer import build_index
from harness import fence, join
from tests.conftest import PROJECT_ROOT, git
from tests.test_join import SPEC_SURFACED, SURFACED_FILES, make_join_fixture

HOOK = PROJECT_ROOT / ".claude" / "hooks" / "write-fence.py"


def fenced_fixture(tmp_path, node="base"):
    specs, repo = make_join_fixture(tmp_path, SPEC_SURFACED, SURFACED_FILES)
    plan = join.load_plan(specs)
    index = build_index(repo, None)
    resolved = join.resolve_writes(plan, index)
    built = fence.build_fence(
        plan, index, resolved, node, repo=repo, packet_hash="abc123def456"
    )
    return built, repo


def test_build_fence_contents_and_determinism(tmp_path):
    built, repo = fenced_fixture(tmp_path)
    assert built["node"] == "base"
    assert built["packet_hash"] == "abc123def456"
    assert len(built["plan"]) == 12
    assert built["allowed"]["core/base.py"].startswith("exists@")
    (tmp_path / "again").mkdir()
    again, _ = fenced_fixture(tmp_path / "again")
    assert json.dumps(built, sort_keys=True) == json.dumps(again, sort_keys=True)


def test_build_fence_to_create(tmp_path):
    spec = SPEC_SURFACED.replace("core/base.py", "core/unbuilt.py").replace(
        "core.base.", "core.unbuilt."
    )
    specs, repo = make_join_fixture(tmp_path, spec, SURFACED_FILES)
    plan = join.load_plan(specs)
    index = build_index(repo, None)
    resolved = join.resolve_writes(plan, index)
    built = fence.build_fence(plan, index, resolved, "base", repo=repo)
    assert built["allowed"]["core/unbuilt.py"] == "to_create"


def test_write_fence_lands_in_harness_dir(tmp_path):
    built, repo = fenced_fixture(tmp_path)
    path = fence.write_fence(built, repo)
    assert path.name == "fence.json"
    assert path.parent.name == ".harness"
    assert json.loads(path.read_text())["node"] == "base"


def test_apply_and_release_fence_chmod_roundtrip(tmp_path):
    built, repo = fenced_fixture(tmp_path)
    fence.write_fence(built, repo)
    out_of_scope = repo / "core" / "a.py"
    in_scope = repo / "core" / "base.py"
    before = out_of_scope.stat().st_mode
    fence.apply_fence(built, repo)
    assert not out_of_scope.stat().st_mode & stat.S_IWUSR
    assert in_scope.stat().st_mode & stat.S_IWUSR
    fence.release_fence(repo)
    assert out_of_scope.stat().st_mode == before


def test_diff_gate_clean_and_violated(tmp_path):
    built, repo = fenced_fixture(tmp_path)
    fence.write_fence(built, repo)
    assert fence.check_diff(repo) == []
    (repo / "core" / "base.py").write_text("def ground() -> int:\n    return 1\n")
    assert fence.check_diff(repo) == []  # in-scope edit is fine
    (repo / "core" / "b.py").write_text("def beta():\n    return 99\n")
    violations = fence.check_diff(repo)
    assert violations == ["core/b.py"]


def run_hook(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )


def test_hook_allows_in_scope_write(tmp_path):
    built, repo = fenced_fixture(tmp_path)
    fence.write_fence(built, repo)
    result = run_hook(
        {"tool_name": "Write", "cwd": str(repo),
         "tool_input": {"file_path": str(repo / "core" / "base.py")}}
    )
    assert result.returncode == 0


def test_hook_denies_out_of_scope_write(tmp_path):
    built, repo = fenced_fixture(tmp_path)
    fence.write_fence(built, repo)
    result = run_hook(
        {"tool_name": "Write", "cwd": str(repo),
         "tool_input": {"file_path": str(repo / "core" / "b.py")}}
    )
    assert result.returncode == 2
    assert "out of scope" in result.stderr
    assert "REQUEST_MEM or file a defect" in result.stderr
    assert "Do not work around" in result.stderr


def test_hook_denies_bash_redirect_and_sed_and_git_apply(tmp_path):
    built, repo = fenced_fixture(tmp_path)
    fence.write_fence(built, repo)
    for cmd in (
        "echo hacked > core/b.py",
        "cat notes >> core/b.py",
        "sed -i '' 's/x/y/' core/b.py",
        "echo diff | git apply",
    ):
        result = run_hook(
            {"tool_name": "Bash", "cwd": str(repo), "tool_input": {"command": cmd}}
        )
        assert result.returncode == 2, cmd
    ok = run_hook(
        {"tool_name": "Bash", "cwd": str(repo),
         "tool_input": {"command": "echo fine > core/base.py"}}
    )
    assert ok.returncode == 0
    quiet = run_hook(
        {"tool_name": "Bash", "cwd": str(repo),
         "tool_input": {"command": "pytest -q 2>&1 | tail -2"}}
    )
    assert quiet.returncode == 0  # stderr redirect is not a file write


def test_hook_noop_without_fence(tmp_path):
    result = run_hook(
        {"tool_name": "Write", "cwd": str(tmp_path),
         "tool_input": {"file_path": str(tmp_path / "anything.py")}}
    )
    assert result.returncode == 0
