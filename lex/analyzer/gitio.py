"""Git plumbing: file listings and blob contents at a rev, diff ranges.

Everything reads objects directly — no checkouts, no temp worktrees.
"""

import re
import subprocess
from pathlib import Path


class GitError(Exception):
    pass


def _git(repo: str | Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), "-c", "core.quotePath=false", *args],
        capture_output=True,
        input=input_bytes,
    )
    if result.returncode != 0:
        raise GitError(
            f"git {' '.join(args)} failed: {result.stderr.decode(errors='replace').strip()}"
        )
    return result.stdout


def resolve_commit(repo: str | Path, rev: str) -> str:
    return _git(repo, "rev-parse", "--verify", f"{rev}^{{commit}}").decode().strip()


def list_py_files(repo: str | Path, rev: str) -> list[str]:
    out = _git(repo, "ls-tree", "-r", "--name-only", "--full-tree", rev).decode()
    return sorted(p for p in out.splitlines() if p.endswith(".py"))


def read_files(repo: str | Path, rev: str, paths: list[str]) -> dict[str, bytes]:
    if not paths:
        return {}
    queries = "".join(f"{rev}:{p}\n" for p in paths).encode()
    out = _git(repo, "cat-file", "--batch", input_bytes=queries)
    blobs: dict[str, bytes] = {}
    pos = 0
    for path in paths:
        header_end = out.index(b"\n", pos)
        header = out[pos:header_end].decode()
        pos = header_end + 1
        if header.endswith(" missing"):
            raise GitError(f"object {rev}:{path} not found")
        size = int(header.rsplit(" ", 1)[1])
        blobs[path] = out[pos : pos + size]
        pos += size + 1  # blob content is followed by one newline
    return blobs


_HUNK = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

Range = tuple[int, int]


def changed_files(
    repo: str | Path, old: str, new: str
) -> dict[str, tuple[list[Range], list[Range]]]:
    """Changed line ranges per file: {path: (old_side_ranges, new_side_ranges)}.

    Ranges are inclusive (start, end) 1-based line pairs. A pure insertion
    contributes nothing to the old side; a pure deletion nothing to the new.
    Renames are surfaced as delete + add (--no-renames).
    """
    out = _git(
        repo, "diff", "--no-ext-diff", "--no-renames", "--unified=0", old, new
    ).decode(errors="replace")
    files: dict[str, tuple[list[Range], list[Range]]] = {}
    current: tuple[list[Range], list[Range]] | None = None
    in_header = False
    a_path: str | None = None
    for line in out.splitlines():
        if line.startswith("diff --git "):
            in_header = True
            current = None
            a_path = None
            continue
        if in_header and line.startswith("--- "):
            name = line[4:]
            a_path = name[2:] if name.startswith("a/") else None
            continue
        if in_header and line.startswith("+++ "):
            name = line[4:]
            path = name[2:] if name.startswith("b/") else a_path
            if path is not None:
                current = files.setdefault(path, ([], []))
            continue
        match = _HUNK.match(line)
        if match and current is not None:
            in_header = False
            old_start = int(match.group(1))
            old_count = 1 if match.group(2) is None else int(match.group(2))
            new_start = int(match.group(3))
            new_count = 1 if match.group(4) is None else int(match.group(4))
            if old_count:
                current[0].append((old_start, old_start + old_count - 1))
            if new_count:
                current[1].append((new_start, new_start + new_count - 1))
    return files
