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

## Task  [provenance: spec, verbatim]

node: affected_symbols
one_liner: Given two commits, reports which symbols changed and whether the change was to the signature, the body, or only line positions.
write scope (exhaustive — writing anything else is a violation):
  - analyzer/affected.py
  - analyzer/gitio.py
surface (the exported contract done_when is tested through):
  - analyzer.affected.compute_affected(repo, old_rev: str, new_rev: str) -> AffectedReport
  - analyzer.affected.render_report(report: AffectedReport, out=sys.stdout) -> None
  - analyzer.gitio.changed_files(repo: str | Path, old: str, new: str) -> dict[str, tuple[list[Range], list[Range]]]
  - analyzer.gitio.list_py_files(repo: str | Path, rev: str) -> list[str]
  - analyzer.gitio.read_files(repo: str | Path, rev: str, paths: list[str]) -> dict[str, bytes]
  - analyzer.gitio.resolve_commit(repo: str | Path, rev: str) -> str
  - analyzer.gitio.GitError(Exception)

delta [compiled at dispatch from surface x index — surface is what makes the delta computable; it is never spec-authored and never handoff-carried]:
  writes:
    - analyzer/affected.py: exists@fa5af16b
    - analyzer/gitio.py: exists@d9a191d5
  surface:
    - analyzer.affected.compute_affected(repo, old_rev: str, new_rev: str) -> AffectedReport: present
    - analyzer.affected.render_report(report: AffectedReport, out=sys.stdout) -> None: present
    - analyzer.gitio.changed_files(repo: str | Path, old: str, new: str) -> dict[str, tuple[list[Range], list[Range]]]: present
    - analyzer.gitio.list_py_files(repo: str | Path, rev: str) -> list[str]: present
    - analyzer.gitio.read_files(repo: str | Path, rev: str, paths: list[str]) -> dict[str, bytes]: present
    - analyzer.gitio.resolve_commit(repo: str | Path, rev: str) -> str: present
    - analyzer.gitio.GitError(Exception): present
  => empty delta — validation-only dispatch

## State — compiled  [provenance: verified at baad6d55691a42e3e0208372c1e408ba114b33d1]

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

source (verbatim at baad6d55691a42e3e0208372c1e408ba114b33d1):
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

#### analyzer/gitio.py
- analyzer.gitio.GitError  [class, confidence high]  lines 11-12
  signature: (Exception)
- analyzer.gitio._git  [function, confidence high]  lines 15-25
  signature: (repo: str | Path, *args: str, input_bytes: bytes | None = None) -> bytes
- analyzer.gitio.changed_files  [function, confidence high]  lines 61-104
  signature: (repo: str | Path, old: str, new: str) -> dict[str, tuple[list[Range], list[Range]]]
  doc: Changed line ranges per file: {path: (old_side_ranges, new_side_ranges)}.
    
    Ranges are inclusive (start, end) 1-based line pairs. A pure insertion
    contributes nothing to the old side; a pure deletion nothing to the new.
    Renames are surfaced as delete + add (--no-renames).
- analyzer.gitio.list_py_files  [function, confidence high]  lines 32-34
  signature: (repo: str | Path, rev: str) -> list[str]
- analyzer.gitio.read_files  [function, confidence high]  lines 37-53
  signature: (repo: str | Path, rev: str, paths: list[str]) -> dict[str, bytes]
- analyzer.gitio.resolve_commit  [function, confidence high]  lines 28-29
  signature: (repo: str | Path, rev: str) -> str

