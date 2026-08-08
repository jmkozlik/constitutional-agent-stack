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
from analyzer.indexer import build_index, import_origins
from analyzer.modpath import module_path


@dataclass
class Row:
    path: str
    category: str
    detail: str
    callers: list = field(default_factory=list)
    error: bool = False
    callers_unknowable: bool = False


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


# A caller list is only as complete as the files it was gathered from. Where
# a file in the symbol's importer set holds a site the reference layer could
# not decide, an edge may exist that no record names — so the row says so
# rather than presenting its count as a total.
_UNKNOWABLE_NOTE = "importer set carries unresolved sites"


def _importer_files(index: dict, records: list[dict], origins: dict) -> set[str]:
    """The contract's importer set for a symbol with these old records.

    The symbol's own file(s), plus every file whose import table binds
    anything whose resolved origin is the symbol's defining module.
    `import_origins` answers the second half from the index's own imports
    table by matching the `module` field, so an importer reaching the
    symbol only through a package facade still counts against the module
    that actually defines it — which is what makes a re-export chain
    visible here without walking one. The module string comes from
    `module_path`, the same function the indexer wrote `module` with, so
    the two agree by construction rather than by coincidence.

    `origins` memoises the per-module answer across rows; a symbol with no
    old records has no own file and no defining module, so its set is empty.
    """
    files = {r["file"] for r in records}
    for module in {module_path(f) for f in files}:
        if module not in origins:
            origins[module] = import_origins(index, module)
        files.update(origins[module])
    return files


def _note(detail: str, unknowable: bool) -> str:
    """Append the unknowability note to a detail that claims something about
    callers. `body`/`moved`/`added` details speak to effect, not to the
    caller list, so they are left alone and the flag carries the fact."""
    return f"{detail}; {_UNKNOWABLE_NOTE}" if unknowable else detail


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

    # Unknowability is read off the OLD index: it is the index the caller
    # lists were gathered from, so it is the one whose blind spots those
    # lists inherit.
    old_unresolved = {u["file"] for u in old_index["unresolved"]}
    origins: dict[str, list[str]] = {}

    rows = []
    for path in sorted(candidates):
        olds = old_records.get(path, [])
        news = new_records.get(path, [])
        callers = olds[0]["referenced_by"] if olds else []
        unknowable = bool(
            _importer_files(old_index, olds, origins) & old_unresolved
        )
        files = {r["file"] for r in olds + news}
        if files & new_bad:
            rows.append(
                Row(
                    path,
                    "unknown",
                    "file does not parse at new rev; assume affected",
                    callers=callers,
                    error=bool(callers),
                    callers_unknowable=unknowable,
                )
            )
            continue
        if files & old_bad:
            rows.append(
                Row(
                    path,
                    "unknown",
                    "file does not parse at old rev; assume affected",
                    callers_unknowable=unknowable,
                )
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
                        _note(f"ERROR: {len(callers)} recorded caller(s)", unknowable),
                        callers=callers,
                        error=True,
                        callers_unknowable=unknowable,
                    )
                )
            else:
                # "no callers recorded" alone reads as a clearance. It is
                # only one when nothing in the importer set was undecidable.
                rows.append(
                    Row(
                        path,
                        "deleted",
                        _note("no callers recorded", unknowable),
                        callers_unknowable=unknowable,
                    )
                )
        elif _sig_multiset(olds) != _sig_multiset(news):
            rows.append(
                Row(
                    path,
                    "signature",
                    _note(f"callers affected ({len(callers)})", unknowable),
                    callers=callers,
                    callers_unknowable=unknowable,
                )
            )
        elif _body_multiset(olds) != _body_multiset(news):
            rows.append(
                Row(path, "body", "owner only", callers_unknowable=unknowable)
            )
        elif _decor_multiset(olds) != _decor_multiset(news):
            rows.append(
                Row(
                    path,
                    "decorators",
                    _note(f"callers affected ({len(callers)})", unknowable),
                    callers=callers,
                    callers_unknowable=unknowable,
                )
            )
        elif _position_multiset(olds) != _position_multiset(news):
            rows.append(
                Row(path, "moved", "no effect", callers_unknowable=unknowable)
            )
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
        if row.callers_unknowable:
            # Printed for every flagged row, not just the ones whose detail
            # carries the note: a reader acting on this output should never
            # have to infer the gap from a count.
            print(f"    callers unknowable: {_UNKNOWABLE_NOTE}", file=out)
