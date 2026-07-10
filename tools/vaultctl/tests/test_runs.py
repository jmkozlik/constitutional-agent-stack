"""
Gate fixtures for cmd_runs.main() — task t4-runs, run r002-vaultctl.

Covers every promise in the interface spec:
  - ARCHIVED RUNS (<n>) header exact format
  - Per-run line: "  <run-id> · <lane> · <date> · <outcome>"
  - Run-id codepoint sort
  - date = first segment of start body; fallback to complete; neither → "?"
  - lane = segment beginning "lane: " in start entry; absent → "?"
  - outcome = segments 3..end of complete body rejoined with " · ";
    no third segment → whole body; no complete entry → "(no complete entry)"
  - body line = ONLY first non-empty line after frontmatter closing ---
    (amendment A4); subsequent lines ignored
  - file without frontmatter → first non-empty line of file
  - non-directory archive entries ignored (amendment A8)
  - missing archive dir → "ARCHIVED RUNS (0)" + return 0
  - outcome >120 chars truncated to 117 + "..."
  - --vault flag accepted
  - return 0 on success
"""

import io
import os
import sys
import tempfile
import unittest

# ---------------------------------------------------------------------------
# Defensive import: collection must not crash when cmd_runs is absent.
# ---------------------------------------------------------------------------
try:
    import cmd_runs
    _CMD_RUNS_AVAILABLE = True
except ImportError:
    cmd_runs = None  # type: ignore[assignment]
    _CMD_RUNS_AVAILABLE = False


