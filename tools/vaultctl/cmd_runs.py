"""
cmd_runs — list archived runs with ledger start/complete metadata.

Stdlib only. Fully self-contained (no sibling imports by design).
"""
from __future__ import annotations

import argparse
import os
import re
import sys

# Terminal-state vocabulary (panel motion r002-runs-detection, Option B).
# Whole-token, case-sensitive. A run is "complete" if a non-start entry
# belonging to it carries one of these tokens in its body line.
_TERMINAL_TOKENS = ("COMPLETE", "PROMOTED", "CLOSED")
_TERMINAL_RE = re.compile(r"\b(" + "|".join(_TERMINAL_TOKENS) + r")\b")


def _frontmatter_runid(path: str) -> str:
    """Return the `run-id:` value from a note's frontmatter, or '' if absent."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            in_fm = False
            for i, line in enumerate(fh):
                s = line.rstrip("\n")
                if i == 0 and s.strip() == "---":
                    in_fm = True
                    continue
                if in_fm:
                    if s.strip() == "---":
                        break
                    m = re.match(r"\s*run-id:\s*(\S+)", s)
                    if m:
                        return m.group(1)
    except OSError:
        return ""
    return ""


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _parse_body_line(path: str) -> str:
    """
    Return ONLY the first non-empty line after the closing '---' of frontmatter.
    All subsequent lines are ignored (amendment A4).

    Frontmatter = lines between a first-line '---' and the next line that is
    exactly '---'. A file without frontmatter → first non-empty line of file.
    """
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return ""

    if not lines:
        return ""

    body_start = 0  # index of first line to scan for the body

    if lines[0].rstrip() == "---":
        # Find the closing ---
        for i in range(1, len(lines)):
            if lines[i].rstrip() == "---":
                body_start = i + 1
                break
        # If no closing --- found, treat whole file as body
        else:
            body_start = 0

    # First non-empty line after body_start
    for i in range(body_start, len(lines)):
        stripped = lines[i].strip()
        if stripped:
            return stripped

    return ""


def _get_ledger_entries(vault: str, run_id: str) -> tuple[str, str]:
    """
    Return (start_body, complete_body) for the given run_id.
    Empty string means no matching entry found.
    """
    ledger_dir = os.path.join(vault, "ledger")
    start_body = ""
    complete_body = ""

    if not os.path.isdir(ledger_dir):
        return start_body, complete_body

    try:
        entries = os.listdir(ledger_dir)
    except OSError:
        return start_body, complete_body

    # An entry BELONGS to this run if its frontmatter run-id matches, OR
    # (fallback for un-frontmattered entries) its filename carries the slug.
    start_suffix = f"-{run_id}-start.md"
    slug = f"-{run_id}-"
    start_name = ""
    # terminal candidates: (filename, body) for non-start belonging entries
    # whose body carries a terminal token. Last sort-order wins on ties.
    terminal_candidates: list[tuple[str, str]] = []

    for name in sorted(entries):
        if not name.endswith(".md"):
            continue
        full_path = os.path.join(ledger_dir, name)
        if not os.path.isfile(full_path):
            continue
        belongs = _frontmatter_runid(full_path) == run_id or slug in name
        if not belongs:
            continue
        if name.endswith(start_suffix):
            start_body = _parse_body_line(full_path)
            start_name = name
            continue
        body = _parse_body_line(full_path)
        if _TERMINAL_RE.search(body):
            terminal_candidates.append((name, body))

    # Exclude the start entry from terminal scan (already handled above);
    # highest-sorted filename is the terminal entry (last-writer semantics).
    terminal_candidates = [c for c in terminal_candidates if c[0] != start_name]
    if terminal_candidates:
        complete_body = sorted(terminal_candidates)[-1][1]

    return start_body, complete_body


def _derive_fields(
    start_body: str, complete_body: str
) -> tuple[str, str, str]:
    """
    Derive (date, lane, outcome) from ledger body lines.

    date  = first segment of start_body; else first segment of complete_body;
            else '?'.
    lane  = segment beginning 'lane: ' in start_body; strip prefix; else '?'.
    outcome = from complete_body: everything after the segment containing
              'COMPLETE' (segments after it, joined with ' · ').
              If no such segment or no segments after it, use the whole body.
              No complete_body → '(no complete entry)'.
    Outcome > 120 chars is truncated to 117 + '...'.
    """
    SEP = " · "

    # --- date ---
    date = "?"
    if start_body:
        segs = start_body.split(SEP)
        if segs[0].strip():
            date = segs[0].strip()
    if date == "?" and complete_body:
        segs = complete_body.split(SEP)
        if segs[0].strip():
            date = segs[0].strip()

    # --- lane ---
    lane = "?"
    if start_body:
        for seg in start_body.split(SEP):
            if seg.startswith("lane: "):
                lane = seg[len("lane: "):]
                break

    # --- outcome ---
    if not complete_body:
        outcome = "(no complete entry)"
    else:
        segs = complete_body.split(SEP)
        # Find the segment containing 'COMPLETE'
        complete_idx = None
        for i, seg in enumerate(segs):
            if "COMPLETE" in seg:
                complete_idx = i
                break

        if complete_idx is None:
            # No segment with COMPLETE found — use whole body
            outcome = complete_body
        else:
            after = segs[complete_idx + 1:]
            if after:
                outcome = SEP.join(after)
            else:
                # No segments after COMPLETE — use whole body
                outcome = complete_body

    # Truncate if > 120 chars
    if len(outcome) > 120:
        outcome = outcome[:117] + "..."

    return date, lane, outcome


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="vaultctl runs")
    parser.add_argument(
        "--vault",
        default=os.environ.get("VAULT_ROOT", os.path.expanduser("~/vault")),
        metavar="PATH",
        help="path to vault root",
    )
    args = parser.parse_args(argv)
    vault: str = args.vault

    archive_dir = os.path.join(vault, "executors", "archive")

    # Collect run-ids: only directories (amendment A8)
    run_ids: list[str] = []
    if os.path.isdir(archive_dir):
        try:
            for name in os.listdir(archive_dir):
                full = os.path.join(archive_dir, name)
                if os.path.isdir(full):
                    run_ids.append(name)
        except OSError:
            pass

    run_ids.sort()  # codepoint order

    print(f"ARCHIVED RUNS ({len(run_ids)})")

    for run_id in run_ids:
        start_body, complete_body = _get_ledger_entries(vault, run_id)
        date, lane, outcome = _derive_fields(start_body, complete_body)
        print(f"  {run_id} · {lane} · {date} · {outcome}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
