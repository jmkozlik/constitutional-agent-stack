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

node: index_assembly
language: python
observed_through: the value returned by the surface callable, unless a done_when bullet names a rendering callable explicitly
one_liner: Assembles the index for a repo at a commit - symbol records, reference edges, unresolved sites, and each file's import bindings with their resolved origins.
write scope (exhaustive — writing anything else is a violation):
  - analyzer/indexer.py
surface (the exported contract done_when is tested through):
  callables:
    - analyzer.indexer.build_index(repo: str | Path, commit: str | None) -> dict  [seeded]
    - analyzer.indexer.serialize(index: dict) -> str  [seeded]
    - analyzer.indexer.load_index(path: str | Path) -> dict  [seeded]
    - analyzer.indexer.import_origins(index: dict, module: str) -> list[str]  [authored]
  types:
    - analyzer.indexer.record(path: str, kind: str, file: str, start_line: int, end_line: int, signature: str, doc: str | None, sig_hash: str, body_hash: str, decor_hash: str, parent: str, confidence: str, referenced_by: list; class records add fields: list)  [authored]
    - analyzer.indexer.imports: the index adds a top-level imports table — {file - [{name - str, kind - module | symbol, origin - dotted resolved terminal, being the symbol path for name bindings and the module path for module bindings, module - dotted defining module, equal to origin for module-kind entries}]} — taken from the Resolver's output at build time, never recomputed downstream. Files emit sorted by path and each file's entries emit sorted by (name, origin), so byte-identity survives the new key.  [authored]
    - analyzer.indexer.import_origins: matches entries on the module field — the dotted defining module — and answers from the index's imports table, never by recomputation.  [authored]
    - analyzer.indexer.imports: an import whose bound names cannot be resolved but whose source module is stated (star_import) emits kind unresolved with origin null and module = the source module. An import whose target itself cannot be resolved (unresolved_import_target) emits kind unresolved with origin and module null. The binding is recorded, never invented — and a stated source module is a fact, not an invention.  [authored]
    - analyzer.indexer.imports: every indexed file gets an entry list, empty when it imports nothing; a file that fails to parse gets an empty list alongside its parse_error unresolved site.  [authored]
    - analyzer.indexer.import_origins: returns the sorted, deduplicated repo-relative files importing that module — empty for an unknown module and for an index built before the imports key existed.  [authored]
    - analyzer.affected.Row.path: the affected symbol's dotted path; one row per affected symbol path  [authored]  [from affected_symbols]
    - analyzer.refs.Resolver(symbols: dict[str, list[dict]], tables: dict[str, 'ImportTable'])  [seeded]  [from reference_map]
  errors:
    - analyzer.indexer.IndexLoadError: raised by load_index when the index file is unreadable or not an analyzer index; a missing file raises FileNotFoundError unchanged  [seeded]
done_when (attest against, or file against, on a validation-only dispatch):
  - Indexing the same commit twice produces byte identical output.
  - The emitted index maps every symbol path to at least one record carrying its definition location and signature.
  - build_index exposes each file's import bindings with resolved origins, re-export chains included, and import_origins answers from them.
  - A bare module import that is never called yields a module-kind imports entry whose origin and module are both the imported module, so an imported-but-uncalled binding leaves a trace in the index.
  - A star-importing file lands in the source module's importer set — its imports entry carries kind unresolved with module set to the source module, so import_origins names it.

