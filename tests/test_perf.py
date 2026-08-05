"""Acceptance: a 20k-line repo indexes in under 10 seconds."""

import time

from tests.conftest import make_repo, run_cli


def _module(i: int, funcs: int = 24) -> str:
    lines = []
    if i > 0:
        lines.append(f"from src.mod_{i - 1} import helper_0, Widget_{i - 1}")
    lines.append("")
    for f in range(funcs):
        lines += [
            f"def helper_{f}(value, scale={f}, *, strict=False):",
            f"    total = value * scale + {f}",
            "    parts = [total]",
            "    for step in range(3):",
            "        parts.append(total + step)",
            "    if strict:",
            "        total += sum(parts)",
        ]
        if i > 0 and f % 3 == 0:
            lines.append(f"    total += helper_0(value)")
        lines += ["    return total", "", ""]
    lines += [
        f"class Widget_{i}:",
        "    def __init__(self, seed):",
        "        self.seed = seed",
        "",
    ]
    for m in range(6):
        lines += [
            f"    def step_{m}(self, amount):",
            f"        acc = self.seed + amount * {m}",
            "        for k in range(4):",
            "            acc += helper_1(k)",
            "        return acc",
            "",
        ]
    return "\n".join(lines) + "\n"


def test_20k_line_repo_indexes_under_10s(tmp_path):
    files = {f"src/mod_{i}.py": _module(i) for i in range(72)}
    total_lines = sum(content.count("\n") for content in files.values())
    assert total_lines >= 20_000, f"fixture only {total_lines} lines"
    repo = make_repo(tmp_path, files)
    started = time.monotonic()
    result = run_cli("index", str(repo), "-o", "perf.json", cwd=repo)
    elapsed = time.monotonic() - started
    assert result.returncode == 0, result.stderr
    assert elapsed < 10.0, f"indexing took {elapsed:.2f}s on {total_lines} lines"
