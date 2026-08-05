"""Pass 2: reference resolution and unresolved-site detection.

Scoping model (plan A1-A5): resolution walks a stack of frames
(module / class / function / comprehension). Every binding carries an
origin — opaque bindings (params, assignments, targets) shadow; import
bindings carry dotted targets; def bindings carry the indexed symbol
path, so calls to nested defs resolve instead of being dropped as
shadowed locals. Class frames are invisible to lookups from nested
functions, matching Python. When exact resolution misses, the fallback
matches the terminal attribute name against every indexed symbol and
marks the reference ambiguous — noise is preferred to silence, and a
terminal name matching nothing indexed cannot hide an in-repo edge.
"""

import ast
from collections import defaultdict

_DEF_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
_FUNC_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)
_COMP_NODES = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
_DYNAMIC_DUNDERS = {"__getattr__", "__setattr__", "__getattribute__"}
_MAX_CHASE_DEPTH = 10


# --- statement traversal that stays at one scope level ----------------------


def _scope_stmts(stmts):
    """Yield statements reachable at the same scope level: descends through
    control flow (if/try/for/while/with) but never into defs or classes."""
    for stmt in stmts:
        yield stmt
        if isinstance(stmt, _DEF_NODES):
            continue
        for field in ("body", "orelse", "finalbody"):
            yield from _scope_stmts(getattr(stmt, field, []) or [])
        for handler in getattr(stmt, "handlers", []) or []:
            yield from _scope_stmts(handler.body)
        for case in getattr(stmt, "cases", []) or []:
            yield from _scope_stmts(case.body)


# --- import table -----------------------------------------------------------


class ImportTable:
    def __init__(self, module_path: str, *, is_package: bool = False):
        parts = module_path.split(".") if module_path else []
        self._package_parts = parts if is_package else parts[:-1]
        self._bindings: dict[str, tuple[str, ...]] = {}
        self.has_star = False

    @classmethod
    def from_module(
        cls, tree: ast.Module, module_path: str, *, is_package: bool = False
    ) -> "ImportTable":
        table = cls(module_path, is_package=is_package)
        for stmt in _scope_stmts(tree.body):
            table.add(stmt)
        return table

    def add(self, stmt: ast.stmt) -> None:
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                if alias.asname:
                    self._bind(alias.asname, alias.name)
                else:
                    top = alias.name.split(".")[0]
                    self._bind(top, top)
        elif isinstance(stmt, ast.ImportFrom):
            base = self.base_of(stmt)
            for alias in stmt.names:
                if alias.name == "*":
                    self.has_star = True
                    continue
                target = f"{base}.{alias.name}" if base else alias.name
                self._bind(alias.asname or alias.name, target)

    def base_of(self, stmt: ast.ImportFrom) -> str:
        """Dotted module the from-import pulls from, relative levels resolved."""
        if stmt.level == 0:
            return stmt.module or ""
        anchor = self._package_parts[: len(self._package_parts) - (stmt.level - 1)]
        if stmt.module:
            anchor = anchor + [stmt.module]
        return ".".join(anchor)

    def _bind(self, name: str, target: str) -> None:
        existing = self._bindings.get(name, ())
        if target not in existing:
            self._bindings[name] = existing + (target,)

    def resolve(self, name: str) -> tuple[str, ...]:
        return self._bindings.get(name, ())


# --- opaque local bindings --------------------------------------------------


def _target_names(node, out: set[str]) -> None:
    if isinstance(node, ast.Name):
        out.add(node.id)
    elif isinstance(node, (ast.Tuple, ast.List)):
        for elt in node.elts:
            _target_names(elt, out)
    elif isinstance(node, ast.Starred):
        _target_names(node.value, out)


