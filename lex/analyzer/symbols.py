"""Pass 1: walk one file's AST and emit a symbol record per definition.

Records here carry everything except `confidence` and `referenced_by`,
which the indexer merges in after pass 2.
"""

import ast
import hashlib

from analyzer.modpath import module_path

_DEF_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


class ParseFailure(Exception):
    def __init__(self, rel_path: str, error: Exception):
        super().__init__(f"{rel_path}: {error}")
        self.rel_path = rel_path
        self.error = error


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:8]


def _param(arg: ast.arg, has_default: bool) -> str:
    ann = ast.unparse(arg.annotation) if arg.annotation else ""
    return f"{arg.arg}:{ann}:{'=' if has_default else ''}"


def _sig_canonical(node: ast.AST) -> str:
    # Identity covers: name, parameter names, parameter annotations, defaults
    # PRESENCE (not values), return annotation (brief §1). Documented
    # deviation (plan A11): positional-only "/", bare "*" and */** markers are
    # included too — f(a, b) -> f(a, *, b) breaks call sites and must not
    # classify as merely "moved".
    if isinstance(node, ast.ClassDef):
        # Class analog: bases and keywords (metaclass) are its "parameters" —
        # changing a base changes what callers get, so it is signature-level.
        parts = [ast.unparse(b) for b in node.bases]
        parts += [f"{kw.arg}={ast.unparse(kw.value)}" for kw in node.keywords]
        return f"{node.name}({','.join(parts)})"
    a = node.args
    pos = a.posonlyargs + a.args
    first_default = len(pos) - len(a.defaults)
    parts = [_param(arg, i >= first_default) for i, arg in enumerate(pos)]
    if a.posonlyargs:
        parts.insert(len(a.posonlyargs), "/")
    if a.vararg:
        parts.append("*" + _param(a.vararg, False))
    elif a.kwonlyargs:
        parts.append("*")
    parts += [
        _param(arg, default is not None)
        for arg, default in zip(a.kwonlyargs, a.kw_defaults)
    ]
    if a.kwarg:
        parts.append("**" + _param(a.kwarg, False))
    ret = ast.unparse(node.returns) if node.returns else ""
    return f"{node.name}({','.join(parts)})->{ret}"


def _param_display(arg: ast.arg, default: ast.AST | None) -> str:
    out = arg.arg
    if arg.annotation:
        out += f": {ast.unparse(arg.annotation)}"
    if default is not None:
        # PEP 8: spaces around = only when the parameter is annotated.
        out += f" = {ast.unparse(default)}" if arg.annotation else f"={ast.unparse(default)}"
    return out


def _signature_display(node: ast.AST) -> str:
    if isinstance(node, ast.ClassDef):
        parts = [ast.unparse(b) for b in node.bases]
        parts += [f"{kw.arg}={ast.unparse(kw.value)}" for kw in node.keywords]
        return f"({', '.join(parts)})" if parts else ""
    a = node.args
    pos = a.posonlyargs + a.args
    defaults = [None] * (len(pos) - len(a.defaults)) + list(a.defaults)
    parts = [_param_display(arg, d) for arg, d in zip(pos, defaults)]
    if a.posonlyargs:
        parts.insert(len(a.posonlyargs), "/")
    if a.vararg:
        parts.append("*" + _param_display(a.vararg, None))
    elif a.kwonlyargs:
        parts.append("*")
    parts += [_param_display(arg, d) for arg, d in zip(a.kwonlyargs, a.kw_defaults)]
    if a.kwarg:
        parts.append("**" + _param_display(a.kwarg, None))
    sig = f"({', '.join(parts)})"
    if node.returns:
        sig += f" -> {ast.unparse(node.returns)}"
    return sig


def _body_hash(node: ast.AST) -> str:
    # Unparsing the AST drops comments/blank lines/formatting for free
    # (brief, notes for the implementer). Docstrings are body, not comments,
    # so they participate.
    return _hash("\n".join(ast.unparse(stmt) for stmt in node.body))


def _class_fields(node: ast.ClassDef) -> list[str]:
    """Annotated class-body targets in body order, rendered like parameters
    (`name: annotation = default`, defaults verbatim) — the field list a
    spec surface's type entry seeds from."""
    fields = []
    for stmt in node.body:
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            rendered = f"{stmt.target.id}: {ast.unparse(stmt.annotation)}"
            if stmt.value is not None:
                rendered += f" = {ast.unparse(stmt.value)}"
            fields.append(rendered)
    return fields


def _kind(node: ast.AST) -> str:
    if isinstance(node, ast.ClassDef):
        return "class"
    if isinstance(node, ast.AsyncFunctionDef):
        return "async_function"
    return "function"


def extract_symbols(source: bytes, rel_path: str) -> list[dict]:
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError) as e:
        raise ParseFailure(rel_path, e) from e
    return extract_from_tree(tree, rel_path)


def extract_from_tree(tree: ast.Module, rel_path: str) -> list[dict]:
    records: list[dict] = []
    # TODO(brief open question): module-level constants are not indexed as
    # symbols; only def/async def/class produce records.
    _visit(tree, module_path(rel_path), rel_path, records)
    return records


def _visit(node: ast.AST, prefix: str, rel_path: str, records: list[dict]) -> None:
    for child in ast.iter_child_nodes(node):
        if isinstance(child, _DEF_NODES):
            path = f"{prefix}.{child.name}"
            start = child.lineno
            if child.decorator_list:
                start = min(start, child.decorator_list[0].lineno)
            record = {
                    "path": path,
                    "kind": _kind(child),
                    "file": rel_path,
                    "start_line": start,
                    "end_line": child.end_lineno,
                    "signature": _signature_display(child),
                    "doc": ast.get_docstring(child),
                    "sig_hash": _hash(_sig_canonical(child)),
                    "body_hash": _body_hash(child),
                    # Not part of the brief's identity triple; lets `affected`
                    # surface decorator-only edits that both hashes are blind
                    # to (plan amendment A9).
                    "decor_hash": _hash(
                        "\n".join(ast.unparse(d) for d in child.decorator_list)
                    ),
                    "parent": prefix,
                }
            if isinstance(child, ast.ClassDef):
                record["fields"] = _class_fields(child)
            records.append(record)
            # TODO(brief open question): nested functions currently get their
            # own entries, dotted through the enclosing function; the
            # alternative is folding them into the parent (their source is
            # already part of the parent's body_hash either way).
            _visit(child, path, rel_path, records)
        else:
            # Defs inside if/try/with blocks keep the enclosing scope's path.
            _visit(child, prefix, rel_path, records)
