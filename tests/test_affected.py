from analyzer.affected import compute_affected
from tests.conftest import commit_all, git, make_repo, run_cli

BASE = {
    "src/config.py": (
        "def load_settings(path, strict=False):\n"
        "    return {'path': path}\n"
        "\n"
        "\n"
        "class Loader:\n"
        "    def parse(self):\n"
        "        return 1\n"
    ),
    "src/app.py": (
        "from src.config import load_settings\n"
        "\n"
        "\n"
        "def boot():\n"
        "    return load_settings('./conf.yml', strict=True)\n"
    ),
    "src/other.py": "def untouched():\n    return 41\n",
}


def rows_by_path(report):
    return {row.path: row for row in report.rows}


def edit(tmp_path, new_files):
    repo = make_repo(tmp_path, BASE)
    old = git(repo, "rev-parse", "HEAD")
    new = commit_all(repo, new_files)
    return repo, old, new


def test_import_added_at_top_all_moved_nothing_changed(tmp_path):
    repo, old, new = edit(
        tmp_path, {"src/config.py": "import os\n" + BASE["src/config.py"]}
    )
    report = compute_affected(repo, old, new)
    rows = rows_by_path(report)
    assert {r.category for r in report.rows} == {"moved"}
    assert set(rows) == {
        "src.config.load_settings",
        "src.config.Loader",
        "src.config.Loader.parse",
    }
    assert not report.has_error


def test_body_only_change_reports_body_owner_only(tmp_path):
    repo, old, new = edit(
        tmp_path,
        {
            "src/config.py": BASE["src/config.py"].replace(
                "return {'path': path}", "return {'p': path}"
            )
        },
    )
    report = compute_affected(repo, old, new)
    row = rows_by_path(report)["src.config.load_settings"]
    assert row.category == "body"
    assert row.detail == "owner only"
    assert row.callers == []


def test_param_change_reports_signature_and_names_sites(tmp_path):
    repo, old, new = edit(
        tmp_path,
        {
            "src/config.py": BASE["src/config.py"].replace(
                "def load_settings(path, strict=False):",
                "def load_settings(path, strict=False, extra=None):",
            )
        },
    )
    report = compute_affected(repo, old, new)
    row = rows_by_path(report)["src.config.load_settings"]
    assert row.category == "signature"
    caller_positions = {(c["file"], c["line"]) for c in row.callers}
    assert ("src/app.py", 5) in caller_positions


def test_sig_and_body_both_changed_reports_signature(tmp_path):
    repo, old, new = edit(
        tmp_path,
        {
            "src/config.py": BASE["src/config.py"].replace(
                "def load_settings(path, strict=False):\n    return {'path': path}",
                "def load_settings(path):\n    return {}",
            )
        },
    )
    report = compute_affected(repo, old, new)
    assert rows_by_path(report)["src.config.load_settings"].category == "signature"


def test_deleted_with_callers_is_error(tmp_path):
    content = BASE["src/config.py"].replace(
        "def load_settings(path, strict=False):\n    return {'path': path}\n\n\n", ""
    )
    repo, old, new = edit(tmp_path, {"src/config.py": content})
    report = compute_affected(repo, old, new)
    row = rows_by_path(report)["src.config.load_settings"]
    assert row.category == "deleted"
    assert report.has_error
    result = run_cli("affected", old, new, "--repo", str(repo), cwd=repo)
    assert result.returncode == 1
    assert "deleted" in result.stdout


def test_deleted_without_callers_is_not_error(tmp_path):
    repo, old, new = edit(tmp_path, {"src/other.py": "def renamed_away():\n    return 41\n"})
    report = compute_affected(repo, old, new)
    assert rows_by_path(report)["src.other.untouched"].category == "deleted"
    assert not report.has_error


def test_added_symbol_reported_as_added(tmp_path):
    repo, old, new = edit(
        tmp_path, {"src/config.py": BASE["src/config.py"] + "\n\ndef fresh():\n    return 2\n"}
    )
    report = compute_affected(repo, old, new)
    assert rows_by_path(report)["src.config.fresh"].category == "added"


