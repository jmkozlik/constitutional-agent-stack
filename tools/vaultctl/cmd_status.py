"""
cmd_status.py — vault status report subcommand.

Self-contained: no sibling module imports. Stdlib only.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _truncate(line: str, limit: int = 100) -> str:
    """Truncate line to limit chars; if longer, return first 97 chars + '...'."""
    if len(line) > limit:
        return line[:97] + "..."
    return line


def _parse_frontmatter(text: str) -> dict[str, str]:
    """
    Parse YAML-ish frontmatter from a note's text.

    Amendment A6: frontmatter is between the FIRST line that is exactly `---`
    and the SECOND line that is exactly `---`.  Any later `---` lines are body.

    Returns a dict of key → value (both stripped).  Returns {} if no valid
    frontmatter is found (first line is not `---`).
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    fm: dict[str, str] = {}
    # Skip line 0 (opener ---), scan for closing ---
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            # Closing marker found — everything before is frontmatter
            break
        if ":" in lines[i]:
            key, _, value = lines[i].partition(":")
            fm[key.strip()] = value.strip()
    return fm


def _frontmatter_body_start(lines: list[str]) -> int:
    """
    Return the index of the first line AFTER the closing `---` of frontmatter.

    Amendment A6: the closing `---` is the SECOND line that is exactly `---`.
    If the file has no opener `---` on line 0, returns 0 (whole file is body).
    If no closing `---` found, returns len(lines) (no body).
    """
    if not lines or lines[0].strip() != "---":
        return 0
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return i + 1
    return len(lines)


# ---------------------------------------------------------------------------
# Input parsers
# ---------------------------------------------------------------------------

def _read_run_state(vault: Path) -> dict[str, str] | None:
    """
    Read <vault>/council/state.md, extract the first HTML comment block
    beginning `<!-- RUN-STATE` and ending `-->`.

    Returns dict of key→value, or None on failure (also prints to stderr).
    """
    state_path = vault / "council" / "state.md"
    if not state_path.exists():
        print(f"error: {state_path} not found", file=sys.stderr)
        return None

    text = state_path.read_text(encoding="utf-8")
    # Find first <!-- RUN-STATE ... --> block
    match = re.search(r"<!--\s*RUN-STATE(.*?)-->", text, re.DOTALL)
    if not match:
        print(f"error: no RUN-STATE block found in {state_path}", file=sys.stderr)
        return None

    block = match.group(1)
    result: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


def _read_executor_notes(vault: Path) -> list[tuple[str, str, str]]:
    """
    Read <vault>/executors/active/*.md excluding _index.md.

    For each note returns (filename_stem, agent, status, current_task_line)
    as a 4-tuple… actually returns list of (agent, status, task_line).

    Notes without frontmatter: agent = filename stem, status = '?'.
    Current task: first non-empty line after `## Current task` heading.
    """
    active_dir = vault / "executors" / "active"
    if not active_dir.exists():
        return []

    notes: list[tuple[str, str, str, str]] = []  # (stem, agent, status, task)
    for path in sorted(active_dir.glob("*.md")):
        if path.name == "_index.md":
            continue
        stem = path.stem
        text = path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        if not fm:
            agent = stem
            status = "?"
        else:
            agent = fm.get("agent", stem)
            status = fm.get("status", "?")

        # Find current task line
        task_line = ""
        lines = text.splitlines()
        in_current_task = False
        # We want the first non-empty line AFTER the `## Current task` heading.
        # But we need to respect frontmatter — skip it first (amendment A6).
        body_start = _frontmatter_body_start(lines)
        for i in range(body_start, len(lines)):
            stripped = lines[i].strip()
            if in_current_task:
                if stripped:
                    task_line = stripped
                    break
            else:
                if stripped == "## Current task":
                    in_current_task = True

        notes.append((stem, agent, status, task_line))

    # Sort by filename (stem already, but sorted by path above)
    return [(agent, status, task_line) for (stem, agent, status, task_line) in notes]


def _read_ledger(vault: Path) -> list[tuple[str, str]]:
    """
    Read <vault>/ledger/*.md matching NNNN-*.md (4-digit prefix).
    Exclude _index.md. Sort by NNNN descending, take first 3.

    For each returns (filename_without_ext, body_line) where body_line is
    the first non-empty line after the closing `---` of frontmatter.
    """
    ledger_dir = vault / "ledger"
    if not ledger_dir.exists():
        return []

    pattern = re.compile(r"^(\d{4})-.*\.md$")
    entries: list[tuple[int, str, Path]] = []
    for path in ledger_dir.glob("*.md"):
        m = pattern.match(path.name)
        if not m:
            continue
        if path.name == "_index.md":
            continue
        num = int(m.group(1))
        entries.append((num, path.stem, path))

    entries.sort(key=lambda e: e[0], reverse=True)
    top3 = entries[:3]

    result: list[tuple[str, str]] = []
    for _num, stem, path in top3:
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        body_start = _frontmatter_body_start(lines)
        body_line = ""
        for i in range(body_start, len(lines)):
            stripped = lines[i].strip()
            if stripped:
                body_line = stripped
                break
        result.append((stem, body_line))
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="vaultctl status",
        description="Print vault run-state and executor summary.",
    )
    parser.add_argument(
        "--vault",
        default=os.environ.get("VAULT_ROOT", os.path.expanduser("~/vault")),
        metavar="PATH",
        help="Path to the vault root (default: $VAULT_ROOT (or ~/vault))",
    )
    args = parser.parse_args(argv)
    vault = Path(args.vault)

    # 1. RUN-STATE
    run_state = _read_run_state(vault)
    if run_state is None:
        return 1

    run_id = run_state.get("run-id", "?")
    lane = run_state.get("lane", "?")
    status = run_state.get("status", "?")
    project = run_state.get("project", "?")

    # 2. Executor notes
    executor_entries = _read_executor_notes(vault)

    # 3. Ledger
    ledger_entries = _read_ledger(vault)

    # Output
    lines_out: list[str] = []
    lines_out.append(f"VAULT STATUS — {args.vault}")
    lines_out.append("")
    lines_out.append("RUN-STATE")
    lines_out.append(f"  run-id:   {run_id}")
    lines_out.append(f"  lane:     {lane}")
    lines_out.append(f"  status:   {status}")
    lines_out.append(f"  project:  {project}")
    lines_out.append("")
    lines_out.append(f"EXECUTORS ({len(executor_entries)} active)")
    if executor_entries:
        for agent, st, task in executor_entries:
            task_display = _truncate(task) if task else ""
            lines_out.append(f"  {agent} · {st} · {task_display}")
    else:
        lines_out.append("  (none)")
    lines_out.append("")
    lines_out.append("RECENT LEDGER")
    if ledger_entries:
        for stem, body in ledger_entries:
            body_display = _truncate(body) if body else ""
            lines_out.append(f"  {stem} · {body_display}")
    else:
        lines_out.append("  (none)")

    print("\n".join(lines_out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
