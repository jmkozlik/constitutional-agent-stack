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
import time


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


def _tool_targets(tool, tool_input):
    """Absolute paths a tool call names, for binding the fence by TARGET."""
    out = []
    for key in ("file_path", "notebook_path", "path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            out.append(value)
    return [p for p in out if os.path.isabs(p)]


def bind_fence(cwd, tool, tool_input):
    """F28: bind the fence to the dispatch this call actually touches.

    Walking up from cwd alone left the hook inert for a subagent, whose
    cwd is the parent repo rather than the worktree. Binding from the
    TARGET path first fixes that without a process-global variable, which
    would misbind when two dispatches are live at once — as they were in
    the session that filed this.
    """
    for target in _tool_targets(tool, tool_input):
        start = target if os.path.isdir(target) else os.path.dirname(target)
        fence_path, root = find_fence(start)
        if fence_path:
            return fence_path, root
    override = os.environ.get("LEX_FENCE")
    if override and os.path.exists(override):
        return override, os.path.dirname(os.path.dirname(os.path.abspath(override)))
    return find_fence(cwd)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    cwd = data.get("cwd") or os.getcwd()
    tool = data.get("tool_name")
    tool_input = data.get("tool_input") or {}
    fence_path, root = bind_fence(cwd, tool, tool_input)
    if fence_path is None:
        return 0
    try:
        fence = json.load(open(fence_path))
    except Exception:
        return 0
    allowed = set(fence.get("allowed", {}))
    node = fence.get("node", "?")

    # When the fence root is not an ancestor of cwd — the subagent case —
    # relative Bash targets belong to the root, not to cwd. Resolving them
    # against cwd produced ../../-shaped paths that were denied with a name
    # the agent never typed.
    base = root if not os.path.abspath(cwd).startswith(root) else cwd

    def rel(target):
        absolute = (
            target
            if os.path.isabs(target)
            else os.path.abspath(os.path.join(base, target))
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

    # --- F29: reads. Not forbidden; invisible reads are. -------------------
    read_policy = fence.get("read_policy", "disclose")
    reads = fence.get("reads") or []

    def read_in_scope(rel_path):
        return any(
            rel_path == prefix or rel_path.startswith(prefix + os.sep)
            for prefix in reads
        )

    def disclose(tool_name, rel_path):
        """Append one read event, atomically — hooks run concurrently when
        the model batches tool calls, and a torn line would under-report
        the very thing being measured."""
        line = json.dumps(
            {"tool": tool_name, "path": rel_path, "ts": int(time.time())},
            sort_keys=True,
        ) + "\n"
        try:
            fd = os.open(
                os.path.join(root, ".harness", "read_events.jsonl"),
                os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644,
            )
            try:
                os.write(fd, line.encode())
            finally:
                os.close(fd)
        except OSError:
            pass

    if tool in ("Read", "Grep", "Glob"):
        target = tool_input.get("file_path") or tool_input.get("path")
        if target is None:
            # A pathless Grep/Glob searches the whole tree. Under a hard
            # policy that is the P6 leak itself, so it is refused outright.
            if read_policy == "hard" and tool in ("Grep", "Glob"):
                sys.stderr.write(
                    f"read fence [{node}]: a {tool} with no path searches "
                    "outside your packet — REQUEST_MEM instead. Readable: "
                    f"{', '.join(reads) or '(nothing)'}\n"
                )
                return 2
            return 0
        rel_path = rel(target)
        if read_in_scope(rel_path):
            return 0
        if read_policy == "hard":
            sys.stderr.write(
                f"read fence [{node}]: '{rel_path}' is outside your packet — "
                "REQUEST_MEM or file a defect. Do not work around. "
                f"Readable: {', '.join(reads) or '(nothing)'}\n"
            )
            return 2
        disclose(tool, rel_path)
        return 0

    if tool in ("Write", "Edit", "NotebookEdit"):
        target = tool_input.get("file_path") or tool_input.get("notebook_path")
        if target:
            rel_path = rel(target)
            if not in_scope(rel_path):
                return deny(rel_path)
        return 0

    if tool == "Bash":
        command = tool_input.get("command") or ""
        # Read shapes are never denied here (bash stays soft), but they are
        # never invisible either: 3d-1's out-of-scope read reproduces as
        # `sed -n '1,270p' analyzer/refs.py`, which no write-shape matches.
        for reader in re.findall(
            r"\b(?:cat|head|tail|less|more|rg|grep|awk|sed)\b[^|;&]*", command
        ):
            for word in reader.split()[1:]:
                word = word.strip("'\"")
                if word.startswith("-") or word.startswith("$"):
                    continue
                if "/" not in word and not word.endswith(".py"):
                    continue
                candidate = rel(word)
                if not read_in_scope(candidate):
                    disclose("Bash", candidate)
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