def test_untouched_file_not_in_report(tmp_path):
    repo, old, new = edit(
        tmp_path, {"src/config.py": "import os\n" + BASE["src/config.py"]}
    )
    report = compute_affected(repo, old, new)
    assert "src.other.untouched" not in rows_by_path(report)


def test_module_to_package_refactor_is_moved_not_deleted(tmp_path):
    repo = make_repo(tmp_path, BASE)
    old = git(repo, "rev-parse", "HEAD")
    git(repo, "mv", "src/config.py", "src/config_tmp.py")
    (repo / "src/config").mkdir()
    git(repo, "mv", "src/config_tmp.py", "src/config/__init__.py")
    git(repo, "commit", "-q", "-m", "package-ify")
    new = git(repo, "rev-parse", "HEAD")
    report = compute_affected(repo, old, new)
    row = rows_by_path(report)["src.config.load_settings"]
    assert row.category == "moved"
    assert not report.has_error


def test_async_conversion_is_signature_level(tmp_path):
    repo, old, new = edit(
        tmp_path,
        {
            "src/config.py": BASE["src/config.py"].replace(
                "def load_settings", "async def load_settings"
            )
        },
    )
    report = compute_affected(repo, old, new)
    assert rows_by_path(report)["src.config.load_settings"].category == "signature"


def test_decorator_only_change_reported(tmp_path):
    repo, old, new = edit(
        tmp_path,
        {
            "src/config.py": "import functools\n"
            + BASE["src/config.py"].replace(
                "def load_settings", "@functools.lru_cache\ndef load_settings"
            )
        },
    )
    report = compute_affected(repo, old, new)
    row = rows_by_path(report)["src.config.load_settings"]
    assert row.category == "decorators"


def test_property_getter_body_edit_not_masked_by_setter(tmp_path):
    files = {
        "src/c.py": (
            "class C:\n"
            "    @property\n"
            "    def value(self):\n"
            "        return self._v\n"
            "    @value.setter\n"
            "    def value(self, v):\n"
            "        self._v = v\n"
        )
    }
    repo = make_repo(tmp_path, files)
    old = git(repo, "rev-parse", "HEAD")
    new = commit_all(
        repo,
        {"src/c.py": files["src/c.py"].replace("return self._v", "return self._v or 0")},
    )
    report = compute_affected(repo, old, new)
    assert rows_by_path(report)["src.c.C.value"].category == "body"


def test_new_rev_parse_failure_reports_unknown_not_deleted(tmp_path):
    repo = make_repo(tmp_path, {"mod.py": "def solo():\n    return None\n"})
    old = git(repo, "rev-parse", "HEAD")
    new = commit_all(
        repo, {"mod.py": "def solo():\n    return None\n\ndef broken(:\n"}
    )
    report = compute_affected(repo, old, new)
    row = rows_by_path(report)["mod.solo"]
    assert row.category == "unknown"
    assert "parse" in row.detail
    assert not report.has_error


def test_new_rev_parse_failure_with_callers_is_error(tmp_path):
    repo = make_repo(
        tmp_path,
        {
            "mod.py": "def solo():\n    return None\n",
            "use.py": "from mod import solo\ndef go():\n    return solo()\n",
        },
    )
    old = git(repo, "rev-parse", "HEAD")
    new = commit_all(
        repo, {"mod.py": "def solo():\n    return None\n\ndef broken(:\n"}
    )
    report = compute_affected(repo, old, new)
    assert rows_by_path(report)["mod.solo"].category == "unknown"
    assert report.has_error


def test_cli_output_shape(tmp_path):
    repo, old, new = edit(
        tmp_path,
        {
            "src/config.py": BASE["src/config.py"].replace(
                "def load_settings(path, strict=False):",
                "def load_settings(path, mode, strict=False):",
            )
        },
    )
    result = run_cli("affected", old, new, "--repo", str(repo), cwd=repo)
    assert result.returncode == 0, result.stderr
    assert "src.config.load_settings" in result.stdout
    assert "signature" in result.stdout
    assert "callers affected (" in result.stdout
    assert "src/app.py:5" in result.stdout
