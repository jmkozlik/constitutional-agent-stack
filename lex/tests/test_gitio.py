from analyzer import gitio
from tests.conftest import commit_all, git, make_repo


def test_list_py_files_sorted_and_filtered(tmp_path):
    repo = make_repo(
        tmp_path,
        {
            "src/b.py": "x = 1\n",
            "src/a.py": "y = 2\n",
            "README.md": "hi\n",
            "src/data.json": "{}\n",
        },
    )
    rev = git(repo, "rev-parse", "HEAD")
    assert gitio.list_py_files(repo, rev) == ["src/a.py", "src/b.py"]


def test_read_files_round_trips_content(tmp_path):
    repo = make_repo(tmp_path, {"src/a.py": "def f():\n    return 1\n"})
    rev = git(repo, "rev-parse", "HEAD")
    blobs = gitio.read_files(repo, rev, ["src/a.py"])
    assert blobs["src/a.py"] == b"def f():\n    return 1\n"


def test_resolve_commit_full_sha(tmp_path):
    repo = make_repo(tmp_path, {"a.py": "x = 1\n"})
    sha = gitio.resolve_commit(repo, "HEAD")
    assert len(sha) == 40
    assert sha == git(repo, "rev-parse", "HEAD")


def test_changed_files_insertion(tmp_path):
    repo = make_repo(tmp_path, {"a.py": "def f():\n    return 1\n"})
    old = git(repo, "rev-parse", "HEAD")
    new = commit_all(repo, {"a.py": "import os\ndef f():\n    return 1\n"})
    changed = gitio.changed_files(repo, old, new)
    assert list(changed) == ["a.py"]
    old_ranges, new_ranges = changed["a.py"]
    assert old_ranges == []  # pure insertion: no old lines touched
    assert new_ranges == [(1, 1)]


def test_changed_files_modification_and_multiple_hunks(tmp_path):
    repo = make_repo(
        tmp_path,
        {"a.py": "def f():\n    return 1\n\n\ndef g():\n    return 2\n"},
    )
    old = git(repo, "rev-parse", "HEAD")
    new = commit_all(
        repo,
        {"a.py": "def f():\n    return 10\n\n\ndef g():\n    return 20\n"},
    )
    old_ranges, new_ranges = gitio.changed_files(repo, old, new)["a.py"]
    assert old_ranges == [(2, 2), (6, 6)]
    assert new_ranges == [(2, 2), (6, 6)]


def test_rename_appears_as_delete_plus_add(tmp_path):
    repo = make_repo(tmp_path, {"a.py": "def f():\n    return 1\n"})
    old = git(repo, "rev-parse", "HEAD")
    git(repo, "mv", "a.py", "b.py")
    git(repo, "commit", "-q", "-m", "rename")
    new = git(repo, "rev-parse", "HEAD")
    changed = gitio.changed_files(repo, old, new)
    assert set(changed) == {"a.py", "b.py"}


def test_deleted_file_reported(tmp_path):
    repo = make_repo(tmp_path, {"a.py": "def f():\n    return 1\n", "b.py": "x = 1\n"})
    old = git(repo, "rev-parse", "HEAD")
    git(repo, "rm", "-q", "a.py")
    git(repo, "commit", "-q", "-m", "delete")
    new = git(repo, "rev-parse", "HEAD")
    changed = gitio.changed_files(repo, old, new)
    old_ranges, new_ranges = changed["a.py"]
    assert old_ranges == [(1, 2)]
    assert new_ranges == []
