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

node: symbol_table
one_liner: Walks a Python repo at a commit and records every function and class with its location, signature, and separate hashes for signature and body.
write scope (exhaustive — writing anything else is a violation):
  - analyzer/modpath.py
  - analyzer/symbols.py
  - analyzer/indexer.py
surface (the exported contract done_when is tested through):
  callables:
    - analyzer.indexer.build_index(repo: str | Path, commit: str | None) -> dict
    - analyzer.indexer.serialize(index: dict) -> str
    - analyzer.indexer.load_index(path: str | Path) -> dict
    - analyzer.symbols.extract_symbols(source: bytes, rel_path: str) -> list[dict]
  types:
    (none declared)
  errors:
    - analyzer.symbols.ParseFailure: raised by extract_symbols when source does not parse; build_index instead records an unresolved site with reason parse_error
    - analyzer.indexer.IndexLoadError: raised by load_index when the index file is unreadable or not an analyzer index; a missing file raises FileNotFoundError unchanged
open (undecided — TODO, do not resolve by expanding scope):
  - Nested functions as their own symbols, or folded into the parent?
  - Index module level constants?
done_when (attest against, or file against, on a validation-only dispatch):
  - Indexing the same commit twice produces byte identical output.
  - Given a symbol path, returns its definition and signature.
  - Reformatting whitespace does not change the body hash.
  - Ranges are recomputed per commit, never stored as identity.

delta [compiled at dispatch from surface x index — surface is what makes the delta computable; it is never spec-authored and never handoff-carried]:
  writes:
    - analyzer/modpath.py: exists@f585b83b
    - analyzer/symbols.py: exists@b3689cbc
    - analyzer/indexer.py: exists@8a42ca02
  callables:
    - analyzer.indexer.build_index(repo: str | Path, commit: str | None) -> dict: present
    - analyzer.indexer.serialize(index: dict) -> str: present
    - analyzer.indexer.load_index(path: str | Path) -> dict: present
    - analyzer.symbols.extract_symbols(source: bytes, rel_path: str) -> list[dict]: present
  errors:
    - analyzer.symbols.ParseFailure: raised by extract_symbols when source does not parse; build_index instead records an unresolved site with reason parse_error: present
    - analyzer.indexer.IndexLoadError: raised by load_index when the index file is unreadable or not an analyzer index; a missing file raises FileNotFoundError unchanged: present
  => empty delta — validation-only dispatch

## State — compiled  [provenance: verified at a238cce945102dff2b5c26834eddae41972b26bb]

### Write scope as it exists

#### analyzer/modpath.py
- analyzer.modpath.module_path  [function, confidence high]  lines 4-8
  signature: (rel_path: str) -> str

source (verbatim at a238cce945102dff2b5c26834eddae41972b26bb):
     1  """File path -> dotted module path, relative to the indexed repo root."""
     2  
     3  
     4  def module_path(rel_path: str) -> str:
     5      parts = rel_path.removesuffix(".py").split("/")
     6      if parts[-1] == "__init__":
     7          parts.pop()
     8      return ".".join(parts)

#### analyzer/symbols.py
- analyzer.symbols.ParseFailure  [class, confidence high]  lines 15-19
  signature: (Exception)
- analyzer.symbols.ParseFailure.__init__  [function, confidence high]  lines 16-19
  signature: (self, rel_path: str, error: Exception)
- analyzer.symbols._body_hash  [function, confidence high]  lines 97-101
  signature: (node: ast.AST) -> str
- analyzer.symbols._class_fields  [function, confidence high]  lines 104-115
  signature: (node: ast.ClassDef) -> list[str]
  doc: Annotated class-body targets in body order, rendered like parameters
    (`name: annotation = default`, defaults verbatim) — the field list a
    spec surface's type entry seeds from.
- analyzer.symbols._hash  [function, confidence high]  lines 22-23
  signature: (text: str) -> str
- analyzer.symbols._kind  [function, confidence high]  lines 118-123
  signature: (node: ast.AST) -> str
- analyzer.symbols._param  [function, confidence high]  lines 26-28
  signature: (arg: ast.arg, has_default: bool) -> str
