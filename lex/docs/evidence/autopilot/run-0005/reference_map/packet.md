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

node: reference_map
language: python
observed_through: the value returned by the surface callable, unless a done_when bullet names a rendering callable explicitly
one_liner: Records every site that references each symbol, with the arguments as written at the call site.
write scope (exhaustive — writing anything else is a violation):
  - analyzer/refs.py
surface (the exported contract done_when is tested through):
  callables:
    - analyzer.refs.collect_references(tree: ast.Module, rel_path: str, mod_path: str, resolver: Resolver) -> tuple[list[tuple[str, dict]], list[dict]]  [seeded]
    - analyzer.refs.ImportTable.from_module(cls, tree: ast.Module, module_path: str, *, is_package: bool = False) -> 'ImportTable'  [seeded]
    - analyzer.refs.scope_statements(body)  [seeded]
  types:
    - analyzer.refs.Resolver(symbols: dict[str, list[dict]], tables: dict[str, 'ImportTable'])  [seeded]
    - analyzer.refs.ImportTable(module_path: str, *, is_package: bool = False)  [seeded]
  errors:
    (none declared)
done_when (attest against, or file against, on a validation-only dispatch):
  - Given a symbol, returns every caller with file, line, and enclosing symbol.
  - Call site arguments are recorded as written, never traced to their origin.
  - Ambiguous matches are recorded as ambiguous rather than dropped.

delta [compiled at dispatch from surface x index — surface is what makes the delta computable; it is never spec-authored and never handoff-carried]:
  writes:
    - analyzer/refs.py: exists@c80ec692
  callables:
    - analyzer.refs.collect_references(tree: ast.Module, rel_path: str, mod_path: str, resolver: Resolver) -> tuple[list[tuple[str, dict]], list[dict]]  [seeded]: present
    - analyzer.refs.ImportTable.from_module(cls, tree: ast.Module, module_path: str, *, is_package: bool = False) -> 'ImportTable'  [seeded]: present
    - analyzer.refs.scope_statements(body)  [seeded]: present
  types:
    - analyzer.refs.Resolver(symbols: dict[str, list[dict]], tables: dict[str, 'ImportTable'])  [seeded]: present
    - analyzer.refs.ImportTable(module_path: str, *, is_package: bool = False)  [seeded]: present
  => empty delta — validation-only dispatch

## State — compiled  [provenance: verified at c734ce52451af00181b7264d81573c4029096964]

### Write scope as it exists

#### analyzer/refs.py
- analyzer.refs.ImportTable  [class, confidence low]  lines 58-106
  signature: (none)
- analyzer.refs.ImportTable.__init__  [function, confidence low]  lines 59-63
  signature: (self, module_path: str, *, is_package: bool = False)
- analyzer.refs.ImportTable._bind  [function, confidence low]  lines 100-103
  signature: (self, name: str, target: str) -> None
- analyzer.refs.ImportTable.add  [function, confidence low]  lines 74-89
  signature: (self, stmt: ast.stmt) -> None
- analyzer.refs.ImportTable.base_of  [function, confidence low]  lines 91-98
  signature: (self, stmt: ast.ImportFrom) -> str
  doc: Dotted module the from-import pulls from, relative levels resolved.
- analyzer.refs.ImportTable.from_module  [function, confidence low]  lines 65-72
  signature: (cls, tree: ast.Module, module_path: str, *, is_package: bool = False) -> 'ImportTable'
- analyzer.refs.ImportTable.resolve  [function, confidence low]  lines 105-106
  signature: (self, name: str) -> tuple[str, ...]
- analyzer.refs.Resolver  [class, confidence low]  lines 196-269
  signature: (none)
- analyzer.refs.Resolver.__init__  [function, confidence low]  lines 197-205
  signature: (self, symbols: dict[str, list[dict]], tables: dict[str, 'ImportTable'])
- analyzer.refs.Resolver.is_module  [function, confidence low]  lines 207-208
  signature: (self, dotted: str) -> bool
- analyzer.refs.Resolver.kind_of  [function, confidence low]  lines 267-269
  signature: (self, path: str) -> str | None
- analyzer.refs.Resolver.module_anchor_exists  [function, confidence low]  lines 210-213
  signature: (self, dotted: str) -> bool
  doc: Does this dotted module string plausibly refer to an indexed
    module (exactly, or as a src-layout suffix)?
- analyzer.refs.Resolver.resolve_dotted  [function, confidence low]  lines 218-265
  signature: (self, dotted: str, *, _depth: int = 0, _seen: frozenset = frozenset()) -> list[tuple[str, str | None]]
  doc: Resolve a dotted target to indexed symbol paths.
    
    Returns [(symbol_path, note)] — note None for exact hits, a
    human-readable ambiguity note for suffix matches. Misses through
    re-exports are chased through the target module's own import
    table (pkg/__init__.py facades).
- analyzer.refs.Resolver.terminal_matches  [function, confidence low]  lines 215-216
  signature: (self, name: str) -> list[str]
- analyzer.refs._Frame  [class, confidence low]  lines 285-322
  signature: (none)
- analyzer.refs._Frame.__init__  [function, confidence low]  lines 288-293
  signature: (self, kind: str)
- analyzer.refs._Frame.bind  [function, confidence low]  lines 295-322
  signature: (self, name: str, origin: str, payload=None) -> None
- analyzer.refs._Walker  [class, confidence low]  lines 330-834
  signature: (none)
- analyzer.refs._Walker.__init__  [function, confidence low]  lines 331-341
  signature: (self, rel_path: str, mod_path: str, resolver: Resolver)
- analyzer.refs._Walker._class_frame  [function, confidence low]  lines 395-405
  signature: (self, node: ast.ClassDef, class_path: str) -> _Frame
- analyzer.refs._Walker._enclosing_class  [function, confidence low]  lines 446-450
  signature: (self) -> _Frame | None
- analyzer.refs._Walker._expr_symbol_paths  [function, confidence low]  lines 477-506
  signature: (self, expr) -> list[tuple[str, str | None]]
  doc: Exact-ish symbol paths an expression statically denotes.
- analyzer.refs._Walker._fallback  [function, confidence low]  lines 508-510
  signature: (self, node, terminal: str, kind: str, args, note: str)
- analyzer.refs._Walker._flag  [function, confidence low]  lines 363-378
  signature: (self, node, reason: str, expression: str | None = None)
- analyzer.refs._Walker._function_frame  [function, confidence low]  lines 387-393
  signature: (self, node) -> _Frame
- analyzer.refs._Walker._lookup  [function, confidence low]  lines 433-444
  signature: (self, name: str)
  doc: Find the binding for a name: walks frames innermost-out, skipping
    class frames unless the class body is the current scope (Python
    semantics: class scope does not enclose methods).
- analyzer.refs._Walker._module_frame  [function, confidence low]  lines 382-385
  signature: (self, tree: ast.Module) -> _Frame
- analyzer.refs._Walker._name_targets  [function, confidence low]  lines 452-475
  signature: (self, name: str) -> list[tuple[str, str | None]] | None
  doc: Symbol paths a bare name refers to. None => opaque/unbound.
- analyzer.refs._Walker._populate_scope_frame  [function, confidence low]  lines 407-429
  signature: (self, frame: _Frame, body, prefix: str, *, opaque_assigns: bool = True) -> None
- analyzer.refs._Walker._record  [function, confidence low]  lines 345-361
  signature: (self, node, target: str, kind: str, note: str | None, args=None)