delta [compiled at dispatch from surface x index — surface is what makes the delta computable; it is never spec-authored and never handoff-carried]:
  writes:
    - analyzer/indexer.py: exists@8a42ca02
  callables:
    - analyzer.indexer.build_index(repo: str | Path, commit: str | None) -> dict  [seeded]: present
    - analyzer.indexer.serialize(index: dict) -> str  [seeded]: present
    - analyzer.indexer.load_index(path: str | Path) -> dict  [seeded]: present
    - analyzer.indexer.import_origins(index: dict, module: str) -> list[str]  [authored]: absent
  types:
    - analyzer.indexer.record(path: str, kind: str, file: str, start_line: int, end_line: int, signature: str, doc: str | None, sig_hash: str, body_hash: str, decor_hash: str, parent: str, confidence: str, referenced_by: list; class records add fields: list)  [authored]: authored (contract — tester-verified, delta-exempt)
    - analyzer.indexer.imports: the index adds a top-level imports table — {file - [{name - str, kind - module | symbol, origin - dotted resolved terminal, being the symbol path for name bindings and the module path for module bindings, module - dotted defining module, equal to origin for module-kind entries}]} — taken from the Resolver's output at build time, never recomputed downstream. Files emit sorted by path and each file's entries emit sorted by (name, origin), so byte-identity survives the new key.  [authored]: authored (contract — tester-verified, delta-exempt)
    - analyzer.indexer.import_origins: matches entries on the module field — the dotted defining module — and answers from the index's imports table, never by recomputation.  [authored]: authored (contract — tester-verified, delta-exempt)
    - analyzer.indexer.imports: an import whose bound names cannot be resolved but whose source module is stated (star_import) emits kind unresolved with origin null and module = the source module. An import whose target itself cannot be resolved (unresolved_import_target) emits kind unresolved with origin and module null. The binding is recorded, never invented — and a stated source module is a fact, not an invention.  [authored]: authored (contract — tester-verified, delta-exempt)
    - analyzer.indexer.imports: every indexed file gets an entry list, empty when it imports nothing; a file that fails to parse gets an empty list alongside its parse_error unresolved site.  [authored]: authored (contract — tester-verified, delta-exempt)
    - analyzer.indexer.import_origins: returns the sorted, deduplicated repo-relative files importing that module — empty for an unknown module and for an index built before the imports key existed.  [authored]: authored (contract — tester-verified, delta-exempt)
  errors:
    - analyzer.indexer.IndexLoadError: raised by load_index when the index file is unreadable or not an analyzer index; a missing file raises FileNotFoundError unchanged  [seeded]: present
  => 1 outstanding: analyzer.indexer.import_origins(index: dict, module: str) -> list[str]  [authored]

## State — compiled  [provenance: verified at f146eb16d654cc25fdba3858ea6b393cc833b188]

### Write scope as it exists

#### analyzer/indexer.py
- analyzer.indexer.IndexLoadError  [class, confidence high]  lines 203-204
  signature: (Exception)
- analyzer.indexer._is_git_repo  [function, confidence high]  lines 19-24
  signature: (root: Path) -> bool
- analyzer.indexer._worktree_files  [function, confidence high]  lines 27-42
  signature: (root: Path) -> list[str]
- analyzer.indexer.build_index  [function, confidence high]  lines 45-196
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
- analyzer.indexer.load_index  [function, confidence high]  lines 207-217
  signature: (path: str | Path) -> dict
- analyzer.indexer.serialize  [function, confidence high]  lines 199-200
  signature: (index: dict) -> str