def _scan_opaque(node, opaque: set[str], excluded: set[str], in_comp: bool) -> None:
    if isinstance(node, _DEF_NODES) or isinstance(node, ast.Lambda):
        return  # own scope; names bound there do not leak
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return  # import origin, not opaque
    if isinstance(node, (ast.Global, ast.Nonlocal)):
        excluded.update(node.names)
        return
    if isinstance(node, _COMP_NODES):
        # Comprehensions are their own scope: their targets never leak, but a
        # walrus inside them binds in the enclosing function (PEP 572).
        for child in ast.iter_child_nodes(node):
            _scan_opaque(child, opaque, excluded, True)
        return
    if isinstance(node, ast.comprehension):
        _scan_opaque(node.iter, opaque, excluded, in_comp)
        for cond in node.ifs:
            _scan_opaque(cond, opaque, excluded, in_comp)
        return  # node.target deliberately skipped
    if isinstance(node, ast.NamedExpr):
        _target_names(node.target, opaque)
        _scan_opaque(node.value, opaque, excluded, in_comp)
        return
    if in_comp:
        for child in ast.iter_child_nodes(node):
            _scan_opaque(child, opaque, excluded, True)
        return
    if isinstance(node, ast.Assign):
        for target in node.targets:
            _target_names(target, opaque)
    elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
        _target_names(node.target, opaque)
    elif isinstance(node, (ast.For, ast.AsyncFor)):
        _target_names(node.target, opaque)
    elif isinstance(node, (ast.With, ast.AsyncWith)):
        for item in node.items:
            if item.optional_vars:
                _target_names(item.optional_vars, opaque)
    elif isinstance(node, ast.ExceptHandler) and node.name:
        opaque.add(node.name)
    elif isinstance(node, ast.MatchAs) and node.name:
        opaque.add(node.name)
    elif isinstance(node, ast.MatchStar) and node.name:
        opaque.add(node.name)
    elif isinstance(node, ast.MatchMapping) and node.rest:
        opaque.add(node.rest)
    for child in ast.iter_child_nodes(node):
        _scan_opaque(child, opaque, excluded, in_comp)


def _params_of(args: ast.arguments) -> set[str]:
    names = {a.arg for a in args.posonlyargs + args.args + args.kwonlyargs}
    if args.vararg:
        names.add(args.vararg.arg)
    if args.kwarg:
        names.add(args.kwarg.arg)
    return names


def local_bindings(func_node) -> set[str]:
    """Names bound opaquely (shadowing) in a function scope: params,
    assignments, loop/with/except/match targets, walrus — minus names
    declared global/nonlocal. Nested defs and local imports are excluded:
    they bind too, but resolvably (def/import origin)."""
    opaque = _params_of(func_node.args)
    excluded: set[str] = set()
    for stmt in func_node.body:
        _scan_opaque(stmt, opaque, excluded, False)
    return opaque - excluded


# --- project-wide resolver --------------------------------------------------


class Resolver:
    def __init__(
        self, symbols: dict[str, list[dict]], tables: dict[str, "ImportTable"]
    ):
        self.symbols = symbols
        self.tables = tables
        self.modules = set(tables)
        self.by_terminal: dict[str, list[str]] = defaultdict(list)
        for path in sorted(symbols):
            self.by_terminal[path.rsplit(".", 1)[-1]].append(path)

    def is_module(self, dotted: str) -> bool:
        return any(m == dotted or m.endswith("." + dotted) for m in self.modules)

    def module_anchor_exists(self, dotted: str) -> bool:
        """Does this dotted module string plausibly refer to an indexed
        module (exactly, or as a src-layout suffix)?"""
        return self.is_module(dotted)

    def terminal_matches(self, name: str) -> list[str]:
        return self.by_terminal.get(name, [])

    def resolve_dotted(
        self, dotted: str, *, _depth: int = 0, _seen: frozenset = frozenset()
    ) -> list[tuple[str, str | None]]:
        """Resolve a dotted target to indexed symbol paths.

        Returns [(symbol_path, note)] — note None for exact hits, a
        human-readable ambiguity note for suffix matches. Misses through
        re-exports are chased through the target module's own import
        table (pkg/__init__.py facades)."""
        if _depth > _MAX_CHASE_DEPTH or dotted in _seen:
            return []
        seen = _seen | {dotted}
        if dotted in self.symbols:
            return [(dotted, None)]
        results: list[tuple[str, str | None]] = []
        # Re-export chase: longest indexed-module prefix, remainder rebound
        # through that module's import table.
        parts = dotted.split(".")
        for cut in range(len(parts) - 1, 0, -1):
            module = ".".join(parts[:cut])
            if module not in self.tables:
                continue
            remainder = parts[cut:]
            for target in self.tables[module].resolve(remainder[0]):
                chased = ".".join([target] + remainder[1:])
                results.extend(
                    self.resolve_dotted(chased, _depth=_depth + 1, _seen=seen)
                )
            break  # only the longest module prefix is meaningful
        if results:
            return _dedupe_resolutions(results)
        # Src-layout suffix match: mypkg.config -> src.mypkg.config.
        for cut in range(len(parts), 0, -1):
            left = ".".join(parts[:cut])
            remainder = parts[cut:]
            for module in sorted(self.modules):
                if not module.endswith("." + left):
                    continue
                candidate = ".".join([module] + remainder)
                for path, _ in self.resolve_dotted(
                    candidate, _depth=_depth + 1, _seen=seen
                ):
                    results.append(
                        (path, "module path matched by suffix (src layout)")
                    )
            if results:
                return _dedupe_resolutions(results)
        return []

    def kind_of(self, path: str) -> str | None:
        records = self.symbols.get(path)
        return records[0]["kind"] if records else None


