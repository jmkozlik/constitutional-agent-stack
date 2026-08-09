from analyzer.modpath import module_path


def test_plain_module():
    assert module_path("src/config.py") == "src.config"


def test_top_level_module():
    assert module_path("main.py") == "main"


def test_package_init():
    assert module_path("pkg/__init__.py") == "pkg"


def test_nested_package_init():
    assert module_path("a/b/__init__.py") == "a.b"