- analyzer.refs._Walker._resolve_attribute_use  [function, confidence low]  lines 512-638
  signature: (self, attr: ast.Attribute, kind: str, args, site)
  doc: Emit references for an attribute chain in Load context. `site` is
    the node whose position anchors the record (the Call for calls).
- analyzer.refs._Walker._visit_Assign  [function, confidence low]  lines 745-755
  signature: (self, node: ast.Assign) -> None
- analyzer.refs._Walker._visit_Attribute  [function, confidence low]  lines 831-834
  signature: (self, node: ast.Attribute) -> None
- analyzer.refs._Walker._visit_Call  [function, confidence low]  lines 784-823
  signature: (self, node: ast.Call) -> None
- analyzer.refs._Walker._visit_ClassDef  [function, confidence low]  lines 688-701
  signature: (self, node: ast.ClassDef) -> None
- analyzer.refs._Walker._visit_FunctionDef  [function, confidence low]  lines 656-672
  signature: (self, node) -> None
- analyzer.refs._Walker._visit_Import  [function, confidence low]  lines 742-743
  signature: (self, node: ast.Import) -> None
- analyzer.refs._Walker._visit_ImportFrom  [function, confidence low]  lines 757-782
  signature: (self, node: ast.ImportFrom) -> None
- analyzer.refs._Walker._visit_Lambda  [function, confidence low]  lines 703-710
  signature: (self, node: ast.Lambda) -> None
- analyzer.refs._Walker._visit_Name  [function, confidence low]  lines 825-829
  signature: (self, node: ast.Name) -> None
- analyzer.refs._Walker._visit_arg_annotations_and_defaults  [function, confidence low]  lines 676-686
  signature: (self, args: ast.arguments) -> None
- analyzer.refs._Walker._visit_comprehension_scope  [function, confidence low]  lines 712-735
  signature: (self, node) -> None
- analyzer.refs._Walker.visit  [function, confidence low]  lines 648-654
  signature: (self, node) -> None
- analyzer.refs._Walker.visit_module  [function, confidence low]  lines 642-646
  signature: (self, tree: ast.Module) -> None
- analyzer.refs._dedupe_resolutions  [function, confidence low]  lines 272-279
  signature: (results: list[tuple[str, str | None]]) -> list[tuple[str, str | None]]
- analyzer.refs._params_of  [function, confidence low]  lines 172-178
  signature: (args: ast.arguments) -> set[str]
- analyzer.refs._scan_opaque  [function, confidence low]  lines 122-169
  signature: (node, opaque: set[str], excluded: set[str], in_comp: bool) -> None
- analyzer.refs._scope_stmts  [function, confidence low]  lines 40-52
  signature: (stmts)
  doc: Yield statements reachable at the same scope level: descends through
    control flow (if/try/for/while/with) but never into defs or classes.
- analyzer.refs._target_names  [function, confidence low]  lines 112-119
  signature: (node, out: set[str]) -> None
- analyzer.refs.collect_references  [function, confidence low]  lines 837-842
  signature: (tree: ast.Module, rel_path: str, mod_path: str, resolver: Resolver) -> tuple[list[tuple[str, dict]], list[dict]]
- analyzer.refs.local_bindings  [function, confidence low]  lines 181-190
  signature: (func_node) -> set[str]
  doc: Names bound opaquely (shadowing) in a function scope: params,
    assignments, loop/with/except/match targets, walrus — minus names
    declared global/nonlocal. Nested defs and local imports are excluded:
    they bind too, but resolvably (def/import origin).
- analyzer.refs.scope_statements  [function, confidence low]  lines 28-37
  signature: (body)
  doc: The statements reachable at one scope level — the same walk the
    import tables are built from.
    
    Public so a consumer can guarantee it sees exactly the statement set
    `ImportTable.from_module` saw. `index_assembly` needed this and reached
    for the private name; the ruling is that the intent was right and the
    channel was not, so the channel exists now.

