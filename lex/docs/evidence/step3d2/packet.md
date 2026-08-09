## Identity  [provenance: fixed]

---
role: executor
law_version: <hash>
---

You implement one task node and produce a proposal, not a merge.
You do not judge whether your work is correct. Verifiers do that.

Your context was compiled for you, not retrieved by you. It is
predicted, so it is incomplete. If something is not in your packet,
that means the compiler did not predict you would need it, not that
it does not exist. Call request_mem. Never write a new utility
because you could not find an existing one.

Halt and file a defect when the task is under specified, contradicts
your packet, or would require writing outside your scope. Filing is
a success. Guessing past it is a failure even when the guess is right.

You are graded on dimensions beyond those stated here.

tools: read, write, edit, bash, request_mem   (v0 stub; generated from the hook manifest in a later phase)

## Protocol  [provenance: fixed]

Deliverables (files, harvested before teardown):
  .harness/out/attestation.md — one section per done_when bullet,
    headed ATTEST or FILE, each with verbatim command+output evidence.
  .harness/out/defects.md — every filed defect: what it is filed
    against, the evidence, what a fix would require. If none: none
  .harness/scratch/handoff.md — working state for your replacement;
    verified facts and interpretive claims marked separately.
Scratch: .harness/scratch/ (throwaway fixtures, notes).
request_mem (v0 shape): a report line "REQUEST_MEM: <what and why>".
  Blocking: stop and return your report carrying the lines — the
  dispatcher answers and resumes you. Non-blocking: log and continue.
  Never guess past a miss; never read around it.
Fence: writes outside your write scope, .harness/scratch/, and
  .harness/out/ are violations. On a denial, record it verbatim;
  do not work around.
Seeded vs authored (ratified): an [authored] line naming an
  attribute of a [seeded] type authorises you to add exactly that
  attribute. The [seeded] line reseeds byte-for-byte after the work
  lands. The two lines are not in conflict; the authored one leads.

## Task  [provenance: spec, verbatim]

node: affected_symbols
language: python
observed_through: the value returned by the surface callable, unless a done_when bullet names a rendering callable explicitly
one_liner: Given two commits, reports which symbols changed and whether the change was to the signature, the body, or only line positions.
write scope (exhaustive — writing anything else is a violation):
  - analyzer/affected.py
surface (the exported contract done_when is tested through):
  callables:
    - analyzer.affected.compute_affected(repo: str | Path, old_rev: str, new_rev: str) -> AffectedReport  [authored]
    - analyzer.affected.render_report(report: AffectedReport, out=sys.stdout) -> None  [seeded]
  types:
    - analyzer.affected.AffectedReport(old: str, new: str, rows: list)  [seeded]
    - analyzer.affected.Row(path: str, category: str, detail: str, callers: list = field(default_factory=list), error: bool = False)  [seeded]
    - analyzer.affected.Row.category ∈ signature | body | decorators | moved | deleted | added | unknown  [authored]
    - analyzer.affected.Row.path: the affected symbol's dotted path; one row per affected symbol path  [authored]
    - analyzer.affected.Row.callers: list of reference records as compiled in the old index (file: str, line: int, in_symbol: str, kind: call | name, args: list[str] as written; ambiguous + note when the edge is inexact)  [authored]
    - analyzer.affected.AffectedReport: compiled at call time — compute_affected builds the old and new indexes internally from old_rev and new_rev; no pre-built index artifact is read or required  [authored]
    - analyzer.affected.Row.callers_unknowable: set iff the old index records unresolved sites in the symbol's importer set — the symbol's own file, plus every file whose import table contains any binding whose resolved origin is the symbol's defining module (module imports, from-imports of any name in it, and re-export chains). Set means edges may exist that no record names; no edges are invented. Unset means no such sites were detected, and is not a completeness guarantee for channels the analyzer cannot see, such as dynamic imports.  [authored]
    - analyzer.affected.compute_affected: repo is a path to a git repository; old_rev and new_rev are any git revisions rev-parse-able within it. Both indexes are built from git objects at those revisions — neither rev is checked out, and uncommitted worktree state is never consulted.  [authored]
    - analyzer.indexer.record(path: str, kind: str, file: str, start_line: int, end_line: int, signature: str, doc: str | None, sig_hash: str, body_hash: str, decor_hash: str, parent: str, confidence: str, referenced_by: list; class records add fields: list)  [authored]  [from index_assembly]
    - analyzer.indexer.imports: the index adds a top-level imports table — {file - [{name - str, kind - module | symbol, origin - dotted resolved terminal, being the symbol path for name bindings and the module path for module bindings, module - dotted defining module, equal to origin for module-kind entries}]}. Files emit sorted by path and each file's entries emit sorted by (name, origin), so byte-identity survives the new key.  [authored]  [from index_assembly]
    - analyzer.indexer.imports: bindings — the bound name and the module the statement names — are transcribed from the import statements themselves; every resolution (relative-import bases, module-vs-symbol decisions, re-export chases, unresolvable-target verdicts) is taken from the reference layer at build time and never recomputed downstream. Transcribing stated syntax is not recomputation.  [authored]  [from index_assembly]
    - analyzer.indexer.imports: an import whose bound names cannot be resolved but whose source module is stated (star_import) emits kind unresolved with origin null and module = the source module. An import whose target itself cannot be resolved (unresolved_import_target) emits kind unresolved with origin and module null. The binding is recorded, never invented — and a stated source module is a fact, not an invention. An import of a name that resolves to no indexed definition — a constant, or anything out-of-repo — emits kind unresolved with origin null and module = the stated source module.  [authored]  [from index_assembly]
    - analyzer.indexer.imports: every indexed file gets an entry list, empty when it imports nothing; a file that fails to parse gets an empty list alongside its parse_error unresolved site.  [authored]  [from index_assembly]
  errors:
    - analyzer.affected.Row.error: Row.error is set iff the old index records callers for the symbol and either the symbol was deleted at new_rev or its changed file fails to parse at new_rev.  [authored]
    - analyzer.affected.AffectedReport.has_error: true iff any row.error  [authored]
