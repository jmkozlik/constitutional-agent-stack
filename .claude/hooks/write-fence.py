#!/usr/bin/env python3
"""PreToolUse write-fence hook. Static, committed once, inherited by every
worktree. If the working directory (or an ancestor) carries
.harness/fence.json, writes outside its allowed set are denied.

Write/Edit/NotebookEdit: hard layer — the target path is known exactly.
Bash: soft layer, best-effort — denies the obvious write shapes
(> / >> redirects, tee, sed -i, git apply) when they name an
out-of-scope path. A determined workaround can evade this layer; the
diff gate (harness.fence check) catches it at run end.
"""

import json
import os
import re
import sys


def find_fence(start):
    d = os.path.abspath(start)
    while True:
        candidate = os.path.join(d, ".harness", "fence.json")
        if os.path.exists(candidate):
            return candidate, d
        parent = os.path.dirname(d)
        if parent == d:
            return None, None
        d = parent


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    cwd = data.get("cwd") or os.getcwd()
    fence_path, root = find_fence(cwd)
    if fence_path is None:
        return 0
    try:
        fence = json.load(open(fence_path))
    except Exception:
        return 0
    allowed = set(fence.get("allowed", {}))
    node = fence.get("node", "?")

    def rel(target):
        absolute = (
            target
            if os.path.isabs(target)
            else os.path.abspath(os.path.join(cwd, target))
        )
        try:
            return os.path.relpath(absolute, root)
        except ValueError:
            return target

    def deny(target):
        sys.stderr.write(
            f"write fence [{node}]: '{target}' is out of scope — "
            "REQUEST_MEM or file a defect. Do not work around. "
            f"Your write scope: {', '.join(sorted(allowed)) or '(empty)'}\n"
        )
        return 2

    def in_scope(rel_path):
        if (
            rel_path in allowed
            or rel_path == ".harness"
            or rel_path.startswith(".harness" + os.sep)
        ):
            return True
        # Sanctioned scratch space (v0.4.1): declared in the fence itself.
        for scratch in fence.get("scratch", []):
            if rel_path == scratch or rel_path.startswith(scratch + os.sep):
                return True
        return False

    tool = data.get("tool_name")
    tool_input = data.get("tool_input") or {}

    if tool in ("Write", "Edit", "NotebookEdit"):
        target = tool_input.get("file_path") or tool_input.get("notebook_path")
        if target:
            rel_path = rel(target)
            if not in_scope(rel_path):
                return deny(rel_path)
        return 0

    if tool == "Bash":
        command = tool_input.get("command") or ""
        if re.search(r"\bgit\s+apply\b", command):
            return deny("git apply (a patch can write anywhere)")
        targets = []
        # `> file` / `>> file`, but not fd redirects like 2>&1 or >&2.
        targets += re.findall(r"(?<![<>0-9])>{1,2}\s*([^\s;|&)]+)", command)
        targets += re.findall(r"\btee\s+(?:-a\s+)?([^\s;|&]+)", command)
        sed = re.search(
            r"\bsed\s+-\S*i\S*\s+(?:''\s+|\"\"\s+)?(?:-e\s+)?"
            r"(?:'[^']*'|\"[^\"]*\"|\S+)\s+([^\s;|&]+)",
            command,
        )
        if sed:
            targets.append(sed.group(1))
        for target in targets:
            target = target.strip("'\"")
            if target in ("/dev/null", "/dev/stderr", "/dev/stdout") or target.startswith("$"):
                continue
            rel_path = rel(target)
            if not in_scope(rel_path):
                return deny(rel_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