source (verbatim at f146eb16d654cc25fdba3858ea6b393cc833b188):
     1  """Orchestration: walk a repo (working tree or commit), run both passes,
     2  emit a deterministic index dict / JSON document."""
     3  
     4  import ast
     5  import json
     6  import subprocess
     7  import sys
     8  from collections import defaultdict
     9  from pathlib import Path
    10  
    11  from analyzer import gitio
    12  from analyzer.modpath import module_path
    13  from analyzer.refs import ImportTable, Resolver, collect_references
    14  from analyzer.symbols import extract_from_tree
    15  
    16  _SKIP_DIRS = {"__pycache__", "venv", ".venv", "node_modules"}
    17  
    18  
    19  def _is_git_repo(root: Path) -> bool:
    20      result = subprocess.run(
    21          ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
    22          capture_output=True,
    23      )
    24      return result.returncode == 0 and result.stdout.strip() == b"true"
    25  
    26  
    27  def _worktree_files(root: Path) -> list[str]:
    28      if _is_git_repo(root):
    29          # Same file-listing rule as --commit (tracked files, dot-dirs
    30          # included) plus untracked-but-not-ignored work in progress.
    31          out = gitio._git(
    32              root, "ls-files", "--cached", "--others", "--exclude-standard",
    33              "--", "*.py",
    34          ).decode()
    35          return sorted({p for p in out.splitlines() if p.endswith(".py")})
    36      files = []
    37      for path in root.rglob("*.py"):
    38          rel_parts = path.relative_to(root).parts
    39          if any(p.startswith(".") or p in _SKIP_DIRS for p in rel_parts[:-1]):
    40              continue
    41          files.append("/".join(rel_parts))
    42      return sorted(files)
    43  
    44  
    45  def build_index(repo: str | Path, commit: str | None) -> dict:
    46      """Index a repo (working tree, or a commit's blobs when `commit` is set).
    47  
    48      Returns the index dict, serialized 1:1 into index.json:
    49        version: 1
    50        commit:  full sha, or None for a working-tree index
    51        files:   every indexed .py path, sorted, repo-relative
    52        symbols: one record per definition, sorted by
    53                 (path, file, start_line, sig_hash, body_hash):
    54                 path (dotted), kind (function|async_function|class), file,
    55                 start_line/end_line (decorators included), signature (display
    56                 string), doc (docstring or null), sig_hash (name+params+
    57                 annotations+defaults-presence+return), body_hash (unparsed
    58                 body), decor_hash, parent (enclosing scope's dotted path),
    59                 confidence ("low" iff the file has any unresolved record),
    60                 referenced_by (sites: file, line, in_symbol, kind call|name,
    61                 args as written for calls, ambiguous+note when inexact).
    62                 Class records additionally carry fields (annotated class-body
    63                 targets in body order, rendered `name: ann = default`).
    64                 Duplicate dotted paths are legal (property pairs, conditional
    65                 defs); records sharing a path share their referenced_by.
    66        unresolved: sites whose target is statically undecidable — file, line,
    67                 in_symbol, reason (subscript_call | getattr_call |
    68                 attribute_of_call | star_import | dynamic_attribute |
    69                 parse_error | unresolved_import_target), expression.
    70      """
    71      root = Path(repo)
    72      read_failures: list[tuple[str, str]] = []
    73      if commit is not None:
    74          sha = gitio.resolve_commit(root, commit)
    75          files = gitio.list_py_files(root, sha)
    76          blobs = gitio.read_files(root, sha, files)
    77      else:
    78          if not root.is_dir():
    79              raise FileNotFoundError(f"{root} is not a directory")
    80          sha = None
    81          files = _worktree_files(root)
    82          blobs = {}
    83          for rel in files:
    84              try:
    85                  blobs[rel] = (root / rel).read_bytes()
    86              except OSError as exc:
    87                  read_failures.append((rel, str(exc)))
    88          files = [f for f in files if f in blobs]
    89  
    90      symbols_by_path: dict[str, list[dict]] = defaultdict(list)
    91      trees: dict[str, tuple[ast.Module, str]] = {}
    92      unresolved: list[dict] = [
    93          {
    94              "file": rel,
    95              "line": 1,
    96              "in_symbol": module_path(rel),
    97              "reason": "parse_error",
    98              "expression": f"unreadable: {message}",
    99          }
   100          for rel, message in read_failures
   101      ]
   102      # Deep-but-legal trees (chained binops in generated code) can exceed the
   103      # default recursion limit inside ast.unparse or the walkers; give
   104      # headroom and degrade any remaining blowup to a per-file flag.
   105      sys.setrecursionlimit(max(sys.getrecursionlimit(), 10_000))
   106      for rel in files:
   107          mod = module_path(rel)
   108          try:
   109              tree = ast.parse(blobs[rel])
   110              records = extract_from_tree(tree, rel)
   111          except (SyntaxError, ValueError, RecursionError) as exc:
   112              unresolved.append(
   113                  {
   114                      "file": rel,
   115                      "line": 1,
   116                      "in_symbol": mod,
   117                      "reason": "parse_error",
   118                      "expression": "recursion limit exceeded while analyzing"
   119                      if isinstance(exc, RecursionError)
   120                      else str(exc),
   121                  }
   122              )
   123              continue
   124          for record in records:
   125              symbols_by_path[record["path"]].append(record)
   126          trees[rel] = (tree, mod)
   127  
   128      tables = {
   129          mod: ImportTable.from_module(tree, mod, is_package=rel.endswith("__init__.py"))
   130          for rel, (tree, mod) in trees.items()
   131      }
   132      resolver = Resolver(dict(symbols_by_path), tables)
   133  
   134      refs_by_target: dict[str, list[dict]] = defaultdict(list)
   135      for rel in sorted(trees):
   136          tree, mod = trees[rel]
   137          try:
   138              refs, unres = collect_references(tree, rel, mod, resolver)
   139          except RecursionError:
   140              unresolved.append(
   141                  {
   142                      "file": rel,
   143                      "line": 1,
   144                      "in_symbol": mod,
   145                      "reason": "parse_error",
   146                      "expression": "recursion limit exceeded during reference pass",
   147                  }
   148              )
   149              continue
   150          for target, record in refs:
   151              refs_by_target[target].append(record)
   152          unresolved.extend(unres)
   153  
   154      low_confidence_files = {u["file"] for u in unresolved}
   155      symbols_out = []
   156      for path, records in symbols_by_path.items():
   157          callers = sorted(
   158              refs_by_target.get(path, []),
   159              key=lambda r: (
   160                  r["file"],
   161                  r["line"],
   162                  r["in_symbol"],
   163                  r["kind"],
   164                  r.get("note", ""),
   165                  r.get("args", []),
   166              ),
   167          )
   168          for record in records:
   169              out = dict(record)
   170              out["confidence"] = (
   171                  "low" if record["file"] in low_confidence_files else "high"
   172              )
   173              # Duplicate dotted paths are legal (property/setter pairs,
   174              # conditional defs); every record of a path carries the same
   175              # callers because call sites cannot pick between them (plan A6).
   176              out["referenced_by"] = callers
   177              symbols_out.append(out)
   178      symbols_out.sort(
   179          key=lambda s: (
   180              s["path"],
   181              s["file"],
   182              s["start_line"],
   183              s["sig_hash"],
   184              s["body_hash"],
   185          )
   186      )
   187      unresolved.sort(
   188          key=lambda u: (u["file"], u["line"], u["reason"], u["expression"])
   189      )
   190      return {
   191          "version": 1,
   192          "commit": sha,
   193          "files": list(files),
   194          "symbols": symbols_out,
   195          "unresolved": unresolved,
   196      }
   197  
   198  
   199  def serialize(index: dict) -> str:
   200      return json.dumps(index, indent=2, sort_keys=True) + "\n"
   201  
   202  
   203  class IndexLoadError(Exception):
   204      pass
   205  
   206  
   207  def load_index(path: str | Path) -> dict:
   208      try:
   209          with open(path, encoding="utf-8") as fh:
   210              index = json.load(fh)
   211      except FileNotFoundError:
   212          raise
   213      except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
   214          raise IndexLoadError(f"cannot read index {str(path)!r}: {exc}") from exc
   215      if not isinstance(index, dict) or "symbols" not in index or "unresolved" not in index:
   216          raise IndexLoadError(f"{str(path)!r} is not an analyzer index file")
   217      return index