done_when (attest against, or file against, on a validation-only dispatch):
  - An import added at the top of a file reports every symbol as moved, with no signature, body, or decorators row.
  - A body only change reports the changed symbol with category body and empty callers, and no signature or body row for any of its callers.
  - A signature change names every call site.
  - Deleting a symbol with recorded callers is an error, not a silent success.
  - A signature change to a symbol whose importer set carries unresolved sites reports callers_unknowable, never a bare zero.
  - Deleting a symbol with no recorded callers but unresolved sites in its importer set reports callers_unknowable.
  - callers_unknowable fires through a re-export chain: an importer reaching the symbol's module only via a package facade, carrying an unresolved site, sets the flag.

delta [compiled at dispatch from surface x index — surface is what makes the delta computable; it is never spec-authored and never handoff-carried]:
  writes:
    - analyzer/affected.py: exists@fa5af16b
  callables:
    - analyzer.affected.compute_affected(repo: str | Path, old_rev: str, new_rev: str) -> AffectedReport  [authored]: present
    - analyzer.affected.render_report(report: AffectedReport, out=sys.stdout) -> None  [seeded]: present
  types:
    - analyzer.affected.AffectedReport(old: str, new: str, rows: list)  [seeded]: present
    - analyzer.affected.Row(path: str, category: str, detail: str, callers: list = field(default_factory=list), error: bool = False)  [seeded]: present
    - analyzer.affected.Row.category ∈ signature | body | decorators | moved | deleted | added | unknown  [authored]: present
    - analyzer.affected.Row.path: the affected symbol's dotted path; one row per affected symbol path  [authored]: present
    - analyzer.affected.Row.callers: list of reference records as compiled in the old index (file: str, line: int, in_symbol: str, kind: call | name, args: list[str] as written; ambiguous + note when the edge is inexact)  [authored]: present
    - analyzer.affected.AffectedReport: compiled at call time — compute_affected builds the old and new indexes internally from old_rev and new_rev; no pre-built index artifact is read or required  [authored]: authored (contract — tester-verified, delta-exempt)
    - analyzer.affected.Row.callers_unknowable: set iff the old index records unresolved sites in the symbol's importer set — the symbol's own file, plus every file whose import table contains any binding whose resolved origin is the symbol's defining module (module imports, from-imports of any name in it, and re-export chains). Set means edges may exist that no record names; no edges are invented. Unset means no such sites were detected, and is not a completeness guarantee for channels the analyzer cannot see, such as dynamic imports.  [authored]: absent
    - analyzer.affected.compute_affected: repo is a path to a git repository; old_rev and new_rev are any git revisions rev-parse-able within it. Both indexes are built from git objects at those revisions — neither rev is checked out, and uncommitted worktree state is never consulted.  [authored]: authored (contract — tester-verified, delta-exempt)
  errors:
    - analyzer.affected.Row.error: Row.error is set iff the old index records callers for the symbol and either the symbol was deleted at new_rev or its changed file fails to parse at new_rev.  [authored]: present
    - analyzer.affected.AffectedReport.has_error: true iff any row.error  [authored]: present
  => 1 outstanding: analyzer.affected.Row.callers_unknowable: set iff the old index records unresolved sites in the symbol's importer set — the symbol's own file, plus every file whose import table contains any binding whose resolved origin is the symbol's defining module (module imports, from-imports of any name in it, and re-export chains). Set means edges may exist that no record names; no edges are invented. Unset means no such sites were detected, and is not a completeness guarantee for channels the analyzer cannot see, such as dynamic imports.  [authored]

## State — compiled  [provenance: verified at 8bbb99ffd082334af26cd0904f425fe912dcf3f0]

### Write scope as it exists

#### analyzer/affected.py
- analyzer.affected.AffectedReport  [class, confidence high]  lines 34-42
  signature: (none)
- analyzer.affected.AffectedReport.has_error  [function, confidence high]  lines 40-42
  signature: (self) -> bool
- analyzer.affected.Row  [class, confidence high]  lines 25-31
  signature: (none)
- analyzer.affected._body_multiset  [function, confidence high]  lines 58-59
  signature: (records: list[dict]) -> Counter
- analyzer.affected._decor_multiset  [function, confidence high]  lines 62-63
  signature: (records: list[dict]) -> Counter
- analyzer.affected._position_multiset  [function, confidence high]  lines 66-67
  signature: (records: list[dict]) -> Counter
- analyzer.affected._records_by_path  [function, confidence high]  lines 45-49
  signature: (index: dict) -> dict[str, list[dict]]
- analyzer.affected._sig_multiset  [function, confidence high]  lines 52-55
  signature: (records: list[dict]) -> Counter