source (verbatim at baad6d55691a42e3e0208372c1e408ba114b33d1):
     1  """Git plumbing: file listings and blob contents at a rev, diff ranges.
     2  
     3  Everything reads objects directly — no checkouts, no temp worktrees.
     4  """
     5  
     6  import re
     7  import subprocess
     8  from pathlib import Path
     9  
    10  
    11  class GitError(Exception):
    12      pass
    13  
    14  
    15  def _git(repo: str | Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    16      result = subprocess.run(
    17          ["git", "-C", str(repo), "-c", "core.quotePath=false", *args],
    18          capture_output=True,
    19          input=input_bytes,
    20      )
    21      if result.returncode != 0:
    22          raise GitError(
    23              f"git {' '.join(args)} failed: {result.stderr.decode(errors='replace').strip()}"
    24          )
    25      return result.stdout
    26  
    27  
    28  def resolve_commit(repo: str | Path, rev: str) -> str:
    29      return _git(repo, "rev-parse", "--verify", f"{rev}^{{commit}}").decode().strip()
    30  
    31  
    32  def list_py_files(repo: str | Path, rev: str) -> list[str]:
    33      out = _git(repo, "ls-tree", "-r", "--name-only", "--full-tree", rev).decode()
    34      return sorted(p for p in out.splitlines() if p.endswith(".py"))
    35  
    36  
    37  def read_files(repo: str | Path, rev: str, paths: list[str]) -> dict[str, bytes]:
    38      if not paths:
    39          return {}
    40      queries = "".join(f"{rev}:{p}\n" for p in paths).encode()
    41      out = _git(repo, "cat-file", "--batch", input_bytes=queries)
    42      blobs: dict[str, bytes] = {}
    43      pos = 0
    44      for path in paths:
    45          header_end = out.index(b"\n", pos)
    46          header = out[pos:header_end].decode()
    47          pos = header_end + 1
    48          if header.endswith(" missing"):
    49              raise GitError(f"object {rev}:{path} not found")
    50          size = int(header.rsplit(" ", 1)[1])
    51          blobs[path] = out[pos : pos + size]
    52          pos += size + 1  # blob content is followed by one newline
    53      return blobs
    54  
    55  
    56  _HUNK = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
    57  
    58  Range = tuple[int, int]
    59  
    60  
    61  def changed_files(
    62      repo: str | Path, old: str, new: str
    63  ) -> dict[str, tuple[list[Range], list[Range]]]:
    64      """Changed line ranges per file: {path: (old_side_ranges, new_side_ranges)}.
    65  
    66      Ranges are inclusive (start, end) 1-based line pairs. A pure insertion
    67      contributes nothing to the old side; a pure deletion nothing to the new.
    68      Renames are surfaced as delete + add (--no-renames).
    69      """
    70      out = _git(
    71          repo, "diff", "--no-ext-diff", "--no-renames", "--unified=0", old, new
    72      ).decode(errors="replace")
    73      files: dict[str, tuple[list[Range], list[Range]]] = {}
    74      current: tuple[list[Range], list[Range]] | None = None
    75      in_header = False
    76      a_path: str | None = None
    77      for line in out.splitlines():
    78          if line.startswith("diff --git "):
    79              in_header = True
    80              current = None
    81              a_path = None
    82              continue
    83          if in_header and line.startswith("--- "):
    84              name = line[4:]
    85              a_path = name[2:] if name.startswith("a/") else None
    86              continue
    87          if in_header and line.startswith("+++ "):
    88              name = line[4:]
    89              path = name[2:] if name.startswith("b/") else a_path
    90              if path is not None:
    91                  current = files.setdefault(path, ([], []))
    92              continue
    93          match = _HUNK.match(line)
    94          if match and current is not None:
    95              in_header = False
    96              old_start = int(match.group(1))
    97              old_count = 1 if match.group(2) is None else int(match.group(2))
    98              new_start = int(match.group(3))
    99              new_count = 1 if match.group(4) is None else int(match.group(4))
   100              if old_count:
   101                  current[0].append((old_start, old_start + old_count - 1))
   102              if new_count:
   103                  current[1].append((new_start, new_start + new_count - 1))
   104      return files

### Interfaces you consume
- analyzer.indexer.IndexLoadError  [class, confidence high]  lines 201-202  [available: symbol_table]
  signature: (Exception)
- analyzer.indexer._is_git_repo  [function, confidence high]  lines 19-24  [available: symbol_table]
  signature: (root: Path) -> bool
- analyzer.indexer._worktree_files  [function, confidence high]  lines 27-42  [available: symbol_table]
  signature: (root: Path) -> list[str]
- analyzer.indexer.build_index  [function, confidence high]  lines 45-194  [declared: symbol_table]
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
               Duplicate dotted paths are legal (property pairs, conditional
               defs); records sharing a path share their referenced_by.
      unresolved: sites whose target is statically undecidable — file, line,
               in_symbol, reason (subscript_call | getattr_call |
               attribute_of_call | star_import | dynamic_attribute |
               parse_error | unresolved_import_target), expression.
- analyzer.indexer.load_index  [function, confidence high]  lines 205-215  [available: symbol_table]
  signature: (path: str | Path) -> dict
- analyzer.indexer.serialize  [function, confidence high]  lines 197-198  [available: symbol_table]
  signature: (index: dict) -> str
- analyzer.modpath.module_path  [function, confidence high]  lines 4-8  [available: symbol_table]
  signature: (rel_path: str) -> str
- analyzer.refs.ImportTable  [class, confidence low]  lines 46-94  [available: reference_map]
  signature: (none)
- analyzer.refs.ImportTable.__init__  [function, confidence low]  lines 47-51  [available: reference_map]
  signature: (self, module_path: str, *, is_package: bool = False)
- analyzer.refs.ImportTable._bind  [function, confidence low]  lines 88-91  [available: reference_map]
  signature: (self, name: str, target: str) -> None
- analyzer.refs.ImportTable.add  [function, confidence low]  lines 62-77  [available: reference_map]
  signature: (self, stmt: ast.stmt) -> None
- analyzer.refs.ImportTable.base_of  [function, confidence low]  lines 79-86  [available: reference_map]
  signature: (self, stmt: ast.ImportFrom) -> str
  doc: Dotted module the from-import pulls from, relative levels resolved.
- analyzer.refs.ImportTable.from_module  [function, confidence low]  lines 53-60  [available: reference_map]
  signature: (cls, tree: ast.Module, module_path: str, *, is_package: bool = False) -> 'ImportTable'
- analyzer.refs.ImportTable.resolve  [function, confidence low]  lines 93-94  [available: reference_map]
  signature: (self, name: str) -> tuple[str, ...]
- analyzer.refs.Resolver  [class, confidence low]  lines 184-257  [available: reference_map]
  signature: (none)
- analyzer.refs.Resolver.__init__  [function, confidence low]  lines 185-193  [available: reference_map]
  signature: (self, symbols: dict[str, list[dict]], tables: dict[str, 'ImportTable'])
- analyzer.refs.Resolver.is_module  [function, confidence low]  lines 195-196  [available: reference_map]
  signature: (self, dotted: str) -> bool
- analyzer.refs.Resolver.kind_of  [function, confidence low]  lines 255-257  [available: reference_map]
  signature: (self, path: str) -> str | None
- analyzer.refs.Resolver.module_anchor_exists  [function, confidence low]  lines 198-201  [available: reference_map]
  signature: (self, dotted: str) -> bool
  doc: Does this dotted module string plausibly refer to an indexed
    module (exactly, or as a src-layout suffix)?
- analyzer.refs.Resolver.resolve_dotted  [function, confidence low]  lines 206-253  [available: reference_map]
  signature: (self, dotted: str, *, _depth: int = 0, _seen: frozenset = frozenset()) -> list[tuple[str, str | None]]
  doc: Resolve a dotted target to indexed symbol paths.
    
    Returns [(symbol_path, note)] — note None for exact hits, a
    human-readable ambiguity note for suffix matches. Misses through
    re-exports are chased through the target module's own import
    table (pkg/__init__.py facades).
- analyzer.refs.Resolver.terminal_matches  [function, confidence low]  lines 203-204  [available: reference_map]
  signature: (self, name: str) -> list[str]
- analyzer.refs._Frame  [class, confidence low]  lines 273-310  [available: reference_map]
  signature: (none)
- analyzer.refs._Frame.__init__  [function, confidence low]  lines 276-281  [available: reference_map]
  signature: (self, kind: str)
- analyzer.refs._Frame.bind  [function, confidence low]  lines 283-310  [available: reference_map]
  signature: (self, name: str, origin: str, payload=None) -> None
- analyzer.refs._Walker  [class, confidence low]  lines 318-822  [available: reference_map]
  signature: (none)
- analyzer.refs._Walker.__init__  [function, confidence low]  lines 319-329  [available: reference_map]
  signature: (self, rel_path: str, mod_path: str, resolver: Resolver)
- analyzer.refs._Walker._class_frame  [function, confidence low]  lines 383-393  [available: reference_map]
  signature: (self, node: ast.ClassDef, class_path: str) -> _Frame
- analyzer.refs._Walker._enclosing_class  [function, confidence low]  lines 434-438  [available: reference_map]
  signature: (self) -> _Frame | None
- analyzer.refs._Walker._expr_symbol_paths  [function, confidence low]  lines 465-494  [available: reference_map]
  signature: (self, expr) -> list[tuple[str, str | None]]
  doc: Exact-ish symbol paths an expression statically denotes.
- analyzer.refs._Walker._fallback  [function, confidence low]  lines 496-498  [available: reference_map]
  signature: (self, node, terminal: str, kind: str, args, note: str)
- analyzer.refs._Walker._flag  [function, confidence low]  lines 351-366  [available: reference_map]
  signature: (self, node, reason: str, expression: str | None = None)
- analyzer.refs._Walker._function_frame  [function, confidence low]  lines 375-381  [available: reference_map]
  signature: (self, node) -> _Frame
- analyzer.refs._Walker._lookup  [function, confidence low]  lines 421-432  [available: reference_map]
  signature: (self, name: str)
  doc: Find the binding for a name: walks frames innermost-out, skipping
    class frames unless the class body is the current scope (Python
    semantics: class scope does not enclose methods).
- analyzer.refs._Walker._module_frame  [function, confidence low]  lines 370-373  [available: reference_map]
  signature: (self, tree: ast.Module) -> _Frame
- analyzer.refs._Walker._name_targets  [function, confidence low]  lines 440-463  [available: reference_map]
  signature: (self, name: str) -> list[tuple[str, str | None]] | None
  doc: Symbol paths a bare name refers to. None => opaque/unbound.
- analyzer.refs._Walker._populate_scope_frame  [function, confidence low]  lines 395-417  [available: reference_map]
  signature: (self, frame: _Frame, body, prefix: str, *, opaque_assigns: bool = True) -> None
- analyzer.refs._Walker._record  [function, confidence low]  lines 333-349  [available: reference_map]
  signature: (self, node, target: str, kind: str, note: str | None, args=None)
- analyzer.refs._Walker._resolve_attribute_use  [function, confidence low]  lines 500-626  [available: reference_map]
  signature: (self, attr: ast.Attribute, kind: str, args, site)
  doc: Emit references for an attribute chain in Load context. `site` is
    the node whose position anchors the record (the Call for calls).
- analyzer.refs._Walker._visit_Assign  [function, confidence low]  lines 733-743  [available: reference_map]
  signature: (self, node: ast.Assign) -> None
- analyzer.refs._Walker._visit_Attribute  [function, confidence low]  lines 819-822  [available: reference_map]
  signature: (self, node: ast.Attribute) -> None
- analyzer.refs._Walker._visit_Call  [function, confidence low]  lines 772-811  [available: reference_map]
  signature: (self, node: ast.Call) -> None
- analyzer.refs._Walker._visit_ClassDef  [function, confidence low]  lines 676-689  [available: reference_map]
  signature: (self, node: ast.ClassDef) -> None
- analyzer.refs._Walker._visit_FunctionDef  [function, confidence low]  lines 644-660  [available: reference_map]
  signature: (self, node) -> None
- analyzer.refs._Walker._visit_Import  [function, confidence low]  lines 730-731  [available: reference_map]
  signature: (self, node: ast.Import) -> None
- analyzer.refs._Walker._visit_ImportFrom  [function, confidence low]  lines 745-770  [available: reference_map]
  signature: (self, node: ast.ImportFrom) -> None
- analyzer.refs._Walker._visit_Lambda  [function, confidence low]  lines 691-698  [available: reference_map]
  signature: (self, node: ast.Lambda) -> None
- analyzer.refs._Walker._visit_Name  [function, confidence low]  lines 813-817  [available: reference_map]
  signature: (self, node: ast.Name) -> None
- analyzer.refs._Walker._visit_arg_annotations_and_defaults  [function, confidence low]  lines 664-674  [available: reference_map]
  signature: (self, args: ast.arguments) -> None
- analyzer.refs._Walker._visit_comprehension_scope  [function, confidence low]  lines 700-723  [available: reference_map]
  signature: (self, node) -> None
- analyzer.refs._Walker.visit  [function, confidence low]  lines 636-642  [available: reference_map]
  signature: (self, node) -> None
- analyzer.refs._Walker.visit_module  [function, confidence low]  lines 630-634  [available: reference_map]
  signature: (self, tree: ast.Module) -> None
- analyzer.refs._dedupe_resolutions  [function, confidence low]  lines 260-267  [available: reference_map]
  signature: (results: list[tuple[str, str | None]]) -> list[tuple[str, str | None]]
- analyzer.refs._params_of  [function, confidence low]  lines 160-166  [available: reference_map]
  signature: (args: ast.arguments) -> set[str]
- analyzer.refs._scan_opaque  [function, confidence low]  lines 110-157  [available: reference_map]
  signature: (node, opaque: set[str], excluded: set[str], in_comp: bool) -> None
- analyzer.refs._scope_stmts  [function, confidence low]  lines 28-40  [available: reference_map]
  signature: (stmts)
  doc: Yield statements reachable at the same scope level: descends through
    control flow (if/try/for/while/with) but never into defs or classes.
- analyzer.refs._target_names  [function, confidence low]  lines 100-107  [available: reference_map]
  signature: (node, out: set[str]) -> None
- analyzer.refs.collect_references  [function, confidence low]  lines 825-830  [available: reference_map]
  signature: (tree: ast.Module, rel_path: str, mod_path: str, resolver: Resolver) -> tuple[list[tuple[str, dict]], list[dict]]
- analyzer.refs.local_bindings  [function, confidence low]  lines 169-178  [available: reference_map]
  signature: (func_node) -> set[str]
  doc: Names bound opaquely (shadowing) in a function scope: params,
    assignments, loop/with/except/match targets, walrus — minus names
    declared global/nonlocal. Nested defs and local imports are excluded:
    they bind too, but resolvably (def/import origin).
- analyzer.symbols.ParseFailure  [class, confidence high]  lines 15-19  [available: symbol_table]
  signature: (Exception)
- analyzer.symbols.ParseFailure.__init__  [function, confidence high]  lines 16-19  [available: symbol_table]
  signature: (self, rel_path: str, error: Exception)
- analyzer.symbols._body_hash  [function, confidence high]  lines 97-101  [available: symbol_table]
  signature: (node: ast.AST) -> str
- analyzer.symbols._hash  [function, confidence high]  lines 22-23  [available: symbol_table]
  signature: (text: str) -> str
- analyzer.symbols._kind  [function, confidence high]  lines 104-109  [available: symbol_table]
  signature: (node: ast.AST) -> str
- analyzer.symbols._param  [function, confidence high]  lines 26-28  [available: symbol_table]
  signature: (arg: ast.arg, has_default: bool) -> str
- analyzer.symbols._param_display  [function, confidence high]  lines 63-70  [available: symbol_table]
  signature: (arg: ast.arg, default: ast.AST | None) -> str
- analyzer.symbols._sig_canonical  [function, confidence high]  lines 31-60  [available: symbol_table]
  signature: (node: ast.AST) -> str
- analyzer.symbols._signature_display  [function, confidence high]  lines 73-94  [available: symbol_table]
  signature: (node: ast.AST) -> str
- analyzer.symbols._visit  [function, confidence high]  lines 128-162  [available: symbol_table]
  signature: (node: ast.AST, prefix: str, rel_path: str, records: list[dict]) -> None
- analyzer.symbols.extract_from_tree  [function, confidence high]  lines 120-125  [available: symbol_table]
  signature: (tree: ast.Module, rel_path: str) -> list[dict]
- analyzer.symbols.extract_symbols  [function, confidence high]  lines 112-117  [available: symbol_table]
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
- analyzer.gitio.GitError <- analyzer/cli.py:7 in analyzer.cli
- analyzer.gitio.GitError <- analyzer/cli.py:14 in analyzer.cli._cmd_index
- analyzer.gitio.GitError <- analyzer/cli.py:97 in analyzer.cli._cmd_affected
- analyzer.gitio.GitError <- harness/join.py:21 in harness.join
- analyzer.gitio.GitError <- harness/join.py:543 in harness.join._source_of
- analyzer.gitio.GitError <- harness/join.py:835 in harness.join.main
- analyzer.gitio._git <- analyzer/indexer.py:31 in analyzer.indexer._worktree_files args=(root, 'ls-files', '--cached', '--others', '--exclude-standard', '--', '*.py')
- analyzer.gitio.changed_files <- tests/test_gitio.py:37 in tests.test_gitio.test_changed_files_insertion args=(repo, old, new)
- analyzer.gitio.changed_files <- tests/test_gitio.py:54 in tests.test_gitio.test_changed_files_modification_and_multiple_hunks args=(repo, old, new)
- analyzer.gitio.changed_files <- tests/test_gitio.py:65 in tests.test_gitio.test_rename_appears_as_delete_plus_add args=(repo, old, new)
- analyzer.gitio.changed_files <- tests/test_gitio.py:75 in tests.test_gitio.test_deleted_file_reported args=(repo, old, new)
- analyzer.gitio.list_py_files <- analyzer/indexer.py:73 in analyzer.indexer.build_index args=(root, sha)
- analyzer.gitio.list_py_files <- tests/test_gitio.py:16 in tests.test_gitio.test_list_py_files_sorted_and_filtered args=(repo, rev)
- analyzer.gitio.read_files <- analyzer/indexer.py:74 in analyzer.indexer.build_index args=(root, sha, files)
- analyzer.gitio.read_files <- harness/join.py:540 in harness.join._source_of args=(repo, commit, [rel_path])
- analyzer.gitio.read_files <- tests/test_gitio.py:22 in tests.test_gitio.test_read_files_round_trips_content args=(repo, rev, ['src/a.py'])
- analyzer.gitio.resolve_commit <- analyzer/indexer.py:72 in analyzer.indexer.build_index args=(root, commit)
- analyzer.gitio.resolve_commit <- tests/test_gitio.py:28 in tests.test_gitio.test_resolve_commit_full_sha args=(repo, 'HEAD')

### Unresolved sites in scope
(none)

### Coverage
Compiled from an index of 25 files at baad6d55691a42e3e0208372c1e408ba114b33d1. This packet includes your write scope (2 entries), 70 consumed/available interface symbols, and every recorded caller of your scope. Anything not listed was not searched. Missing means query (request_mem), never build. verify with: python -m pytest

## State — handoff  [provenance: agent-authored, claim not fact]

(none for this dispatch)
packet: node=affected_symbols role=executor commit=baad6d55691a42e3e0208372c1e408ba114b33d1 plan=8183a526ab88 packet_hash=b9770e5d4554