- analyzer.symbols._param_display  [function, confidence high]  lines 63-70
  signature: (arg: ast.arg, default: ast.AST | None) -> str
- analyzer.symbols._sig_canonical  [function, confidence high]  lines 31-60
  signature: (node: ast.AST) -> str
- analyzer.symbols._signature_display  [function, confidence high]  lines 73-94
  signature: (node: ast.AST) -> str
- analyzer.symbols._visit  [function, confidence high]  lines 142-177
  signature: (node: ast.AST, prefix: str, rel_path: str, records: list[dict]) -> None
- analyzer.symbols.extract_from_tree  [function, confidence high]  lines 134-139
  signature: (tree: ast.Module, rel_path: str) -> list[dict]
- analyzer.symbols.extract_symbols  [function, confidence high]  lines 126-131
  signature: (source: bytes, rel_path: str) -> list[dict]

source (verbatim at a238cce945102dff2b5c26834eddae41972b26bb):
     1  """Pass 1: walk one file's AST and emit a symbol record per definition.
     2  
     3  Records here carry everything except `confidence` and `referenced_by`,
     4  which the indexer merges in after pass 2.
     5  """
     6  
     7  import ast
     8  import hashlib
     9  
    10  from analyzer.modpath import module_path
    11  
    12  _DEF_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    13  
    14  
    15  class ParseFailure(Exception):
    16      def __init__(self, rel_path: str, error: Exception):
    17          super().__init__(f"{rel_path}: {error}")
    18          self.rel_path = rel_path
    19          self.error = error
    20  
    21  
    22  def _hash(text: str) -> str:
    23      return hashlib.sha256(text.encode()).hexdigest()[:8]
    24  
    25  
    26  def _param(arg: ast.arg, has_default: bool) -> str:
    27      ann = ast.unparse(arg.annotation) if arg.annotation else ""
    28      return f"{arg.arg}:{ann}:{'=' if has_default else ''}"
    29  
    30  
    31  def _sig_canonical(node: ast.AST) -> str:
    32      # Identity covers: name, parameter names, parameter annotations, defaults
    33      # PRESENCE (not values), return annotation (brief §1). Documented
    34      # deviation (plan A11): positional-only "/", bare "*" and */** markers are
    35      # included too — f(a, b) -> f(a, *, b) breaks call sites and must not
    36      # classify as merely "moved".
    37      if isinstance(node, ast.ClassDef):
    38          # Class analog: bases and keywords (metaclass) are its "parameters" —
    39          # changing a base changes what callers get, so it is signature-level.
    40          parts = [ast.unparse(b) for b in node.bases]
    41          parts += [f"{kw.arg}={ast.unparse(kw.value)}" for kw in node.keywords]
    42          return f"{node.name}({','.join(parts)})"
    43      a = node.args
    44      pos = a.posonlyargs + a.args
    45      first_default = len(pos) - len(a.defaults)
    46      parts = [_param(arg, i >= first_default) for i, arg in enumerate(pos)]
    47      if a.posonlyargs:
    48          parts.insert(len(a.posonlyargs), "/")
    49      if a.vararg:
    50          parts.append("*" + _param(a.vararg, False))
    51      elif a.kwonlyargs:
    52          parts.append("*")
    53      parts += [
    54          _param(arg, default is not None)
    55          for arg, default in zip(a.kwonlyargs, a.kw_defaults)
    56      ]
    57      if a.kwarg:
    58          parts.append("**" + _param(a.kwarg, False))
    59      ret = ast.unparse(node.returns) if node.returns else ""
    60      return f"{node.name}({','.join(parts)})->{ret}"
    61  
    62  
    63  def _param_display(arg: ast.arg, default: ast.AST | None) -> str:
    64      out = arg.arg
    65      if arg.annotation:
    66          out += f": {ast.unparse(arg.annotation)}"
    67      if default is not None:
    68          # PEP 8: spaces around = only when the parameter is annotated.
    69          out += f" = {ast.unparse(default)}" if arg.annotation else f"={ast.unparse(default)}"
    70      return out
    71  
    72  
    73  def _signature_display(node: ast.AST) -> str:
    74      if isinstance(node, ast.ClassDef):
    75          parts = [ast.unparse(b) for b in node.bases]
    76          parts += [f"{kw.arg}={ast.unparse(kw.value)}" for kw in node.keywords]
    77          return f"({', '.join(parts)})" if parts else ""
    78      a = node.args
    79      pos = a.posonlyargs + a.args
    80      defaults = [None] * (len(pos) - len(a.defaults)) + list(a.defaults)
    81      parts = [_param_display(arg, d) for arg, d in zip(pos, defaults)]
    82      if a.posonlyargs:
    83          parts.insert(len(a.posonlyargs), "/")
    84      if a.vararg:
    85          parts.append("*" + _param_display(a.vararg, None))
    86      elif a.kwonlyargs:
    87          parts.append("*")
    88      parts += [_param_display(arg, d) for arg, d in zip(a.kwonlyargs, a.kw_defaults)]
    89      if a.kwarg:
    90          parts.append("**" + _param_display(a.kwarg, None))
    91      sig = f"({', '.join(parts)})"
    92      if node.returns:
    93          sig += f" -> {ast.unparse(node.returns)}"
    94      return sig
    95  
    96  
    97  def _body_hash(node: ast.AST) -> str:
    98      # Unparsing the AST drops comments/blank lines/formatting for free
    99      # (brief, notes for the implementer). Docstrings are body, not comments,
   100      # so they participate.
   101      return _hash("\n".join(ast.unparse(stmt) for stmt in node.body))
   102  
   103  
   104  def _class_fields(node: ast.ClassDef) -> list[str]:
   105      """Annotated class-body targets in body order, rendered like parameters
   106      (`name: annotation = default`, defaults verbatim) — the field list a
   107      spec surface's type entry seeds from."""
   108      fields = []
   109      for stmt in node.body:
   110          if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
   111              rendered = f"{stmt.target.id}: {ast.unparse(stmt.annotation)}"
   112              if stmt.value is not None:
   113                  rendered += f" = {ast.unparse(stmt.value)}"
   114              fields.append(rendered)
   115      return fields
   116  
   117  
   118  def _kind(node: ast.AST) -> str:
   119      if isinstance(node, ast.ClassDef):
   120          return "class"
   121      if isinstance(node, ast.AsyncFunctionDef):
   122          return "async_function"
   123      return "function"
   124  
   125  
   126  def extract_symbols(source: bytes, rel_path: str) -> list[dict]:
   127      try:
   128          tree = ast.parse(source)
   129      except (SyntaxError, ValueError) as e:
   130          raise ParseFailure(rel_path, e) from e
   131      return extract_from_tree(tree, rel_path)
   132  
   133  
   134  def extract_from_tree(tree: ast.Module, rel_path: str) -> list[dict]:
   135      records: list[dict] = []
   136      # TODO(brief open question): module-level constants are not indexed as
   137      # symbols; only def/async def/class produce records.
   138      _visit(tree, module_path(rel_path), rel_path, records)
   139      return records
   140  
   141  
   142  def _visit(node: ast.AST, prefix: str, rel_path: str, records: list[dict]) -> None:
   143      for child in ast.iter_child_nodes(node):
   144          if isinstance(child, _DEF_NODES):
   145              path = f"{prefix}.{child.name}"
   146              start = child.lineno
   147              if child.decorator_list:
   148                  start = min(start, child.decorator_list[0].lineno)
   149              record = {
   150                      "path": path,
   151                      "kind": _kind(child),
   152                      "file": rel_path,
   153                      "start_line": start,
   154                      "end_line": child.end_lineno,
   155                      "signature": _signature_display(child),
   156                      "doc": ast.get_docstring(child),
   157                      "sig_hash": _hash(_sig_canonical(child)),
   158                      "body_hash": _body_hash(child),
   159                      # Not part of the brief's identity triple; lets `affected`
   160                      # surface decorator-only edits that both hashes are blind
   161                      # to (plan amendment A9).
   162                      "decor_hash": _hash(
   163                          "\n".join(ast.unparse(d) for d in child.decorator_list)
   164                      ),
   165                      "parent": prefix,
   166                  }
   167              if isinstance(child, ast.ClassDef):
   168                  record["fields"] = _class_fields(child)
   169              records.append(record)
   170              # TODO(brief open question): nested functions currently get their
   171              # own entries, dotted through the enclosing function; the
   172              # alternative is folding them into the parent (their source is
   173              # already part of the parent's body_hash either way).
   174              _visit(child, path, rel_path, records)
   175          else:
   176              # Defs inside if/try/with blocks keep the enclosing scope's path.
   177              _visit(child, prefix, rel_path, records)

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

