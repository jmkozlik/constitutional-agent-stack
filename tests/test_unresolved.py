import ast
from collections import defaultdict

from analyzer.modpath import module_path
from analyzer.refs import ImportTable, Resolver, collect_references
from analyzer.symbols import extract_symbols


def unresolved_in(source: str, rel_path: str = "src/router.py"):
    mod = module_path(rel_path)
    tree = ast.parse(source)
    symbols = defaultdict(list)
    for record in extract_symbols(source.encode(), rel_path):
        symbols[record["path"]].append(record)
    resolver = Resolver(
        dict(symbols), {mod: ImportTable.from_module(tree, mod, is_package=False)}
    )
    _, unres = collect_references(tree, rel_path, mod, resolver)
    return unres


def test_subscript_call():
    (rec,) = unresolved_in(
        "def dispatch(name, payload):\n    return HANDLERS[name](payload)\n"
    )
    assert rec["reason"] == "subscript_call"
    assert rec["expression"] == "HANDLERS[name](payload)"
    assert rec["in_symbol"] == "src.router.dispatch"
    assert rec["line"] == 2


def test_getattr_call_immediately_called():
    (rec,) = unresolved_in("def go(obj, name):\n    return getattr(obj, name)()\n")
    assert rec["reason"] == "getattr_call"


def test_bare_getattr_flagged():
    (rec,) = unresolved_in("def go(obj, name):\n    f = getattr(obj, name)\n    return f\n")
    assert rec["reason"] == "getattr_call"


def test_locally_defined_getattr_not_flagged():
    records = unresolved_in(
        "def getattr(a, b):\n    return 1\n\ndef go(obj):\n    return getattr(obj, 'x')\n"
    )
    assert records == []


def test_call_of_call():
    (rec,) = unresolved_in("def go(factory):\n    return factory()('x')\n")
    assert rec["reason"] == "attribute_of_call"


def test_star_import():
    (rec,) = unresolved_in("from os.path import *\n")
    assert rec["reason"] == "star_import"
    assert rec["line"] == 1


def test_setattr_flagged_dynamic():
    (rec,) = unresolved_in("def go(o):\n    setattr(o, 'k', 1)\n")
    assert rec["reason"] == "dynamic_attribute"


def test_dunder_getattr_def_flagged():
    (rec,) = unresolved_in("def __getattr__(name):\n    return 1\n")
    assert rec["reason"] == "dynamic_attribute"


def test_class_dunder_getattr_flagged():
    (rec,) = unresolved_in(
        "class Proxy:\n    def __getattr__(self, name):\n        return 1\n"
    )
    assert rec["reason"] == "dynamic_attribute"


def test_ordinary_chained_stdlib_call_not_flagged():
    assert unresolved_in("def go(p):\n    return open(p).read()\n") == []


def test_super_call_not_flagged():
    records = unresolved_in(
        "class Base:\n"
        "    def setup(self):\n"
        "        return 1\n"
        "class Child(Base):\n"
        "    def setup(self):\n"
        "        return super().setup()\n"
    )
    assert records == []