def _dedupe_resolutions(
    results: list[tuple[str, str | None]]
) -> list[tuple[str, str | None]]:
    best: dict[str, str | None] = {}
    for path, note in results:
        if path not in best or (best[path] is not None and note is None):
            best[path] = note
    return [(p, best[p]) for p in sorted(best)]


# --- reference walker -------------------------------------------------------


class _Frame:
    __slots__ = ("kind", "bindings", "class_path", "base_paths")

    def __init__(self, kind: str):
        self.kind = kind
        # name -> ("opaque", None) | ("import", tuple[str, ...]) | ("def", str)
        self.bindings: dict[str, tuple[str, object]] = {}
        self.class_path: str | None = None
        self.base_paths: list[str] = []

    def bind(self, name: str, origin: str, payload=None) -> None:
        # def > import > opaque: prefer resolvable origins so that a
        # module-level `f = wrap(f)` next to `def f` over-reports rather
        # than silencing the def.
        rank = {"def": 2, "import": 1, "opaque": 0}
        current = self.bindings.get(name)
        if current is None or rank[origin] >= rank[current[0]]:
            if current is not None and current[0] == "import" and origin == "import":
                payload = tuple(dict.fromkeys(current[1] + payload))
            self.bindings[name] = (origin, payload)


_AMBIG_RECEIVER = "attribute name match; receiver not statically resolvable"


