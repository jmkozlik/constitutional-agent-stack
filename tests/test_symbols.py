import pytest

from analyzer.symbols import ParseFailure, extract_symbols


def syms(source: str, rel_path: str = "src/config.py") -> dict[str, dict]:
    records = extract_symbols(source.encode(), rel_path)
    return {r["path"]: r for r in records}


def test_method_dotted_path_and_parent():
    s = syms("class Loader:\n    def load(self):\n        pass\n")
    assert s["src.config.Loader"]["parent"] == "src.config"
    assert s["src.config.Loader"]["kind"] == "class"
    method = s["src.config.Loader.load"]
    assert method["parent"] == "src.config.Loader"
    assert method["kind"] == "function"
    assert method["file"] == "src/config.py"


def test_decorator_extends_start_line():
    s = syms("import x\n\n@x.deco\ndef f():\n    pass\n")
    assert s["src.config.f"]["start_line"] == 3
    assert s["src.config.f"]["end_line"] == 5


def test_async_function_kind():
    s = syms("async def go():\n    pass\n")
    assert s["src.config.go"]["kind"] == "async_function"


def test_sig_hash_ignores_default_value_change():
    a = syms("def f(path: str, strict: bool = False):\n    pass\n")
    b = syms("def f(path: str, strict: bool = True):\n    pass\n")
    assert a["src.config.f"]["sig_hash"] == b["src.config.f"]["sig_hash"]


def test_sig_hash_changes_on_param_rename():
    a = syms("def f(path):\n    pass\n")
    b = syms("def f(path2):\n    pass\n")
    assert a["src.config.f"]["sig_hash"] != b["src.config.f"]["sig_hash"]


def test_sig_hash_changes_on_annotation_change():
    a = syms("def f(path: str):\n    pass\n")
    b = syms("def f(path: Path):\n    pass\n")
    assert a["src.config.f"]["sig_hash"] != b["src.config.f"]["sig_hash"]


def test_sig_hash_changes_on_default_presence():
    a = syms("def f(strict: bool):\n    pass\n")
    b = syms("def f(strict: bool = False):\n    pass\n")
    assert a["src.config.f"]["sig_hash"] != b["src.config.f"]["sig_hash"]


def test_sig_hash_changes_on_return_annotation():
    a = syms("def f() -> int:\n    pass\n")
    b = syms("def f() -> str:\n    pass\n")
    assert a["src.config.f"]["sig_hash"] != b["src.config.f"]["sig_hash"]


def test_sig_hash_ignores_decorators_and_body():
    a = syms("@deco\ndef f(x):\n    return 1\n")
    b = syms("def f(x):\n    return 2\n")
    assert a["src.config.f"]["sig_hash"] == b["src.config.f"]["sig_hash"]


def test_body_hash_survives_reformat_and_comments():
    a = syms("def f(x):\n    return {'a': 1, 'b': 2}\n")
    b = syms(
        "def f(x):\n"
        "    # a comment\n"
        "\n"
        "    return {\n"
        "        'a': 1,\n"
        "        'b': 2,\n"
        "    }\n"
    )
    assert a["src.config.f"]["body_hash"] == b["src.config.f"]["body_hash"]


def test_body_hash_changes_on_docstring_change():
    a = syms('def f():\n    """one"""\n')
    b = syms('def f():\n    """two"""\n')
    assert a["src.config.f"]["body_hash"] != b["src.config.f"]["body_hash"]


def test_nested_function_indexed_through_parent():
    s = syms("def outer():\n    def inner():\n        pass\n    return inner\n")
    assert "src.config.outer.inner" in s
    assert s["src.config.outer.inner"]["parent"] == "src.config.outer"


def test_def_inside_conditional_still_indexed():
    s = syms("if True:\n    def f():\n        pass\n")
    assert s["src.config.f"]["parent"] == "src.config"


def test_signature_display_string():
    s = syms("def f(path: str, strict: bool = False) -> dict[str, str]:\n    pass\n")
    assert s["src.config.f"]["signature"] == "(path: str, strict: bool = False) -> dict[str, str]"


def test_class_sig_hash_covers_bases():
    a = syms("class C(Base):\n    pass\n")
    b = syms("class C(Other):\n    pass\n")
    assert a["src.config.C"]["sig_hash"] != b["src.config.C"]["sig_hash"]


def test_parse_failure_raises():
    with pytest.raises(ParseFailure):
        extract_symbols(b"def broken(:\n", "src/bad.py")
