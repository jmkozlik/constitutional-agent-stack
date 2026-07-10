"""cmd_index — regenerate a folder's _index.md from frontmatter of markdown notes.

Stdlib only. No sibling imports. Fully self-contained.

WRITE GUARD: the ONLY file opened for writing is <folder>/_index.md.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Frontmatter parsing (amendments A5, A6)
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> dict[str, str]:
    """Return {key: raw_value} for the YAML-ish frontmatter block.

    Rules (amendment A6):
      - Block starts when the FIRST LINE of the file is exactly `---`.
      - Block closes at the NEXT line that is exactly `---`.
      - Later `---` lines are body; they do NOT reopen the block.
      - Lines inside the block of the form `key: value` are captured.
      - If first line is not `---`, return {}.
    """
    lines = text.splitlines()
    if not lines or lines[0].rstrip("\r") != "---":
        return {}

    fm: dict[str, str] = {}
    for line in lines[1:]:
        stripped = line.rstrip("\r")
        if stripped == "---":
            break
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)", stripped)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    return fm


def _parse_labels(raw: str) -> str:
    """Format a raw labels value per amendment A5.

    Amendment A5: value NOT matching `[...]` form → `-`.
    `[a, b, c]` → `a, b, c`.
    `[]` (empty) → `-`.
    Bare word (no brackets) → `-`.
    """
    stripped = raw.strip()
    m = re.match(r"^\[(.*)]\s*$", stripped)
    if m is None:
        return "-"
    inner = m.group(1).strip()
    if not inner:
        return "-"
    # Normalise whitespace around commas
    parts = [p.strip() for p in inner.split(",")]
    parts = [p for p in parts if p]
    if not parts:
        return "-"
    return ", ".join(parts)


def _find_title(text: str, fm_end_line: int) -> str | None:
    """Return text of first `# ` heading after the frontmatter block."""
    lines = text.splitlines()
    for line in lines[fm_end_line:]:
        m = re.match(r"^#\s+(.*)", line.rstrip("\r"))
        if m:
            return m.group(1).strip()
    return None


def _fm_end_line(text: str) -> int:
    """Return line index (0-based) of the line AFTER the closing `---`.

    If no frontmatter, return 0.
    """
    lines = text.splitlines()
    if not lines or lines[0].rstrip("\r") != "---":
        return 0
    for i, line in enumerate(lines[1:], start=1):
        if line.rstrip("\r") == "---":
            return i + 1
    # Unclosed frontmatter — treat whole file as frontmatter, no body
    return len(lines)


# ---------------------------------------------------------------------------
# Note processing
# ---------------------------------------------------------------------------

def _process_note(path: Path) -> dict[str, str]:
    """Read a note (read-only) and return title, type, labels."""
    text = path.read_text(encoding="utf-8")

    fm = _parse_frontmatter(text)
    end = _fm_end_line(text)

    note_type = fm.get("type", "?") or "?"

    raw_labels = fm.get("labels", "")
    if raw_labels:
        labels = _parse_labels(raw_labels)
    else:
        labels = "-"

    title = _find_title(text, end)
    if title is None:
        title = path.stem  # filename without .md

    return {"title": title, "type": note_type, "labels": labels}


# ---------------------------------------------------------------------------
# Index generation
# ---------------------------------------------------------------------------

def _generate_index(folder: Path) -> str:
    """Build the full _index.md content for *folder*."""
    notes = sorted(
        [
            p
            for p in folder.iterdir()
            if p.suffix == ".md" and p.name != "_index.md" and p.is_file()
        ],
        key=lambda p: p.name,
    )

    lines: list[str] = [f"# Index: {folder.name}", ""]

    for note_path in notes:
        info = _process_note(note_path)
        line = (
            f"- [{info['title']}]({note_path.name})"
            f" — type: {info['type']}"
            f" · labels: {info['labels']}"
        )
        lines.append(line)

    lines.append("")  # trailing newline
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vaultctl index",
        description="Regenerate _index.md for a vault folder.",
    )
    parser.add_argument("folder", help="Folder to index (path or vault-relative name).")
    parser.add_argument(
        "--vault",
        default=os.environ.get("VAULT_ROOT", os.path.expanduser("~/vault")),
        help="Vault root (default: $VAULT_ROOT (or ~/vault)).",
    )
    args = parser.parse_args(argv)

    # Folder resolution: (1) as given, (2) <vault>/<folder>
    candidate = Path(args.folder)
    if candidate.is_dir():
        folder = candidate.resolve()
    else:
        candidate2 = Path(args.vault) / args.folder
        if candidate2.is_dir():
            folder = candidate2.resolve()
        else:
            print(
                f"error: folder not found: {args.folder!r} "
                f"(tried {candidate} and {candidate2})",
                file=sys.stderr,
            )
            return 1

    content = _generate_index(folder)

    index_path = folder / "_index.md"
    # WRITE GUARD: this is the ONLY path opened for writing, and it must be a
    # REGULAR file. If `_index.md` pre-exists as a symlink, `write_text` would
    # follow it and clobber the link TARGET — which could be any other file.
    # Unlink the symlink first (permitted: the guard protects OTHER files, and
    # `_index.md` itself is ours to replace) so the target stays byte-identical
    # and we always write a fresh regular file.
    if index_path.is_symlink():
        index_path.unlink()
    index_path.write_text(content, encoding="utf-8")

    note_count = content.count("\n- [")
    print(f"wrote {index_path} ({note_count} notes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
