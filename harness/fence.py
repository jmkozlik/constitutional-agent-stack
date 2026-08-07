"""The write-fence: a node's write scope, compiled into a wall.

Derived ONLY from the node's resolved writes — the same data as the
packet's DELTA block — so the fence and the packet can never disagree
about scope. Three layers, hardest first:

1. the diff gate (`check_diff`): git's view of what changed must be a
   subset of the fence — the run auto-fails otherwise;
2. the PreToolUse hook (.claude/hooks/write-fence.py): denies Write/Edit
   outside the fence and, best-effort, obvious Bash write patterns;
3. `apply_fence`: chmod existing out-of-scope files read-only,
   reversibly — friction, not proof.

Run: python -m harness.fence build|apply|release|check ...
"""

import argparse
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

from analyzer.indexer import build_index
from harness import join

FENCE_DIR = ".harness"


def build_fence(
    plan, code_index, resolved, node_id: str, *, repo=None, packet_hash=None
) -> dict:
    if node_id not in plan.nodes:
        raise join.JoinError(f"unknown node {node_id!r}")
    delta = join.compute_delta(plan, code_index, resolved, node_id, repo=repo)
    dispatch = join.serialize_plan(
        plan, join.plan_checks(plan, code_index, resolved)
    )
    return {
        "version": 1,
        "node": node_id,
        "plan": dispatch.plan_hash,
        "packet_hash": packet_hash,
        "allowed": {entry: status for entry, status in delta["writes"]},
        # Sanctioned ephemeral space (v0.4.1): fixtures, notes, the handoff.
        # Inside the worktree so the fence sees it; under .harness so the
        # diff gate exempts it.
        "scratch": [f"{FENCE_DIR}/scratch"],
    }


def write_fence(fence: dict, worktree) -> Path:
    target_dir = Path(worktree) / FENCE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "fence.json"
    target.write_text(json.dumps(fence, indent=2, sort_keys=True) + "\n")
    for scratch in fence.get("scratch", []):
        (Path(worktree) / scratch).mkdir(parents=True, exist_ok=True)
    return target


def _tracked_files(worktree) -> list:
    out = subprocess.run(
        ["git", "-C", str(worktree), "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [line for line in out.splitlines() if line]


def apply_fence(fence: dict, worktree) -> list:
    """Chmod existing out-of-scope files read-only; reversible via the
    recorded mode map. Friction against accidental writes — the hook and
    the diff gate are the real walls."""
    root = Path(worktree)
    allowed = set(fence.get("allowed", {}))
    modes = {}
    for rel in _tracked_files(worktree):
        if rel in allowed or rel.startswith(FENCE_DIR):
            continue
        path = root / rel
        if not path.is_file():
            continue
        mode = path.stat().st_mode
        modes[rel] = mode
        path.chmod(mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    mode_file = root / FENCE_DIR / "fence_modes.json"
    mode_file.parent.mkdir(parents=True, exist_ok=True)
    mode_file.write_text(json.dumps(modes, indent=2, sort_keys=True) + "\n")
    return sorted(modes)


def release_fence(worktree) -> int:
    root = Path(worktree)
    mode_file = root / FENCE_DIR / "fence_modes.json"
    if not mode_file.exists():
        return 0
    modes = json.loads(mode_file.read_text())
    for rel, mode in modes.items():
        path = root / rel
        if path.exists():
            path.chmod(mode)
    mode_file.unlink()
    return len(modes)


def check_diff(worktree) -> list:
    """The gate: every path git sees as changed (staged, unstaged, or
    untracked) must be inside the fence. Violations fail the run."""
    fence = json.loads((Path(worktree) / FENCE_DIR / "fence.json").read_text())
    allowed = set(fence.get("allowed", {}))
    out = subprocess.run(
        ["git", "-C", str(worktree), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    changed = set()
    for line in out.splitlines():
        if not line.strip():
            continue
        path = line[3:]
        if " -> " in path:
            old, new = path.split(" -> ", 1)
            changed.update((old, new))
        else:
            changed.add(path)
    return sorted(
        p
        for p in changed
        if not p.startswith(FENCE_DIR + "/") and p.rstrip("/") != FENCE_DIR
        and p not in allowed
    )


def _cmd_build(args) -> int:
    plan = join.load_plan(args.specs)
    commit = None if args.worktree else (args.commit or "HEAD")
    index = build_index(args.repo, commit)
    resolved = join.resolve_writes(plan, index)
    fence = build_fence(
        plan, index, resolved, args.node,
        repo=args.repo, packet_hash=args.packet_hash,
    )
    if args.target:
        path = write_fence(fence, args.target)
        print(f"fence -> {path}", file=sys.stderr)
    else:
        sys.stdout.write(json.dumps(fence, indent=2, sort_keys=True) + "\n")
    return 0


def _cmd_apply(args) -> int:
    fence = json.loads(
        (Path(args.worktree_dir) / FENCE_DIR / "fence.json").read_text()
    )
    locked = apply_fence(fence, args.worktree_dir)
    print(f"fenced: {len(locked)} out-of-scope files now read-only")
    return 0


def _cmd_release(args) -> int:
    restored = release_fence(args.worktree_dir)
    print(f"released: {restored} files restored")
    return 0


def _cmd_check(args) -> int:
    violations = check_diff(args.worktree_dir)
    if violations:
        print("write-fence gate: RUN FAILS — out-of-scope changes:", file=sys.stderr)
        for path in violations:
            print(f"  {path}", file=sys.stderr)
        return 1
    print("write-fence gate: clean (all changes within scope)")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="harness.fence", description="Build and enforce a node's write fence."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build")
    p_build.add_argument("node")
    p_build.add_argument("--specs", default="harness/specs")
    p_build.add_argument("--repo", default=".")
    p_build.add_argument("--commit", default=None)
    p_build.add_argument("--worktree", action="store_true")
    p_build.add_argument("--packet-hash", default=None)
    p_build.add_argument("-t", "--target", default=None,
                         help="worktree to land .harness/fence.json in")
    p_build.set_defaults(func=_cmd_build)

    for name, func in (("apply", _cmd_apply), ("release", _cmd_release), ("check", _cmd_check)):
        p = sub.add_parser(name)
        p.add_argument("worktree_dir")
        p.set_defaults(func=func)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (join.JoinError, FileNotFoundError, subprocess.CalledProcessError) as exc:
        print(f"fence: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
