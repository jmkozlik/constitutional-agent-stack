import ast
from collections import defaultdict

from analyzer.modpath import module_path
from analyzer.refs import (
    ImportTable,
    Resolver,
    collect_references,
    local_bindings,
)
from analyzer.symbols import extract_symbols


# --- import table -----------------------------------------------------------


def imports(source: str, mod: str = "src.app", is_package: bool = False) -> ImportTable:
    return ImportTable.from_module(ast.parse(source), mod, is_package=is_package)


def test_plain_import_binds_top_name():
    assert imports("import src.config\n").resolve("src") == ("src",)


def test_import_as_binds_alias_to_full_path():
    assert imports("import src.config as cfg\n").resolve("cfg") == ("src.config",)


def test_from_import():
    t = imports("from src.config import load_settings\n")
    assert t.resolve("load_settings") == ("src.config.load_settings",)


def test_from_import_as():
    t = imports("from src.config import load_settings as ls\n")
    assert t.resolve("ls") == ("src.config.load_settings",)


def test_relative_import_from_module():
    t = imports("from . import util\n", mod="pkg.mod")
    assert t.resolve("util") == ("pkg.util",)


def test_relative_import_from_package_init():
    t = imports("from . import util\n", mod="pkg", is_package=True)
    assert t.resolve("util") == ("pkg.util",)


def test_relative_from_import_in_package_init():
    t = imports("from .config import load_settings\n", mod="pkg", is_package=True)
    assert t.resolve("load_settings") == ("pkg.config.load_settings",)


def test_relative_import_two_levels():
    t = imports("from ..config import load_settings\n", mod="pkg.sub.mod")
    assert t.resolve("load_settings") == ("pkg.config.load_settings",)


def test_dual_import_keeps_both_targets():
    t = imports(
        "try:\n"
        "    from src._speedups import escape\n"
        "except ImportError:\n"
        "    from src._native import escape\n"
    )
    assert set(t.resolve("escape")) == {
        "src._speedups.escape",
        "src._native.escape",
    }


def test_star_import_sets_flag():
    assert imports("from src.config import *\n").has_star


def test_unknown_name_resolves_empty():
    assert imports("import os\n").resolve("nothing") == ()


# --- local (opaque) bindings ------------------------------------------------


def func(source: str) -> ast.FunctionDef:
    return ast.parse(source).body[0]


def test_local_bindings_params_and_assignments():
    node = func("def f(a, b=1, *args, **kw):\n    c = 2\n    d, e = 3, 4\n")
    assert {"a", "b", "args", "kw", "c", "d", "e"} <= local_bindings(node)


def test_local_bindings_targets():
    node = func(
        "def f(xs):\n"
        "    for i in xs:\n"
        "        pass\n"
        "    with open('x') as fh:\n"
        "        pass\n"
        "    try:\n"
        "        pass\n"
        "    except ValueError as err:\n"
        "        pass\n"
        "    (z := 1)\n"
    )
    assert {"i", "fh", "err", "z"} <= local_bindings(node)


def test_comprehension_targets_do_not_leak():
    node = func("def f(xs):\n    ys = [y for y in xs]\n    return ys\n")
    bound = local_bindings(node)
    assert "ys" in bound
    assert "y" not in bound


def test_global_names_excluded():
    node = func("def f():\n    global api\n    api = 1\n")
    assert "api" not in local_bindings(node)


def test_nested_defs_and_imports_are_not_opaque():
    node = func(
        "def f():\n"
        "    import json\n"
        "    def g():\n"
        "        pass\n"
        "    class C:\n"
        "        pass\n"
    )
    bound = local_bindings(node)
    assert "g" not in bound and "C" not in bound and "json" not in bound


def test_bindings_do_not_leak_from_nested_scope():
    node = func("def f():\n    def g():\n        inner_only = 1\n")
    assert "inner_only" not in local_bindings(node)


# --- reference resolution ---------------------------------------------------


def build(files: dict[str, str]):
    trees, symbols, tables = {}, defaultdict(list), {}
    for rel, src in files.items():
        mod = module_path(rel)
        trees[rel] = (ast.parse(src), mod, rel.endswith("__init__.py"))
        for record in extract_symbols(src.encode(), rel):
            symbols[record["path"]].append(record)
    for rel, (tree, mod, is_pkg) in trees.items():
        tables[mod] = ImportTable.from_module(tree, mod, is_package=is_pkg)
    resolver = Resolver(dict(symbols), tables)
    refs = defaultdict(list)
    unresolved = []
    for rel in sorted(trees):
        tree, mod, is_pkg = trees[rel]
        found, unres = collect_references(tree, rel, mod, resolver)
        for target, record in found:
            refs[target].append(record)
        unresolved.extend(unres)
    return refs, unresolved


CONFIG = (
    "def load_settings(path, strict=False):\n"
    "    return {}\n"
    "\n"
    "\n"
    "class Loader:\n"
    "    def load(self):\n"
    "        return 1\n"
)