### Interfaces you consume
- analyzer.gitio.GitError  [class, confidence high]  lines 11-12  [available: gitio]
  signature: (Exception)
- analyzer.gitio._git  [function, confidence high]  lines 15-25  [declared: gitio]
  signature: (repo: str | Path, *args: str, input_bytes: bytes | None = None) -> bytes
- analyzer.gitio.changed_files  [function, confidence high]  lines 61-104  [available: gitio]
  signature: (repo: str | Path, old: str, new: str) -> dict[str, tuple[list[Range], list[Range]]]
  doc: Changed line ranges per file: {path: (old_side_ranges, new_side_ranges)}.
    
    Ranges are inclusive (start, end) 1-based line pairs. A pure insertion
    contributes nothing to the old side; a pure deletion nothing to the new.
    Renames are surfaced as delete + add (--no-renames).
- analyzer.gitio.list_py_files  [function, confidence high]  lines 32-34  [declared: gitio]
  signature: (repo: str | Path, rev: str) -> list[str]
- analyzer.gitio.read_files  [function, confidence high]  lines 37-53  [declared: gitio]
  signature: (repo: str | Path, rev: str, paths: list[str]) -> dict[str, bytes]
- analyzer.gitio.resolve_commit  [function, confidence high]  lines 28-29  [declared: gitio]
  signature: (repo: str | Path, rev: str) -> str
- analyzer.modpath.module_path  [function, confidence high]  lines 4-8  [declared: symbol_table]
  signature: (rel_path: str) -> str
- analyzer.refs.ImportTable  [class, confidence low]  lines 46-94  [declared: reference_map]
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
- analyzer.refs.ImportTable.from_module  [function, confidence low]  lines 53-60  [declared: reference_map]
  signature: (cls, tree: ast.Module, module_path: str, *, is_package: bool = False) -> 'ImportTable'
- analyzer.refs.ImportTable.resolve  [function, confidence low]  lines 93-94  [available: reference_map]
  signature: (self, name: str) -> tuple[str, ...]