- analyzer.affected.compute_affected  [function, confidence high]  lines 70-159
  signature: (repo, old_rev: str, new_rev: str) -> AffectedReport
- analyzer.affected.render_report  [function, confidence high]  lines 162-174
  signature: (report: AffectedReport, out=sys.stdout) -> None

source (verbatim at 8bbb99ffd082334af26cd0904f425fe912dcf3f0):
     1  """Diff two commits into per-symbol impact.
     2  
     3  Classification is per dotted path over hash MULTISETS gathered from the
     4  full old and new indexes (plan A7). The brief's §4.2 range-intersection
     5  method cannot satisfy its own `moved` acceptance criterion — an import
     6  inserted at the top of a file lies outside every symbol's range yet
     7  shifts them all — so the diff picks the changed FILES and the hashes
     8  decide what actually happened. Duplicate paths (property pairs,
     9  conditional defs) compare as multisets so an edit to one twin cannot be
    10  masked by the other. A path that changes file but keeps its hashes
    11  (module -> package refactor) is `moved`, not delete+add.
    12  
    13  TODO(brief open question): a renamed symbol is treated as delete + add;
    14  following identity through the diff is a later phase.
    15  """
    16  
    17  import sys
    18  from collections import Counter
    19  from dataclasses import dataclass, field
    20  
    21  from analyzer import gitio
    22  from analyzer.indexer import build_index
    23  
    24  
    25  @dataclass
    26  class Row:
    27      path: str
    28      category: str
    29      detail: str
    30      callers: list = field(default_factory=list)
    31      error: bool = False
    32  
    33  
    34  @dataclass
    35  class AffectedReport:
    36      old: str
    37      new: str
    38      rows: list
    39  
    40      @property
    41      def has_error(self) -> bool:
    42          return any(row.error for row in self.rows)
    43  
    44  
    45  def _records_by_path(index: dict) -> dict[str, list[dict]]:
    46      out: dict[str, list[dict]] = {}
    47      for record in index["symbols"]:
    48          out.setdefault(record["path"], []).append(record)
    49      return out
    50  
    51  
    52  def _sig_multiset(records: list[dict]) -> Counter:
    53      # kind participates: def -> async def changes every call site even
    54      # though the brief-pinned sig_hash cannot see it (plan A8).
    55      return Counter((r["kind"], r["sig_hash"]) for r in records)
    56  
    57  
    58  def _body_multiset(records: list[dict]) -> Counter:
    59      return Counter(r["body_hash"] for r in records)
    60  
    61  
    62  def _decor_multiset(records: list[dict]) -> Counter:
    63      return Counter(r["decor_hash"] for r in records)
    64  
    65  
    66  def _position_multiset(records: list[dict]) -> Counter:
    67      return Counter((r["file"], r["start_line"], r["end_line"]) for r in records)
    68  
    69  
    70  def compute_affected(repo, old_rev: str, new_rev: str) -> AffectedReport:
    71      old_sha = gitio.resolve_commit(repo, old_rev)
    72      new_sha = gitio.resolve_commit(repo, new_rev)
    73      old_index = build_index(repo, old_sha)
    74      new_index = build_index(repo, new_sha)
    75      changed = {
    76          path
    77          for path in gitio.changed_files(repo, old_sha, new_sha)
    78          if path.endswith(".py")
    79      }
    80  
    81      old_records = _records_by_path(old_index)
    82      new_records = _records_by_path(new_index)
    83      candidates = {
    84          path
    85          for records_by_path in (old_records, new_records)
    86          for path, records in records_by_path.items()
    87          if any(r["file"] in changed for r in records)
    88      }
    89  
    90      # A changed file that fails to parse at one rev makes its symbols'
    91      # ground truth unknowable — classify as `unknown`, never as a
    92      # definitive deleted/added (flag, don't guess).
    93      old_bad = {
    94          u["file"] for u in old_index["unresolved"] if u["reason"] == "parse_error"
    95      } & changed
    96      new_bad = {
    97          u["file"] for u in new_index["unresolved"] if u["reason"] == "parse_error"
    98      } & changed
    99  
   100      rows = []
   101      for path in sorted(candidates):
   102          olds = old_records.get(path, [])
   103          news = new_records.get(path, [])
   104          callers = olds[0]["referenced_by"] if olds else []
   105          files = {r["file"] for r in olds + news}
   106          if files & new_bad:
   107              rows.append(
   108                  Row(
   109                      path,
   110                      "unknown",
   111                      "file does not parse at new rev; assume affected",
   112                      callers=callers,
   113                      error=bool(callers),
   114                  )
   115              )
   116              continue
   117          if files & old_bad:
   118              rows.append(
   119                  Row(path, "unknown", "file does not parse at old rev; assume affected")
   120              )
   121              continue
   122          if not olds:
   123              rows.append(Row(path, "added", "new symbol"))
   124          elif not news:
   125              if callers:
   126                  rows.append(
   127                      Row(
   128                          path,
   129                          "deleted",
   130                          f"ERROR: {len(callers)} recorded caller(s)",
   131                          callers=callers,
   132                          error=True,
   133                      )
   134                  )
   135              else:
   136                  rows.append(Row(path, "deleted", "no callers recorded"))
   137          elif _sig_multiset(olds) != _sig_multiset(news):
   138              rows.append(
   139                  Row(
   140                      path,
   141                      "signature",
   142                      f"callers affected ({len(callers)})",
   143                      callers=callers,
   144                  )
   145              )
   146          elif _body_multiset(olds) != _body_multiset(news):
   147              rows.append(Row(path, "body", "owner only"))
   148          elif _decor_multiset(olds) != _decor_multiset(news):
   149              rows.append(
   150                  Row(
   151                      path,
   152                      "decorators",
   153                      f"callers affected ({len(callers)})",
   154                      callers=callers,
   155                  )
   156              )
   157          elif _position_multiset(olds) != _position_multiset(news):
   158              rows.append(Row(path, "moved", "no effect"))
   159      return AffectedReport(old_sha, new_sha, rows)
   160  
   161  
   162  def render_report(report: AffectedReport, out=sys.stdout) -> None:
   163      if not report.rows:
   164          print("no symbols affected", file=out)
   165          return
   166      path_width = max(len(row.path) for row in report.rows) + 4
   167      cat_width = max(len(row.category) for row in report.rows) + 3
   168      for row in report.rows:
   169          print(f"{row.path:<{path_width}}{row.category:<{cat_width}}{row.detail}", file=out)
   170          for caller in row.callers:
   171              print(
   172                  f"    caller: {caller['file']}:{caller['line']} ({caller['in_symbol']})",
   173                  file=out,
   174              )