class _Walker:
    def __init__(self, rel_path: str, mod_path: str, resolver: Resolver):
        self.rel_path = rel_path
        self.mod_path = mod_path
        self.resolver = resolver
        self.table = resolver.tables.get(mod_path) or ImportTable(mod_path)
        self.refs: list[tuple[str, dict]] = []
        self.unresolved: list[dict] = []
        self.frames: list[_Frame] = []
        self.sym_stack: list[str] = [mod_path]
        self._seen_refs: set = set()
        self._seen_unresolved: set = set()

    # -- record emission --

    def _record(self, node, target: str, kind: str, note: str | None, args=None):
        key = (target, node.lineno, node.col_offset, kind)
        if key in self._seen_refs:
            return
        self._seen_refs.add(key)
        record = {
            "file": self.rel_path,
            "line": node.lineno,
            "in_symbol": self.sym_stack[-1],
            "kind": kind,
        }
        if args is not None:
            record["args"] = args
        if note is not None:
            record["ambiguous"] = True
            record["note"] = note
        self.refs.append((target, record))

    def _flag(self, node, reason: str, expression: str | None = None):
        key = (node.lineno, node.col_offset, reason)
        if key in self._seen_unresolved:
            return
        self._seen_unresolved.add(key)
        self.unresolved.append(
            {
                "file": self.rel_path,
                "line": node.lineno,
                "in_symbol": self.sym_stack[-1],
                "reason": reason,
                "expression": expression
                if expression is not None
                else ast.unparse(node),
            }
        )

    # -- frame construction --

    def _module_frame(self, tree: ast.Module) -> _Frame:
        frame = _Frame("module")
        self._populate_scope_frame(frame, tree.body, self.mod_path)
        return frame

    def _function_frame(self, node) -> _Frame:
        frame = _Frame("function")
        for name in local_bindings(node):
            frame.bind(name, "opaque")
        path = f"{self.sym_stack[-1]}.{node.name}"
        self._populate_scope_frame(frame, node.body, path, opaque_assigns=False)
        return frame

    def _class_frame(self, node: ast.ClassDef, class_path: str) -> _Frame:
        frame = _Frame("class")
        frame.class_path = class_path
        for base in node.bases:
            frame.base_paths.extend(
                path
                for path, note in self._expr_symbol_paths(base)
                if note is None and self.resolver.kind_of(path) == "class"
            )
        self._populate_scope_frame(frame, node.body, class_path)
        return frame

    def _populate_scope_frame(
        self, frame: _Frame, body, prefix: str, *, opaque_assigns: bool = True
    ) -> None:
        local_table = ImportTable(self.mod_path)
        local_table._package_parts = self.table._package_parts
        for stmt in _scope_stmts(body):
            if isinstance(stmt, _DEF_NODES):
                frame.bind(stmt.name, "def", f"{prefix}.{stmt.name}")
            elif isinstance(stmt, (ast.Import, ast.ImportFrom)):
                local_table.add(stmt)
            elif opaque_assigns and isinstance(stmt, ast.Assign):
                names: set[str] = set()
                for target in stmt.targets:
                    _target_names(target, names)
                for name in names:
                    frame.bind(name, "opaque")
            elif opaque_assigns and isinstance(stmt, (ast.AnnAssign, ast.AugAssign)):
                names = set()
                _target_names(stmt.target, names)
                for name in names:
                    frame.bind(name, "opaque")
        for name, targets in local_table._bindings.items():
            frame.bind(name, "import", targets)

    # -- name / attribute resolution --

    def _lookup(self, name: str):
        """Find the binding for a name: walks frames innermost-out, skipping
        class frames unless the class body is the current scope (Python
        semantics: class scope does not enclose methods)."""
        top = len(self.frames) - 1
        for i in range(top, -1, -1):
            frame = self.frames[i]
            if frame.kind == "class" and i != top:
                continue
            if name in frame.bindings:
                return frame.bindings[name]
        return None

    def _enclosing_class(self) -> _Frame | None:
        for frame in reversed(self.frames):
            if frame.kind == "class":
                return frame
        return None

    def _name_targets(self, name: str) -> list[tuple[str, str | None]] | None:
        """Symbol paths a bare name refers to. None => opaque/unbound."""
        binding = self._lookup(name)
        if binding is None or binding[0] == "opaque":
            return None
        if binding[0] == "def":
            path = binding[1]
            return [(path, None)] if path in self.resolver.symbols else []
        results: list[tuple[str, str | None]] = []
        multi = len(binding[1]) > 1
        for target in binding[1]:
            for path, note in self.resolver.resolve_dotted(target):
                if multi and note is None:
                    note = "bound by multiple imports"
                results.append((path, note))
        return _dedupe_resolutions(results)

    def _expr_symbol_paths(self, expr) -> list[tuple[str, str | None]]:
        """Exact-ish symbol paths an expression statically denotes."""
        if isinstance(expr, ast.Name):
            return self._name_targets(expr.id) or []
        if isinstance(expr, ast.Attribute):
            parts = []
            cur = expr
            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr)
                cur = cur.value
            parts.reverse()
            if not isinstance(cur, ast.Name):
                return []
            base_binding = self._lookup(cur.id)
            if base_binding is None or base_binding[0] == "opaque":
                return []
            results: list[tuple[str, str | None]] = []
            if base_binding[0] == "def":
                bases = [(base_binding[1], None)]
            else:
                bases = [(t, None) for t in base_binding[1]]
            for base, base_note in bases:
                dotted = ".".join([base] + parts)
                for path, note in self.resolver.resolve_dotted(dotted):
                    results.append((path, note or base_note))
            return _dedupe_resolutions(results)
        return []

    def _fallback(self, node, terminal: str, kind: str, args, note: str):
        for path in self.resolver.terminal_matches(terminal):
            self._record(node, path, kind, note, args)

    def _resolve_attribute_use(self, attr: ast.Attribute, kind: str, args, site):
        """Emit references for an attribute chain in Load context. `site` is
        the node whose position anchors the record (the Call for calls)."""
        parts = []
        cur = attr
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        parts.reverse()
        terminal = parts[-1]

        if isinstance(cur, ast.Name):
            # self / cls inside a method resolve against the enclosing class.
            cls_frame = self._enclosing_class()
            if (
                cur.id in ("self", "cls")
                and cls_frame is not None
                and self._lookup(cur.id) == ("opaque", None)
            ):
                dotted = ".".join([cls_frame.class_path] + parts)
                hits = self.resolver.resolve_dotted(dotted)
                if hits:
                    for path, note in hits:
                        self._record(site, path, kind, note, args)
                    return
                for base_path in cls_frame.base_paths:
                    hits = self.resolver.resolve_dotted(
                        ".".join([base_path] + parts)
                    )
                    if hits:
                        for path, note in hits:
                            self._record(site, path, kind, note, args)
                        return
                self._fallback(
                    site,
                    terminal,
                    kind,
                    args,
                    "attribute of self; not found on class or direct bases",
                )
                return
            targets = self._name_targets(cur.id)
            if targets is None:
                self._fallback(site, terminal, kind, args, _AMBIG_RECEIVER)
                return
            # Compose against every dotted target the base name carries
            # (import targets may point outside the symbol table).
            emitted = False
            binding = self._lookup(cur.id)
            base_dotted: list[str] = []
            if binding[0] == "def":
                base_dotted = [binding[1]]
            elif binding[0] == "import":
                base_dotted = list(binding[1])
            for base in base_dotted:
                for path, note in self.resolver.resolve_dotted(
                    ".".join([base] + parts)
                ):
                    self._record(site, path, kind, note, args)
                    emitted = True
            if not emitted:
                self._fallback(site, terminal, kind, args, _AMBIG_RECEIVER)
            return

        if isinstance(cur, ast.Call):
            inner = cur
            if (
                isinstance(inner.func, ast.Name)
                and inner.func.id == "super"
                and self._lookup("super") is None
            ):
                cls_frame = self._enclosing_class()
                if cls_frame is None:
                    return
                for base_path in cls_frame.base_paths:
                    hits = self.resolver.resolve_dotted(
                        ".".join([base_path] + parts)
                    )
                    if hits:
                        for path, note in hits:
                            self._record(site, path, kind, note, args)
                        return
                if cls_frame.base_paths:
                    self._fallback(
                        site,
                        terminal,
                        kind,
                        args,
                        "resolved via super(); exact base chain unknown",
                    )
                return  # external hierarchy: no in-repo edge can hide here
            callee_paths = [
                path
                for path, note in self._expr_symbol_paths(inner.func)
                if self.resolver.kind_of(path) == "class"
            ]
            emitted = False
            for cls_path in callee_paths:
                for path, note in self.resolver.resolve_dotted(
                    ".".join([cls_path] + parts)
                ):
                    self._record(site, path, kind, note, args)
                    emitted = True
            if emitted:
                return
            if callee_paths:
                self._fallback(
                    site,
                    terminal,
                    kind,
                    args,
                    "method not found on constructed class; possibly inherited",
                )
                return
            # External or opaque factory (open(p).read()): exact resolution is
            # impossible, but a terminal name matching nothing indexed cannot
            # hide an in-repo edge — name-match, else stay silent (plan A5).
            self._fallback(site, terminal, kind, args, _AMBIG_RECEIVER)
            return

        # Subscript / literal / anything else as receiver.
        self._fallback(site, terminal, kind, args, _AMBIG_RECEIVER)

    # -- visitation --

    def visit_module(self, tree: ast.Module) -> None:
        self.frames.append(self._module_frame(tree))
        for stmt in tree.body:
            self.visit(stmt)
        self.frames.pop()

    def visit(self, node) -> None:
        method = getattr(self, f"_visit_{type(node).__name__}", None)
        if method is not None:
            method(node)
            return
        for child in ast.iter_child_nodes(node):
            self.visit(child)

    def _visit_FunctionDef(self, node) -> None:
        for deco in node.decorator_list:
            self.visit(deco)
        self._visit_arg_annotations_and_defaults(node.args)
        if node.returns is not None:
            self.visit(node.returns)
        if node.name in _DYNAMIC_DUNDERS:
            # setattr / __getattr__ definitions make attribute traffic in
            # this file statically undecidable (brief §3).
            self._flag(node, "dynamic_attribute", f"def {node.name}(...)")
        path = f"{self.sym_stack[-1]}.{node.name}"
        self.frames.append(self._function_frame(node))
        self.sym_stack.append(path)
        for stmt in node.body:
            self.visit(stmt)
        self.sym_stack.pop()
        self.frames.pop()

    _visit_AsyncFunctionDef = _visit_FunctionDef

    def _visit_arg_annotations_and_defaults(self, args: ast.arguments) -> None:
        for arg in args.posonlyargs + args.args + args.kwonlyargs:
            if arg.annotation is not None:
                self.visit(arg.annotation)
        for arg in (args.vararg, args.kwarg):
            if arg is not None and arg.annotation is not None:
                self.visit(arg.annotation)
        for default in list(args.defaults) + [
            d for d in args.kw_defaults if d is not None
        ]:
            self.visit(default)

    def _visit_ClassDef(self, node: ast.ClassDef) -> None:
        for deco in node.decorator_list:
            self.visit(deco)
        for base in node.bases:
            self.visit(base)
        for kw in node.keywords:
            self.visit(kw.value)
        path = f"{self.sym_stack[-1]}.{node.name}"
        self.frames.append(self._class_frame(node, path))
        self.sym_stack.append(path)
        for stmt in node.body:
            self.visit(stmt)
        self.sym_stack.pop()
        self.frames.pop()

    def _visit_Lambda(self, node: ast.Lambda) -> None:
        self._visit_arg_annotations_and_defaults(node.args)
        frame = _Frame("function")
        for name in _params_of(node.args):
            frame.bind(name, "opaque")
        self.frames.append(frame)
        self.visit(node.body)
        self.frames.pop()

    def _visit_comprehension_scope(self, node) -> None:
        frame = _Frame("comprehension")
        for gen in node.generators:
            names: set[str] = set()
            _target_names(gen.target, names)
            for name in names:
                frame.bind(name, "opaque")
        self.frames.append(frame)
        for child in ast.iter_child_nodes(node):
            self.visit(child)
        self.frames.pop()

    _visit_ListComp = _visit_comprehension_scope
    _visit_SetComp = _visit_comprehension_scope
    _visit_DictComp = _visit_comprehension_scope
    _visit_GeneratorExp = _visit_comprehension_scope

    def _visit_Import(self, node: ast.Import) -> None:
        pass  # module objects are not symbols; uses are resolved at use sites

    def _visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if any(alias.name == "*" for alias in node.names):
            self._flag(node, "star_import")
            return
        base = self.table.base_of(node)
        for alias in node.names:
            target = f"{base}.{alias.name}" if base else alias.name
            if self.resolver.is_module(target):
                continue  # `from pkg import submodule`
            hits = self.resolver.resolve_dotted(target)
            for path, note in hits:
                self._record(node, path, "name", note)
            if not hits and base and self.resolver.module_anchor_exists(base):
                # The module is ours but the name resolves nowhere: flag it
                # rather than silently dropping a possible in-repo edge.
                self._flag(node, "unresolved_import_target")

    def _visit_Call(self, node: ast.Call) -> None:
        func = node.func
        args_written = [ast.unparse(a) for a in node.args] + [
            f"{kw.arg}={ast.unparse(kw.value)}"
            if kw.arg is not None
            else f"**{ast.unparse(kw.value)}"
            for kw in node.keywords
        ]
        if isinstance(func, ast.Subscript):
            self._flag(node, "subscript_call")
            self.visit(func)
        elif isinstance(func, ast.Call):
            if (
                isinstance(func.func, ast.Name)
                and func.func.id == "getattr"
                and self._lookup("getattr") is None
            ):
                self._flag(node, "getattr_call")
            else:
                self._flag(node, "attribute_of_call")
            self.visit(func)
        elif isinstance(func, ast.Name):
            binding = self._lookup(func.id)
            if func.id == "getattr" and binding is None:
                self._flag(node, "getattr_call")
            elif func.id == "setattr" and binding is None:
                self._flag(node, "dynamic_attribute")
            else:
                targets = self._name_targets(func.id)
                for path, note in targets or []:
                    self._record(node, path, "call", note, args_written)
        elif isinstance(func, ast.Attribute):
            self._resolve_attribute_use(func, "call", args_written, node)
            self.visit(func.value)
        else:
            self.visit(func)
        for arg in node.args:
            self.visit(arg)
        for kw in node.keywords:
            self.visit(kw.value)

    def _visit_Name(self, node: ast.Name) -> None:
        if not isinstance(node.ctx, ast.Load):
            return
        for path, note in self._name_targets(node.id) or []:
            self._record(node, path, "name", note)

    def _visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.ctx, ast.Load):
            self._resolve_attribute_use(node, "name", None, node)
        self.visit(node.value)


def collect_references(
    tree: ast.Module, rel_path: str, mod_path: str, resolver: Resolver
) -> tuple[list[tuple[str, dict]], list[dict]]:
    walker = _Walker(rel_path, mod_path, resolver)
    walker.visit_module(tree)
    return walker.refs, walker.unresolved