- analyzer.refs.Resolver  [class, confidence low]  lines 184-257  [declared: reference_map]
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
- analyzer.refs.collect_references  [function, confidence low]  lines 825-830  [declared: reference_map]
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
- analyzer.symbols.extract_from_tree  [function, confidence high]  lines 134-139  [declared: symbol_table]
  signature: (tree: ast.Module, rel_path: str) -> list[dict]
- analyzer.symbols.extract_symbols  [function, confidence high]  lines 126-131  [available: symbol_table]
  signature: (source: bytes, rel_path: str) -> list[dict]
- harness.speccc.load  [function, confidence high]  lines 25-43  [unowned file] [ambiguous attribution — edge known only by name match]
  signature: (spec_dir)

### Callers of your write scope
- analyzer.indexer.IndexLoadError <- analyzer/cli.py:8 in analyzer.cli
- analyzer.indexer.IndexLoadError <- analyzer/cli.py:38 in analyzer.cli._load
- analyzer.indexer.build_index <- analyzer/affected.py:22 in analyzer.affected
- analyzer.indexer.build_index <- analyzer/affected.py:73 in analyzer.affected.compute_affected args=(repo, old_sha)
- analyzer.indexer.build_index <- analyzer/affected.py:74 in analyzer.affected.compute_affected args=(repo, new_sha)
- analyzer.indexer.build_index <- analyzer/cli.py:8 in analyzer.cli
- analyzer.indexer.build_index <- analyzer/cli.py:13 in analyzer.cli._cmd_index args=(args.repo, args.commit)
- analyzer.indexer.build_index <- harness/dispatch.py:25 in harness.dispatch
- analyzer.indexer.build_index <- harness/dispatch.py:94 in harness.dispatch.prepare args=(repo, sha)
- analyzer.indexer.build_index <- harness/fence.py:25 in harness.fence
- analyzer.indexer.build_index <- harness/fence.py:161 in harness.fence._cmd_build args=(args.repo, commit)
- analyzer.indexer.build_index <- harness/join.py:24 in harness.join
- analyzer.indexer.build_index <- harness/join.py:1139 in harness.join._cmd_plan args=(args.repo, args.commit)
- analyzer.indexer.build_index <- harness/join.py:1173 in harness.join._cmd_packet args=(args.repo, commit)
- analyzer.indexer.build_index <- harness/join.py:1307 in harness.join._cmd_record args=(args.repo, sha)
- analyzer.indexer.build_index <- tests/test_fence.py:10 in tests.test_fence
- analyzer.indexer.build_index <- tests/test_fence.py:21 in tests.test_fence.fenced_fixture args=(repo, None)
- analyzer.indexer.build_index <- tests/test_fence.py:46 in tests.test_fence.test_build_fence_to_create args=(repo, None)
- analyzer.indexer.build_index <- tests/test_fence.py:59 in tests.test_fence.test_tester_fence_allows_no_tracked_writes args=(repo, None)
- analyzer.indexer.build_index <- tests/test_fence.py:76 in tests.test_fence.test_executor_fence_unchanged_by_role_parameter args=(repo2, None)
- analyzer.indexer.build_index <- tests/test_fence.py:91 in tests.test_fence.test_diff_gate_catches_tester_writing_implementation args=(repo, None)
- analyzer.indexer.build_index <- tests/test_fence.py:128 in tests.test_fence.test_f29_tester_hard_read_denies_outside_and_allows_harness args=(repo, None)
- analyzer.indexer.build_index <- tests/test_indexer.py:1 in tests.test_indexer
- analyzer.indexer.build_index <- tests/test_indexer.py:37 in tests.test_indexer.test_build_index_end_to_end args=(repo, None)
- analyzer.indexer.build_index <- tests/test_indexer.py:50 in tests.test_indexer.test_low_confidence_marks_whole_file_only args=(repo, None)
- analyzer.indexer.build_index <- tests/test_indexer.py:59 in tests.test_indexer.test_index_records_file_list args=(repo, None)
- analyzer.indexer.build_index <- tests/test_indexer.py:65 in tests.test_indexer.test_serialize_deterministic args=(repo, None)
- analyzer.indexer.build_index <- tests/test_indexer.py:66 in tests.test_indexer.test_serialize_deterministic args=(repo, None)
- analyzer.indexer.build_index <- tests/test_indexer.py:74 in tests.test_indexer.test_commit_and_worktree_parity args=(repo, 'HEAD')
- analyzer.indexer.build_index <- tests/test_indexer.py:75 in tests.test_indexer.test_commit_and_worktree_parity args=(repo, None)
- analyzer.indexer.build_index <- tests/test_indexer.py:87 in tests.test_indexer.test_parse_error_flagged_not_fatal args=(repo, None)
- analyzer.indexer.build_index <- tests/test_indexer.py:100 in tests.test_indexer.test_recursion_bomb_degrades_to_parse_error args=(repo, None)
- analyzer.indexer.build_index <- tests/test_indexer.py:127 in tests.test_indexer.test_duplicate_paths_share_referenced_by args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:8 in tests.test_join
- analyzer.indexer.build_index <- tests/test_join.py:61 in tests.test_join.joined args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:103 in tests.test_join.test_escaping_path_is_e06 args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:249 in tests.test_join.real_packet args=(PROJECT_ROOT, None)
- analyzer.indexer.build_index <- tests/test_join.py:307 in tests.test_join.test_to_create_rendered_in_packet args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:378 in tests.test_join.test_degenerate_writes_entry_is_e06 args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:541 in tests.test_join.test_delta_empty_when_everything_present args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:560 in tests.test_join.test_delta_full_on_greenfield args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:577 in tests.test_join.test_delta_signature_mismatch args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:593 in tests.test_join.test_delta_type_shape_mismatch args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:614 in tests.test_join.test_delta_constructor_shaped_type_matches_init args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:627 in tests.test_join.test_delta_alias_type_is_unindexed_never_outstanding args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:642 in tests.test_join.test_delta_error_via_field_path args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:656 in tests.test_join.test_delta_error_condition_may_contain_colons args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:676 in tests.test_join.test_delta_without_surface_not_computable args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:685 in tests.test_join.test_executor_packet_carries_delta_block args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:700 in tests.test_join.test_executor_done_when_sits_above_delta args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:719 in tests.test_join.test_foreign_type_resolves_from_owning_node args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:732 in tests.test_join.test_tester_packet_carries_surface_only args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:775 in tests.test_join.test_authored_entries_are_delta_exempt args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:794 in tests.test_join.test_seeded_mismatch_still_fails_delta args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:805 in tests.test_join.test_meta_language_renders_in_both_packets args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:905 in tests.test_join.test_structural_authored_absent_is_outstanding args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:923 in tests.test_join.test_structural_authored_present_and_behavioral_exempt args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:938 in tests.test_join.test_f20_locked_demonstration_on_real_spec args=(PROJECT_ROOT, None)
- analyzer.indexer.build_index <- tests/test_join.py:961 in tests.test_join.test_f20_callable_extension_in_scope_presence_checks args=(PROJECT_ROOT, None)
- analyzer.indexer.build_index <- tests/test_join.py:980 in tests.test_join.test_f20_callable_extension_absent_until_built_on_real_spec args=(PROJECT_ROOT, None)
- analyzer.indexer.build_index <- tests/test_join.py:1006 in tests.test_join.test_f20_callable_outside_own_scope_stays_behavioral args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:1059 in tests.test_join.test_tester_packet_surface_is_contained_in_its_own_node args=(PROJECT_ROOT, None)
- analyzer.indexer.build_index <- tests/test_join.py:1072 in tests.test_join.test_prose_type_line_does_not_leak_into_other_nodes_packets args=(PROJECT_ROOT, None)
- analyzer.indexer.build_index <- tests/test_join.py:1138 in tests.test_join.test_record_emitter_composes_from_artifacts args=(repo, sha)
- analyzer.indexer.build_index <- tests/test_join.py:1174 in tests.test_join.test_record_emitter_rejects_trailer_mismatch args=(repo, sha)
- analyzer.indexer.build_index <- tests/test_join.py:1198 in tests.test_join.test_real_spec_resolves_against_this_repo args=(PROJECT_ROOT, None)
- analyzer.indexer.load_index <- analyzer/cli.py:8 in analyzer.cli
- analyzer.indexer.load_index <- analyzer/cli.py:31 in analyzer.cli._load args=(args.index)
- analyzer.indexer.serialize <- analyzer/cli.py:8 in analyzer.cli
- analyzer.indexer.serialize <- analyzer/cli.py:18 in analyzer.cli._cmd_index args=(index)
- analyzer.indexer.serialize <- tests/test_indexer.py:1 in tests.test_indexer
- analyzer.indexer.serialize <- tests/test_indexer.py:65 in tests.test_indexer.test_serialize_deterministic args=(build_index(repo, None))
- analyzer.indexer.serialize <- tests/test_indexer.py:66 in tests.test_indexer.test_serialize_deterministic args=(build_index(repo, None))

