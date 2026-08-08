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


def _source_of_committed(repo, commit, rel_path):
    from analyzer import gitio

    try:
        return gitio.read_files(repo, commit, [rel_path])[rel_path].decode(
            errors="replace"
        )
    except (GitError, KeyError):
        return None


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
    handoff=None,
    handoff_path=None,
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

    handoff_text = None
    if handoff:
        raise DispatchError(
            "--handoff takes raw text from outside the commit, which is what "
            "broke replay (F36): a packet built from it cannot be rebuilt "
            "from the commit. Commit the handoff and pass --handoff-path "
            "<repo-relative path> instead."
        )
    packet = join.assemble_packet(
        plan, index, resolved, node, role,
        identities_dir=identities, repo=repo, handoff=handoff_text,
        handoff_path=handoff_path,
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
    if handoff_text or handoff_path:
        # The input to a dispatch is evidence: keep it where harvest can see
        # it, so a future reader has what the executor was actually handed.
        (worktree / ".harness" / "handoff.md").write_text(
            handoff_text or _source_of_committed(repo, sha, handoff_path) or "",
            encoding="utf-8",
        )
    fence_mod.apply_fence(built, worktree)

    wall = canary(worktree)
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
        # Recorded so replay knows whether this packet is rebuildable.
        "handoff_path": handoff_path,
        "handoff_replayable": bool(handoff_path) or not handoff,
        "wall": wall,
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


HOOK = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "write-fence.py"


def canary(worktree) -> dict:
    """F28 spawn canary: prove the wall refuses before an agent runs.

    Feeds the hook the probes a dispatch must never be allowed — a write
    outside the fence, and (under a hard read policy) a pathless search —
    and fails if either is permitted.

    LIMIT, stated because it matters: this exercises the hook SCRIPT. It
    cannot prove the hook is registered in the session that will spawn the
    agent, so it does not detect an unregistered matcher or a session with
    hooks disabled. Proving registration needs an agent-side first-call
    canary — filed, not claimed.
    """
    worktree = Path(worktree)
    fence = json.loads((worktree / fence_mod.FENCE_DIR / "fence.json").read_text())
    probes = [{
        "tool": "Write",
        "payload": {
            "cwd": str(worktree),
            "tool_name": "Write",
            "tool_input": {"file_path": str(worktree / "conftest.py")},
        },
    }]
    if fence.get("read_policy") == "hard":
        probes.append({
            "tool": "Grep",
            "payload": {
                "cwd": str(worktree),
                "tool_name": "Grep",
                "tool_input": {"pattern": "def "},
            },
        })
    results = []
    for probe in probes:
        proc = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(probe["payload"]),
            capture_output=True, text=True,
        )
        results.append({
            "probe": probe["tool"],
            "denied": proc.returncode == 2,
            "message": proc.stderr.strip()[:200],
        })
    live = all(r["denied"] for r in results)
    return {"wall": "live" if live else "INERT", "probes": results,
            "proves": "hook script logic only, not its registration"}


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
    # F29 telemetry: read events live at .harness/ (neither out/ nor
    # scratch/), so they must be folded explicitly or they are lost at
    # teardown along with the only record of what was read.
    handoff_src = worktree / ".harness" / "handoff.md"
    if handoff_src.exists():
        shutil.copy2(handoff_src, evidence / "handoff.md")
    events_path = worktree / ".harness" / "read_events.jsonl"
    reads_out_of_packet = []
    if events_path.exists():
        shutil.copy2(events_path, evidence / "read_events.jsonl")
        for line in events_path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                reads_out_of_packet.append(json.loads(line))
            except json.JSONDecodeError:
                reads_out_of_packet.append({"unparseable": line[:200]})
    result["reads_out_of_packet"] = reads_out_of_packet
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
        # A distinct key on purpose: miss_log has counted request_mem gaps
        # since 3a, and folding reads into it would put a schema step change
        # into the ledger's miss column and call it behaviour.
        "reads_out_of_packet": reads_out_of_packet,
        "self_served_misses": len(reads_out_of_packet),
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
        interpreter=args.interpreter, handoff=args.handoff,
        handoff_path=args.handoff_path,
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


def _cmd_canary(args) -> int:
    result = canary(args.worktree)
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0 if result["wall"] == "live" else 1


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
    p.add_argument("--handoff", default=None,
                   help="raw file whose text lands in the handoff section "
                        "(NOT replayable — see F36; prefer --handoff-path)")
    p.add_argument("--handoff-path", default=None,
                   help="repo-relative path, read AT THE PINNED COMMIT, so the "
                        "packet stays reproducible by replay")
    p.set_defaults(func=_cmd_prepare)

    h = sub.add_parser("harvest", help="collect artifacts, run the gate, emit the record")
    h.add_argument("worktree")
    h.add_argument("--evidence", default=None)
    h.add_argument("--started", default=None)
    h.add_argument("--finished", default=None)
    h.set_defaults(func=_cmd_harvest)

    c = sub.add_parser("canary", help="prove the fence refuses before spawning")
    c.add_argument("worktree")
    c.set_defaults(func=_cmd_canary)

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