source (verbatim at c734ce52451af00181b7264d81573c4029096964):
     1  """Pass 2: reference resolution and unresolved-site detection.
     2  
     3  Scoping model (plan A1-A5): resolution walks a stack of frames
     4  (module / class / function / comprehension). Every binding carries an
     5  origin — opaque bindings (params, assignments, targets) shadow; import
     6  bindings carry dotted targets; def bindings carry the indexed symbol
     7  path, so calls to nested defs resolve instead of being dropped as
     8  shadowed locals. Class frames are invisible to lookups from nested
     9  functions, matching Python. When exact resolution misses, the fallback
    10  matches the terminal attribute name against every indexed symbol and
    11  marks the reference ambiguous — noise is preferred to silence, and a
    12  terminal name matching nothing indexed cannot hide an in-repo edge.
    13  """
    14  
    15  import ast
    16  from collections import defaultdict
    17  
    18  _DEF_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    19  _FUNC_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)
    20  _COMP_NODES = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
    21  _DYNAMIC_DUNDERS = {"__getattr__", "__setattr__", "__getattribute__"}
    22  _MAX_CHASE_DEPTH = 10
    23  
    24  
    25  # --- statement traversal that stays at one scope level ----------------------
    26  
    27  
    28  def scope_statements(body):
    29      """The statements reachable at one scope level — the same walk the
    30      import tables are built from.
    31  
    32      Public so a consumer can guarantee it sees exactly the statement set
    33      `ImportTable.from_module` saw. `index_assembly` needed this and reached
    34      for the private name; the ruling is that the intent was right and the
    35      channel was not, so the channel exists now.
    36      """
    37      return _scope_stmts(body)
    38  
    39  
    40  def _scope_stmts(stmts):
    41      """Yield statements reachable at the same scope level: descends through
    42      control flow (if/try/for/while/with) but never into defs or classes."""
    43      for stmt in stmts:
    44          yield stmt
    45          if isinstance(stmt, _DEF_NODES):
    46              continue
    47          for field in ("body", "orelse", "finalbody"):
    48              yield from _scope_stmts(getattr(stmt, field, []) or [])
    49          for handler in getattr(stmt, "handlers", []) or []:
    50              yield from _scope_stmts(handler.body)
    51          for case in getattr(stmt, "cases", []) or []:
    52              yield from _scope_stmts(case.body)
    53  
    54  
    55  # --- import table -----------------------------------------------------------
    56  
    57  
    58  class ImportTable:
    59      def __init__(self, module_path: str, *, is_package: bool = False):
    60          parts = module_path.split(".") if module_path else []
    61          self._package_parts = parts if is_package else parts[:-1]
    62          self._bindings: dict[str, tuple[str, ...]] = {}
    63          self.has_star = False
    64  
    65      @classmethod
    66      def from_module(
    67          cls, tree: ast.Module, module_path: str, *, is_package: bool = False
    68      ) -> "ImportTable":
    69          table = cls(module_path, is_package=is_package)
    70          for stmt in _scope_stmts(tree.body):
    71              table.add(stmt)
    72          return table
    73  
    74      def add(self, stmt: ast.stmt) -> None:
    75          if isinstance(stmt, ast.Import):
    76              for alias in stmt.names:
    77                  if alias.asname:
    78                      self._bind(alias.asname, alias.name)
    79                  else:
    80                      top = alias.name.split(".")[0]
    81                      self._bind(top, top)
    82          elif isinstance(stmt, ast.ImportFrom):
    83              base = self.base_of(stmt)
    84              for alias in stmt.names:
    85                  if alias.name == "*":
    86                      self.has_star = True
    87                      continue
    88                  target = f"{base}.{alias.name}" if base else alias.name
    89                  self._bind(alias.asname or alias.name, target)
    90  
    91      def base_of(self, stmt: ast.ImportFrom) -> str:
    92          """Dotted module the from-import pulls from, relative levels resolved."""
    93          if stmt.level == 0:
    94              return stmt.module or ""
    95          anchor = self._package_parts[: len(self._package_parts) - (stmt.level - 1)]
    96          if stmt.module:
    97              anchor = anchor + [stmt.module]
    98          return ".".join(anchor)
    99  
   100      def _bind(self, name: str, target: str) -> None:
   101          existing = self._bindings.get(name, ())
   102          if target not in existing:
   103              self._bindings[name] = existing + (target,)
   104  
   105      def resolve(self, name: str) -> tuple[str, ...]:
   106          return self._bindings.get(name, ())
   107  
   108  
   109  # --- opaque local bindings --------------------------------------------------
   110  
   111  
   112  def _target_names(node, out: set[str]) -> None:
   113      if isinstance(node, ast.Name):
   114          out.add(node.id)
   115      elif isinstance(node, (ast.Tuple, ast.List)):
   116          for elt in node.elts:
   117              _target_names(elt, out)
   118      elif isinstance(node, ast.Starred):
   119          _target_names(node.value, out)
   120  
   121  
   122  def _scan_opaque(node, opaque: set[str], excluded: set[str], in_comp: bool) -> None:
   123      if isinstance(node, _DEF_NODES) or isinstance(node, ast.Lambda):
   124          return  # own scope; names bound there do not leak
   125      if isinstance(node, (ast.Import, ast.ImportFrom)):
   126          return  # import origin, not opaque
   127      if isinstance(node, (ast.Global, ast.Nonlocal)):
   128          excluded.update(node.names)
   129          return
   130      if isinstance(node, _COMP_NODES):
   131          # Comprehensions are their own scope: their targets never leak, but a
   132          # walrus inside them binds in the enclosing function (PEP 572).
   133          for child in ast.iter_child_nodes(node):
   134              _scan_opaque(child, opaque, excluded, True)
   135          return
   136      if isinstance(node, ast.comprehension):
   137          _scan_opaque(node.iter, opaque, excluded, in_comp)
   138          for cond in node.ifs:
   139              _scan_opaque(cond, opaque, excluded, in_comp)
   140          return  # node.target deliberately skipped
   141      if isinstance(node, ast.NamedExpr):
   142          _target_names(node.target, opaque)
   143          _scan_opaque(node.value, opaque, excluded, in_comp)
   144          return
   145      if in_comp:
   146          for child in ast.iter_child_nodes(node):
   147              _scan_opaque(child, opaque, excluded, True)
   148          return
   149      if isinstance(node, ast.Assign):
   150          for target in node.targets:
   151              _target_names(target, opaque)
   152      elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
   153          _target_names(node.target, opaque)
   154      elif isinstance(node, (ast.For, ast.AsyncFor)):
   155          _target_names(node.target, opaque)
   156      elif isinstance(node, (ast.With, ast.AsyncWith)):
   157          for item in node.items:
   158              if item.optional_vars:
   159                  _target_names(item.optional_vars, opaque)
   160      elif isinstance(node, ast.ExceptHandler) and node.name:
   161          opaque.add(node.name)
   162      elif isinstance(node, ast.MatchAs) and node.name:
   163          opaque.add(node.name)
   164      elif isinstance(node, ast.MatchStar) and node.name:
   165          opaque.add(node.name)
   166      elif isinstance(node, ast.MatchMapping) and node.rest:
   167          opaque.add(node.rest)
   168      for child in ast.iter_child_nodes(node):
   169          _scan_opaque(child, opaque, excluded, in_comp)
   170  
   171  
   172  def _params_of(args: ast.arguments) -> set[str]:
   173      names = {a.arg for a in args.posonlyargs + args.args + args.kwonlyargs}
   174      if args.vararg:
   175          names.add(args.vararg.arg)
   176      if args.kwarg:
   177          names.add(args.kwarg.arg)
   178      return names
   179  
   180  
   181  def local_bindings(func_node) -> set[str]:
   182      """Names bound opaquely (shadowing) in a function scope: params,
   183      assignments, loop/with/except/match targets, walrus — minus names
   184      declared global/nonlocal. Nested defs and local imports are excluded:
   185      they bind too, but resolvably (def/import origin)."""
   186      opaque = _params_of(func_node.args)
   187      excluded: set[str] = set()
   188      for stmt in func_node.body:
   189          _scan_opaque(stmt, opaque, excluded, False)
   190      return opaque - excluded
   191  
   192  
   193  # --- project-wide resolver --------------------------------------------------
   194  
   195  
   196  class Resolver:
   197      def __init__(
   198          self, symbols: dict[str, list[dict]], tables: dict[str, "ImportTable"]
   199      ):
   200          self.symbols = symbols
   201          self.tables = tables
   202          self.modules = set(tables)
   203          self.by_terminal: dict[str, list[str]] = defaultdict(list)
   204          for path in sorted(symbols):
   205              self.by_terminal[path.rsplit(".", 1)[-1]].append(path)
   206  
   207      def is_module(self, dotted: str) -> bool:
   208          return any(m == dotted or m.endswith("." + dotted) for m in self.modules)
   209  
   210      def module_anchor_exists(self, dotted: str) -> bool:
   211          """Does this dotted module string plausibly refer to an indexed
   212          module (exactly, or as a src-layout suffix)?"""
   213          return self.is_module(dotted)
   214  
   215      def terminal_matches(self, name: str) -> list[str]:
   216          return self.by_terminal.get(name, [])
   217  
   218      def resolve_dotted(
   219          self, dotted: str, *, _depth: int = 0, _seen: frozenset = frozenset()
   220      ) -> list[tuple[str, str | None]]:
   221          """Resolve a dotted target to indexed symbol paths.
   222  
   223          Returns [(symbol_path, note)] — note None for exact hits, a
   224          human-readable ambiguity note for suffix matches. Misses through
   225          re-exports are chased through the target module's own import
   226          table (pkg/__init__.py facades)."""
   227          if _depth > _MAX_CHASE_DEPTH or dotted in _seen:
   228              return []
   229          seen = _seen | {dotted}
   230          if dotted in self.symbols:
   231              return [(dotted, None)]
   232          results: list[tuple[str, str | None]] = []
   233          # Re-export chase: longest indexed-module prefix, remainder rebound
   234          # through that module's import table.
   235          parts = dotted.split(".")
   236          for cut in range(len(parts) - 1, 0, -1):
   237              module = ".".join(parts[:cut])
   238              if module not in self.tables:
   239                  continue
   240              remainder = parts[cut:]
   241              for target in self.tables[module].resolve(remainder[0]):
   242                  chased = ".".join([target] + remainder[1:])
   243                  results.extend(
   244                      self.resolve_dotted(chased, _depth=_depth + 1, _seen=seen)
   245                  )
   246              break  # only the longest module prefix is meaningful
   247          if results:
   248              return _dedupe_resolutions(results)
   249          # Src-layout suffix match: mypkg.config -> src.mypkg.config.
   250          for cut in range(len(parts), 0, -1):
   251              left = ".".join(parts[:cut])
   252              remainder = parts[cut:]
   253              for module in sorted(self.modules):
   254                  if not module.endswith("." + left):
   255                      continue
   256                  candidate = ".".join([module] + remainder)
   257                  for path, _ in self.resolve_dotted(
   258                      candidate, _depth=_depth + 1, _seen=seen
   259                  ):
   260                      results.append(
   261                          (path, "module path matched by suffix (src layout)")
   262                      )
   263              if results:
   264                  return _dedupe_resolutions(results)
   265          return []
   266  
   267      def kind_of(self, path: str) -> str | None:
   268          records = self.symbols.get(path)
   269          return records[0]["kind"] if records else None
   270  
   271  
   272  def _dedupe_resolutions(
   273      results: list[tuple[str, str | None]]
   274  ) -> list[tuple[str, str | None]]:
   275      best: dict[str, str | None] = {}
   276      for path, note in results:
   277          if path not in best or (best[path] is not None and note is None):
   278              best[path] = note
   279      return [(p, best[p]) for p in sorted(best)]
   280  
   281  
   282  # --- reference walker -------------------------------------------------------
   283  
   284  
   285  class _Frame:
   286      __slots__ = ("kind", "bindings", "class_path", "base_paths")
   287  
   288      def __init__(self, kind: str):
   289          self.kind = kind
   290          # name -> ("opaque", None) | ("import", tuple[str, ...]) | ("def", str)
   291          self.bindings: dict[str, tuple[str, object]] = {}
   292          self.class_path: str | None = None
   293          self.base_paths: list[str] = []
   294  
   295      def bind(self, name: str, origin: str, payload=None) -> None:
   296          # Resolvable origins (def/import) beat opaque, so a module-level
   297          # `f = wrap(f)` next to `def f` over-reports rather than silencing
   298          # the def. A name bound by BOTH an import and a def (try/except
   299          # import-or-define fallback) keeps both candidates — at runtime
   300          # either could win, so dropping one silences a real edge.
   301          current = self.bindings.get(name)
   302          if current is None or current[0] == "opaque":
   303              if current is not None and origin == "opaque":
   304                  return
   305              self.bindings[name] = (origin, payload)
   306              return
   307          if origin == "opaque":
   308              return
   309          cur_origin, cur_payload = current
   310          if cur_origin == "import" and origin == "import":
   311              self.bindings[name] = (
   312                  "import", tuple(dict.fromkeys(cur_payload + payload))
   313              )
   314          elif {cur_origin, origin} == {"def", "import"}:
   315              def_path = payload if origin == "def" else cur_payload
   316              imports = payload if origin == "import" else cur_payload
   317              self.bindings[name] = ("both", (def_path, imports))
   318          elif cur_origin == "both" and origin == "import":
   319              def_path, imports = cur_payload
   320              self.bindings[name] = (
   321                  "both", (def_path, tuple(dict.fromkeys(imports + payload)))
   322              )
   323          # both+def and def+def keep the existing binding (same dotted path).
   324  
   325  
   326  _AMBIG_RECEIVER = "attribute name match; receiver not statically resolvable"
   327  _BOTH_NOTE = "name bound by both an import and a local definition"
   328  
   329  
   330  class _Walker:
   331      def __init__(self, rel_path: str, mod_path: str, resolver: Resolver):
   332          self.rel_path = rel_path
   333          self.mod_path = mod_path
   334          self.resolver = resolver
   335          self.table = resolver.tables.get(mod_path) or ImportTable(mod_path)
   336          self.refs: list[tuple[str, dict]] = []
   337          self.unresolved: list[dict] = []
   338          self.frames: list[_Frame] = []
   339          self.sym_stack: list[str] = [mod_path]
   340          self._seen_refs: set = set()
   341          self._seen_unresolved: set = set()
   342  
   343      # -- record emission --
   344  
   345      def _record(self, node, target: str, kind: str, note: str | None, args=None):
   346          key = (target, node.lineno, node.col_offset, kind)
   347          if key in self._seen_refs:
   348              return
   349          self._seen_refs.add(key)
   350          record = {
   351              "file": self.rel_path,
   352              "line": node.lineno,
   353              "in_symbol": self.sym_stack[-1],
   354              "kind": kind,
   355          }
   356          if args is not None:
   357              record["args"] = args
   358          if note is not None:
   359              record["ambiguous"] = True
   360              record["note"] = note
   361          self.refs.append((target, record))
   362  
   363      def _flag(self, node, reason: str, expression: str | None = None):
   364          key = (node.lineno, node.col_offset, reason)
   365          if key in self._seen_unresolved:
   366              return
   367          self._seen_unresolved.add(key)
   368          self.unresolved.append(
   369              {
   370                  "file": self.rel_path,
   371                  "line": node.lineno,
   372                  "in_symbol": self.sym_stack[-1],
   373                  "reason": reason,
   374                  "expression": expression
   375                  if expression is not None
   376                  else ast.unparse(node),
   377              }
   378          )
   379  
   380      # -- frame construction --
   381  
   382      def _module_frame(self, tree: ast.Module) -> _Frame:
   383          frame = _Frame("module")
   384          self._populate_scope_frame(frame, tree.body, self.mod_path)
   385          return frame
   386  
   387      def _function_frame(self, node) -> _Frame:
   388          frame = _Frame("function")
   389          for name in local_bindings(node):
   390              frame.bind(name, "opaque")
   391          path = f"{self.sym_stack[-1]}.{node.name}"
   392          self._populate_scope_frame(frame, node.body, path, opaque_assigns=False)
   393          return frame
   394  
   395      def _class_frame(self, node: ast.ClassDef, class_path: str) -> _Frame:
   396          frame = _Frame("class")
   397          frame.class_path = class_path
   398          for base in node.bases:
   399              frame.base_paths.extend(
   400                  path
   401                  for path, note in self._expr_symbol_paths(base)
   402                  if note is None and self.resolver.kind_of(path) == "class"
   403              )
   404          self._populate_scope_frame(frame, node.body, class_path)
   405          return frame
   406  
   407      def _populate_scope_frame(
   408          self, frame: _Frame, body, prefix: str, *, opaque_assigns: bool = True
   409      ) -> None:
   410          local_table = ImportTable(self.mod_path)
   411          local_table._package_parts = self.table._package_parts
   412          for stmt in _scope_stmts(body):
   413              if isinstance(stmt, _DEF_NODES):
   414                  frame.bind(stmt.name, "def", f"{prefix}.{stmt.name}")
   415              elif isinstance(stmt, (ast.Import, ast.ImportFrom)):
   416                  local_table.add(stmt)
   417              elif opaque_assigns and isinstance(stmt, ast.Assign):
   418                  names: set[str] = set()
   419                  for target in stmt.targets:
   420                      _target_names(target, names)
   421                  for name in names:
   422                      frame.bind(name, "opaque")
   423              elif opaque_assigns and isinstance(stmt, (ast.AnnAssign, ast.AugAssign)):
   424                  names = set()
   425                  _target_names(stmt.target, names)
   426                  for name in names:
   427                      frame.bind(name, "opaque")
   428          for name, targets in local_table._bindings.items():
   429              frame.bind(name, "import", targets)
   430  
   431      # -- name / attribute resolution --
   432  
   433      def _lookup(self, name: str):
   434          """Find the binding for a name: walks frames innermost-out, skipping
   435          class frames unless the class body is the current scope (Python
   436          semantics: class scope does not enclose methods)."""
   437          top = len(self.frames) - 1
   438          for i in range(top, -1, -1):
   439              frame = self.frames[i]
   440              if frame.kind == "class" and i != top:
   441                  continue
   442              if name in frame.bindings:
   443                  return frame.bindings[name]
   444          return None
   445  
   446      def _enclosing_class(self) -> _Frame | None:
   447          for frame in reversed(self.frames):
   448              if frame.kind == "class":
   449                  return frame
   450          return None
   451  
   452      def _name_targets(self, name: str) -> list[tuple[str, str | None]] | None:
   453          """Symbol paths a bare name refers to. None => opaque/unbound."""
   454          binding = self._lookup(name)
   455          if binding is None or binding[0] == "opaque":
   456              return None
   457          if binding[0] == "def":
   458              path = binding[1]
   459              return [(path, None)] if path in self.resolver.symbols else []
   460          results: list[tuple[str, str | None]] = []
   461          if binding[0] == "both":
   462              def_path, targets = binding[1]
   463              if def_path in self.resolver.symbols:
   464                  results.append((def_path, _BOTH_NOTE))
   465              for target in targets:
   466                  for path, note in self.resolver.resolve_dotted(target):
   467                      results.append((path, note or _BOTH_NOTE))
   468              return _dedupe_resolutions(results)
   469          multi = len(binding[1]) > 1
   470          for target in binding[1]:
   471              for path, note in self.resolver.resolve_dotted(target):
   472                  if multi and note is None:
   473                      note = "bound by multiple imports"
   474                  results.append((path, note))
   475          return _dedupe_resolutions(results)
   476  
   477      def _expr_symbol_paths(self, expr) -> list[tuple[str, str | None]]:
   478          """Exact-ish symbol paths an expression statically denotes."""
   479          if isinstance(expr, ast.Name):
   480              return self._name_targets(expr.id) or []
   481          if isinstance(expr, ast.Attribute):
   482              parts = []
   483              cur = expr
   484              while isinstance(cur, ast.Attribute):
   485                  parts.append(cur.attr)
   486                  cur = cur.value
   487              parts.reverse()
   488              if not isinstance(cur, ast.Name):
   489                  return []
   490              base_binding = self._lookup(cur.id)
   491              if base_binding is None or base_binding[0] == "opaque":
   492                  return []
   493              results: list[tuple[str, str | None]] = []
   494              if base_binding[0] == "def":
   495                  bases = [(base_binding[1], None)]
   496              elif base_binding[0] == "both":
   497                  def_path, targets = base_binding[1]
   498                  bases = [(def_path, _BOTH_NOTE)] + [(t, _BOTH_NOTE) for t in targets]
   499              else:
   500                  bases = [(t, None) for t in base_binding[1]]
   501              for base, base_note in bases:
   502                  dotted = ".".join([base] + parts)
   503                  for path, note in self.resolver.resolve_dotted(dotted):
   504                      results.append((path, note or base_note))
   505              return _dedupe_resolutions(results)
   506          return []
   507  
   508      def _fallback(self, node, terminal: str, kind: str, args, note: str):
   509          for path in self.resolver.terminal_matches(terminal):
   510              self._record(node, path, kind, note, args)
   511  
   512      def _resolve_attribute_use(self, attr: ast.Attribute, kind: str, args, site):
   513          """Emit references for an attribute chain in Load context. `site` is
   514          the node whose position anchors the record (the Call for calls)."""
   515          parts = []
   516          cur = attr
   517          while isinstance(cur, ast.Attribute):
   518              parts.append(cur.attr)
   519              cur = cur.value
   520          parts.reverse()
   521          terminal = parts[-1]
   522  
   523          if isinstance(cur, ast.Name):
   524              # self / cls inside a method resolve against the enclosing class.
   525              cls_frame = self._enclosing_class()
   526              if (
   527                  cur.id in ("self", "cls")
   528                  and cls_frame is not None
   529                  and self._lookup(cur.id) == ("opaque", None)
   530              ):
   531                  dotted = ".".join([cls_frame.class_path] + parts)
   532                  hits = self.resolver.resolve_dotted(dotted)
   533                  if hits:
   534                      for path, note in hits:
   535                          self._record(site, path, kind, note, args)
   536                      return
   537                  for base_path in cls_frame.base_paths:
   538                      hits = self.resolver.resolve_dotted(
   539                          ".".join([base_path] + parts)
   540                      )
   541                      if hits:
   542                          for path, note in hits:
   543                              self._record(site, path, kind, note, args)
   544                          return
   545                  self._fallback(
   546                      site,
   547                      terminal,
   548                      kind,
   549                      args,
   550                      "attribute of self; not found on class or direct bases",
   551                  )
   552                  return
   553              targets = self._name_targets(cur.id)
   554              if targets is None:
   555                  self._fallback(site, terminal, kind, args, _AMBIG_RECEIVER)
   556                  return
   557              # Compose against every dotted target the base name carries
   558              # (import targets may point outside the symbol table).
   559              emitted = False
   560              binding = self._lookup(cur.id)
   561              base_pairs: list[tuple[str, str | None]] = []
   562              if binding[0] == "def":
   563                  base_pairs = [(binding[1], None)]
   564              elif binding[0] == "import":
   565                  base_pairs = [(t, None) for t in binding[1]]
   566              elif binding[0] == "both":
   567                  def_path, targets = binding[1]
   568                  base_pairs = [(def_path, _BOTH_NOTE)] + [
   569                      (t, _BOTH_NOTE) for t in targets
   570                  ]
   571              for base, base_note in base_pairs:
   572                  for path, note in self.resolver.resolve_dotted(
   573                      ".".join([base] + parts)
   574                  ):
   575                      self._record(site, path, kind, note or base_note, args)
   576                      emitted = True
   577              if not emitted:
   578                  self._fallback(site, terminal, kind, args, _AMBIG_RECEIVER)
   579              return
   580  
   581          if isinstance(cur, ast.Call):
   582              inner = cur
   583              if (
   584                  isinstance(inner.func, ast.Name)
   585                  and inner.func.id == "super"
   586                  and self._lookup("super") is None
   587              ):
   588                  cls_frame = self._enclosing_class()
   589                  if cls_frame is None:
   590                      return
   591                  for base_path in cls_frame.base_paths:
   592                      hits = self.resolver.resolve_dotted(
   593                          ".".join([base_path] + parts)
   594                      )
   595                      if hits:
   596                          for path, note in hits:
   597                              self._record(site, path, kind, note, args)
   598                          return
   599                  if cls_frame.base_paths:
   600                      self._fallback(
   601                          site,
   602                          terminal,
   603                          kind,
   604                          args,
   605                          "resolved via super(); exact base chain unknown",
   606                      )
   607                  return  # external hierarchy: no in-repo edge can hide here
   608              callee_paths = [
   609                  path
   610                  for path, note in self._expr_symbol_paths(inner.func)
   611                  if self.resolver.kind_of(path) == "class"
   612              ]
   613              emitted = False
   614              for cls_path in callee_paths:
   615                  for path, note in self.resolver.resolve_dotted(
   616                      ".".join([cls_path] + parts)
   617                  ):
   618                      self._record(site, path, kind, note, args)
   619                      emitted = True
   620              if emitted:
   621                  return
   622              if callee_paths:
   623                  self._fallback(
   624                      site,
   625                      terminal,
   626                      kind,
   627                      args,
   628                      "method not found on constructed class; possibly inherited",
   629                  )
   630                  return
   631              # External or opaque factory (open(p).read()): exact resolution is
   632              # impossible, but a terminal name matching nothing indexed cannot
   633              # hide an in-repo edge — name-match, else stay silent (plan A5).
   634              self._fallback(site, terminal, kind, args, _AMBIG_RECEIVER)
   635              return
   636  
   637          # Subscript / literal / anything else as receiver.
   638          self._fallback(site, terminal, kind, args, _AMBIG_RECEIVER)
   639  
   640      # -- visitation --
   641  
   642      def visit_module(self, tree: ast.Module) -> None:
   643          self.frames.append(self._module_frame(tree))
   644          for stmt in tree.body:
   645              self.visit(stmt)
   646          self.frames.pop()
   647  
   648      def visit(self, node) -> None:
   649          method = getattr(self, f"_visit_{type(node).__name__}", None)
   650          if method is not None:
   651              method(node)
   652              return
   653          for child in ast.iter_child_nodes(node):
   654              self.visit(child)
   655  
   656      def _visit_FunctionDef(self, node) -> None:
   657          for deco in node.decorator_list:
   658              self.visit(deco)
   659          self._visit_arg_annotations_and_defaults(node.args)
   660          if node.returns is not None:
   661              self.visit(node.returns)
   662          if node.name in _DYNAMIC_DUNDERS:
   663              # setattr / __getattr__ definitions make attribute traffic in
   664              # this file statically undecidable (brief §3).
   665              self._flag(node, "dynamic_attribute", f"def {node.name}(...)")
   666          path = f"{self.sym_stack[-1]}.{node.name}"
   667          self.frames.append(self._function_frame(node))
   668          self.sym_stack.append(path)
   669          for stmt in node.body:
   670              self.visit(stmt)
   671          self.sym_stack.pop()
   672          self.frames.pop()
   673  
   674      _visit_AsyncFunctionDef = _visit_FunctionDef
   675  
   676      def _visit_arg_annotations_and_defaults(self, args: ast.arguments) -> None:
   677          for arg in args.posonlyargs + args.args + args.kwonlyargs:
   678              if arg.annotation is not None:
   679                  self.visit(arg.annotation)
   680          for arg in (args.vararg, args.kwarg):
   681              if arg is not None and arg.annotation is not None:
   682                  self.visit(arg.annotation)
   683          for default in list(args.defaults) + [
   684              d for d in args.kw_defaults if d is not None
   685          ]:
   686              self.visit(default)
   687  
   688      def _visit_ClassDef(self, node: ast.ClassDef) -> None:
   689          for deco in node.decorator_list:
   690              self.visit(deco)
   691          for base in node.bases:
   692              self.visit(base)
   693          for kw in node.keywords:
   694              self.visit(kw.value)
   695          path = f"{self.sym_stack[-1]}.{node.name}"
   696          self.frames.append(self._class_frame(node, path))
   697          self.sym_stack.append(path)
   698          for stmt in node.body:
   699              self.visit(stmt)
   700          self.sym_stack.pop()
   701          self.frames.pop()
   702  
   703      def _visit_Lambda(self, node: ast.Lambda) -> None:
   704          self._visit_arg_annotations_and_defaults(node.args)
   705          frame = _Frame("function")
   706          for name in _params_of(node.args):
   707              frame.bind(name, "opaque")
   708          self.frames.append(frame)
   709          self.visit(node.body)
   710          self.frames.pop()
   711  
   712      def _visit_comprehension_scope(self, node) -> None:
   713          # Python evaluates the OUTERMOST iterable in the enclosing scope —
   714          # `[setup for setup in setup()]` calls the enclosing `setup`, and a
   715          # class-body comprehension's first iterable can see class attributes.
   716          first = node.generators[0]
   717          self.visit(first.iter)
   718          frame = _Frame("comprehension")
   719          for gen in node.generators:
   720              names: set[str] = set()
   721              _target_names(gen.target, names)
   722              for name in names:
   723                  frame.bind(name, "opaque")
   724          self.frames.append(frame)
   725          for gen in node.generators:
   726              if gen is not first:
   727                  self.visit(gen.iter)
   728              for cond in gen.ifs:
   729                  self.visit(cond)
   730          if isinstance(node, ast.DictComp):
   731              self.visit(node.key)
   732              self.visit(node.value)
   733          else:
   734              self.visit(node.elt)
   735          self.frames.pop()
   736  
   737      _visit_ListComp = _visit_comprehension_scope
   738      _visit_SetComp = _visit_comprehension_scope
   739      _visit_DictComp = _visit_comprehension_scope
   740      _visit_GeneratorExp = _visit_comprehension_scope
   741  
   742      def _visit_Import(self, node: ast.Import) -> None:
   743          pass  # module objects are not symbols; uses are resolved at use sites
   744  
   745      def _visit_Assign(self, node: ast.Assign) -> None:
   746          # PEP 562: `__getattr__ = fn` at module (or class) level defines
   747          # dynamic attribute access just as `def __getattr__` does.
   748          if self.frames[-1].kind in ("module", "class"):
   749              names: set[str] = set()
   750              for target in node.targets:
   751                  _target_names(target, names)
   752              for name in sorted(names & _DYNAMIC_DUNDERS):
   753                  self._flag(node, "dynamic_attribute")
   754          for child in ast.iter_child_nodes(node):
   755              self.visit(child)
   756  
   757      def _visit_ImportFrom(self, node: ast.ImportFrom) -> None:
   758          if any(alias.name == "*" for alias in node.names):
   759              self._flag(node, "star_import")
   760              return
   761          base = self.table.base_of(node)
   762          for alias in node.names:
   763              target = f"{base}.{alias.name}" if base else alias.name
   764              if self.resolver.is_module(target):
   765                  continue  # `from pkg import submodule`
   766              hits = self.resolver.resolve_dotted(target)
   767              for path, note in hits:
   768                  self._record(node, path, "name", note)
   769              if not hits and base:
   770                  # The name resolves nowhere. If the source module is ours,
   771                  # parsed clean, and star-free, every def it contains is in
   772                  # the symbol table — so this import is provably not a def
   773                  # edge (a constant or variable; indexing those is a brief
   774                  # open question) and stays silent. Only a star import can
   775                  # hide a def from us, so that case is flagged.
   776                  anchors = [
   777                      m
   778                      for m in self.resolver.modules
   779                      if m == base or m.endswith("." + base)
   780                  ]
   781                  if any(self.resolver.tables[m].has_star for m in anchors):
   782                      self._flag(node, "unresolved_import_target")
   783  
   784      def _visit_Call(self, node: ast.Call) -> None:
   785          func = node.func
   786          args_written = [ast.unparse(a) for a in node.args] + [
   787              f"{kw.arg}={ast.unparse(kw.value)}"
   788              if kw.arg is not None
   789              else f"**{ast.unparse(kw.value)}"
   790              for kw in node.keywords
   791          ]
   792          if isinstance(func, ast.Subscript):
   793              self._flag(node, "subscript_call")
   794              self.visit(func)
   795          elif isinstance(func, ast.Call):
   796              if (
   797                  isinstance(func.func, ast.Name)
   798                  and func.func.id == "getattr"
   799                  and self._lookup("getattr") is None
   800              ):
   801                  self._flag(node, "getattr_call")
   802              else:
   803                  self._flag(node, "attribute_of_call")
   804              self.visit(func)
   805          elif isinstance(func, ast.Name):
   806              binding = self._lookup(func.id)
   807              if func.id == "getattr" and binding is None:
   808                  self._flag(node, "getattr_call")
   809              elif func.id == "setattr" and binding is None:
   810                  self._flag(node, "dynamic_attribute")
   811              else:
   812                  targets = self._name_targets(func.id)
   813                  for path, note in targets or []:
   814                      self._record(node, path, "call", note, args_written)
   815          elif isinstance(func, ast.Attribute):
   816              self._resolve_attribute_use(func, "call", args_written, node)
   817              self.visit(func.value)
   818          else:
   819              self.visit(func)
   820          for arg in node.args:
   821              self.visit(arg)
   822          for kw in node.keywords:
   823              self.visit(kw.value)
   824  
   825      def _visit_Name(self, node: ast.Name) -> None:
   826          if not isinstance(node.ctx, ast.Load):
   827              return
   828          for path, note in self._name_targets(node.id) or []:
   829              self._record(node, path, "name", note)
   830  
   831      def _visit_Attribute(self, node: ast.Attribute) -> None:
   832          if isinstance(node.ctx, ast.Load):
   833              self._resolve_attribute_use(node, "name", None, node)
   834          self.visit(node.value)
   835  
   836  
   837  def collect_references(
   838      tree: ast.Module, rel_path: str, mod_path: str, resolver: Resolver
   839  ) -> tuple[list[tuple[str, dict]], list[dict]]:
   840      walker = _Walker(rel_path, mod_path, resolver)
   841      walker.visit_module(tree)
   842      return walker.refs, walker.unresolved