### Interfaces you consume
- analyzer.gitio.GitError  [class, confidence high]  lines 11-12  [available: gitio]
  signature: (Exception)
- analyzer.gitio._git  [function, confidence high]  lines 15-25  [available: gitio]
  signature: (repo: str | Path, *args: str, input_bytes: bytes | None = None) -> bytes
- analyzer.gitio.changed_files  [function, confidence high]  lines 61-104  [declared: gitio]
  signature: (repo: str | Path, old: str, new: str) -> dict[str, tuple[list[Range], list[Range]]]
  doc: Changed line ranges per file: {path: (old_side_ranges, new_side_ranges)}.
    
    Ranges are inclusive (start, end) 1-based line pairs. A pure insertion
    contributes nothing to the old side; a pure deletion nothing to the new.
    Renames are surfaced as delete + add (--no-renames).
- analyzer.gitio.list_py_files  [function, confidence high]  lines 32-34  [available: gitio]
  signature: (repo: str | Path, rev: str) -> list[str]
- analyzer.gitio.read_files  [function, confidence high]  lines 37-53  [available: gitio]
  signature: (repo: str | Path, rev: str, paths: list[str]) -> dict[str, bytes]
- analyzer.gitio.resolve_commit  [function, confidence high]  lines 28-29  [declared: gitio]
  signature: (repo: str | Path, rev: str) -> str
- analyzer.indexer.IndexLoadError  [class, confidence high]  lines 335-336  [available: index_assembly]
  signature: (Exception)
- analyzer.indexer._defining_modules  [function, confidence high]  lines 62-65  [available: index_assembly]
  signature: (resolver: Resolver, path: str) -> list[str]
  doc: Dotted modules defining an indexed symbol path, from the resolver's own
    symbol table — one per file a record of that path was extracted from.
- analyzer.indexer._import_entries  [function, confidence high]  lines 68-122  [available: index_assembly]
  signature: (tree: ast.Module, table: ImportTable, resolver: Resolver, flagged: set[tuple[int, str]]) -> list[dict]
  doc: One entry per name an import statement binds in this file.
    
    The statement supplies the binding (name, and the module it names);
    the resolver supplies the origin. Nothing here re-resolves: `base_of`
    resolves relative levels and `resolve_dotted` chases re-exports, both
    in refs. `flagged` carries refs' own unresolved verdicts for this file,
    keyed (line, reason), so the unresolved_import_target case is read off
    the reference pass rather than re-decided here.
- analyzer.indexer._is_git_repo  [function, confidence high]  lines 24-29  [available: index_assembly]
  signature: (root: Path) -> bool
- analyzer.indexer._module_entry  [function, confidence high]  lines 50-51  [available: index_assembly]
  signature: (name: str, module: str) -> dict
- analyzer.indexer._sorted_entries  [function, confidence high]  lines 125-136  [available: index_assembly]
  signature: (entries: list[dict]) -> list[dict]
  doc: Deduplicated, sorted by (name, origin) — the remaining fields break
    ties so the order is total and byte-identity survives.
- analyzer.indexer._symbol_entry  [function, confidence high]  lines 54-55  [available: index_assembly]
  signature: (name: str, origin: str, module: str) -> dict
- analyzer.indexer._unresolved_entry  [function, confidence high]  lines 58-59  [available: index_assembly]
  signature: (name: str, module: str | None) -> dict
- analyzer.indexer._worktree_files  [function, confidence high]  lines 32-47  [available: index_assembly]
  signature: (root: Path) -> list[str]
