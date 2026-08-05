"""CLI: index / symbol / affected / unresolved."""

import argparse
import sys
from pathlib import Path

from analyzer.gitio import GitError
from analyzer.indexer import build_index, load_index, serialize


def _cmd_index(args) -> int:
    try:
        index = build_index(args.repo, args.commit)
    except (GitError, FileNotFoundError) as exc:
        print(f"analyzer: {exc}", file=sys.stderr)
        return 1
    Path(args.output).write_text(serialize(index), encoding="utf-8")
    print(
        f"indexed {len(index['symbols'])} symbols, "
        f"{len(index['unresolved'])} unresolved sites -> {args.output}"
    )
    return 0


def _load(args) -> dict | None:
    try:
        return load_index(args.index)
    except FileNotFoundError:
        print(
            f"analyzer: index file {args.index!r} not found (run `analyzer index` first)",
            file=sys.stderr,
        )
        return None


def _format_caller(ref: dict) -> str:
    line = f"  caller: {ref['file']}:{ref['line']} in {ref['in_symbol']}"
    if "args" in ref:
        line += f" args=({', '.join(ref['args'])})"
    if ref.get("ambiguous"):
        line += f" [ambiguous: {ref['note']}]"
    return line


def _cmd_symbol(args) -> int:
    index = _load(args)
    if index is None:
        return 1
    records = [s for s in index["symbols"] if s["path"] == args.path]
    if not records:
        print(f"analyzer: symbol {args.path!r} not found", file=sys.stderr)
        return 1
    for record in records:
        print(f"{record['path']}  [{record['kind']}, confidence {record['confidence']}]")
        print(f"  defined: {record['file']}:{record['start_line']}-{record['end_line']}")
        print(f"  signature: {record['signature'] or '(none)'}")
        print(f"  parent: {record['parent']}")
        print(
            f"  hashes: sig {record['sig_hash']}  body {record['body_hash']}  "
            f"decorators {record['decor_hash']}"
        )
        callers = record["referenced_by"]
        if callers:
            print(f"  referenced by {len(callers)} site(s):")
            for ref in callers:
                print(_format_caller(ref))
        else:
            print("  referenced by: nobody recorded")
        print()
    return 0


def _cmd_unresolved(args) -> int:
    index = _load(args)
    if index is None:
        return 1
    for record in index["unresolved"]:
        print(
            f"{record['file']}:{record['line']}  {record['reason']}  "
            f"in {record['in_symbol']}  {record['expression']}"
        )
    return 0


def _cmd_affected(args) -> int:
    from analyzer.affected import compute_affected, render_report

    try:
        report = compute_affected(args.repo, args.old, args.new)
    except GitError as exc:
        print(f"analyzer: {exc}", file=sys.stderr)
        return 1
    render_report(report, sys.stdout)
    return 1 if report.has_error else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="analyzer",
        description="Index a Python repo: symbols, references, unresolved sites, diff impact.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser("index", help="index a repo into a JSON file")
    p_index.add_argument("repo")
    p_index.add_argument("--commit", default=None, help="rev to index (default: working tree)")
    p_index.add_argument("-o", "--output", default="index.json")
    p_index.set_defaults(func=_cmd_index)

    p_symbol = sub.add_parser("symbol", help="show a symbol's definition and callers")
    p_symbol.add_argument("path")
    p_symbol.add_argument("--index", default="index.json")
    p_symbol.set_defaults(func=_cmd_symbol)

    p_affected = sub.add_parser("affected", help="symbols affected between two revs")
    p_affected.add_argument("old")
    p_affected.add_argument("new")
    p_affected.add_argument("--repo", default=".")
    p_affected.set_defaults(func=_cmd_affected)

    p_unresolved = sub.add_parser("unresolved", help="list unresolved call sites")
    p_unresolved.add_argument("--index", default="index.json")
    p_unresolved.set_defaults(func=_cmd_unresolved)

    args = parser.parse_args(argv)
    return args.func(args)