def test_direct_call_records_args_as_written():
    refs, _ = build(
        {
            "src/config.py": CONFIG,
            "src/app.py": (
                "from src.config import load_settings\n"
                "def boot():\n"
                "    return load_settings('./conf.yml', strict=True)\n"
            ),
        }
    )
    call_sites = [r for r in refs["src.config.load_settings"] if r["kind"] == "call"]
    (site,) = call_sites
    assert site["file"] == "src/app.py"
    assert site["line"] == 3
    assert site["in_symbol"] == "src.app.boot"
    assert site["args"] == ["'./conf.yml'", "strict=True"]


def test_imported_alias_attribute_call():
    refs, _ = build(
        {
            "src/config.py": CONFIG,
            "src/app.py": (
                "import src.config as cfg\n"
                "def boot(p):\n"
                "    return cfg.load_settings(p)\n"
            ),
        }
    )
    (site,) = refs["src.config.load_settings"]
    assert site["kind"] == "call"
    assert site["args"] == ["p"]
    assert not site.get("ambiguous")


def test_full_dotted_attribute_call():
    refs, _ = build(
        {
            "src/config.py": CONFIG,
            "src/app.py": (
                "import src.config\n"
                "def boot(p):\n"
                "    return src.config.load_settings(p)\n"
            ),
        }
    )
    assert len([r for r in refs["src.config.load_settings"] if r["kind"] == "call"]) == 1


def test_local_shadowing_not_a_reference():
    refs, _ = build(
        {
            "src/config.py": CONFIG,
            "src/app.py": "def boot(load_settings):\n    return load_settings('x')\n",
        }
    )
    assert refs["src.config.load_settings"] == []


def test_same_module_call_resolves():
    refs, _ = build(
        {"src/config.py": CONFIG + "\n\ndef reload():\n    return load_settings('d')\n"}
    )
    (site,) = refs["src.config.load_settings"]
    assert site["in_symbol"] == "src.config.reload"


def test_nested_def_call_from_defining_scope_resolves():
    refs, _ = build(
        {
            "src/app.py": (
                "def process(items):\n"
                "    def validate(i):\n"
                "        return i\n"
                "    return [validate(i) for i in items]\n"
            ),
        }
    )
    sites = refs["src.app.process.validate"]
    assert len(sites) == 1
    assert sites[0]["in_symbol"] == "src.app.process"


def test_global_rebind_read_is_a_reference():
    refs, _ = build(
        {
            "src/app.py": (
                "def api():\n"
                "    return 1\n"
                "def install(wrapped):\n"
                "    global api\n"
                "    api = wrapped(api)\n"
            ),
        }
    )
    sites = refs["src.app.api"]
    assert any(s["in_symbol"] == "src.app.install" for s in sites)


def test_comprehension_target_does_not_shadow_module_symbol():
    refs, _ = build(
        {
            "src/app.py": (
                "def config():\n"
                "    return {}\n"
                "def collect(sections):\n"
                "    d = {config: 1 for config in sections}\n"
                "    return config()\n"
            ),
        }
    )
    sites = refs["src.app.config"]
    assert any(s["kind"] == "call" and s["line"] == 5 for s in sites)


def test_self_method_call_resolves_to_class():
    refs, _ = build(
        {
            "src/config.py": (
                "class Loader:\n"
                "    def load(self):\n"
                "        return 1\n"
                "    def load_twice(self):\n"
                "        return self.load() + self.load()\n"
            ),
        }
    )
    sites = refs["src.config.Loader.load"]
    assert len(sites) == 2
    assert all(s["in_symbol"] == "src.config.Loader.load_twice" for s in sites)
    assert not any(s.get("ambiguous") for s in sites)


def test_class_instantiation_is_reference():
    refs, _ = build(
        {
            "src/config.py": CONFIG,
            "src/app.py": (
                "from src.config import Loader\n"
                "def boot():\n"
                "    return Loader()\n"
            ),
        }
    )
    assert len([r for r in refs["src.config.Loader"] if r["kind"] == "call"]) == 1


def test_constructor_then_method_resolves():
    refs, _ = build(
        {
            "src/config.py": CONFIG,
            "src/app.py": (
                "from src.config import Loader\n"
                "def boot():\n"
                "    return Loader().load()\n"
            ),
        }
    )
    (site,) = refs["src.config.Loader.load"]
    assert not site.get("ambiguous")


def test_inherited_method_call_not_silently_dropped():
    refs, _ = build(
        {
            "src/config.py": CONFIG,
            "src/sub.py": (
                "from src.config import Loader\n"
                "class Derived(Loader):\n"
                "    pass\n"
            ),
            "src/app.py": (
                "from src.sub import Derived\n"
                "def boot():\n"
                "    return Derived().load()\n"
            ),
        }
    )
    sites = [s for s in refs["src.config.Loader.load"] if s["file"] == "src/app.py"]
    assert len(sites) == 1
    assert sites[0]["ambiguous"] is True