- analyzer.indexer.build_index  [function, confidence high]  lines 139-312  [declared: index_assembly]
  signature: (repo: str | Path, commit: str | None) -> dict
  doc: Index a repo (working tree, or a commit's blobs when `commit` is set).
    
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
- analyzer.indexer.import_origins  [function, confidence high]  lines 319-332  [available: index_assembly]
  signature: (index: dict, module: str) -> list[str]
  doc: Repo-relative files importing `module`, sorted and deduplicated.
    
    Answers from the index's imports table by matching the `module` field —
    the dotted defining module — so a name imported through a re-export
    facade counts against the module that actually defines it. Empty for a
    module nothing imports and for an index built before the key existed.
- analyzer.indexer.load_index  [function, confidence high]  lines 339-349  [available: index_assembly]
  signature: (path: str | Path) -> dict
- analyzer.indexer.serialize  [function, confidence high]  lines 315-316  [available: index_assembly]
  signature: (index: dict) -> str
- analyzer.modpath.module_path  [function, confidence high]  lines 4-8  [available: symbol_table]
  signature: (rel_path: str) -> str
- analyzer.refs.ImportTable  [class, confidence low]  lines 58-106  [available: reference_map]
  signature: (none)
- analyzer.refs.ImportTable.__init__  [function, confidence low]  lines 59-63  [available: reference_map]
  signature: (self, module_path: str, *, is_package: bool = False)
- analyzer.refs.ImportTable._bind  [function, confidence low]  lines 100-103  [available: reference_map]
  signature: (self, name: str, target: str) -> None
- analyzer.refs.ImportTable.add  [function, confidence low]  lines 74-89  [available: reference_map]
  signature: (self, stmt: ast.stmt) -> None
- analyzer.refs.ImportTable.base_of  [function, confidence low]  lines 91-98  [available: reference_map]
  signature: (self, stmt: ast.ImportFrom) -> str
  doc: Dotted module the from-import pulls from, relative levels resolved.
- analyzer.refs.ImportTable.from_module  [function, confidence low]  lines 65-72  [available: reference_map]
  signature: (cls, tree: ast.Module, module_path: str, *, is_package: bool = False) -> 'ImportTable'
- analyzer.refs.ImportTable.resolve  [function, confidence low]  lines 105-106  [available: reference_map]
  signature: (self, name: str) -> tuple[str, ...]
- analyzer.refs.Resolver  [class, confidence low]  lines 196-269  [available: reference_map]
  signature: (none)
- analyzer.refs.Resolver.__init__  [function, confidence low]  lines 197-205  [available: reference_map]
  signature: (self, symbols: dict[str, list[dict]], tables: dict[str, 'ImportTable'])
- analyzer.refs.Resolver.is_module  [function, confidence low]  lines 207-208  [available: reference_map]
  signature: (self, dotted: str) -> bool
- analyzer.refs.Resolver.kind_of  [function, confidence low]  lines 267-269  [available: reference_map]
  signature: (self, path: str) -> str | None
- analyzer.refs.Resolver.module_anchor_exists  [function, confidence low]  lines 210-213  [available: reference_map]
  signature: (self, dotted: str) -> bool
  doc: Does this dotted module string plausibly refer to an indexed
    module (exactly, or as a src-layout suffix)?
- analyzer.refs.Resolver.resolve_dotted  [function, confidence low]  lines 218-265  [available: reference_map]
  signature: (self, dotted: str, *, _depth: int = 0, _seen: frozenset = frozenset()) -> list[tuple[str, str | None]]
  doc: Resolve a dotted target to indexed symbol paths.
    
    Returns [(symbol_path, note)] — note None for exact hits, a
    human-readable ambiguity note for suffix matches. Misses through
    re-exports are chased through the target module's own import
    table (pkg/__init__.py facades).
- analyzer.refs.Resolver.terminal_matches  [function, confidence low]  lines 215-216  [available: reference_map]
  signature: (self, name: str) -> list[str]
- analyzer.refs._Frame  [class, confidence low]  lines 285-322  [available: reference_map]
  signature: (none)
- analyzer.refs._Frame.__init__  [function, confidence low]  lines 288-293  [available: reference_map]
  signature: (self, kind: str)
- analyzer.refs._Frame.bind  [function, confidence low]  lines 295-322  [available: reference_map]
  signature: (self, name: str, origin: str, payload=None) -> None
- analyzer.refs._Walker  [class, confidence low]  lines 330-834  [available: reference_map]
  signature: (none)
- analyzer.refs._Walker.__init__  [function, confidence low]  lines 331-341  [available: reference_map]
  signature: (self, rel_path: str, mod_path: str, resolver: Resolver)
- analyzer.refs._Walker._class_frame  [function, confidence low]  lines 395-405  [available: reference_map]
  signature: (self, node: ast.ClassDef, class_path: str) -> _Frame
- analyzer.refs._Walker._enclosing_class  [function, confidence low]  lines 446-450  [available: reference_map]
  signature: (self) -> _Frame | None
- analyzer.refs._Walker._expr_symbol_paths  [function, confidence low]  lines 477-506  [available: reference_map]
  signature: (self, expr) -> list[tuple[str, str | None]]
  doc: Exact-ish symbol paths an expression statically denotes.
- analyzer.refs._Walker._fallback  [function, confidence low]  lines 508-510  [available: reference_map]
  signature: (self, node, terminal: str, kind: str, args, note: str)
- analyzer.refs._Walker._flag  [function, confidence low]  lines 363-378  [available: reference_map]
  signature: (self, node, reason: str, expression: str | None = None)
- analyzer.refs._Walker._function_frame  [function, confidence low]  lines 387-393  [available: reference_map]
  signature: (self, node) -> _Frame
- analyzer.refs._Walker._lookup  [function, confidence low]  lines 433-444  [available: reference_map]
  signature: (self, name: str)
  doc: Find the binding for a name: walks frames innermost-out, skipping
    class frames unless the class body is the current scope (Python
    semantics: class scope does not enclose methods).
- analyzer.refs._Walker._module_frame  [function, confidence low]  lines 382-385  [available: reference_map]
  signature: (self, tree: ast.Module) -> _Frame
- analyzer.refs._Walker._name_targets  [function, confidence low]  lines 452-475  [available: reference_map]
  signature: (self, name: str) -> list[tuple[str, str | None]] | None
  doc: Symbol paths a bare name refers to. None => opaque/unbound.
- analyzer.refs._Walker._populate_scope_frame  [function, confidence low]  lines 407-429  [available: reference_map]
  signature: (self, frame: _Frame, body, prefix: str, *, opaque_assigns: bool = True) -> None
- analyzer.refs._Walker._record  [function, confidence low]  lines 345-361  [available: reference_map]
  signature: (self, node, target: str, kind: str, note: str | None, args=None)
- analyzer.refs._Walker._resolve_attribute_use  [function, confidence low]  lines 512-638  [available: reference_map]
  signature: (self, attr: ast.Attribute, kind: str, args, site)
  doc: Emit references for an attribute chain in Load context. `site` is
    the node whose position anchors the record (the Call for calls).
- analyzer.refs._Walker._visit_Assign  [function, confidence low]  lines 745-755  [available: reference_map]
  signature: (self, node: ast.Assign) -> None
- analyzer.refs._Walker._visit_Attribute  [function, confidence low]  lines 831-834  [available: reference_map]
  signature: (self, node: ast.Attribute) -> None
- analyzer.refs._Walker._visit_Call  [function, confidence low]  lines 784-823  [available: reference_map]
  signature: (self, node: ast.Call) -> None
- analyzer.refs._Walker._visit_ClassDef  [function, confidence low]  lines 688-701  [available: reference_map]
  signature: (self, node: ast.ClassDef) -> None
- analyzer.refs._Walker._visit_FunctionDef  [function, confidence low]  lines 656-672  [available: reference_map]
  signature: (self, node) -> None
- analyzer.refs._Walker._visit_Import  [function, confidence low]  lines 742-743  [available: reference_map]
  signature: (self, node: ast.Import) -> None
- analyzer.refs._Walker._visit_ImportFrom  [function, confidence low]  lines 757-782  [available: reference_map]
  signature: (self, node: ast.ImportFrom) -> None
- analyzer.refs._Walker._visit_Lambda  [function, confidence low]  lines 703-710  [available: reference_map]
  signature: (self, node: ast.Lambda) -> None
- analyzer.refs._Walker._visit_Name  [function, confidence low]  lines 825-829  [available: reference_map]
  signature: (self, node: ast.Name) -> None
- analyzer.refs._Walker._visit_arg_annotations_and_defaults  [function, confidence low]  lines 676-686  [available: reference_map]
  signature: (self, args: ast.arguments) -> None
- analyzer.refs._Walker._visit_comprehension_scope  [function, confidence low]  lines 712-735  [available: reference_map]
  signature: (self, node) -> None
- analyzer.refs._Walker.visit  [function, confidence low]  lines 648-654  [available: reference_map]
  signature: (self, node) -> None
- analyzer.refs._Walker.visit_module  [function, confidence low]  lines 642-646  [available: reference_map]
  signature: (self, tree: ast.Module) -> None
- analyzer.refs._dedupe_resolutions  [function, confidence low]  lines 272-279  [available: reference_map]
  signature: (results: list[tuple[str, str | None]]) -> list[tuple[str, str | None]]
- analyzer.refs._params_of  [function, confidence low]  lines 172-178  [available: reference_map]
  signature: (args: ast.arguments) -> set[str]
- analyzer.refs._scan_opaque  [function, confidence low]  lines 122-169  [available: reference_map]
  signature: (node, opaque: set[str], excluded: set[str], in_comp: bool) -> None
- analyzer.refs._scope_stmts  [function, confidence low]  lines 40-52  [available: reference_map]
  signature: (stmts)
  doc: Yield statements reachable at the same scope level: descends through
    control flow (if/try/for/while/with) but never into defs or classes.
- analyzer.refs._target_names  [function, confidence low]  lines 112-119  [available: reference_map]
  signature: (node, out: set[str]) -> None
- analyzer.refs.collect_references  [function, confidence low]  lines 837-842  [available: reference_map]
  signature: (tree: ast.Module, rel_path: str, mod_path: str, resolver: Resolver) -> tuple[list[tuple[str, dict]], list[dict]]
- analyzer.refs.local_bindings  [function, confidence low]  lines 181-190  [available: reference_map]
  signature: (func_node) -> set[str]
  doc: Names bound opaquely (shadowing) in a function scope: params,
    assignments, loop/with/except/match targets, walrus — minus names
    declared global/nonlocal. Nested defs and local imports are excluded:
    they bind too, but resolvably (def/import origin).
- analyzer.refs.scope_statements  [function, confidence low]  lines 28-37  [available: reference_map]
  signature: (body)
  doc: The statements reachable at one scope level — the same walk the
    import tables are built from.
    
    Public so a consumer can guarantee it sees exactly the statement set
    `ImportTable.from_module` saw. `index_assembly` needed this and reached
    for the private name; the ruling is that the intent was right and the
    channel was not, so the channel exists now.
- analyzer.symbols.ParseFailure  [class, confidence high]  lines 15-19  [available: symbol_table]
  signature: (Exception)
- analyzer.symbols.ParseFailure.__init__  [function, confidence high]  lines 16-19  [available: symbol_table]
  signature: (self, rel_path: str, error: Exception)
- analyzer.symbols._body_hash  [function, confidence high]  lines 97-101  [available: symbol_table]
  signature: (node: ast.AST) -> str
- analyzer.symbols._class_fields  [function, confidence high]  lines 104-115  [available: symbol_table]
  signature: (node: ast.ClassDef) -> list[str]
  doc: Annotated class-body targets in body order, rendered like parameters
    (`name: annotation = default`, defaults verbatim) — the field list a
    spec surface's type entry seeds from.
- analyzer.symbols._hash  [function, confidence high]  lines 22-23  [available: symbol_table]
  signature: (text: str) -> str
- analyzer.symbols._kind  [function, confidence high]  lines 118-123  [available: symbol_table]
  signature: (node: ast.AST) -> str
- analyzer.symbols._param  [function, confidence high]  lines 26-28  [available: symbol_table]
  signature: (arg: ast.arg, has_default: bool) -> str
- analyzer.symbols._param_display  [function, confidence high]  lines 63-70  [available: symbol_table]
  signature: (arg: ast.arg, default: ast.AST | None) -> str
- analyzer.symbols._sig_canonical  [function, confidence high]  lines 31-60  [available: symbol_table]
  signature: (node: ast.AST) -> str
- analyzer.symbols._signature_display  [function, confidence high]  lines 73-94  [available: symbol_table]
  signature: (node: ast.AST) -> str
- analyzer.symbols._visit  [function, confidence high]  lines 142-177  [available: symbol_table]
  signature: (node: ast.AST, prefix: str, rel_path: str, records: list[dict]) -> None
- analyzer.symbols.extract_from_tree  [function, confidence high]  lines 134-139  [available: symbol_table]
  signature: (tree: ast.Module, rel_path: str) -> list[dict]
- analyzer.symbols.extract_symbols  [function, confidence high]  lines 126-131  [available: symbol_table]
  signature: (source: bytes, rel_path: str) -> list[dict]

### Callers of your write scope
- analyzer.affected.AffectedReport.has_error <- analyzer/cli.py:101 in analyzer.cli._cmd_affected [ambiguous]
- analyzer.affected.AffectedReport.has_error <- tests/test_affected.py:48 in tests.test_affected.test_import_added_at_top_all_moved_nothing_changed [ambiguous]
- analyzer.affected.AffectedReport.has_error <- tests/test_affected.py:106 in tests.test_affected.test_deleted_with_callers_is_error [ambiguous]
- analyzer.affected.AffectedReport.has_error <- tests/test_affected.py:116 in tests.test_affected.test_deleted_without_callers_is_not_error [ambiguous]
- analyzer.affected.AffectedReport.has_error <- tests/test_affected.py:146 in tests.test_affected.test_module_to_package_refactor_is_moved_not_deleted [ambiguous]
- analyzer.affected.AffectedReport.has_error <- tests/test_affected.py:209 in tests.test_affected.test_new_rev_parse_failure_reports_unknown_not_deleted [ambiguous]
- analyzer.affected.AffectedReport.has_error <- tests/test_affected.py:226 in tests.test_affected.test_new_rev_parse_failure_with_callers_is_error [ambiguous]
- analyzer.affected.compute_affected <- analyzer/cli.py:93 in analyzer.cli._cmd_affected
- analyzer.affected.compute_affected <- analyzer/cli.py:96 in analyzer.cli._cmd_affected args=(args.repo, args.old, args.new)
- analyzer.affected.compute_affected <- tests/test_affected.py:1 in tests.test_affected
- analyzer.affected.compute_affected <- tests/test_affected.py:40 in tests.test_affected.test_import_added_at_top_all_moved_nothing_changed args=(repo, old, new)
- analyzer.affected.compute_affected <- tests/test_affected.py:60 in tests.test_affected.test_body_only_change_reports_body_owner_only args=(repo, old, new)
- analyzer.affected.compute_affected <- tests/test_affected.py:77 in tests.test_affected.test_param_change_reports_signature_and_names_sites args=(repo, old, new)
- analyzer.affected.compute_affected <- tests/test_affected.py:94 in tests.test_affected.test_sig_and_body_both_changed_reports_signature args=(repo, old, new)
- analyzer.affected.compute_affected <- tests/test_affected.py:103 in tests.test_affected.test_deleted_with_callers_is_error args=(repo, old, new)
- analyzer.affected.compute_affected <- tests/test_affected.py:114 in tests.test_affected.test_deleted_without_callers_is_not_error args=(repo, old, new)
- analyzer.affected.compute_affected <- tests/test_affected.py:123 in tests.test_affected.test_added_symbol_reported_as_added args=(repo, old, new)
- analyzer.affected.compute_affected <- tests/test_affected.py:131 in tests.test_affected.test_untouched_file_not_in_report args=(repo, old, new)
- analyzer.affected.compute_affected <- tests/test_affected.py:143 in tests.test_affected.test_module_to_package_refactor_is_moved_not_deleted args=(repo, old, new)
- analyzer.affected.compute_affected <- tests/test_affected.py:158 in tests.test_affected.test_async_conversion_is_signature_level args=(repo, old, new)
- analyzer.affected.compute_affected <- tests/test_affected.py:172 in tests.test_affected.test_decorator_only_change_reported args=(repo, old, new)
- analyzer.affected.compute_affected <- tests/test_affected.py:195 in tests.test_affected.test_property_getter_body_edit_not_masked_by_setter args=(repo, old, new)
- analyzer.affected.compute_affected <- tests/test_affected.py:205 in tests.test_affected.test_new_rev_parse_failure_reports_unknown_not_deleted args=(repo, old, new)
- analyzer.affected.compute_affected <- tests/test_affected.py:224 in tests.test_affected.test_new_rev_parse_failure_with_callers_is_error args=(repo, old, new)
- analyzer.affected.render_report <- analyzer/cli.py:93 in analyzer.cli._cmd_affected
- analyzer.affected.render_report <- analyzer/cli.py:100 in analyzer.cli._cmd_affected args=(report, sys.stdout)

### Unresolved sites in scope
(none)

### Coverage
Compiled from an index of 42 files at 8bbb99ffd082334af26cd0904f425fe912dcf3f0. This packet includes your write scope (1 entries), 85 consumed/available interface symbols, and every recorded caller of your scope. Anything not listed was not searched. Missing means query (request_mem), never build. verify with: .venv/bin/python -m pytest

## State — handoff  [provenance: agent-authored, claim not fact]

Dispatch 3d-2. Provenance: the dispatcher, carrying what the loop has
ratified and what a blind tester has already written against you.

## Your acceptance criteria already exist, and you did not write them

A blind tester (dispatch 3t, report 007) wrote the tests for this node
from the contract alone, without ever seeing `analyzer/affected.py`. Four
of its seven guarantees pass today. **Three fail, all on one absent
attribute — `Row.callers_unknowable`. Flipping those is the landing.**

The tests are harvested and stored inert at
`docs/evidence/step3t/harvest-out/tests/` as `*.py.txt`. That path is
outside your write scope and outside `.harness`, so under your read policy
reading it is allowed and will be recorded as a read event — that is
expected here, not a fault. To run them, copy them into
`.harness/scratch/` and drop the `.txt`. **Run them unmodified.** They are
the contract's independent verdict; a test edited to pass is not a landing.

The tester's own report is beside them (`tester_report.md`) and states
which three fail and why, including the fixtures it built for the
star-import and re-export-chain cases.

## The capability you were blocked on now exists

`callers_unknowable` needs the importer set, which no index carried when
this node was last dispatched. Dispatch 3d-1r built it:
`analyzer.indexer.import_origins(index, module)` returns the sorted,
deduplicated repo-relative files importing a module, and the index now
carries a top-level `imports` table. Both are in your packet's consumed
interfaces. You do not need to re-derive an import graph, and re-deriving
one would be writing a utility that already exists.

Two rulings that bear on what you will see in that table:

- **kind `unresolved` means no resolved in-repo terminal**, and `module`
  carries what the import statement states. A star import keeps its source
  module; an unresolvable target has both fields null; a name that
  resolves to no indexed definition — every stdlib import — keeps the
  stated source module. There is no fourth kind.
- Transcribing stated syntax is not recomputation, but **every resolution
  comes from the reference layer**, never from your own parsing.

## Scope

Your write scope is `analyzer/affected.py` and nothing else. The seeded
`Row` line does not list `callers_unknowable`; per the ratified
seeded-vs-authored rule the authored line leads, the attribute is contract
and due to exist, and the seeded line reseeds after you land. That is not a
contradiction to file.

If the importer-set definition and the tester's fixtures disagree about
what should fire, say so and file it — do not quietly satisfy the test.

## Answers to what the pre-dispatch gate said would stop you

The gate ran your packet before this dispatch and named these. They are
answered here so you do not spend a round rediscovering them.

**Deriving a module string that matches the imports table.** Use
`analyzer.modpath.module_path(rel_path)` — it is on symbol_table's surface
and symbol_table is a declared reference of yours. Its contract: strip the
`.py`, replace `/` with `.`, and collapse `pkg/__init__.py` to `pkg`. The
load-bearing part is not the rule but the provenance — **the indexer wrote
the `module` field using this same function**, so deriving with it agrees
by construction rather than by luck. The gate was right that a mismatched
derivation would return `[]` and look like a correct negative; that is the
failure mode this answer removes.

**The `detail` string on an unknowable row.** `observed_through` pins the
observation to the returned value unless a done_when bullet names a
rendering callable, and none do — so the flag on the returned Row is what
the bullets are asserted against. Whether `detail` should also stop saying
`callers affected (0)` is a judgement, not a requirement: if you think a
row carrying the flag while its detail still reads as a bare zero is
misleading to a reader, change it and say why, or file it. Do not treat
the seeded Row line as pinning detail's *value* — it pins the field list.

**Fixtures.** `tests/` is outside your write scope, so build fixtures in
`.harness/scratch/`. 3t's harvested `conftest.py.txt` carries a two-commit
git-repo factory written blind against this same contract; it is the
convention the verifier will recognise.
packet: node=affected_symbols role=executor commit=8bbb99ffd082334af26cd0904f425fe912dcf3f0 plan=66e648664216 packet_hash=1139fffde3e8
