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
  - analyzer.indexer.build_index(repo: str | Path, commit: str | None) -> dict
  - analyzer.indexer.serialize(index: dict) -> str
  - analyzer.indexer.load_index(path: str | Path) -> dict
  - analyzer.indexer.IndexLoadError(Exception)
  - analyzer.symbols.extract_symbols(source: bytes, rel_path: str) -> list[dict]
open (undecided — TODO, do not resolve by expanding scope):
  - Nested functions as their own symbols, or folded into the parent?
  - Index module level constants?

delta [compiled at dispatch from surface x index — surface is what makes the delta computable; it is never spec-authored and never handoff-carried]:
  writes:
    - analyzer/modpath.py: exists@f585b83b
    - analyzer/symbols.py: exists@76414ffb
    - analyzer/indexer.py: exists@881b930a
  surface:
    - analyzer.indexer.build_index(repo: str | Path, commit: str | None) -> dict: present
    - analyzer.indexer.serialize(index: dict) -> str: present
    - analyzer.indexer.load_index(path: str | Path) -> dict: present
    - analyzer.indexer.IndexLoadError(Exception): present
    - analyzer.symbols.extract_symbols(source: bytes, rel_path: str) -> list[dict]: present
  => empty delta — validation-only dispatch

## State — compiled  [provenance: verified at baad6d55691a42e3e0208372c1e408ba114b33d1]

### Write scope as it exists

#### analyzer/modpath.py
- analyzer.modpath.module_path  [function, confidence high]  lines 4-8
  signature: (rel_path: str) -> str

source (verbatim at baad6d55691a42e3e0208372c1e408ba114b33d1):
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
- analyzer.symbols._hash  [function, confidence high]  lines 22-23
  signature: (text: str) -> str
- analyzer.symbols._kind  [function, confidence high]  lines 104-109
  signature: (node: ast.AST) -> str
- analyzer.symbols._param  [function, confidence high]  lines 26-28
  signature: (arg: ast.arg, has_default: bool) -> str
- analyzer.symbols._param_display  [function, confidence high]  lines 63-70
  signature: (arg: ast.arg, default: ast.AST | None) -> str
- analyzer.symbols._sig_canonical  [function, confidence high]  lines 31-60
  signature: (node: ast.AST) -> str
- analyzer.symbols._signature_display  [function, confidence high]  lines 73-94
  signature: (node: ast.AST) -> str
- analyzer.symbols._visit  [function, confidence high]  lines 128-162
  signature: (node: ast.AST, prefix: str, rel_path: str, records: list[dict]) -> None
- analyzer.symbols.extract_from_tree  [function, confidence high]  lines 120-125
  signature: (tree: ast.Module, rel_path: str) -> list[dict]
- analyzer.symbols.extract_symbols  [function, confidence high]  lines 112-117
  signature: (source: bytes, rel_path: str) -> list[dict]

source (verbatim at baad6d55691a42e3e0208372c1e408ba114b33d1):
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
   104  def _kind(node: ast.AST) -> str:
   105      if isinstance(node, ast.ClassDef):
   106          return "class"
   107      if isinstance(node, ast.AsyncFunctionDef):
   108          return "async_function"
   109      return "function"
   110  
   111  
   112  def extract_symbols(source: bytes, rel_path: str) -> list[dict]:
   113      try:
   114          tree = ast.parse(source)
   115      except (SyntaxError, ValueError) as e:
   116          raise ParseFailure(rel_path, e) from e
   117      return extract_from_tree(tree, rel_path)
   118  
   119  
   120  def extract_from_tree(tree: ast.Module, rel_path: str) -> list[dict]:
   121      records: list[dict] = []
   122      # TODO(brief open question): module-level constants are not indexed as
   123      # symbols; only def/async def/class produce records.
   124      _visit(tree, module_path(rel_path), rel_path, records)
   125      return records
   126  
   127  
   128  def _visit(node: ast.AST, prefix: str, rel_path: str, records: list[dict]) -> None:
   129      for child in ast.iter_child_nodes(node):
   130          if isinstance(child, _DEF_NODES):
   131              path = f"{prefix}.{child.name}"
   132              start = child.lineno
   133              if child.decorator_list:
   134                  start = min(start, child.decorator_list[0].lineno)
   135              records.append(
   136                  {
   137                      "path": path,
   138                      "kind": _kind(child),
   139                      "file": rel_path,
   140                      "start_line": start,
   141                      "end_line": child.end_lineno,
   142                      "signature": _signature_display(child),
   143                      "doc": ast.get_docstring(child),
   144                      "sig_hash": _hash(_sig_canonical(child)),
   145                      "body_hash": _body_hash(child),
   146                      # Not part of the brief's identity triple; lets `affected`
   147                      # surface decorator-only edits that both hashes are blind
   148                      # to (plan amendment A9).
   149                      "decor_hash": _hash(
   150                          "\n".join(ast.unparse(d) for d in child.decorator_list)
   151                      ),
   152                      "parent": prefix,
   153                  }
   154              )
   155              # TODO(brief open question): nested functions currently get their
   156              # own entries, dotted through the enclosing function; the
   157              # alternative is folding them into the parent (their source is
   158              # already part of the parent's body_hash either way).
   159              _visit(child, path, rel_path, records)
   160          else:
   161              # Defs inside if/try/with blocks keep the enclosing scope's path.
   162              _visit(child, prefix, rel_path, records)