### Unresolved sites in scope
(none)

### Coverage
Compiled from an index of 30 files at f146eb16d654cc25fdba3858ea6b393cc833b188. This packet includes your write scope (1 entries), 72 consumed/available interface symbols, and every recorded caller of your scope. Anything not listed was not searched. Missing means query (request_mem), never build. verify with: .venv/bin/python -m pytest

## State — handoff  [provenance: agent-authored, claim not fact]

Carried forward from dispatch 3d-1 (same node's work, now owned by
index_assembly after the ratified restructure). Provenance: the first
section is the previous executor's own words; the second is the
dispatcher answering the blocking REQUEST_MEM lines it stopped on.

## Rulings that answer your predecessor's blocking questions

- D-3d1-1 is ruled: **candidate 3, as reconciliation.** The imports entry
  carries name / kind / origin / module, and `import_origins` matches on
  `module`. The entry shape and its sort rule are in your surface — read
  them there, not here.
- Unresolvable imports now have a legal kind, which they did not when you
  stopped: a **star_import keeps its source module** (kind unresolved,
  origin null, module = source module), while an **unresolved_import_target**
  has both null. Reason on record: nulling module for star imports would
  drop star-importing files from the importer set and under-set
  callers_unknowable downstream.
- Key-presence and the `import_origins` return contract are also ruled and
  are in your surface.
