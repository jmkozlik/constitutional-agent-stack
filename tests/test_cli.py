from tests.conftest import make_repo, run_cli

PROJECT = {
    "src/config.py": (
        "def load_settings(path, strict=False):\n"
        "    return {}\n"
    ),
    "src/app.py": (
        "from src.config import load_settings\n"
        "def boot():\n"
        "    return load_settings('./conf.yml')\n"
    ),
    "src/router.py": (
        "def dispatch(name, payload):\n"
        "    return HANDLERS[name](payload)\n"
    ),
}


def test_index_writes_deterministic_bytes(tmp_path):
    repo = make_repo(tmp_path, PROJECT)
    first = run_cli("index", str(repo), "--commit", "HEAD", "-o", "a.json", cwd=repo)
    second = run_cli("index", str(repo), "--commit", "HEAD", "-o", "b.json", cwd=repo)
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert (repo / "a.json").read_bytes() == (repo / "b.json").read_bytes()


def test_symbol_prints_definition_and_callers(tmp_path):
    repo = make_repo(tmp_path, PROJECT)
    assert run_cli("index", str(repo), cwd=repo).returncode == 0
    result = run_cli("symbol", "src.config.load_settings", cwd=repo)
    assert result.returncode == 0, result.stderr
    assert "src/config.py" in result.stdout
    assert "(path, strict=False)" in result.stdout
    assert "src/app.py:3" in result.stdout
    assert "src.app.boot" in result.stdout


def test_symbol_unknown_exits_nonzero(tmp_path):
    repo = make_repo(tmp_path, PROJECT)
    run_cli("index", str(repo), cwd=repo)
    result = run_cli("symbol", "src.config.missing", cwd=repo)
    assert result.returncode == 1
    assert "not found" in result.stderr.lower()


def test_unresolved_lists_records(tmp_path):
    repo = make_repo(tmp_path, PROJECT)
    run_cli("index", str(repo), cwd=repo)
    result = run_cli("unresolved", cwd=repo)
    assert result.returncode == 0
    assert "src/router.py:2" in result.stdout
    assert "subscript_call" in result.stdout


def test_index_missing_repo_errors(tmp_path):
    result = run_cli("index", str(tmp_path / "nope"), cwd=tmp_path)
    assert result.returncode == 1


def test_corrupt_index_clean_error(tmp_path):
    (tmp_path / "corrupt.json").write_text("{ this is not json\n")
    for cmd in (["symbol", "foo"], ["unresolved"]):
        result = run_cli(*cmd, "--index", "corrupt.json", cwd=tmp_path)
        assert result.returncode == 1
        assert "analyzer:" in result.stderr
        assert "Traceback" not in result.stderr


def test_wrong_shape_index_clean_error(tmp_path):
    (tmp_path / "shape.json").write_text('{"symbols": []}\n')
    result = run_cli("unresolved", "--index", "shape.json", cwd=tmp_path)
    assert result.returncode == 1
    assert "Traceback" not in result.stderr


def test_index_output_into_missing_dir_clean_error(tmp_path):
    repo = make_repo(tmp_path, PROJECT)
    result = run_cli("index", str(repo), "-o", "/no/such/dir/out.json", cwd=repo)
    assert result.returncode == 1
    assert "analyzer:" in result.stderr
    assert "Traceback" not in result.stderr


def test_index_flag_pointing_at_directory_clean_error(tmp_path):
    result = run_cli("symbol", "foo", "--index", ".", cwd=tmp_path)
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
