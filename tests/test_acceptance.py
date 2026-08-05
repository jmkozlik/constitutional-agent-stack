"""One test per acceptance bullet in docs/brief.md, driven through the
real CLI against fixture git repos — no internal imports, so this suite
tests the contract, not the implementation."""

import json

from tests.conftest import commit_all, git, make_repo, run_cli

PROJECT = {
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
    "src/cli.py": (
        "from src.config import load_settings\n"
        "\n"
        "\n"
        "def main(path):\n"
        "    return load_settings(path)\n"
    ),
    "src/router.py": (
        "HANDLERS = {}\n"
        "\n"
        "\n"
        "def dispatch(name, payload):\n"
        "    return HANDLERS[name](payload)\n"
    ),
}


def test_indexing_same_commit_twice_is_byte_identical(tmp_path):
    repo = make_repo(tmp_path, PROJECT)
    for name in ("a.json", "b.json"):
        result = run_cli("index", str(repo), "--commit", "HEAD", "-o", name, cwd=repo)
        assert result.returncode == 0, result.stderr
    assert (repo / "a.json").read_bytes() == (repo / "b.json").read_bytes()


def test_symbol_returns_definition_signature_every_caller(tmp_path):
    repo = make_repo(tmp_path, PROJECT)
    run_cli("index", str(repo), cwd=repo)
    result = run_cli("symbol", "src.config.load_settings", cwd=repo)
    assert result.returncode == 0, result.stderr
    assert "src/config.py:1-2" in result.stdout
    assert "(path, strict=False)" in result.stdout
    assert "src/app.py:5" in result.stdout and "src.app.boot" in result.stdout
    assert "src/cli.py:5" in result.stdout and "src.cli.main" in result.stdout


def test_import_at_top_reports_moved_and_nothing_changed(tmp_path):
    repo = make_repo(tmp_path, PROJECT)
    old = git(repo, "rev-parse", "HEAD")
    new = commit_all(repo, {"src/config.py": "import os\n" + PROJECT["src/config.py"]})
    result = run_cli("affected", old, new, "--repo", str(repo), cwd=repo)
    assert result.returncode == 0, result.stderr
    lines = [l for l in result.stdout.splitlines() if l and not l.startswith(" ")]
    assert lines, result.stdout
    assert all(" moved " in f" {l} " or "moved" in l.split() for l in lines)
    for symbol in ("src.config.load_settings", "src.config.Loader", "src.config.Loader.parse"):
        assert symbol in result.stdout
    assert "signature" not in result.stdout and "body" not in result.stdout


def test_body_change_reports_body_not_callers(tmp_path):
    repo = make_repo(tmp_path, PROJECT)
    old = git(repo, "rev-parse", "HEAD")
    new = commit_all(
        repo,
        {
            "src/config.py": PROJECT["src/config.py"].replace(
                "return {'path': path}", "return dict(path=path)"
            )
        },
    )
    result = run_cli("affected", old, new, "--repo", str(repo), cwd=repo)
    assert result.returncode == 0, result.stderr
    assert "body" in result.stdout
    assert "owner only" in result.stdout
    assert "caller:" not in result.stdout
    assert "signature" not in result.stdout


def test_param_change_reports_signature_and_names_every_call_site(tmp_path):
    repo = make_repo(tmp_path, PROJECT)
    old = git(repo, "rev-parse", "HEAD")
    new = commit_all(
        repo,
        {
            "src/config.py": PROJECT["src/config.py"].replace(
                "def load_settings(path, strict=False):",
                "def load_settings(path, mode, strict=False):",
            )
        },
    )
    result = run_cli("affected", old, new, "--repo", str(repo), cwd=repo)
    assert result.returncode == 0, result.stderr
    assert "signature" in result.stdout
    assert "src/app.py:5" in result.stdout
    assert "src/cli.py:5" in result.stdout


def test_subscript_call_flagged_and_file_low_confidence(tmp_path):
    repo = make_repo(tmp_path, PROJECT)
    run_cli("index", str(repo), cwd=repo)
    result = run_cli("unresolved", cwd=repo)
    assert "src/router.py" in result.stdout
    assert "subscript_call" in result.stdout
    assert "HANDLERS[name](payload)" in result.stdout
    index = json.loads((repo / "index.json").read_text())
    confidences = {
        s["path"]: s["confidence"]
        for s in index["symbols"]
        if s["file"] == "src/router.py"
    }
    assert confidences and set(confidences.values()) == {"low"}
    other = {s["confidence"] for s in index["symbols"] if s["file"] == "src/config.py"}
    assert other == {"high"}


def test_deleting_symbol_with_callers_is_an_error(tmp_path):
    repo = make_repo(tmp_path, PROJECT)
    old = git(repo, "rev-parse", "HEAD")
    new = commit_all(
        repo,
        {
            "src/config.py": (
                "class Loader:\n"
                "    def parse(self):\n"
                "        return 1\n"
            )
        },
    )
    result = run_cli("affected", old, new, "--repo", str(repo), cwd=repo)
    assert result.returncode == 1
    assert "deleted" in result.stdout
    assert "ERROR" in result.stdout