#### analyzer/indexer.py
- analyzer.indexer.IndexLoadError  [class, confidence high]  lines 201-202
  signature: (Exception)
- analyzer.indexer._is_git_repo  [function, confidence high]  lines 19-24
  signature: (root: Path) -> bool
- analyzer.indexer._worktree_files  [function, confidence high]  lines 27-42
  signature: (root: Path) -> list[str]
- analyzer.indexer.build_index  [function, confidence high]  lines 45-194
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
- analyzer.indexer.load_index  [function, confidence high]  lines 205-215
  signature: (path: str | Path) -> dict
- analyzer.indexer.serialize  [function, confidence high]  lines 197-198
  signature: (index: dict) -> str

source (verbatim at baad6d55691a42e3e0208372c1e408ba114b33d1):
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
    62                 Duplicate dotted paths are legal (property pairs, conditional
    63                 defs); records sharing a path share their referenced_by.
    64        unresolved: sites whose target is statically undecidable — file, line,
    65                 in_symbol, reason (subscript_call | getattr_call |
    66                 attribute_of_call | star_import | dynamic_attribute |
    67                 parse_error | unresolved_import_target), expression.
    68      """
    69      root = Path(repo)
    70      read_failures: list[tuple[str, str]] = []
    71      if commit is not None:
    72          sha = gitio.resolve_commit(root, commit)
    73          files = gitio.list_py_files(root, sha)
    74          blobs = gitio.read_files(root, sha, files)
    75      else:
    76          if not root.is_dir():
    77              raise FileNotFoundError(f"{root} is not a directory")
    78          sha = None
    79          files = _worktree_files(root)
    80          blobs = {}
    81          for rel in files:
    82              try:
    83                  blobs[rel] = (root / rel).read_bytes()
    84              except OSError as exc:
    85                  read_failures.append((rel, str(exc)))
    86          files = [f for f in files if f in blobs]
    87  
    88      symbols_by_path: dict[str, list[dict]] = defaultdict(list)
    89      trees: dict[str, tuple[ast.Module, str]] = {}
    90      unresolved: list[dict] = [
    91          {
    92              "file": rel,
    93              "line": 1,
    94              "in_symbol": module_path(rel),
    95              "reason": "parse_error",
    96              "expression": f"unreadable: {message}",
    97          }
    98          for rel, message in read_failures
    99      ]
   100      # Deep-but-legal trees (chained binops in generated code) can exceed the
   101      # default recursion limit inside ast.unparse or the walkers; give
   102      # headroom and degrade any remaining blowup to a per-file flag.
   103      sys.setrecursionlimit(max(sys.getrecursionlimit(), 10_000))
   104      for rel in files:
   105          mod = module_path(rel)
   106          try:
   107              tree = ast.parse(blobs[rel])
   108              records = extract_from_tree(tree, rel)
   109          except (SyntaxError, ValueError, RecursionError) as exc:
   110              unresolved.append(
   111                  {
   112                      "file": rel,
   113                      "line": 1,
   114                      "in_symbol": mod,
   115                      "reason": "parse_error",
   116                      "expression": "recursion limit exceeded while analyzing"
   117                      if isinstance(exc, RecursionError)
   118                      else str(exc),
   119                  }
   120              )
   121              continue
   122          for record in records:
   123              symbols_by_path[record["path"]].append(record)
   124          trees[rel] = (tree, mod)
   125  
   126      tables = {
   127          mod: ImportTable.from_module(tree, mod, is_package=rel.endswith("__init__.py"))
   128          for rel, (tree, mod) in trees.items()
   129      }
   130      resolver = Resolver(dict(symbols_by_path), tables)
   131  
   132      refs_by_target: dict[str, list[dict]] = defaultdict(list)
   133      for rel in sorted(trees):
   134          tree, mod = trees[rel]
   135          try:
   136              refs, unres = collect_references(tree, rel, mod, resolver)
   137          except RecursionError:
   138              unresolved.append(
   139                  {
   140                      "file": rel,
   141                      "line": 1,
   142                      "in_symbol": mod,
   143                      "reason": "parse_error",
   144                      "expression": "recursion limit exceeded during reference pass",
   145                  }
   146              )
   147              continue
   148          for target, record in refs:
   149              refs_by_target[target].append(record)
   150          unresolved.extend(unres)
   151  
   152      low_confidence_files = {u["file"] for u in unresolved}
   153      symbols_out = []
   154      for path, records in symbols_by_path.items():
   155          callers = sorted(
   156              refs_by_target.get(path, []),
   157              key=lambda r: (
   158                  r["file"],
   159                  r["line"],
   160                  r["in_symbol"],
   161                  r["kind"],
   162                  r.get("note", ""),
   163                  r.get("args", []),
   164              ),
   165          )
   166          for record in records:
   167              out = dict(record)
   168              out["confidence"] = (
   169                  "low" if record["file"] in low_confidence_files else "high"
   170              )
   171              # Duplicate dotted paths are legal (property/setter pairs,
   172              # conditional defs); every record of a path carries the same
   173              # callers because call sites cannot pick between them (plan A6).
   174              out["referenced_by"] = callers
   175              symbols_out.append(out)
   176      symbols_out.sort(
   177          key=lambda s: (
   178              s["path"],
   179              s["file"],
   180              s["start_line"],
   181              s["sig_hash"],
   182              s["body_hash"],
   183          )
   184      )
   185      unresolved.sort(
   186          key=lambda u: (u["file"], u["line"], u["reason"], u["expression"])
   187      )
   188      return {
   189          "version": 1,
   190          "commit": sha,
   191          "files": list(files),
   192          "symbols": symbols_out,
   193          "unresolved": unresolved,
   194      }
   195  
   196  
   197  def serialize(index: dict) -> str:
   198      return json.dumps(index, indent=2, sort_keys=True) + "\n"
   199  
   200  
   201  class IndexLoadError(Exception):
   202      pass
   203  
   204  
   205  def load_index(path: str | Path) -> dict:
   206      try:
   207          with open(path, encoding="utf-8") as fh:
   208              index = json.load(fh)
   209      except FileNotFoundError:
   210          raise
   211      except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
   212          raise IndexLoadError(f"cannot read index {str(path)!r}: {exc}") from exc
   213      if not isinstance(index, dict) or "symbols" not in index or "unresolved" not in index:
   214          raise IndexLoadError(f"{str(path)!r} is not an analyzer index file")
   215      return index

### Interfaces you consume
- analyzer.gitio._git  [function, confidence high]  lines 15-25  [UNDECLARED — owned by affected_symbols, no spec path; spec-quality signal]
  signature: (repo: str | Path, *args: str, input_bytes: bytes | None = None) -> bytes
- analyzer.gitio.list_py_files  [function, confidence high]  lines 32-34  [UNDECLARED — owned by affected_symbols, no spec path; spec-quality signal]
  signature: (repo: str | Path, rev: str) -> list[str]
- analyzer.gitio.read_files  [function, confidence high]  lines 37-53  [UNDECLARED — owned by affected_symbols, no spec path; spec-quality signal]
  signature: (repo: str | Path, rev: str, paths: list[str]) -> dict[str, bytes]
- analyzer.gitio.resolve_commit  [function, confidence high]  lines 28-29  [UNDECLARED — owned by affected_symbols, no spec path; spec-quality signal]
  signature: (repo: str | Path, rev: str) -> str
- analyzer.refs.ImportTable  [class, confidence low]  lines 46-94  [UNDECLARED — owned by reference_map, no spec path; spec-quality signal]
  signature: (none)
- analyzer.refs.ImportTable.from_module  [function, confidence low]  lines 53-60  [UNDECLARED — owned by reference_map, no spec path; spec-quality signal]
  signature: (cls, tree: ast.Module, module_path: str, *, is_package: bool = False) -> 'ImportTable'
- analyzer.refs.Resolver  [class, confidence low]  lines 184-257  [UNDECLARED — owned by reference_map, no spec path; spec-quality signal]
  signature: (none)
- analyzer.refs.collect_references  [function, confidence low]  lines 825-830  [UNDECLARED — owned by reference_map, no spec path; spec-quality signal]
  signature: (tree: ast.Module, rel_path: str, mod_path: str, resolver: Resolver) -> tuple[list[tuple[str, dict]], list[dict]]
- harness.speccc.load  [function, confidence high]  lines 24-37  [unowned file] [ambiguous attribution — edge known only by name match]
  signature: (spec_dir)

### Callers of your write scope
- analyzer.indexer.IndexLoadError <- analyzer/cli.py:8 in analyzer.cli
- analyzer.indexer.IndexLoadError <- analyzer/cli.py:38 in analyzer.cli._load
- analyzer.indexer.build_index <- analyzer/affected.py:22 in analyzer.affected
- analyzer.indexer.build_index <- analyzer/affected.py:73 in analyzer.affected.compute_affected args=(repo, old_sha)
- analyzer.indexer.build_index <- analyzer/affected.py:74 in analyzer.affected.compute_affected args=(repo, new_sha)
- analyzer.indexer.build_index <- analyzer/cli.py:8 in analyzer.cli
- analyzer.indexer.build_index <- analyzer/cli.py:13 in analyzer.cli._cmd_index args=(args.repo, args.commit)
- analyzer.indexer.build_index <- harness/join.py:22 in harness.join
- analyzer.indexer.build_index <- harness/join.py:743 in harness.join._cmd_plan args=(args.repo, args.commit)
- analyzer.indexer.build_index <- harness/join.py:777 in harness.join._cmd_packet args=(args.repo, commit)
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
- analyzer.indexer.build_index <- tests/test_join.py:522 in tests.test_join.test_delta_empty_when_everything_present args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:537 in tests.test_join.test_delta_full_on_greenfield args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:553 in tests.test_join.test_delta_signature_mismatch args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:565 in tests.test_join.test_delta_without_surface_not_computable args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:574 in tests.test_join.test_executor_packet_carries_delta_block args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:589 in tests.test_join.test_tester_packet_carries_surface_only args=(repo, None)
- analyzer.indexer.build_index <- tests/test_join.py:624 in tests.test_join.test_real_spec_resolves_against_this_repo args=(PROJECT_ROOT, None)
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
- analyzer.symbols.ParseFailure <- tests/test_symbols.py:148 in tests.test_symbols.test_parse_failure_raises
- analyzer.symbols.extract_symbols <- tests/test_refs.py:11 in tests.test_refs
- analyzer.symbols.extract_symbols <- tests/test_refs.py:146 in tests.test_refs.build args=(src.encode(), rel)
- analyzer.symbols.extract_symbols <- tests/test_symbols.py:3 in tests.test_symbols
- analyzer.symbols.extract_symbols <- tests/test_symbols.py:7 in tests.test_symbols.syms args=(source.encode(), rel_path)
- analyzer.symbols.extract_symbols <- tests/test_symbols.py:131 in tests.test_symbols.test_duplicate_paths_both_kept args=('class C:\n    @property\n    def value(self):\n        return self._v\n    @value.setter\n    def value(self, v):\n        self._v = v\n'.encode(), 'src/config.py')
- analyzer.symbols.extract_symbols <- tests/test_symbols.py:149 in tests.test_symbols.test_parse_failure_raises args=(b'def broken(:\n', 'src/bad.py')
- analyzer.symbols.extract_symbols <- tests/test_unresolved.py:6 in tests.test_unresolved
- analyzer.symbols.extract_symbols <- tests/test_unresolved.py:13 in tests.test_unresolved.unresolved_in args=(source.encode(), rel_path)

### Unresolved sites in scope
(none)

### Coverage
Compiled from an index of 25 files at baad6d55691a42e3e0208372c1e408ba114b33d1. This packet includes your write scope (3 entries), 9 consumed/available interface symbols, and every recorded caller of your scope. Anything not listed was not searched. Missing means query (request_mem), never build. verify with: python -m pytest

## State — handoff  [provenance: agent-authored, claim not fact]

(none for this dispatch)
packet: node=symbol_table role=executor commit=baad6d55691a42e3e0208372c1e408ba114b33d1 plan=8183a526ab88 packet_hash=3ac8cdc9e75b
