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

node: symbol_table
language: python
observed_through: the value returned by the surface callable, unless a done_when bullet names a rendering callable explicitly
one_liner: Extracts every function and class from Python source with its location, signature, and separate hashes for signature and body.
write scope (exhaustive — writing anything else is a violation):
  - analyzer/modpath.py
  - analyzer/symbols.py
surface (the exported contract done_when is tested through):
  callables:
    - analyzer.symbols.extract_symbols(source: bytes, rel_path: str) -> list[dict]  [seeded]
    - analyzer.modpath.module_path(rel_path: str) -> str  [seeded]
  types:
    - analyzer.symbols.extract_symbols: each returned record carries path, kind, file, start_line, end_line, signature, doc, sig_hash, body_hash, decor_hash and parent; class records add fields. The index layer adds confidence and referenced_by downstream.  [authored]
    - analyzer.affected.Row.path: the affected symbol's dotted path; one row per affected symbol path  [authored]  [from affected_symbols]
    - analyzer.indexer.record(path: str, kind: str, file: str, start_line: int, end_line: int, signature: str, doc: str | None, sig_hash: str, body_hash: str, decor_hash: str, parent: str, confidence: str, referenced_by: list; class records add fields: list)  [authored]  [from index_assembly]
  errors:
    - analyzer.symbols.ParseFailure: raised by extract_symbols when source does not parse; the index layer instead records an unresolved site with reason parse_error  [seeded]
open (undecided — TODO, do not resolve by expanding scope):
  - Nested functions as their own symbols, or folded into the parent?
  - Index module level constants?
done_when (attest against, or file against, on a validation-only dispatch):
  - Reformatting whitespace does not change the body hash.
  - Ranges are recomputed per commit, never stored as identity.

delta [compiled at dispatch from surface x index — surface is what makes the delta computable; it is never spec-authored and never handoff-carried]:
  writes:
    - analyzer/modpath.py: exists@f585b83b
    - analyzer/symbols.py: exists@b3689cbc
  callables:
    - analyzer.symbols.extract_symbols(source: bytes, rel_path: str) -> list[dict]  [seeded]: present
    - analyzer.modpath.module_path(rel_path: str) -> str  [seeded]: present
  types:
    - analyzer.symbols.extract_symbols: each returned record carries path, kind, file, start_line, end_line, signature, doc, sig_hash, body_hash, decor_hash and parent; class records add fields. The index layer adds confidence and referenced_by downstream.  [authored]: authored (contract — tester-verified, delta-exempt)
  errors:
    - analyzer.symbols.ParseFailure: raised by extract_symbols when source does not parse; the index layer instead records an unresolved site with reason parse_error  [seeded]: present
  => empty delta — validation-only dispatch

## State — compiled  [provenance: verified at 9d3bc13c0611b8bea23658237a755960245344bb]

### Write scope as it exists

#### analyzer/modpath.py
- analyzer.modpath.module_path  [function, confidence high]  lines 4-8
  signature: (rel_path: str) -> str

source (verbatim at 9d3bc13c0611b8bea23658237a755960245344bb):
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

source (verbatim at 9d3bc13c0611b8bea23658237a755960245344bb):
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

### Interfaces you consume
(none recorded)

### Callers of your write scope
- analyzer.modpath.module_path <- analyzer/affected.py:23 in analyzer.affected
- analyzer.modpath.module_path <- analyzer/affected.py:96 in analyzer.affected._importer_files args=(f)
- analyzer.modpath.module_path <- analyzer/indexer.py:12 in analyzer.indexer
- analyzer.modpath.module_path <- analyzer/indexer.py:65 in analyzer.indexer._defining_modules args=(r['file'])
- analyzer.modpath.module_path <- analyzer/indexer.py:198 in analyzer.indexer.build_index args=(rel)
- analyzer.modpath.module_path <- analyzer/indexer.py:209 in analyzer.indexer.build_index args=(rel)
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
- analyzer.symbols.extract_from_tree <- analyzer/indexer.py:19 in analyzer.indexer
- analyzer.symbols.extract_from_tree <- analyzer/indexer.py:212 in analyzer.indexer.build_index args=(tree, rel)
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
Compiled from an index of 60 files at 9d3bc13c0611b8bea23658237a755960245344bb. This packet includes your write scope (2 entries), 0 consumed/available interface symbols, and every recorded caller of your scope. Anything not listed was not searched. Missing means query (request_mem), never build. verify with: .venv/bin/python -m pytest

## State — handoff  [provenance: agent-authored, claim not fact]

(none for this dispatch)
packet: node=symbol_table role=executor commit=9d3bc13c0611b8bea23658237a755960245344bb plan=66e648664216 packet_hash=48344a19274d