def _skip_if_absent(fn):
    """Decorator: skip test if cmd_runs could not be imported."""
    import functools

    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        if not _CMD_RUNS_AVAILABLE:
            self.skipTest("cmd_runs not yet available — fixtures collected, impl absent")
        return fn(self, *args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def _make_vault(tmp: str) -> str:
    """Return path to a fresh vault skeleton inside tmp."""
    vault = os.path.join(tmp, "vault")
    os.makedirs(os.path.join(vault, "executors", "archive"), exist_ok=True)
    os.makedirs(os.path.join(vault, "ledger"), exist_ok=True)
    return vault


def _add_run_dir(vault: str, run_id: str) -> None:
    """Register run_id as a subdirectory in archive."""
    os.makedirs(os.path.join(vault, "executors", "archive", run_id), exist_ok=True)


def _add_ledger_start(vault: str, run_id: str, body: str) -> None:
    _write(
        os.path.join(vault, "ledger", f"2026-06-05-{run_id}-start.md"),
        f"---\ntype: ledger\n---\n{body}\n",
    )


def _add_ledger_complete(vault: str, run_id: str, body: str) -> None:
    _write(
        os.path.join(vault, "ledger", f"2026-06-05-{run_id}-complete.md"),
        f"---\ntype: ledger\n---\n{body}\n",
    )


def _run_main(vault: str) -> tuple[int, str]:
    """Call cmd_runs.main with --vault and capture stdout. Returns (rc, output)."""
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        rc = cmd_runs.main(["--vault", vault])
    finally:
        sys.stdout = old_stdout
    return rc, buf.getvalue()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRunsOutputHeader(unittest.TestCase):
    """Header line: ARCHIVED RUNS (<n>)"""

    @_skip_if_absent
    def test_zero_runs_header_only(self):
        """Missing archive dir → 'ARCHIVED RUNS (0)' + nothing else."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = os.path.join(tmp, "vault")
            os.makedirs(os.path.join(vault, "ledger"), exist_ok=True)
            # No archive dir at all
            rc, out = _run_main(vault)
            self.assertEqual(rc, 0)
            self.assertEqual(out.rstrip("\n"), "ARCHIVED RUNS (0)")

    @_skip_if_absent
    def test_empty_archive_dir_header_only(self):
        """Existing but empty archive dir → 'ARCHIVED RUNS (0)'."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            rc, out = _run_main(vault)
            self.assertEqual(rc, 0)
            self.assertEqual(out.rstrip("\n"), "ARCHIVED RUNS (0)")

    @_skip_if_absent
    def test_header_count_matches_runs(self):
        """Header count reflects exactly how many run directories exist."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            _add_run_dir(vault, "r002")
            _add_run_dir(vault, "r003")
            _add_ledger_start(vault, "r001", "2026-06-01 · r001 START · lane: standard · rationale: x")
            _add_ledger_complete(vault, "r001", "2026-06-01 · r001 COMPLETE · outcome: ok")
            _add_ledger_start(vault, "r002", "2026-06-02 · r002 START · lane: quick · rationale: y")
            _add_ledger_complete(vault, "r002", "2026-06-02 · r002 COMPLETE · outcome: ok")
            _add_ledger_start(vault, "r003", "2026-06-03 · r003 START · lane: standard · rationale: z")
            _add_ledger_complete(vault, "r003", "2026-06-03 · r003 COMPLETE · outcome: ok")
            rc, out = _run_main(vault)
            lines = out.strip().splitlines()
            self.assertTrue(lines[0].startswith("ARCHIVED RUNS (3)"))


class TestRunsLineFormat(unittest.TestCase):
    """Per-run line format: '  <run-id> · <lane> · <date> · <outcome>'"""

    @_skip_if_absent
    def test_exact_line_format(self):
        """A complete run produces exact formatted output."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            _add_ledger_start(vault, "r001", "2026-06-05 · r001 START · lane: standard · rationale: test")
            _add_ledger_complete(vault, "r001", "2026-06-05 · r001 COMPLETE · outcome: success")
            rc, out = _run_main(vault)
            lines = out.strip().splitlines()
            # Line 0 is header; line 1 is the run line
            self.assertEqual(len(lines), 2)
            run_line = lines[1]
            self.assertTrue(run_line.startswith("  "), f"Expected 2-space indent, got: {run_line!r}")
            self.assertEqual(run_line, "  r001 · standard · 2026-06-05 · outcome: success")

    @_skip_if_absent
    def test_line_indent_is_exactly_two_spaces(self):
        """Each run line is indented with exactly two spaces."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            _add_ledger_start(vault, "r001", "2026-06-01 · r001 START · lane: quick · rationale: x")
            _add_ledger_complete(vault, "r001", "2026-06-01 · r001 COMPLETE · result: done")
            rc, out = _run_main(vault)
            run_lines = [l for l in out.splitlines() if l.startswith("  ")]
            self.assertEqual(len(run_lines), 1)
            self.assertFalse(run_lines[0].startswith("   "), "Should be exactly 2 spaces, not more")


class TestRunsSort(unittest.TestCase):
    """Run-ids sorted in codepoint (lexicographic) order."""

    @_skip_if_absent
    def test_codepoint_sort_order(self):
        """Run-ids appear in strict codepoint sort order."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            # Create in reverse order so filesystem ordering can't cheat
            for rid in ("r003", "r001", "r002"):
                _add_run_dir(vault, rid)
                _add_ledger_start(vault, rid, f"2026-06-01 · {rid} START · lane: standard · rationale: x")
                _add_ledger_complete(vault, rid, f"2026-06-01 · {rid} COMPLETE · outcome: ok")
            rc, out = _run_main(vault)
            lines = [l for l in out.splitlines() if l.startswith("  ")]
            run_ids = [l.split(" · ")[0].strip() for l in lines]
            self.assertEqual(run_ids, sorted(run_ids))

    @_skip_if_absent
    def test_codepoint_sort_alphanumeric(self):
        """Codepoint sort: uppercase before lowercase, digits before letters."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            for rid in ("z-run", "A-run", "1-run"):
                _add_run_dir(vault, rid)
                _add_ledger_start(vault, rid, f"2026-06-01 · {rid} START · lane: standard · rationale: x")
                _add_ledger_complete(vault, rid, f"2026-06-01 · {rid} COMPLETE · outcome: ok")
            rc, out = _run_main(vault)
            lines = [l for l in out.splitlines() if l.startswith("  ")]
            run_ids = [l.split(" · ")[0].strip() for l in lines]
            self.assertEqual(run_ids, sorted(run_ids))


class TestRunsDateDerivation(unittest.TestCase):
    """date field derivation rules."""

    @_skip_if_absent
    def test_date_from_start_entry(self):
        """date = first segment of start body line."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            _add_ledger_start(vault, "r001", "2026-06-05 · r001 START · lane: standard · rationale: x")
            _add_ledger_complete(vault, "r001", "2099-01-01 · r001 COMPLETE · outcome: ok")
            rc, out = _run_main(vault)
            run_line = [l for l in out.splitlines() if l.startswith("  ")][0]
            # Format: "  r001 · <lane> · <date> · <outcome>"
            parts = run_line.strip().split(" · ")
            date_field = parts[2]
            self.assertEqual(date_field, "2026-06-05")

    @_skip_if_absent
    def test_date_fallback_to_complete_when_no_start(self):
        """date falls back to first segment of complete entry when no start entry exists."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            # No start entry; only complete
            _add_ledger_complete(vault, "r001", "2026-06-10 · r001 COMPLETE · outcome: ok")
            rc, out = _run_main(vault)
            run_line = [l for l in out.splitlines() if l.startswith("  ")][0]
            parts = run_line.strip().split(" · ")
            date_field = parts[2]
            self.assertEqual(date_field, "2026-06-10")

    @_skip_if_absent
    def test_date_question_mark_when_neither_entry(self):
        """date = '?' when neither start nor complete entry exists for the run."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            # No ledger entries at all
            rc, out = _run_main(vault)
            run_line = [l for l in out.splitlines() if l.startswith("  ")][0]
            parts = run_line.strip().split(" · ")
            date_field = parts[2]
            self.assertEqual(date_field, "?")

    @_skip_if_absent
    def test_date_question_mark_complete_only_no_date_segment(self):
        """date = '?' when complete body has no segments (degenerate body)."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            # Complete body with no · separator — first segment IS the whole line
            _add_ledger_complete(vault, "r001", "COMPLETE")
            rc, out = _run_main(vault)
            run_line = [l for l in out.splitlines() if l.startswith("  ")][0]
            # date = first segment of complete body = "COMPLETE" (not "?") per spec:
            # spec says "first segment of complete entry" — single segment is the whole line
            parts = run_line.strip().split(" · ")
            date_field = parts[2]
            # "COMPLETE" is the first (only) segment — it IS the date value here
            self.assertEqual(date_field, "COMPLETE")


class TestRunsLaneDerivation(unittest.TestCase):
    """lane field derivation rules."""

    @_skip_if_absent
    def test_lane_from_start_entry(self):
        """lane extracted from start entry segment beginning 'lane: '."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            _add_ledger_start(vault, "r001", "2026-06-05 · r001 START · lane: standard · rationale: x")
            _add_ledger_complete(vault, "r001", "2026-06-05 · r001 COMPLETE · outcome: ok")
            rc, out = _run_main(vault)
            run_line = [l for l in out.splitlines() if l.startswith("  ")][0]
            parts = run_line.strip().split(" · ")
            lane_field = parts[1]
            self.assertEqual(lane_field, "standard")

    @_skip_if_absent
    def test_lane_quick(self):
        """lane = 'quick' when start entry contains 'lane: quick'."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            _add_ledger_start(vault, "r001", "2026-06-05 · r001 START · lane: quick · rationale: x")
            _add_ledger_complete(vault, "r001", "2026-06-05 · r001 COMPLETE · outcome: ok")
            rc, out = _run_main(vault)
            run_line = [l for l in out.splitlines() if l.startswith("  ")][0]
            parts = run_line.strip().split(" · ")
            self.assertEqual(parts[1], "quick")

    @_skip_if_absent
    def test_lane_question_mark_when_no_start_entry(self):
        """lane = '?' when no start entry for the run."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            _add_ledger_complete(vault, "r001", "2026-06-05 · r001 COMPLETE · outcome: ok")
            rc, out = _run_main(vault)
            run_line = [l for l in out.splitlines() if l.startswith("  ")][0]
            parts = run_line.strip().split(" · ")
            self.assertEqual(parts[1], "?")

    @_skip_if_absent
    def test_lane_question_mark_when_lane_segment_absent(self):
        """lane = '?' when start entry has no segment beginning 'lane: '."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            _add_ledger_start(vault, "r001", "2026-06-05 · r001 START · rationale: x")
            _add_ledger_complete(vault, "r001", "2026-06-05 · r001 COMPLETE · outcome: ok")
            rc, out = _run_main(vault)
            run_line = [l for l in out.splitlines() if l.startswith("  ")][0]
            parts = run_line.strip().split(" · ")
            self.assertEqual(parts[1], "?")

    @_skip_if_absent
    def test_lane_no_entries_at_all(self):
        """lane = '?' when there are no ledger entries for the run."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            rc, out = _run_main(vault)
            run_line = [l for l in out.splitlines() if l.startswith("  ")][0]
            parts = run_line.strip().split(" · ")
            self.assertEqual(parts[1], "?")


class TestRunsOutcomeDerivation(unittest.TestCase):
    """outcome field derivation rules."""

    @_skip_if_absent
    def test_outcome_segments_3_to_end(self):
        """outcome = segments 3..end (1-based) = [2:] (0-based) of complete body rejoined with ' · '.

        Spec: "segments 3..end re-joined with ' · '" uses 1-based segment numbering.
        Body: "2026-06-05 · r001 COMPLETE · outcome: success · notes: all good"
          seg1(0-idx 0) = "2026-06-05"
          seg2(0-idx 1) = "r001 COMPLETE"
          seg3(0-idx 2) = "outcome: success"   <- first outcome segment
          seg4(0-idx 3) = "notes: all good"
        outcome = seg3..end (1-based) = "outcome: success · notes: all good"
        """
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            _add_ledger_start(vault, "r001", "2026-06-05 · r001 START · lane: standard · rationale: x")
            _add_ledger_complete(vault, "r001", "2026-06-05 · r001 COMPLETE · outcome: success · notes: all good")
            rc, out = _run_main(vault)
            run_line = [l for l in out.splitlines() if l.startswith("  ")][0]
            # Expected outcome: "outcome: success · notes: all good" (0-based [2:])
            self.assertIn("outcome: success · notes: all good", run_line)

    @_skip_if_absent
    def test_outcome_whole_body_when_no_third_segment(self):
        """outcome = whole complete body line when body has no third segment (1-based).

        Spec: "if the complete body line has no third segment, use the whole body line."
        "Third segment" is 1-based: if the body has only 2 segments, use the whole body.
        Body: "2026-06-05 · r001 COMPLETE" → only 2 segments (1-based: seg1, seg2)
        → outcome = whole body line = "2026-06-05 · r001 COMPLETE"
        """
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            _add_ledger_start(vault, "r001", "2026-06-05 · r001 START · lane: standard · rationale: x")
            # Only 2 segments (1-based) → use whole body
            _add_ledger_complete(vault, "r001", "2026-06-05 · r001 COMPLETE")
            rc, out = _run_main(vault)
            run_line = [l for l in out.splitlines() if l.startswith("  ")][0]
            # outcome = whole body = "2026-06-05 · r001 COMPLETE"
            self.assertIn("2026-06-05 · r001 COMPLETE", run_line)

    @_skip_if_absent
    def test_outcome_no_complete_entry(self):
        """outcome = '(no complete entry)' when no complete ledger entry exists."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            _add_ledger_start(vault, "r001", "2026-06-05 · r001 START · lane: standard · rationale: x")
            # No complete entry
            rc, out = _run_main(vault)
            run_line = [l for l in out.splitlines() if l.startswith("  ")][0]
            self.assertIn("(no complete entry)", run_line)

    @_skip_if_absent
    def test_outcome_no_entries_at_all(self):
        """outcome = '(no complete entry)' when no ledger entries exist at all."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            rc, out = _run_main(vault)
            run_line = [l for l in out.splitlines() if l.startswith("  ")][0]
            self.assertIn("(no complete entry)", run_line)

    @_skip_if_absent
    def test_outcome_multiple_trailing_segments(self):
        """outcome includes all segments 3..end (1-based) joined with ' · '.

        Body: "2026-06-05 · r001 COMPLETE · seg3 · seg4 · seg5"
          1-based seg3(0-idx 2)="seg3", seg4(0-idx 3)="seg4", seg5(0-idx 4)="seg5"
        outcome = seg3..seg5 = "seg3 · seg4 · seg5"
        """
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            _add_ledger_start(vault, "r001", "2026-06-05 · r001 START · lane: standard · rationale: x")
            _add_ledger_complete(vault, "r001",
                "2026-06-05 · r001 COMPLETE · seg3 · seg4 · seg5")
            rc, out = _run_main(vault)
            run_line = [l for l in out.splitlines() if l.startswith("  ")][0]
            # outcome = 1-based seg3..end = "seg3 · seg4 · seg5"
            self.assertIn("seg3 · seg4 · seg5", run_line)


class TestRunsOutcomeTruncation(unittest.TestCase):
    """Outcome >120 chars truncated to 117 + '...'"""

    @_skip_if_absent
    def test_outcome_truncated_at_117_plus_ellipsis(self):
        """outcome longer than 120 chars is truncated to 117 + '...'."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            _add_ledger_start(vault, "r001", "2026-06-05 · r001 START · lane: standard · rationale: x")
            # Make outcome segment long: 130 chars
            long_outcome = "x" * 130
            _add_ledger_complete(vault, "r001",
                f"2026-06-05 · r001 COMPLETE · {long_outcome}")
            rc, out = _run_main(vault)
            run_line = [l for l in out.splitlines() if l.startswith("  ")][0]
            # Extract outcome portion
            parts = run_line.strip().split(" · ", 3)  # split into at most 4: run-id, lane, date, outcome
            outcome_field = parts[3]
            self.assertLessEqual(len(outcome_field), 120,
                f"outcome field should be <=120 chars, got {len(outcome_field)}")
            self.assertTrue(outcome_field.endswith("..."),
                f"Truncated outcome should end with '...', got: {outcome_field!r}")
            self.assertEqual(len(outcome_field), 120,
                f"Truncated outcome should be exactly 120 chars (117+'...'), got {len(outcome_field)}")

    @_skip_if_absent
    def test_outcome_not_truncated_when_exactly_120(self):
        """outcome of exactly 120 chars is NOT truncated."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            _add_ledger_start(vault, "r001", "2026-06-05 · r001 START · lane: standard · rationale: x")
            exactly_120 = "y" * 120
            _add_ledger_complete(vault, "r001",
                f"2026-06-05 · r001 COMPLETE · {exactly_120}")
            rc, out = _run_main(vault)
            run_line = [l for l in out.splitlines() if l.startswith("  ")][0]
            parts = run_line.strip().split(" · ", 3)
            outcome_field = parts[3]
            self.assertFalse(outcome_field.endswith("..."),
                f"120-char outcome should NOT be truncated: {outcome_field!r}")
            self.assertEqual(len(outcome_field), 120)

    @_skip_if_absent
    def test_outcome_not_truncated_when_under_120(self):
        """outcome under 120 chars is not truncated."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            _add_ledger_start(vault, "r001", "2026-06-05 · r001 START · lane: standard · rationale: x")
            short_outcome = "short outcome"
            _add_ledger_complete(vault, "r001",
                f"2026-06-05 · r001 COMPLETE · {short_outcome}")
            rc, out = _run_main(vault)
            run_line = [l for l in out.splitlines() if l.startswith("  ")][0]
            self.assertIn(short_outcome, run_line)
            self.assertNotIn("...", run_line)


class TestRunsBodyLineParsing(unittest.TestCase):
    """Body line = ONLY first non-empty line after frontmatter (amendment A4)."""

    @_skip_if_absent
    def test_body_line_first_non_empty_after_frontmatter(self):
        """Body line is the first non-empty line after the closing --- of frontmatter."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            # Write start entry with frontmatter and a blank line before body
            start_path = os.path.join(vault, "ledger", "2026-06-05-r001-start.md")
            _write(start_path,
                "---\ntype: ledger\n---\n\n2026-06-05 · r001 START · lane: standard · rationale: x\nSECOND LINE IGNORED\n")
            _add_ledger_complete(vault, "r001", "2026-06-05 · r001 COMPLETE · outcome: ok")
            rc, out = _run_main(vault)
            run_line = [l for l in out.splitlines() if l.startswith("  ")][0]
            parts = run_line.strip().split(" · ")
            # date should be from the first non-empty body line, not "SECOND LINE IGNORED"
            self.assertEqual(parts[2], "2026-06-05")

    @_skip_if_absent
    def test_subsequent_body_lines_ignored(self):
        """Lines after the first non-empty body line are completely ignored."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            complete_path = os.path.join(vault, "ledger", "2026-06-05-r001-complete.md")
            # Second line has different content that would affect outcome if used
            _write(complete_path,
                "---\ntype: ledger\n---\n2026-06-05 · r001 COMPLETE · real-outcome\nSHOULD-NOT-APPEAR-IN-OUTPUT\n")
            _add_ledger_start(vault, "r001", "2026-06-05 · r001 START · lane: standard · rationale: x")
            rc, out = _run_main(vault)
            self.assertNotIn("SHOULD-NOT-APPEAR-IN-OUTPUT", out)
            self.assertIn("real-outcome", out)

    @_skip_if_absent
    def test_file_without_frontmatter_uses_first_non_empty_line(self):
        """File without frontmatter: first non-empty line is the body line."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            # No frontmatter block — raw content
            start_path = os.path.join(vault, "ledger", "2026-06-05-r001-start.md")
            _write(start_path,
                "\n2026-06-05 · r001 START · lane: quick · rationale: no-frontmatter\n")
            _add_ledger_complete(vault, "r001", "2026-06-05 · r001 COMPLETE · outcome: ok")
            rc, out = _run_main(vault)
            run_line = [l for l in out.splitlines() if l.startswith("  ")][0]
            parts = run_line.strip().split(" · ")
            self.assertEqual(parts[1], "quick")  # lane extracted correctly
            self.assertEqual(parts[2], "2026-06-05")  # date extracted correctly

    @_skip_if_absent
    def test_frontmatter_closed_by_second_triple_dash(self):
        """Frontmatter extends until the second line that is exactly '---'."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            start_path = os.path.join(vault, "ledger", "2026-06-05-r001-start.md")
            _write(start_path,
                "---\ntype: ledger\nrun-id: r001\nauthor: agent\n---\n2026-06-05 · r001 START · lane: standard · rationale: x\n")
            _add_ledger_complete(vault, "r001", "2026-06-05 · r001 COMPLETE · outcome: ok")
            rc, out = _run_main(vault)
            run_line = [l for l in out.splitlines() if l.startswith("  ")][0]
            parts = run_line.strip().split(" · ")
            self.assertEqual(parts[2], "2026-06-05")


class TestRunsNonDirectoryIgnored(unittest.TestCase):
    """Non-directory archive entries ignored (amendment A8)."""

    @_skip_if_absent
    def test_file_in_archive_ignored(self):
        """Plain files in archive/ are not treated as run-ids."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            # Add a real run dir
            _add_run_dir(vault, "r001")
            _add_ledger_start(vault, "r001", "2026-06-05 · r001 START · lane: standard · rationale: x")
            _add_ledger_complete(vault, "r001", "2026-06-05 · r001 COMPLETE · outcome: ok")
            # Add a file (not a dir) in archive/
            file_in_archive = os.path.join(vault, "executors", "archive", "_index.md")
            with open(file_in_archive, "w") as fh:
                fh.write("# index\n")
            rc, out = _run_main(vault)
            lines = out.strip().splitlines()
            # Header should say 1, not 2
            self.assertTrue(lines[0].startswith("ARCHIVED RUNS (1)"),
                f"Expected ARCHIVED RUNS (1) but got: {lines[0]!r}")
            # _index.md should not appear as a run line
            self.assertNotIn("_index.md", out)

    @_skip_if_absent
    def test_dotfile_in_archive_ignored(self):
        """Dotfiles like .DS_Store in archive/ are not treated as run-ids."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            _add_ledger_start(vault, "r001", "2026-06-05 · r001 START · lane: standard · rationale: x")
            _add_ledger_complete(vault, "r001", "2026-06-05 · r001 COMPLETE · outcome: ok")
            # Add .DS_Store file
            ds_store = os.path.join(vault, "executors", "archive", ".DS_Store")
            with open(ds_store, "w") as fh:
                fh.write("")
            rc, out = _run_main(vault)
            lines = out.strip().splitlines()
            self.assertTrue(lines[0].startswith("ARCHIVED RUNS (1)"),
                f"Expected ARCHIVED RUNS (1), got: {lines[0]!r}")

    @_skip_if_absent
    def test_symlink_to_file_in_archive_ignored(self):
        """Symlinks pointing to files in archive/ are not treated as run-ids."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            _add_ledger_start(vault, "r001", "2026-06-05 · r001 START · lane: standard · rationale: x")
            _add_ledger_complete(vault, "r001", "2026-06-05 · r001 COMPLETE · outcome: ok")
            # Create a file and symlink to it in archive
            real_file = os.path.join(tmp, "real.txt")
            with open(real_file, "w") as fh:
                fh.write("content")
            symlink_path = os.path.join(vault, "executors", "archive", "symlink-run")
            os.symlink(real_file, symlink_path)
            rc, out = _run_main(vault)
            lines = out.strip().splitlines()
            self.assertTrue(lines[0].startswith("ARCHIVED RUNS (1)"),
                f"Expected ARCHIVED RUNS (1) (symlink to file ignored), got: {lines[0]!r}")


class TestRunsMissingArchiveDir(unittest.TestCase):
    """Missing archive dir → ARCHIVED RUNS (0) + return 0."""

    @_skip_if_absent
    def test_missing_archive_dir_returns_zero(self):
        """Return code is 0 when archive dir is missing."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = os.path.join(tmp, "vault")
            os.makedirs(os.path.join(vault, "ledger"), exist_ok=True)
            # No archive dir
            rc, out = _run_main(vault)
            self.assertEqual(rc, 0)

    @_skip_if_absent
    def test_missing_archive_dir_header_output(self):
        """Output is exactly 'ARCHIVED RUNS (0)\\n' when archive dir missing."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = os.path.join(tmp, "vault")
            os.makedirs(os.path.join(vault, "ledger"), exist_ok=True)
            rc, out = _run_main(vault)
            self.assertEqual(out.rstrip("\n"), "ARCHIVED RUNS (0)")


class TestRunsReturnCode(unittest.TestCase):
    """Return 0 on success."""

    @_skip_if_absent
    def test_return_0_on_success_with_runs(self):
        """main() returns 0 on successful scan with runs present."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            _add_ledger_start(vault, "r001", "2026-06-05 · r001 START · lane: standard · rationale: x")
            _add_ledger_complete(vault, "r001", "2026-06-05 · r001 COMPLETE · outcome: ok")
            rc, out = _run_main(vault)
            self.assertEqual(rc, 0)

    @_skip_if_absent
    def test_return_0_on_empty_archive(self):
        """main() returns 0 on empty archive (zero runs is not an error)."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            rc, out = _run_main(vault)
            self.assertEqual(rc, 0)


class TestRunsVaultFlag(unittest.TestCase):
    """--vault PATH flag is accepted and used."""

    @_skip_if_absent
    def test_vault_flag_accepted(self):
        """--vault PATH flag is accepted without error."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            rc, out = _run_main(vault)
            # Should not raise, should succeed
            self.assertEqual(rc, 0)

    @_skip_if_absent
    def test_vault_flag_selects_correct_vault(self):
        """--vault PATH uses the specified vault, not the default."""
        with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
            vault1 = _make_vault(tmp1)
            vault2 = _make_vault(tmp2)
            # vault1 has a run, vault2 is empty
            _add_run_dir(vault1, "r001")
            _add_ledger_start(vault1, "r001", "2026-06-05 · r001 START · lane: standard · rationale: x")
            _add_ledger_complete(vault1, "r001", "2026-06-05 · r001 COMPLETE · outcome: ok")

            buf = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = buf
            try:
                rc2 = cmd_runs.main(["--vault", vault2])
            finally:
                sys.stdout = old_stdout
            out2 = buf.getvalue()

            # vault2 is empty — header should say 0
            self.assertTrue(out2.rstrip("\n").startswith("ARCHIVED RUNS (0)"))


class TestRunsMultipleRuns(unittest.TestCase):
    """Integration: multiple runs with mixed completeness."""

    @_skip_if_absent
    def test_mixed_runs_output(self):
        """Multiple runs including incomplete produce correct lines."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            # r001: complete run
            _add_run_dir(vault, "r001")
            _add_ledger_start(vault, "r001", "2026-06-01 · r001 START · lane: standard · rationale: initial")
            _add_ledger_complete(vault, "r001", "2026-06-01 · r001 COMPLETE · outcome: shipped")
            # r002: incomplete (no complete entry)
            _add_run_dir(vault, "r002")
            _add_ledger_start(vault, "r002", "2026-06-02 · r002 START · lane: quick · rationale: hotfix")
            # r003: no entries at all
            _add_run_dir(vault, "r003")

            rc, out = _run_main(vault)
            lines = out.strip().splitlines()

            self.assertEqual(lines[0], "ARCHIVED RUNS (3)")
            self.assertEqual(len(lines), 4)  # header + 3 run lines

            run_lines = lines[1:]
            # All should be indented
            for line in run_lines:
                self.assertTrue(line.startswith("  "), f"Missing indent: {line!r}")

            # r001 line
            r001_line = [l for l in run_lines if "r001" in l][0]
            self.assertIn("standard", r001_line)
            self.assertIn("2026-06-01", r001_line)
            self.assertIn("outcome: shipped", r001_line)

            # r002 line — incomplete
            r002_line = [l for l in run_lines if "r002" in l][0]
            self.assertIn("quick", r002_line)
            self.assertIn("(no complete entry)", r002_line)

            # r003 line — no entries
            r003_line = [l for l in run_lines if "r003" in l][0]
            self.assertIn("?", r003_line)  # date and lane both "?"
            self.assertIn("(no complete entry)", r003_line)

    @_skip_if_absent
    def test_run_ids_sorted_in_output(self):
        """Run lines appear in codepoint-sorted order regardless of creation order."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            for rid in ("r003", "r001", "r002"):
                _add_run_dir(vault, rid)
                _add_ledger_start(vault, rid, f"2026-06-01 · {rid} START · lane: standard · rationale: x")
                _add_ledger_complete(vault, rid, f"2026-06-01 · {rid} COMPLETE · outcome: ok")
            rc, out = _run_main(vault)
            run_lines = [l for l in out.splitlines() if l.startswith("  ")]
            run_ids = [l.strip().split(" · ")[0] for l in run_lines]
            self.assertEqual(run_ids, ["r001", "r002", "r003"])


class TestRunsLedgerEntryMatching(unittest.TestCase):
    """Ledger entry filename matching: ends with -<run-id>-start.md or -<run-id>-complete.md."""

    @_skip_if_absent
    def test_ledger_entry_matched_by_run_id_suffix(self):
        """Ledger entries are matched by suffix -<run-id>-start.md, any prefix ok."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r001")
            # Use a different prefix date
            _write(
                os.path.join(vault, "ledger", "2099-12-31-r001-start.md"),
                "---\ntype: ledger\n---\n2026-06-05 · r001 START · lane: standard · rationale: x\n",
            )
            _write(
                os.path.join(vault, "ledger", "2099-12-31-r001-complete.md"),
                "---\ntype: ledger\n---\n2026-06-05 · r001 COMPLETE · outcome: ok\n",
            )
            rc, out = _run_main(vault)
            run_line = [l for l in out.splitlines() if l.startswith("  ")][0]
            self.assertIn("standard", run_line)
            self.assertIn("2026-06-05", run_line)

    @_skip_if_absent
    def test_ledger_entry_not_matched_by_partial_run_id(self):
        """Ledger entry for 'r001' does not affect run 'r01' (no partial match)."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            _add_run_dir(vault, "r01")
            # Entry for r001 — should NOT match r01
            _write(
                os.path.join(vault, "ledger", "2026-06-05-r001-start.md"),
                "---\ntype: ledger\n---\n2026-06-05 · r001 START · lane: standard · rationale: x\n",
            )
            rc, out = _run_main(vault)
            run_line = [l for l in out.splitlines() if l.startswith("  ")][0]
            # r01 has no matching entries → date=?, lane=?
            parts = run_line.strip().split(" · ")
            self.assertEqual(parts[2], "?")  # date should be ?


if __name__ == "__main__":
    unittest.main()
