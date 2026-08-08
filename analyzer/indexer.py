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
from analyzer.refs import (
    ImportTable,
    Resolver,
    _scope_stmts,
    collect_references,
)
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


def _module_entry(name: str, module: str) -> dict:
    return {"name": name, "kind": "module", "origin": module, "module": module}


def _symbol_entry(name: str, origin: str, module: str) -> dict:
    return {"name": name, "kind": "symbol", "origin": origin, "module": module}


def _unresolved_entry(name: str, module: str | None) -> dict:
    return {"name": name, "kind": "unresolved", "origin": None, "module": module}


def _defining_modules(resolver: Resolver, path: str) -> list[str]:
    """Dotted modules defining an indexed symbol path, from the resolver's own
    symbol table — one per file a record of that path was extracted from."""
    return sorted({module_path(r["file"]) for r in resolver.symbols.get(path, ())})


def _import_entries(
    tree: ast.Module,
    table: ImportTable,
    resolver: Resolver,
    flagged: set[tuple[int, str]],
) -> list[dict]:
    """One entry per name an import statement binds in this file.

    The statement supplies the binding (name, and the module it names);
    the resolver supplies the origin. Nothing here re-resolves: `base_of`
    resolves relative levels and `resolve_dotted` chases re-exports, both
    in refs. `flagged` carries refs' own unresolved verdicts for this file,
    keyed (line, reason), so the unresolved_import_target case is read off
    the reference pass rather than re-decided here.
    """
    entries: list[dict] = []
    for stmt in _scope_stmts(tree.body):
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                # `import a.b` binds `a` but names the module `a.b`; the
                # binding keeps the name, the entry keeps the module, so an
                # imported-but-uncalled submodule still leaves a trace.
                bound = alias.asname or alias.name.split(".")[0]
                entries.append(_module_entry(bound, alias.name))
        elif isinstance(stmt, ast.ImportFrom):
            base = table.base_of(stmt)
            if any(alias.name == "*" for alias in stmt.names):
                # The bound names are unknowable, but the source module is
                # stated — a fact, so it is kept.
                entries.append(_unresolved_entry("*", base or None))
                continue
            # refs flags a target unresolvable only when the source module
            # itself star-imports, which is what makes the stated base
            # untrustworthy as the definer; then both fields go null.
            poisoned = (stmt.lineno, "unresolved_import_target") in flagged
            for alias in stmt.names:
                bound = alias.asname or alias.name
                target = f"{base}.{alias.name}" if base else alias.name
                if resolver.is_module(target):
                    entries.append(_module_entry(bound, target))
                    continue
                hits = [
                    (path, module)
                    for path, _note in resolver.resolve_dotted(target)
                    for module in _defining_modules(resolver, path)
                ]
                if hits:
                    entries.extend(
                        _symbol_entry(bound, path, module) for path, module in hits
                    )
                elif poisoned:
                    entries.append(_unresolved_entry(bound, None))
                else:
                    entries.append(_unresolved_entry(bound, base or None))
    return entries


def _sorted_entries(entries: list[dict]) -> list[dict]:
    """Deduplicated, sorted by (name, origin) — the remaining fields break
    ties so the order is total and byte-identity survives."""
    unique = {
        (e["name"], e["origin"], e["kind"], e["module"]): e for e in entries
    }
    return [
        unique[key]
        for key in sorted(
            unique, key=lambda k: (k[0], k[1] or "", k[2], k[3] or "")
        )
    ]


def build_index(repo: str | Path, commit: str | None) -> dict:
    """Index a repo (working tree, or a commit's blobs when `commit` is set).

    Returns the index dict, serialized 1:1 into index.json:
      version: 1
      commit:  full sha, or None for a working-tree index
      files:   every indexed .py path, sorted, repo-relative
      symbols: one record per definition, sorted by
               (path, file, start_line, sig_hash, body_hash):
               path (dotted), kind (function|async_function|class), file,
               start_line/end_line (decorators included), signature (display
               string), doc (docstring or null), sig_hash (name+params+
               annotations+defaults-presence+return), body_hash (unparsed
               body), decor_hash, parent (enclosing scope's dotted path),
               confidence ("low" iff the file has any unresolved record),
               referenced_by (sites: file, line, in_symbol, kind call|name,
               args as written for calls, ambiguous+note when inexact).
               Class records additionally carry fields (annotated class-body
               targets in body order, rendered `name: ann = default`).
               Duplicate dotted paths are legal (property pairs, conditional
               defs); records sharing a path share their referenced_by.
      unresolved: sites whose target is statically undecidable — file, line,
               in_symbol, reason (subscript_call | getattr_call |
               attribute_of_call | star_import | dynamic_attribute |
               parse_error | unresolved_import_target), expression.
      imports: {file: [binding]} — every indexed file, empty list when it
               imports nothing or failed to parse. A binding is name (as
               bound in this file), kind (module | symbol | unresolved),
               origin (dotted resolved terminal: the symbol path for a name
               binding, the module path for a module binding, null when
               unresolvable) and module (dotted defining module, equal to
               origin for module-kind entries). Files sorted by path,
               entries by (name, origin).
    """
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
    flagged_by_file: dict[str, set[tuple[int, str]]] = defaultdict(set)
    for site in unresolved:
        flagged_by_file[site["file"]].add((site["line"], site["reason"]))
    imports = {}
    for rel in sorted(files):
        if rel not in trees:
            imports[rel] = []  # never parsed; its parse_error site stands
            continue
        tree, mod = trees[rel]
        imports[rel] = _sorted_entries(
            _import_entries(tree, tables[mod], resolver, flagged_by_file[rel])
        )

    return {
        "version": 1,
        "commit": sha,
        "files": list(files),
        "symbols": symbols_out,
        "unresolved": unresolved,
        "imports": imports,
    }


def serialize(index: dict) -> str:
    return json.dumps(index, indent=2, sort_keys=True) + "\n"


def import_origins(index: dict, module: str) -> list[str]:
    """Repo-relative files importing `module`, sorted and deduplicated.

    Answers from the index's imports table by matching the `module` field —
    the dotted defining module — so a name imported through a re-export
    facade counts against the module that actually defines it. Empty for a
    module nothing imports and for an index built before the key existed.
    """
    imports = index.get("imports") or {}
    return sorted(
        file
        for file, entries in imports.items()
        if any(entry.get("module") == module for entry in entries)
    )


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
