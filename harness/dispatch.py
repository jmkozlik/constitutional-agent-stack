"""The deterministic hands of a dispatch.

Everything a dispatch does EXCEPT the model call: cut the worktree, build
and apply the fence, compile and deliver the packet, compile the prompt,
then harvest, gate, record and tear down. 3a/3b/3t established this
procedure by hand; this module is that procedure with the hands made
deterministic, so every caller — the CLI, the interface, a future
scheduler — performs the identical sequence.

The agent spawn stays with the operator on purpose. It is the one
non-deterministic step, so it is the one step that is not in here.

Run: python -m harness.dispatch prepare|harvest|teardown ...
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from analyzer.gitio import GitError
from analyzer.indexer import build_index
from harness import fence as fence_mod
from harness import join

GENERATOR = "harness.dispatch/1"

_HARVEST_SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv"}
_HARVEST_SKIP_SUFFIXES = {".pyc", ".pyo"}

# Operational context only. The contract — deliverables, request_mem shape,
# fence terms, done_when — lives in the packet's own Protocol section (F3:
# dispatch prompts carry no law). Everything here is environment.
PROMPT_TEMPLATE = """You are dispatched into a git worktree at {worktree}

FIRST: read {packet}

That packet is your complete contract. Follow it exactly. Nothing in this
prompt overrides it or adds to it.

Operational environment only (environment, not contract):
- Interpreter: {interpreter}
- Working directory: the worktree path above. The package under test is
  importable when you run from there.
- git is available for building fixtures. Configure identity per-command
  (git -c user.email=t@t.t -c user.name=t), never globally.
- Work only inside the worktree. Files outside your scope are read-only by
  design; if a write is denied, record it verbatim and do not work around.