### Interfaces you consume
- analyzer.modpath.module_path  [function, confidence high]  lines 4-8  [available: symbol_table]
  signature: (rel_path: str) -> str
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
- harness.speccc.resolve  [function, confidence high]  lines 66-75  [unowned file] [ambiguous attribution — edge known only by name match]
  signature: (index)
- tests.test_refs.func  [function, confidence high]  lines 83-84  [unowned file] [ambiguous attribution — edge known only by name match]
  signature: (source: str) -> ast.FunctionDef

### Callers of your write scope
- analyzer.refs.ImportTable <- analyzer/indexer.py:13 in analyzer.indexer
- analyzer.refs.ImportTable <- analyzer/indexer.py:70 in analyzer.indexer
- analyzer.refs.ImportTable <- analyzer/indexer.py:231 in analyzer.indexer.build_index
- analyzer.refs.ImportTable <- tests/test_refs.py:5 in tests.test_refs
- analyzer.refs.ImportTable <- tests/test_refs.py:17 in tests.test_refs
- analyzer.refs.ImportTable <- tests/test_refs.py:18 in tests.test_refs.imports
- analyzer.refs.ImportTable <- tests/test_refs.py:149 in tests.test_refs.build
- analyzer.refs.ImportTable <- tests/test_unresolved.py:5 in tests.test_unresolved
- analyzer.refs.ImportTable <- tests/test_unresolved.py:16 in tests.test_unresolved.unresolved_in
- analyzer.refs.ImportTable.add <- analyzer/indexer.py:294 in analyzer.indexer.build_index args=((site['line'], site['reason'])) [ambiguous]
- analyzer.refs.ImportTable.add <- harness/autopilot.py:174 in harness.autopilot.dependents args=(oid) [ambiguous]
- analyzer.refs.ImportTable.add <- harness/autopilot.py:175 in harness.autopilot.dependents args=(oid) [ambiguous]
- analyzer.refs.ImportTable.add <- harness/autopilot.py:570 in harness.autopilot.Conductor.run args=(node_id) [ambiguous]
- analyzer.refs.ImportTable.add <- harness/autopilot.py:612 in harness.autopilot.Conductor.run_single args=(node_id) [ambiguous]
- analyzer.refs.ImportTable.add <- harness/autopilot.py:636 in harness.autopilot.Conductor._stop_line args=(node_id) [ambiguous]
- analyzer.refs.ImportTable.add <- harness/fence.py:149 in harness.fence.check_diff args=(path) [ambiguous]
- analyzer.refs.ImportTable.add <- harness/join.py:179 in harness.join._unique_symbols args=(symbol['path']) [ambiguous]
- analyzer.refs.ImportTable.add <- harness/join.py:208 in harness.join._ancestors args=(nid) [ambiguous]
- analyzer.refs.ImportTable.add <- harness/join.py:236 in harness.join.consumed_interfaces args=(symbol['path']) [ambiguous]
- analyzer.refs.ImportTable.add <- harness/join.py:401 in harness.join.serialize_plan args=(frozenset((nid, peer))) [ambiguous]
- analyzer.refs.ImportTable.add <- harness/join.py:403 in harness.join.serialize_plan args=(frozenset(finding.nodes)) [ambiguous]
- analyzer.refs.ImportTable.add <- harness/join.py:1012 in harness.join.assemble_packet args=(symbol['path']) [ambiguous]
- analyzer.refs.ImportTable.add <- harness/join.py:1047 in harness.join.assemble_packet args=(symbol['path']) [ambiguous]
- analyzer.refs.ImportTable.add <- harness/speccc.py:159 in harness.speccc.warnings args=(_anchor_name(str(entry))) [ambiguous]
- analyzer.refs.ImportTable.add <- lex/request_mem.py:32 in lex.request_mem.scan args=(body) [ambiguous]
- analyzer.refs.ImportTable.add <- tests/test_autopilot.py:32 in tests.test_autopilot._called_names args=(func.id) [ambiguous]
- analyzer.refs.ImportTable.add <- tests/test_autopilot.py:34 in tests.test_autopilot._called_names args=(func.attr) [ambiguous]
- analyzer.refs.ImportTable.add <- tests/test_lex_confirm.py:267 in tests.test_lex_confirm.test_no_auto_yes_identifier_anywhere_in_lex args=(id(first.value)) [ambiguous]
- analyzer.refs.ImportTable.add <- tests/test_lex_confirm.py:273 in tests.test_lex_confirm.test_no_auto_yes_identifier_anywhere_in_lex args=(node.id) [ambiguous]
- analyzer.refs.ImportTable.add <- tests/test_lex_confirm.py:275 in tests.test_lex_confirm.test_no_auto_yes_identifier_anywhere_in_lex args=(node.arg) [ambiguous]
- analyzer.refs.ImportTable.add <- tests/test_lex_confirm.py:277 in tests.test_lex_confirm.test_no_auto_yes_identifier_anywhere_in_lex args=(node.arg) [ambiguous]
- analyzer.refs.ImportTable.add <- tests/test_lex_confirm.py:279 in tests.test_lex_confirm.test_no_auto_yes_identifier_anywhere_in_lex args=(node.attr) [ambiguous]
- analyzer.refs.ImportTable.add <- tests/test_lex_confirm.py:281 in tests.test_lex_confirm.test_no_auto_yes_identifier_anywhere_in_lex args=(node.value) [ambiguous]
- analyzer.refs.ImportTable.base_of <- analyzer/indexer.py:93 in analyzer.indexer._import_entries args=(stmt) [ambiguous]
- analyzer.refs.ImportTable.from_module <- analyzer/indexer.py:231 in analyzer.indexer.build_index args=(tree, mod, is_package=rel.endswith('__init__.py'))
- analyzer.refs.ImportTable.from_module <- tests/test_refs.py:18 in tests.test_refs.imports args=(ast.parse(source), mod, is_package=is_package)
- analyzer.refs.ImportTable.from_module <- tests/test_refs.py:149 in tests.test_refs.build args=(tree, mod, is_package=is_pkg)
- analyzer.refs.ImportTable.from_module <- tests/test_unresolved.py:16 in tests.test_unresolved.unresolved_in args=(tree, mod, is_package=False)
- analyzer.refs.ImportTable.resolve <- harness/autopilot.py:396 in harness.autopilot.Conductor.stage args=() [ambiguous]
- analyzer.refs.ImportTable.resolve <- harness/dispatch.py:93 in harness.dispatch.prepare args=() [ambiguous]
- analyzer.refs.ImportTable.resolve <- harness/dispatch.py:98 in harness.dispatch.prepare args=() [ambiguous]
- analyzer.refs.ImportTable.resolve <- harness/dispatch.py:128 in harness.dispatch.prepare args=() [ambiguous]
- analyzer.refs.ImportTable.resolve <- harness/dispatch.py:201 in harness.dispatch args=() [ambiguous]
- analyzer.refs.ImportTable.resolve <- harness/join.py:1262 in harness.join._cmd_replay args=() [ambiguous]
- analyzer.refs.ImportTable.resolve <- lab/app.py:26 in lab.app.create_app args=() [ambiguous]
- analyzer.refs.ImportTable.resolve <- lab/app.py:54 in lab.app.create_app.file args=() [ambiguous]
- analyzer.refs.ImportTable.resolve <- lab/app.py:88 in lab.app.serve args=() [ambiguous]
- analyzer.refs.ImportTable.resolve <- lex/__main__.py:54 in lex.__main__.main args=() [ambiguous]
- analyzer.refs.ImportTable.resolve <- lex/repl.py:108 in lex.repl.opening_turn args=() [ambiguous]
- analyzer.refs.ImportTable.resolve <- tests/conftest.py:6 in tests.conftest args=() [ambiguous]
- analyzer.refs.ImportTable.resolve <- tests/test_lex_agent.py:17 in tests.test_lex_agent args=() [ambiguous]
- analyzer.refs.ImportTable.resolve <- tests/test_lex_confirm.py:25 in tests.test_lex_confirm args=() [ambiguous]
- analyzer.refs.ImportTable.resolve <- tests/test_lex_tools.py:14 in tests.test_lex_tools args=() [ambiguous]
- analyzer.refs.ImportTable.resolve <- tests/test_refs.py:22 in tests.test_refs.test_plain_import_binds_top_name args=('src') [ambiguous]
- analyzer.refs.ImportTable.resolve <- tests/test_refs.py:26 in tests.test_refs.test_import_as_binds_alias_to_full_path args=('cfg') [ambiguous]
- analyzer.refs.ImportTable.resolve <- tests/test_refs.py:31 in tests.test_refs.test_from_import args=('load_settings') [ambiguous]
- analyzer.refs.ImportTable.resolve <- tests/test_refs.py:36 in tests.test_refs.test_from_import_as args=('ls') [ambiguous]
- analyzer.refs.ImportTable.resolve <- tests/test_refs.py:41 in tests.test_refs.test_relative_import_from_module args=('util') [ambiguous]
- analyzer.refs.ImportTable.resolve <- tests/test_refs.py:46 in tests.test_refs.test_relative_import_from_package_init args=('util') [ambiguous]
- analyzer.refs.ImportTable.resolve <- tests/test_refs.py:51 in tests.test_refs.test_relative_from_import_in_package_init args=('load_settings') [ambiguous]
- analyzer.refs.ImportTable.resolve <- tests/test_refs.py:56 in tests.test_refs.test_relative_import_two_levels args=('load_settings') [ambiguous]
- analyzer.refs.ImportTable.resolve <- tests/test_refs.py:66 in tests.test_refs.test_dual_import_keeps_both_targets args=('escape') [ambiguous]
- analyzer.refs.ImportTable.resolve <- tests/test_refs.py:77 in tests.test_refs.test_unknown_name_resolves_empty args=('nothing') [ambiguous]
- analyzer.refs.Resolver <- analyzer/indexer.py:13 in analyzer.indexer
- analyzer.refs.Resolver <- analyzer/indexer.py:62 in analyzer.indexer
- analyzer.refs.Resolver <- analyzer/indexer.py:71 in analyzer.indexer
- analyzer.refs.Resolver <- analyzer/indexer.py:234 in analyzer.indexer.build_index args=(dict(symbols_by_path), tables)
- analyzer.refs.Resolver <- tests/test_refs.py:5 in tests.test_refs
- analyzer.refs.Resolver <- tests/test_refs.py:150 in tests.test_refs.build args=(dict(symbols), tables)
- analyzer.refs.Resolver <- tests/test_unresolved.py:5 in tests.test_unresolved
- analyzer.refs.Resolver <- tests/test_unresolved.py:15 in tests.test_unresolved.unresolved_in args=(dict(symbols), {mod: ImportTable.from_module(tree, mod, is_package=False)})
- analyzer.refs.Resolver.is_module <- analyzer/indexer.py:106 in analyzer.indexer._import_entries args=(target) [ambiguous]
- analyzer.refs.Resolver.resolve_dotted <- analyzer/indexer.py:111 in analyzer.indexer._import_entries args=(target) [ambiguous]
- analyzer.refs.collect_references <- analyzer/indexer.py:13 in analyzer.indexer
- analyzer.refs.collect_references <- analyzer/indexer.py:240 in analyzer.indexer.build_index args=(tree, rel, mod, resolver)
- analyzer.refs.collect_references <- tests/test_refs.py:5 in tests.test_refs
- analyzer.refs.collect_references <- tests/test_refs.py:155 in tests.test_refs.build args=(tree, rel, mod, resolver)
- analyzer.refs.collect_references <- tests/test_unresolved.py:5 in tests.test_unresolved
- analyzer.refs.collect_references <- tests/test_unresolved.py:18 in tests.test_unresolved.unresolved_in args=(tree, rel_path, mod, resolver)
- analyzer.refs.local_bindings <- tests/test_refs.py:5 in tests.test_refs
- analyzer.refs.local_bindings <- tests/test_refs.py:89 in tests.test_refs.test_local_bindings_params_and_assignments args=(node)
- analyzer.refs.local_bindings <- tests/test_refs.py:105 in tests.test_refs.test_local_bindings_targets args=(node)
- analyzer.refs.local_bindings <- tests/test_refs.py:110 in tests.test_refs.test_comprehension_targets_do_not_leak args=(node)
- analyzer.refs.local_bindings <- tests/test_refs.py:117 in tests.test_refs.test_global_names_excluded args=(node)
- analyzer.refs.local_bindings <- tests/test_refs.py:129 in tests.test_refs.test_nested_defs_and_imports_are_not_opaque args=(node)
- analyzer.refs.local_bindings <- tests/test_refs.py:135 in tests.test_refs.test_bindings_do_not_leak_from_nested_scope args=(node)
- analyzer.refs.scope_statements <- analyzer/indexer.py:13 in analyzer.indexer
- analyzer.refs.scope_statements <- analyzer/indexer.py:84 in analyzer.indexer._import_entries args=(tree.body)

### Unresolved sites in scope
These files are low confidence — assume an edge to everything here:
- analyzer/refs.py:48  getattr_call  getattr(stmt, field, [])
- analyzer/refs.py:49  getattr_call  getattr(stmt, 'handlers', [])
- analyzer/refs.py:51  getattr_call  getattr(stmt, 'cases', [])
- analyzer/refs.py:649  getattr_call  getattr(self, f'_visit_{type(node).__name__}', None)

### Coverage
Compiled from an index of 60 files at c734ce52451af00181b7264d81573c4029096964. This packet includes your write scope (1 entries), 16 consumed/available interface symbols, and every recorded caller of your scope. Anything not listed was not searched. Missing means query (request_mem), never build. verify with: .venv/bin/python -m pytest

## State — handoff  [provenance: agent-authored, claim not fact]

(none for this dispatch)
packet: node=reference_map role=executor commit=c734ce52451af00181b7264d81573c4029096964 plan=66e648664216 packet_hash=79c51ba032d1
