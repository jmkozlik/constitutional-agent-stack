from analyzer.indexer import build_index, serialize
from tests.conftest import git, make_repo

PROJECT = {
    "src/config.py": (
        "def load_settings(path, strict=False):\n"
        "    return {}\n"
        "\n"
        "\n"
        "class Loader:\n"
        "    def load(self):\n"
        "        return 1\n"
    ),
    "src/app.py": (
        "from src.config import load_settings\n"
        "\n"
        "\n"
        "def boot():\n"
        "    return load_settings('./conf.yml', strict=True)\n"
    ),
    "src/router.py": (
        "def dispatch(name, payload):\n"
        "    return HANDLERS[name](payload)\n"
    ),
}


def by_path(index):
    out = {}
    for record in index["symbols"]:
        out.setdefault(record["path"], []).append(record)
    return out


def test_build_index_end_to_end(tmp_path):
    repo = make_repo(tmp_path, PROJECT)
    index = build_index(repo, None)
    symbols = by_path(index)
    assert "src.config.load_settings" in symbols
    assert "src.app.boot" in symbols
    (ls,) = symbols["src.config.load_settings"]
    call_sites = [r for r in ls["referenced_by"] if r["kind"] == "call"]
    assert call_sites and call_sites[0]["file"] == "src/app.py"
    assert call_sites[0]["args"] == ["'./conf.yml'", "strict=True"]
    assert any(u["reason"] == "subscript_call" for u in index["unresolved"])


def test_low_confidence_marks_whole_file_only(tmp_path):
    repo = make_repo(tmp_path, PROJECT)
    index = build_index(repo, None)
    symbols = by_path(index)
    assert symbols["src.router.dispatch"][0]["confidence"] == "low"
    assert symbols["src.config.load_settings"][0]["confidence"] == "high"
    assert symbols["src.app.boot"][0]["confidence"] == "high"


def test_serialize_deterministic(tmp_path):
    repo = make_repo(tmp_path, PROJECT)
    a = serialize(build_index(repo, None))
    b = serialize(build_index(repo, None))
    assert a == b
    assert a.endswith("\n")


def test_commit_and_worktree_parity(tmp_path):
    repo = make_repo(tmp_path, PROJECT)
    sha = git(repo, "rev-parse", "HEAD")
    at_commit = build_index(repo, "HEAD")
    worktree = build_index(repo, None)
    assert at_commit["commit"] == sha
    assert worktree["commit"] is None
    assert at_commit["symbols"] == worktree["symbols"]
    assert at_commit["unresolved"] == worktree["unresolved"]


def test_parse_error_flagged_not_fatal(tmp_path):
    repo = make_repo(
        tmp_path,
        {**PROJECT, "src/broken.py": "def broken(:\n    pass\n"},
    )
    index = build_index(repo, None)
    assert any(
        u["reason"] == "parse_error" and u["file"] == "src/broken.py"
        for u in index["unresolved"]
    )
    symbols = by_path(index)
    assert "src.config.load_settings" in symbols
    assert symbols["src.config.load_settings"][0]["confidence"] == "high"


def test_duplicate_paths_share_referenced_by(tmp_path):
    repo = make_repo(
        tmp_path,
        {
            "src/c.py": (
                "class C:\n"
                "    @property\n"
                "    def value(self):\n"
                "        return self._v\n"
                "    @value.setter\n"
                "    def value(self, v):\n"
                "        self._v = v\n"
            ),
            "src/use.py": (
                "def peek(obj):\n"
                "    return obj.value\n"
            ),
        },
    )
    index = build_index(repo, None)
    records = by_path(index)["src.c.C.value"]
    assert len(records) == 2
    assert all(r["referenced_by"] for r in records)
    assert records[0]["referenced_by"] == records[1]["referenced_by"]