- Your predecessor's own proof — a bare module import that is never called
  must leave a trace — is now a required done_when bullet, as is the
  star-import importer-set case.

## On the Resolver (your predecessor's D-3d1-2)

The restructure gave `analyzer/indexer.py` its own node, and it declares
`reference_map`, so refs' declared surface now compiles into your packet
as consumed interfaces. Two facts, so you are not guessing:

- `ImportTable.resolve(name) -> tuple[str, ...]` returns that name's dotted
  targets; a name bound by several imports keeps all of them.
- The tables are constructed inside your own write scope, so you hold the
  objects at build time — the spec's "taken from the Resolver's output at
  build time" is satisfiable without reaching into another node's file.

**Binding enumeration is still not declared surface.** If you need a public
accessor on `analyzer/refs.py`, that is a spec change owned by
`reference_map`: FILE it, do not reach across and do not re-derive imports
by parsing. Recording the binding is in scope; inventing one is not.

## Read policy, changed since you ran

Reads are no longer undefined. Yours is **disclose**: your write scope and
`.harness` are in-packet; anything else is allowed but recorded as a read
event in the dispatch record. Reads are not forbidden — invisible reads are.
Your predecessor's out-of-scope read was self-reported, which is what made
the rule ratifiable; it is now a mechanism rather than a courtesy.

---

## Predecessor's handoff, verbatim

# Handoff — 3d-1 · node symbol_table · role executor

packet: node=symbol_table role=executor commit=c7c6f7e0535cdc5de579cfadbd436af5860bc924
plan=c98fb664a54f packet_hash=6624a3b2aef7 dispatch_id=3d-1

For whoever resumes this node — most likely me after the blocking
request_mem is answered, otherwise a replacement. State is separated into
**verified** (a command produced it, and the command is named) and
**interpretive** (my reading, which may be wrong and was not acted on).

---

## Where the dispatch stopped

Done_when bullets 1-4 are ATTESTED with evidence. Bullet 5 is FILED, not
built: the outstanding delta item `analyzer.indexer.import_origins` plus the
top-level `imports` table. No tracked file was modified; the three write-scope
files stand byte-for-byte as delivered. Resuming means starting bullet 5 from
zero, with the request_mem answers in hand — nothing half-built to clean up.

## Verified — commands were run, output is on disk

- **Suite is green at the dispatch commit: 234 passed.**
  `/Users/rokko/experiments/lex/.venv/bin/python -m pytest -q`
  → `.harness/scratch/suite_baseline.txt`
