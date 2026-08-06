"""Orchestration: walk a repo (working tree or commit), run both passes,
emit a deterministic index dict / JSON document."""

import ast
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from analyzer import gitio
from analyzer.modpath import module_path
from analyzer.refs import ImportTable, Resolver, collect_references
from analyzer.symbols import extract_from_tree

_SKIP_DIRS = {"__pycache__", "venv", ".venv", "node_modules"}


def _is_git_repo(root: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
    )
    return result.returncode == 0 and result.stdout.strip() == b"true"


def _worktree_files(root: Path) -> list[str]:
    if _is_git_repo(root):
        # Same file-listing rule as --commit (tracked files, dot-dirs
        # included) plus untracked-but-not-ignored work in progress.
        out = gitio._git(
            root, "ls-files", "--cached", "--others", "--exclude-standard",
            "--", "*.py",
        ).decode()
        return sorted({p for p in out.splitlines() if p.endswith(".py")})
    files = []
    for path in root.rglob("*.py"):
        rel_parts = path.relative_to(root).parts
        if any(p.startswith(".") or p in _SKIP_DIRS for p in rel_parts[:-1]):
            continue
        files.append("/".join(rel_parts))
    return sorted(files)


def build_index(repo: str | Path, commit: str | None) -> dict:
    root = Path(repo)
    read_failures: list[tuple[str, str]] = []
    if commit is not None:
        sha = gitio.resolve_commit(root, commit)
        files = gitio.list_py_files(root, sha)
        blobs = gitio.read_files(root, sha, files)
    else:
        if not root.is_dir():
            raise FileNotFoundError(f"{root} is not a directory")
        sha = None
        files = _worktree_files(root)
        blobs = {}
        for rel in files:
            try:
                blobs[rel] = (root / rel).read_bytes()
            except OSError as exc:
                read_failures.append((rel, str(exc)))
        files = [f for f in files if f in blobs]

    symbols_by_path: dict[str, list[dict]] = defaultdict(list)
    trees: dict[str, tuple[ast.Module, str]] = {}
    unresolved: list[dict] = [
        {
            "file": rel,
            "line": 1,
            "in_symbol": module_path(rel),
            "reason": "parse_error",
            "expression": f"unreadable: {message}",
        }
        for rel, message in read_failures
    ]
    # Deep-but-legal trees (chained binops in generated code) can exceed the
    # default recursion limit inside ast.unparse or the walkers; give
    # headroom and degrade any remaining blowup to a per-file flag.
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 10_000))
    for rel in files:
        mod = module_path(rel)
        try:
            tree = ast.parse(blobs[rel])
            records = extract_from_tree(tree, rel)
        except (SyntaxError, ValueError, RecursionError) as exc:
            unresolved.append(
                {
                    "file": rel,
                    "line": 1,
                    "in_symbol": mod,
                    "reason": "parse_error",
                    "expression": "recursion limit exceeded while analyzing"
                    if isinstance(exc, RecursionError)
                    else str(exc),
                }
            )
            continue
        for record in records:
            symbols_by_path[record["path"]].append(record)
        trees[rel] = (tree, mod)

    tables = {
        mod: ImportTable.from_module(tree, mod, is_package=rel.endswith("__init__.py"))
        for rel, (tree, mod) in trees.items()
    }
    resolver = Resolver(dict(symbols_by_path), tables)

    refs_by_target: dict[str, list[dict]] = defaultdict(list)
    for rel in sorted(trees):
        tree, mod = trees[rel]
        try:
            refs, unres = collect_references(tree, rel, mod, resolver)
        except RecursionError:
            unresolved.append(
                {
                    "file": rel,
                    "line": 1,
                    "in_symbol": mod,
                    "reason": "parse_error",
                    "expression": "recursion limit exceeded during reference pass",
                }
            )
            continue
        for target, record in refs:
            refs_by_target[target].append(record)
        unresolved.extend(unres)

    low_confidence_files = {u["file"] for u in unresolved}
    symbols_out = []
    for path, records in symbols_by_path.items():
        callers = sorted(
            refs_by_target.get(path, []),
            key=lambda r: (
                r["file"],
                r["line"],
                r["in_symbol"],
                r["kind"],
                r.get("note", ""),
                r.get("args", []),
            ),
        )
        for record in records:
            out = dict(record)
            out["confidence"] = (
                "low" if record["file"] in low_confidence_files else "high"
            )
            # Duplicate dotted paths are legal (property/setter pairs,
            # conditional defs); every record of a path carries the same
            # callers because call sites cannot pick between them (plan A6).
            out["referenced_by"] = callers
            symbols_out.append(out)
    symbols_out.sort(
        key=lambda s: (
            s["path"],
            s["file"],
            s["start_line"],
            s["sig_hash"],
            s["body_hash"],
        )
    )
    unresolved.sort(
        key=lambda u: (u["file"], u["line"], u["reason"], u["expression"])
    )
    return {
        "version": 1,
        "commit": sha,
        "files": list(files),
        "symbols": symbols_out,
        "unresolved": unresolved,
    }


def serialize(index: dict) -> str:
    return json.dumps(index, indent=2, sort_keys=True) + "\n"


class IndexLoadError(Exception):
    pass


def load_index(path: str | Path) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            index = json.load(fh)
    except FileNotFoundError:
        raise
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise IndexLoadError(f"cannot read index {str(path)!r}: {exc}") from exc
    if not isinstance(index, dict) or "symbols" not in index or "unresolved" not in index:
        raise IndexLoadError(f"{str(path)!r} is not an analyzer index file")
    return index