When the deliverables your packet names have been written, stop and reply
with a short summary of what you delivered and any lines your packet told
you to surface.
"""


class DispatchError(Exception):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(
    node: str,
    *,
    role: str = "executor",
    repo=".",
    specs=None,
    commit: str | None = None,
    dispatch_id: str | None = None,
    root=None,
    interpreter: str | None = None,
) -> dict:
    """Cut a fenced worktree at `commit`, compile and deliver the packet,
    and return the manifest the operator needs to spawn against."""
    repo = Path(repo).resolve()
    specs = Path(specs) if specs else repo / "harness" / "specs"
    identities = specs.parent / "identities"
    dispatch_id = dispatch_id or node
    root = Path(root) if root else repo.parent / ".lex-dispatches"
    interpreter = interpreter or str(Path(sys.executable).resolve())

    from analyzer import gitio

    sha = gitio.resolve_commit(repo, commit or "HEAD")
    plan = join.load_plan(specs)
    if node not in plan.nodes:
        raise DispatchError(f"unknown node {node!r}")
    index = build_index(repo, sha)
    resolved = join.resolve_writes(plan, index)

    packet = join.assemble_packet(
        plan, index, resolved, node, role,
        identities_dir=identities, repo=repo,
    )
    trailer = packet.rstrip("\n").rsplit("\n", 1)[-1]
    packet_hash = dict(
        part.split("=", 1) for part in trailer.replace("packet: ", "").split(" ")
        if "=" in part
    ).get("packet_hash", "")

    worktree = (root / dispatch_id).resolve()
    if worktree.exists():
        raise DispatchError(f"dispatch dir already exists: {worktree}")
    worktree.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["git", "-C", str(repo), "worktree", "add", "--detach",
             str(worktree), sha],
            capture_output=True, check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise DispatchError(
            f"worktree add failed: {exc.stderr.decode(errors='replace').strip()}"
        ) from exc

    built = fence_mod.build_fence(
        plan, index, resolved, node, repo=repo,
        packet_hash=packet_hash, role=role,
    )
    fence_path = fence_mod.write_fence(built, worktree)
    (worktree / ".harness" / "out").mkdir(parents=True, exist_ok=True)
    (worktree / ".harness" / "packet.md").write_text(packet, encoding="utf-8")
    fence_mod.apply_fence(built, worktree)

    dispatch_plan = join.serialize_plan(
        plan, join.plan_checks(plan, index, resolved)
    ).plan_hash
    manifest = {
        "record": "dispatch-manifest",
        "generator": GENERATOR,
        "dispatch_id": dispatch_id,
        "node": node,
        "role": role,
        "commit": sha,
        "repo": str(repo),
        "specs": str(specs),
        "worktree": str(worktree),
        "packet": str(worktree / ".harness" / "packet.md"),
        "packet_hash": packet_hash,
        "fence": str(fence_path),
        "fence_sha256": _sha256(fence_path),
        "fence_allowed": built["allowed"],
        "spec_plan_hash": plan.plan_hash,
        "dispatch_plan_hash": dispatch_plan,
        "delta": join.delta_summary(
            join.compute_delta(plan, index, resolved, node, repo=repo)
        ),
        "interpreter": interpreter,
        "prompt": PROMPT_TEMPLATE.format(
            worktree=worktree,
            packet=worktree / ".harness" / "packet.md",
            interpreter=interpreter,
        ),
    }
    (worktree / ".harness" / "manifest.json").write_text(
        json.dumps({k: v for k, v in manifest.items() if k != "prompt"},
                   indent=2, sort_keys=True) + "\n"
    )
    return {**manifest, "worktree": worktree}


def _load_manifest(ctx) -> dict:
    if isinstance(ctx, dict):
        return {**ctx, "worktree": Path(ctx["worktree"])}
    worktree = Path(ctx)
    manifest = json.loads((worktree / ".harness" / "manifest.json").read_text())
    return {**manifest, "worktree": worktree}


def harvest(ctx, *, evidence=None, started=None, finished=None) -> dict:
    """Collect the artifacts, run the diff gate, emit the record. Harvested
    code is stored inert (.py.txt) — evidence is never indexable source."""
    manifest = _load_manifest(ctx)
    worktree = manifest["worktree"]
    violations = fence_mod.check_diff(worktree)
    result = {
        "gate": "violated" if violations else "clean",
        "violations": violations,
        "artifacts": [],
    }
    if evidence is None:
        return result
    evidence = Path(evidence)
    evidence.mkdir(parents=True, exist_ok=True)

    for label, source in (
        ("harvest-out", worktree / ".harness" / "out"),
        ("harvest-scratch", worktree / ".harness" / "scratch"),
    ):
        if not source.is_dir():
            continue
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(source)
            # Fixture repos and caches are apparatus, not evidence. 3d-1's
            # scratch carried two full .git trees; harvesting them would
            # bury the artifacts a reader came for.
            if any(part in _HARVEST_SKIP_DIRS for part in rel.parts):
                continue
            if path.suffix in _HARVEST_SKIP_SUFFIXES:
                continue
            # Inert storage: a harvested .py must never be indexable source.
            if path.suffix == ".py":
                rel = rel.with_suffix(".py.txt")
            target = evidence / label / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            result["artifacts"].append(str(Path(label) / rel))

    packet = worktree / ".harness" / "packet.md"
    if packet.exists():
        shutil.copy2(packet, evidence / "packet.md")
    fence_path = worktree / ".harness" / "fence.json"
    record = {
        "record": "dispatch",
        "generator": GENERATOR,
        "dispatch_id": manifest["dispatch_id"],
        "node": manifest["node"],
        "role": manifest["role"],
        "commit": manifest["commit"],
        "spec_plan_hash": manifest["spec_plan_hash"],
        "dispatch_plan_hash": manifest["dispatch_plan_hash"],
        "packet_hash": manifest["packet_hash"],
        "packet_delivery": f"file (.harness/packet.md, sha256 {_sha256(packet)[:16]}…)",
        "fence_sha256": _sha256(fence_path),
        "fence_allowed": manifest.get("fence_allowed", {}),
        "delta_at_dispatch": manifest.get("delta"),
        "gate": result["gate"],
        "violations": violations,
        "artifacts": result["artifacts"],
        "started": started,
        "finished": finished,
    }
    target = evidence / f"dispatch_record_{manifest['dispatch_id']}.json"
    target.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    result["record"] = str(target)
    return result


def teardown(ctx) -> dict:
    """Release the fence, then remove the worktree. Harvest first — this
    is destructive by design."""
    manifest = _load_manifest(ctx)
    worktree = manifest["worktree"]
    restored = 0
    if worktree.exists():
        restored = fence_mod.release_fence(worktree)
        subprocess.run(
            ["git", "-C", manifest.get("repo", str(worktree)),
             "worktree", "remove", "--force", str(worktree)],
            capture_output=True,
        )
        if worktree.exists():
            shutil.rmtree(worktree, ignore_errors=True)
    return {"released": restored, "removed": str(worktree)}


# --- CLI --------------------------------------------------------------------


def _cmd_prepare(args) -> int:
    manifest = prepare(
        args.node, role=args.role, repo=args.repo, specs=args.specs,
        commit=args.commit, dispatch_id=args.id, root=args.root,
        interpreter=args.interpreter,
    )
    sys.stdout.write(
        json.dumps({**manifest, "worktree": str(manifest["worktree"])},
                   indent=2, sort_keys=True) + "\n"
    )
    return 0


def _cmd_harvest(args) -> int:
    result = harvest(
        args.worktree, evidence=args.evidence,
        started=args.started, finished=args.finished,
    )
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 1 if result["gate"] == "violated" else 0


def _cmd_teardown(args) -> int:
    sys.stdout.write(json.dumps(teardown(args.worktree), sort_keys=True) + "\n")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="harness.dispatch",
        description="The deterministic half of a dispatch: fence, packet, harvest, record.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("prepare", help="cut a fenced worktree and deliver the packet")
    p.add_argument("node")
    p.add_argument("--role", default="executor", choices=("executor", "tester"))
    p.add_argument("--repo", default=".")
    p.add_argument("--specs", default=None)
    p.add_argument("--commit", default=None)
    p.add_argument("--id", default=None)
    p.add_argument("--root", default=None)
    p.add_argument("--interpreter", default=None)
    p.set_defaults(func=_cmd_prepare)

    h = sub.add_parser("harvest", help="collect artifacts, run the gate, emit the record")
    h.add_argument("worktree")
    h.add_argument("--evidence", default=None)
    h.add_argument("--started", default=None)
    h.add_argument("--finished", default=None)
    h.set_defaults(func=_cmd_harvest)

    t = sub.add_parser("teardown", help="release the fence and remove the worktree")
    t.add_argument("worktree")
    t.set_defaults(func=_cmd_teardown)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (DispatchError, join.JoinError, GitError, FileNotFoundError) as exc:
        print(f"dispatch: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