- **Bullets 1-4 all hold.**
  `PYTHONPATH=.harness/scratch … python .harness/scratch/probe_3d1.py`, exit 0
  → `.harness/scratch/probe_out.txt`. Fixture builder:
  `.harness/scratch/mkfixture.py` (three commits: baseline / whitespace-only
  reformat + import-at-top / one-token body edit as control).
- **A new top-level `imports` key breaks nothing outside the write scope.**
  234 passed with every index carrying an injected key
  (`-p inject_imports_key`) → `.harness/scratch/suite_with_imports_key.txt`.
  The injection is itself controlled: `.harness/scratch/test_patch_effective.py`
  passes with the plugin and fails without it. **So the scope worry the
  pre-dispatch probe raised is dead — this task is completable inside the
  fence.** Delete that line from the request_mem list; do not re-measure.
- **The index contains no module records, and a bare `import pkg.impl` leaves
  no trace in the returned index at all** — no reference record, no unresolved
  site. `.harness/scratch/probe_origin_contradiction.py` →
  `.harness/scratch/probe_origins_out.txt`. This is the whole basis of
  D-3d1-1 and it is surface-only evidence.
- **The re-export chase already works for a called name**: a call reaching
  `pkg.impl.helper` only through `pkg/__init__.py` resolves to the real
  defining path. Same probe, part (b). Whatever the imports table ends up
  emitting, the chasing machinery underneath it is not the problem.
- **`start_line` participates in the record sort key** `(path, file,
  start_line, sig_hash, body_hash)` and in **no** hash input. Verified by
  reading `analyzer/indexer.py:178-186` (my own write scope) and by the
  identical-text-different-position check in bullet 4.
- **A base-less class renders `signature: ""`**; a class with bases renders
  `'(Widget, metaclass=type)'`. Attested and flagged, not changed.
- **Duplicate dotted paths survive as separate records with distinct
  body hashes** across a whitespace move (the property/setter pair
  `pkg.impl.Widget.value`, 10 records over 9 paths). Anything the imports work
  does must not collapse them.

## Interpretive — my reading, NOT acted on, may be wrong

- **The `origins` contradiction is real, not a wording nit.** My claim: the
  `symbol_table` line describes the Resolver's output (symbol paths) while
  `affected_symbols.Row.callers_unknowable` tests against a defining module,
  and those cannot both be satisfied by one flat `list[str]` of symbol paths.
  The *facts* underneath it are verified above; the *judgement* that this
  blocks rather than admits an obvious reading is mine.
- **My guess at the intended shape, offered only so a ruling has something to
  reject:** origins carry module-level information (either module paths, or
  both namespaces), because the only declared consumer needs modules and
  because bare `import pkg.mod` — named explicitly in that consumer's own
  line — has no symbol to resolve to. I did **not** implement this.
- **`import_origins(index, module)` most likely maps a dotted module to its
  own file's bindings** (parameter named `module`, table keyed by `file`, so
  the function is where `module_path(rel)` gets inverted). But report 005's
  phrase *"importer-set consumption via import_origins"* reads the other way —
  "which files import this module" — and the `list[str]` return cannot
  distinguish the two. Genuinely 50/50; this is blocking request_mem line 2.
- **If origins end up as lists inside the index, sort them.** Bullet 1 is
  attested today and `serialize()` sorts dict keys only, so an unsorted list
  would silently regress a bullet I have already signed. Sorted-by-name for
  entries and sorted for origins is my expectation, not a rule I was given.

## Sequencing note for the resumer

`affected_symbols` (3d-2) is downstream of the ruling on D-3d1-1, not merely
downstream of this code. 3t's seven blind fixtures are already on disk as its
acceptance criteria; if the origin shape is decided in a way that makes
`callers_unknowable` unable to see module imports, those fixtures will fail
for a spec reason rather than an implementation one. Worth deciding D-3d1-1
with 3d-2's fixtures open.

## Read disclosure

Before writing anything I read `analyzer/refs.py` lines 1-270 (outside the
write scope; a module `analyzer/indexer.py` already imports from). No
implementation was derived from it and D-3d1-1's evidence deliberately does
not depend on it. Filed as D-3d1-3 because the packet defines no read fence
and the pre-dispatch probe for this same node read the same sentence the
opposite way. A resumer should not treat my read as precedent until it is
ruled on.
packet: node=index_assembly role=executor commit=f146eb16d654cc25fdba3858ea6b393cc833b188 plan=66e648664216 packet_hash=c8242f97dc1c