def test_super_call_resolves_through_local_base():
    refs, _ = build(
        {
            "src/app.py": (
                "class Base:\n"
                "    def setup(self):\n"
                "        return 1\n"
                "class Child(Base):\n"
                "    def setup(self):\n"
                "        return super().setup() + 1\n"
            ),
        }
    )
    base_sites = [
        s for s in refs["src.app.Base.setup"] if s["in_symbol"] == "src.app.Child.setup"
    ]
    assert len(base_sites) == 1
    assert not base_sites[0].get("ambiguous")


def test_external_chained_call_is_silent(tmp_path=None):
    refs, unresolved = build(
        {
            "src/config.py": CONFIG,
            "src/app.py": (
                "def boot(path):\n"
                "    return open(path).read()\n"
            ),
        }
    )
    assert all(not sites or "read" not in t for t, sites in refs.items())
    assert unresolved == []


def test_unknown_receiver_matches_methods_and_functions():
    refs, _ = build(
        {
            "src/config.py": CONFIG,
            "src/plugins.py": "def setup():\n    return 1\n",
            "src/app.py": (
                "def boot(obj, plugin_module):\n"
                "    obj.load()\n"
                "    plugin_module.setup()\n"
            ),
        }
    )
    (load_site,) = refs["src.config.Loader.load"]
    assert load_site["ambiguous"] is True and "note" in load_site
    (setup_site,) = refs["src.plugins.setup"]
    assert setup_site["ambiguous"] is True


def test_reexport_chase_through_init():
    refs, _ = build(
        {
            "pkg/__init__.py": "from .config import load_settings\n",
            "pkg/config.py": "def load_settings(path):\n    return {}\n",
            "src/app.py": (
                "from pkg import load_settings\n"
                "def boot(p):\n"
                "    return load_settings(p)\n"
            ),
        }
    )
    call_sites = [
        r
        for r in refs["pkg.config.load_settings"]
        if r["kind"] == "call" and r["file"] == "src/app.py"
    ]
    assert len(call_sites) == 1


def test_src_layout_suffix_match():
    refs, _ = build(
        {
            "src/mypkg/config.py": "def load_settings(path):\n    return {}\n",
            "tools/run.py": (
                "from mypkg.config import load_settings\n"
                "def go(p):\n"
                "    return load_settings(p)\n"
            ),
        }
    )
    call_sites = [
        r for r in refs["src.mypkg.config.load_settings"] if r["kind"] == "call"
    ]
    assert len(call_sites) == 1
    assert call_sites[0]["ambiguous"] is True


def test_internal_looking_import_miss_is_flagged():
    _, unresolved = build(
        {
            "src/mypkg/config.py": "def load_settings(path):\n    return {}\n",
            "tools/run.py": "from mypkg.config import does_not_exist\n",
        }
    )
    assert any(u["reason"] == "unresolved_import_target" for u in unresolved)


def test_external_import_miss_is_silent():
    _, unresolved = build(
        {
            "src/config.py": CONFIG,
            "src/app.py": "from requests import get\ndef boot():\n    return get('x')\n",
        }
    )
    assert unresolved == []


def test_decorator_is_reference():
    refs, _ = build(
        {
            "src/config.py": "def register(f):\n    return f\n",
            "src/app.py": (
                "from src.config import register\n"
                "@register\n"
                "def task():\n"
                "    pass\n"
            ),
        }
    )
    deco_sites = [r for r in refs["src.config.register"] if r["line"] == 2]
    assert len(deco_sites) == 1
    assert deco_sites[0]["kind"] == "name"
    assert "args" not in deco_sites[0]


def test_base_class_is_reference():
    refs, _ = build(
        {
            "src/config.py": CONFIG,
            "src/app.py": (
                "from src.config import Loader\n"
                "class Mine(Loader):\n"
                "    pass\n"
            ),
        }
    )
    assert any(r["line"] == 2 for r in refs["src.config.Loader"])


def test_function_passed_as_value_kind_name():
    refs, _ = build(
        {
            "src/config.py": CONFIG,
            "src/app.py": (
                "from src.config import load_settings\n"
                "def boot(run):\n"
                "    return run(callback=load_settings)\n"
            ),
        }
    )
    value_sites = [r for r in refs["src.config.load_settings"] if r["line"] == 3]
    (site,) = value_sites
    assert site["kind"] == "name"
    assert "args" not in site


def test_module_level_reference_in_symbol_is_module():
    refs, _ = build(
        {
            "src/config.py": CONFIG,
            "src/app.py": (
                "from src.config import load_settings\n"
                "SETTINGS = load_settings('boot.yml')\n"
            ),
        }
    )
    call_sites = [r for r in refs["src.config.load_settings"] if r["kind"] == "call"]
    assert call_sites[0]["in_symbol"] == "src.app"


def test_import_itself_is_a_name_reference():
    refs, _ = build(
        {
            "src/config.py": CONFIG,
            "src/app.py": "from src.config import load_settings\n",
        }
    )
    (site,) = refs["src.config.load_settings"]
    assert site["kind"] == "name"
    assert site["line"] == 1
