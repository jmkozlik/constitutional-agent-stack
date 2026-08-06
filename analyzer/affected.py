"""Diff two commits into per-symbol impact.

Classification is per dotted path over hash MULTISETS gathered from the
full old and new indexes (plan A7). The brief's §4.2 range-intersection
method cannot satisfy its own `moved` acceptance criterion — an import
inserted at the top of a file lies outside every symbol's range yet
shifts them all — so the diff picks the changed FILES and the hashes
decide what actually happened. Duplicate paths (property pairs,
conditional defs) compare as multisets so an edit to one twin cannot be
masked by the other. A path that changes file but keeps its hashes
(module -> package refactor) is `moved`, not delete+add.

TODO(brief open question): a renamed symbol is treated as delete + add;
following identity through the diff is a later phase.
"""

import sys
from collections import Counter
from dataclasses import dataclass, field

from analyzer import gitio
from analyzer.indexer import build_index


@dataclass
class Row:
    path: str
    category: str
    detail: str
    callers: list = field(default_factory=list)
    error: bool = False


@dataclass
class AffectedReport:
    old: str
    new: str
    rows: list

    @property
    def has_error(self) -> bool:
        return any(row.error for row in self.rows)


def _records_by_path(index: dict) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for record in index["symbols"]:
        out.setdefault(record["path"], []).append(record)
    return out


def _sig_multiset(records: list[dict]) -> Counter:
    # kind participates: def -> async def changes every call site even
    # though the brief-pinned sig_hash cannot see it (plan A8).
    return Counter((r["kind"], r["sig_hash"]) for r in records)


def _body_multiset(records: list[dict]) -> Counter:
    return Counter(r["body_hash"] for r in records)


def _decor_multiset(records: list[dict]) -> Counter:
    return Counter(r["decor_hash"] for r in records)


def _position_multiset(records: list[dict]) -> Counter:
    return Counter((r["file"], r["start_line"], r["end_line"]) for r in records)


def compute_affected(repo, old_rev: str, new_rev: str) -> AffectedReport:
    old_sha = gitio.resolve_commit(repo, old_rev)
    new_sha = gitio.resolve_commit(repo, new_rev)
    old_index = build_index(repo, old_sha)
    new_index = build_index(repo, new_sha)
    changed = {
        path
        for path in gitio.changed_files(repo, old_sha, new_sha)
        if path.endswith(".py")
    }

    old_records = _records_by_path(old_index)
    new_records = _records_by_path(new_index)
    candidates = {
        path
        for records_by_path in (old_records, new_records)
        for path, records in records_by_path.items()
        if any(r["file"] in changed for r in records)
    }

    # A changed file that fails to parse at one rev makes its symbols'
    # ground truth unknowable — classify as `unknown`, never as a
    # definitive deleted/added (flag, don't guess).
    old_bad = {
        u["file"] for u in old_index["unresolved"] if u["reason"] == "parse_error"
    } & changed
    new_bad = {
        u["file"] for u in new_index["unresolved"] if u["reason"] == "parse_error"
    } & changed

    rows = []
    for path in sorted(candidates):
        olds = old_records.get(path, [])
        news = new_records.get(path, [])
        callers = olds[0]["referenced_by"] if olds else []
        files = {r["file"] for r in olds + news}
        if files & new_bad:
            rows.append(
                Row(
                    path,
                    "unknown",
                    "file does not parse at new rev; assume affected",
                    callers=callers,
                    error=bool(callers),
                )
            )
            continue
        if files & old_bad:
            rows.append(
                Row(path, "unknown", "file does not parse at old rev; assume affected")
            )
            continue
        if not olds:
            rows.append(Row(path, "added", "new symbol"))
        elif not news:
            if callers:
                rows.append(
                    Row(
                        path,
                        "deleted",
                        f"ERROR: {len(callers)} recorded caller(s)",
                        callers=callers,
                        error=True,
                    )
                )
            else:
                rows.append(Row(path, "deleted", "no callers recorded"))
        elif _sig_multiset(olds) != _sig_multiset(news):
            rows.append(
                Row(
                    path,
                    "signature",
                    f"callers affected ({len(callers)})",
                    callers=callers,
                )
            )
        elif _body_multiset(olds) != _body_multiset(news):
            rows.append(Row(path, "body", "owner only"))
        elif _decor_multiset(olds) != _decor_multiset(news):
            rows.append(
                Row(
                    path,
                    "decorators",
                    f"callers affected ({len(callers)})",
                    callers=callers,
                )
            )
        elif _position_multiset(olds) != _position_multiset(news):
            rows.append(Row(path, "moved", "no effect"))
    return AffectedReport(old_sha, new_sha, rows)


def render_report(report: AffectedReport, out=sys.stdout) -> None:
    if not report.rows:
        print("no symbols affected", file=out)
        return
    path_width = max(len(row.path) for row in report.rows) + 4
    cat_width = max(len(row.category) for row in report.rows) + 3
    for row in report.rows:
        print(f"{row.path:<{path_width}}{row.category:<{cat_width}}{row.detail}", file=out)
        for caller in row.callers:
            print(
                f"    caller: {caller['file']}:{caller['line']} ({caller['in_symbol']})",
                file=out,
            )