source (verbatim at a238cce945102dff2b5c26834eddae41972b26bb):
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
- analyzer.refs.ImportTable  [class, confidence low]  lines 46-94  [UNDECLARED — owned by reference_map, no spec path; spec-quality signal]
  signature: (none)
- analyzer.refs.ImportTable.from_module  [function, confidence low]  lines 53-60  [UNDECLARED — owned by reference_map, no spec path; spec-quality signal]
  signature: (cls, tree: ast.Module, module_path: str, *, is_package: bool = False) -> 'ImportTable'
- analyzer.refs.Resolver  [class, confidence low]  lines 184-257  [UNDECLARED — owned by reference_map, no spec path; spec-quality signal]
  signature: (none)
- analyzer.refs.collect_references  [function, confidence low]  lines 825-830  [UNDECLARED — owned by reference_map, no spec path; spec-quality signal]
  signature: (tree: ast.Module, rel_path: str, mod_path: str, resolver: Resolver) -> tuple[list[tuple[str, dict]], list[dict]]
- harness.speccc.load  [function, confidence high]  lines 27-40  [unowned file] [ambiguous attribution — edge known only by name match]
  signature: (spec_dir)

### Callers of your write scope
- analyzer.indexer.IndexLoadError <- analyzer/cli.py:8 in analyzer.cli
- analyzer.indexer.IndexLoadError <- analyzer/cli.py:38 in analyzer.cli._load
- analyzer.indexer.build_index <- analyzer/affected.py:22 in analyzer.affected
- analyzer.indexer.build_index <- analyzer/affected.py:73 in analyzer.affected.compute_affected args=(repo, old_sha)
- analyzer.indexer.build_index <- analyzer/affected.py:74 in analyzer.affected.compute_affected args=(repo, new_sha)
- analyzer.indexer.build_index <- analyzer/cli.py:8 in analyzer.cli
- analyzer.indexer.build_index <- analyzer/cli.py:13 in analyzer.cli._cmd_index args=(args.repo, args.commit)
- analyzer.indexer.build_index <- harness/join.py:23 in harness.join
- analyzer.indexer.build_index <- harness/join.py:887 in harness.join._cmd_plan args=(args.repo, args.commit)
- analyzer.indexer.build_index <- harness/join.py:921 in harness.join._cmd_packet args=(args.repo, commit)
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
- analyzer.indexer.build_index <- tests/test_join.py:7 in tests.test_join
- analyzer.indexer.build_index <- tests/test_join.py:60 in tests.test_join.joined args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:102 in tests.test_join.test_escaping_path_is_e06 args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:248 in tests.test_join.real_packet args=(PROJECT_ROOT, None)
- analyzer.indexer.build_index <- tests/test_join.py:306 in tests.test_join.test_to_create_rendered_in_packet args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:377 in tests.test_join.test_degenerate_writes_entry_is_e06 args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:540 in tests.test_join.test_delta_empty_when_everything_present args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:559 in tests.test_join.test_delta_full_on_greenfield args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:576 in tests.test_join.test_delta_signature_mismatch args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:592 in tests.test_join.test_delta_type_shape_mismatch args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:613 in tests.test_join.test_delta_constructor_shaped_type_matches_init args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:626 in tests.test_join.test_delta_alias_type_is_unindexed_never_outstanding args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:641 in tests.test_join.test_delta_error_via_field_path args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:655 in tests.test_join.test_delta_error_condition_may_contain_colons args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:675 in tests.test_join.test_delta_without_surface_not_computable args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:684 in tests.test_join.test_executor_packet_carries_delta_block args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:699 in tests.test_join.test_executor_done_when_sits_above_delta args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:718 in tests.test_join.test_foreign_type_resolves_from_owning_node args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:731 in tests.test_join.test_tester_packet_carries_surface_only args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:766 in tests.test_join.test_real_spec_resolves_against_this_repo args=(PROJECT_ROOT, None)
- analyzer.indexer.load_index <- analyzer/cli.py:8 in analyzer.cli
- analyzer.indexer.load_index <- analyzer/cli.py:31 in analyzer.cli._load args=(args.index)
- analyzer.indexer.serialize <- analyzer/cli.py:8 in analyzer.cli
- analyzer.indexer.serialize <- analyzer/cli.py:18 in analyzer.cli._cmd_index args=(index)
- analyzer.indexer.serialize <- tests/test_indexer.py:1 in tests.test_indexer
- analyzer.indexer.serialize <- tests/test_indexer.py:65 in tests.test_indexer.test_serialize_deterministic args=(build_index(repo, None))
- analyzer.indexer.serialize <- tests/test_indexer.py:66 in tests.test_indexer.test_serialize_deterministic args=(build_index(repo, None))
- analyzer.modpath.module_path <- tests/test_modpath.py:1 in tests.test_modpath
- analyzer.modpath.module_path <- tests/test_modpath.py:5 in tests.test_modpath.test_plain_module args=('src/config.py')
- analyzer.modpath.module_path <- tests/test_modpath.py:9 in tests.test_modpath.test_top_level_module args=('main.py')
- analyzer.modpath.module_path <- tests/test_modpath.py:13 in tests.test_modpath.test_package_init args=('pkg/__init__.py')
- analyzer.modpath.module_path <- tests/test_modpath.py:17 in tests.test_modpath.test_nested_package_init args=('a/b/__init__.py')
- analyzer.modpath.module_path <- tests/test_refs.py:4 in tests.test_refs
- analyzer.modpath.module_path <- tests/test_refs.py:144 in tests.test_refs.build args=(rel)
- analyzer.modpath.module_path <- tests/test_unresolved.py:4 in tests.test_unresolved
- analyzer.modpath.module_path <- tests/test_unresolved.py:10 in tests.test_unresolved.unresolved_in args=(rel_path)
- analyzer.symbols.ParseFailure <- tests/test_symbols.py:3 in tests.test_symbols
- analyzer.symbols.ParseFailure <- tests/test_symbols.py:179 in tests.test_symbols.test_parse_failure_raises
- analyzer.symbols.extract_symbols <- tests/test_refs.py:11 in tests.test_refs
- analyzer.symbols.extract_symbols <- tests/test_refs.py:146 in tests.test_refs.build args=(src.encode(), rel)
- analyzer.symbols.extract_symbols <- tests/test_symbols.py:3 in tests.test_symbols
- analyzer.symbols.extract_symbols <- tests/test_symbols.py:7 in tests.test_symbols.syms args=(source.encode(), rel_path)
- analyzer.symbols.extract_symbols <- tests/test_symbols.py:162 in tests.test_symbols.test_duplicate_paths_both_kept args=('class C:\n    @property\n    def value(self):\n        return self._v\n    @value.setter\n    def value(self, v):\n        self._v = v\n'.encode(), 'src/config.py')
- analyzer.symbols.extract_symbols <- tests/test_symbols.py:180 in tests.test_symbols.test_parse_failure_raises args=(b'def broken(:\n', 'src/bad.py')
- analyzer.symbols.extract_symbols <- tests/test_unresolved.py:6 in tests.test_unresolved
- analyzer.symbols.extract_symbols <- tests/test_unresolved.py:13 in tests.test_unresolved.unresolved_in args=(source.encode(), rel_path)

### Unresolved sites in scope
(none)

### Coverage
Compiled from an index of 25 files at a238cce945102dff2b5c26834eddae41972b26bb. This packet includes your write scope (3 entries), 11 consumed/available interface symbols, and every recorded caller of your scope. Anything not listed was not searched. Missing means query (request_mem), never build. verify with: python -m pytest

## State — handoff  [provenance: agent-authored, claim not fact]

(none for this dispatch)
packet: node=symbol_table role=executor commit=a238cce945102dff2b5c26834eddae41972b26bb plan=c98fb664a54f packet_hash=801f3c0502f6
