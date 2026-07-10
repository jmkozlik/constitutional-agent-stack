"""
Gate fixtures for t2-status (r002-vaultctl).

Tests are derived EXCLUSIVELY from the interface spec in:
  vault/executors/contracts/r002-vaultctl/t2-status.md

All tests build synthetic vault trees in tempfile.TemporaryDirectory and
invoke cmd_status.main() directly.  The import is guarded so that test
collection succeeds even when cmd_status.py does not yet exist.
"""

import contextlib
import importlib
import io
import os
import pathlib
import sys
import textwrap
import tempfile
import unittest


def _load_cmd_status():
    """Return the cmd_status module, or None if not yet present."""
    spec = importlib.util.find_spec("cmd_status")
    if spec is None:
        return None
    # Re-import in case a previous import cached a stale version.
    if "cmd_status" in sys.modules:
        return sys.modules["cmd_status"]
    return importlib.import_module("cmd_status")


def _skip_if_absent(test_method):
    """Decorator: skip the test when cmd_status.py is not in sys.path."""
    def wrapper(self):
        mod = _load_cmd_status()
        if mod is None:
            raise unittest.SkipTest("cmd_status.py not present — skipping until implementation lands")
        return test_method(self, mod)
    wrapper.__name__ = test_method.__name__
    return wrapper


def _run_main(mod, vault_path: str):
    """
    Call mod.main(["--vault", vault_path]) and capture stdout/stderr.
    Returns (stdout_str, stderr_str, return_code).
    """
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
        try:
            rc = mod.main(["--vault", vault_path])
        except SystemExit as exc:
            rc = exc.code if isinstance(exc.code, int) else 1
    return stdout_buf.getvalue(), stderr_buf.getvalue(), rc


# ---------------------------------------------------------------------------
# Helpers for building synthetic vault trees
# ---------------------------------------------------------------------------

def _make_dir(root: pathlib.Path, *parts: str) -> pathlib.Path:
    d = root.joinpath(*parts)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write(path: pathlib.Path, content: str):
    path.write_text(textwrap.dedent(content), encoding="utf-8")


def _state_md(run_id="r001", lane="standard", rationale="test run",
               project="myproject", status="active"):
    """Minimal council/state.md with a RUN-STATE block."""
    return f"""\
# Council State

<!-- RUN-STATE
run-id: {run_id}
lane: {lane}
rationale: {rationale}
project: {project}
status: {status}
-->

Some other content.
"""


def _executor_note(agent="agent-001", status="active", current_task="doing something"):
    """Well-formed executor note with frontmatter + ## Current task."""
    return f"""\
---
agent: {agent}
status: {status}
---
# Working State — {agent}
## Current task
{current_task}
## Next step
whatever
"""


def _ledger_entry(body_line="Completed phase one"):
    """Minimal ledger note with frontmatter + one body line."""
    return f"""\
---
type: ledger
---
{body_line}
"""


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestStatusHappyPath(unittest.TestCase):
    """Full vault with all sections populated → rc=0 and exact output."""

    @_skip_if_absent
    def test_happy_path_full(self, mod):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)

            # council/state.md
            council = _make_dir(root, "council")
            _write(council / "state.md", _state_md(
                run_id="r002", lane="standard", rationale="integration test",
                project="vaultctl", status="active"
            ))

            # executors/active/ — two notes
            active = _make_dir(root, "executors", "active")
            _write(active / "agent-a.md", _executor_note(
                agent="agent-a", status="active", current_task="building cmd_status"
            ))
            _write(active / "agent-b.md", _executor_note(
                agent="agent-b", status="blocked", current_task="waiting for spec"
            ))

            # ledger/ — three entries
            ledger = _make_dir(root, "ledger")
            _write(ledger / "0001-init.md", _ledger_entry("Scaffolded the repo"))
            _write(ledger / "0002-contracts.md", _ledger_entry("Wrote contracts for r001"))
            _write(ledger / "0003-impl.md", _ledger_entry("Implemented cmd_index"))

            stdout, stderr, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 0, f"Expected rc=0, got {rc}; stderr={stderr!r}")
        self.assertEqual(stderr, "", f"Expected no stderr, got {stderr!r}")

        lines = stdout.splitlines()
        self.assertEqual(lines[0], f"VAULT STATUS — {tmp}")
        self.assertIn("RUN-STATE", stdout)
        self.assertIn("  run-id:   r002", stdout)
        self.assertIn("  lane:     standard", stdout)
        self.assertIn("  status:   active", stdout)
        self.assertIn("  project:  vaultctl", stdout)
        self.assertIn("EXECUTORS (2 active)", stdout)
        self.assertIn("  agent-a · active · building cmd_status", stdout)
        self.assertIn("  agent-b · blocked · waiting for spec", stdout)
        self.assertIn("RECENT LEDGER", stdout)
        self.assertIn("  0003-impl · Implemented cmd_index", stdout)
        self.assertIn("  0002-contracts · Wrote contracts for r001", stdout)
        self.assertIn("  0001-init · Scaffolded the repo", stdout)


class TestStatusExactOutputFormat(unittest.TestCase):
    """Assert the EXACT output format, not just contains-checks."""

    @_skip_if_absent
    def test_exact_output_structure(self, mod):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)

            council = _make_dir(root, "council")
            _write(council / "state.md", _state_md(
                run_id="r099", lane="quick", rationale="format test",
                project="proj", status="done"
            ))

            active = _make_dir(root, "executors", "active")
            _write(active / "exec-1.md", _executor_note(
                agent="exec-1", status="active", current_task="the task"
            ))

            ledger = _make_dir(root, "ledger")
            _write(ledger / "0010-entry.md", _ledger_entry("The ledger body"))

            stdout, _, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 0)
        expected = (
            f"VAULT STATUS — {tmp}\n"
            "\n"
            "RUN-STATE\n"
            "  run-id:   r099\n"
            "  lane:     quick\n"
            "  status:   done\n"
            "  project:  proj\n"
            "\n"
            "EXECUTORS (1 active)\n"
            "  exec-1 · active · the task\n"
            "\n"
            "RECENT LEDGER\n"
            "  0010-entry · The ledger body\n"
        )
        self.assertEqual(stdout, expected,
                         f"Output mismatch.\nGot:\n{stdout!r}\nExpected:\n{expected!r}")


class TestStatusMissingStateFile(unittest.TestCase):
    """Missing council/state.md → stderr message + return 1."""

    @_skip_if_absent
    def test_missing_state_md(self, mod):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _make_dir(root, "council")
            # Do NOT write state.md

            stdout, stderr, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 1, f"Expected rc=1, got {rc}")
        self.assertNotEqual(stderr.strip(), "",
                            "Expected an error message on stderr, got nothing")


class TestStatusNoRunStateBlock(unittest.TestCase):
    """state.md exists but contains no <!-- RUN-STATE --> block → stderr + return 1."""

    @_skip_if_absent
    def test_no_run_state_block(self, mod):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            council = _make_dir(root, "council")
            _write(council / "state.md", "# Council State\n\nNo run-state block here.\n")

            stdout, stderr, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 1, f"Expected rc=1, got {rc}")
        self.assertNotEqual(stderr.strip(), "",
                            "Expected an error message on stderr when no RUN-STATE block")


class TestStatusMissingKeysRenderAsQuestionMark(unittest.TestCase):
    """Keys absent from RUN-STATE block render as `?`."""

    @_skip_if_absent
    def test_missing_run_state_keys(self, mod):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            council = _make_dir(root, "council")
            # Only include run-id and status; omit lane, rationale, project
            _write(council / "state.md", textwrap.dedent("""\
                # Council State

                <!-- RUN-STATE
                run-id: r042
                status: paused
                -->
            """))

            active = _make_dir(root, "executors", "active")
            ledger = _make_dir(root, "ledger")

            stdout, stderr, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 0, f"Expected rc=0 when keys are just missing; stderr={stderr!r}")
        self.assertIn("  run-id:   r042", stdout)
        self.assertIn("  lane:     ?", stdout)
        self.assertIn("  project:  ?", stdout)
        self.assertIn("  status:   paused", stdout)


class TestStatusEmptyActiveDirectory(unittest.TestCase):
    """Empty executors/active/ → EXECUTORS (0 active) with (none)."""

    @_skip_if_absent
    def test_empty_active_dir(self, mod):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            council = _make_dir(root, "council")
            _write(council / "state.md", _state_md())
            _make_dir(root, "executors", "active")   # exists but empty
            _make_dir(root, "ledger")

            stdout, stderr, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 0, f"stderr={stderr!r}")
        self.assertIn("EXECUTORS (0 active)", stdout)
        # The (none) sentinel must appear in the executors section
        executor_section_start = stdout.index("EXECUTORS")
        ledger_section_start = stdout.index("RECENT LEDGER")
        executor_section = stdout[executor_section_start:ledger_section_start]
        self.assertIn("(none)", executor_section)


class TestStatusEmptyLedgerDirectory(unittest.TestCase):
    """Empty ledger/ → RECENT LEDGER section with (none)."""

    @_skip_if_absent
    def test_empty_ledger_dir(self, mod):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            council = _make_dir(root, "council")
            _write(council / "state.md", _state_md())
            _make_dir(root, "executors", "active")
            _make_dir(root, "ledger")   # exists but empty

            stdout, stderr, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 0, f"stderr={stderr!r}")
        self.assertIn("RECENT LEDGER", stdout)
        ledger_section = stdout[stdout.index("RECENT LEDGER"):]
        self.assertIn("(none)", ledger_section)


class TestStatusMissingActiveDirectory(unittest.TestCase):
    """Missing executors/active/ dir → treated as zero notes."""

    @_skip_if_absent
    def test_missing_active_dir(self, mod):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            council = _make_dir(root, "council")
            _write(council / "state.md", _state_md())
            # Do NOT create executors/active/
            _make_dir(root, "ledger")

            stdout, stderr, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 0, f"stderr={stderr!r}")
        self.assertIn("EXECUTORS (0 active)", stdout)
        executor_section_start = stdout.index("EXECUTORS")
        ledger_section_start = stdout.index("RECENT LEDGER")
        executor_section = stdout[executor_section_start:ledger_section_start]
        self.assertIn("(none)", executor_section)


class TestStatusMissingLedgerDirectory(unittest.TestCase):
    """Missing ledger/ dir → treated as zero entries."""

    @_skip_if_absent
    def test_missing_ledger_dir(self, mod):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            council = _make_dir(root, "council")
            _write(council / "state.md", _state_md())
            _make_dir(root, "executors", "active")
            # Do NOT create ledger/

            stdout, stderr, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 0, f"stderr={stderr!r}")
        ledger_section = stdout[stdout.index("RECENT LEDGER"):]
        self.assertIn("(none)", ledger_section)


class TestStatusLedgerSortedDescMax3(unittest.TestCase):
    """Ledger entries sorted by NNNN descending; only the top 3 shown."""

    @_skip_if_absent
    def test_ledger_sort_and_limit(self, mod):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            council = _make_dir(root, "council")
            _write(council / "state.md", _state_md())
            _make_dir(root, "executors", "active")

            ledger = _make_dir(root, "ledger")
            _write(ledger / "0001-alpha.md", _ledger_entry("First entry"))
            _write(ledger / "0002-beta.md", _ledger_entry("Second entry"))
            _write(ledger / "0003-gamma.md", _ledger_entry("Third entry"))
            _write(ledger / "0004-delta.md", _ledger_entry("Fourth entry"))
            _write(ledger / "0005-epsilon.md", _ledger_entry("Fifth entry"))

            stdout, stderr, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 0, f"stderr={stderr!r}")
        # Only 3 most recent
        self.assertIn("  0005-epsilon · Fifth entry", stdout)
        self.assertIn("  0004-delta · Fourth entry", stdout)
        self.assertIn("  0003-gamma · Third entry", stdout)
        self.assertNotIn("0002-beta", stdout)
        self.assertNotIn("0001-alpha", stdout)

    @_skip_if_absent
    def test_ledger_newest_first_order(self, mod):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            council = _make_dir(root, "council")
            _write(council / "state.md", _state_md())
            _make_dir(root, "executors", "active")

            ledger = _make_dir(root, "ledger")
            _write(ledger / "0001-a.md", _ledger_entry("Body one"))
            _write(ledger / "0003-c.md", _ledger_entry("Body three"))
            _write(ledger / "0002-b.md", _ledger_entry("Body two"))

            stdout, _, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 0)
        ledger_section = stdout[stdout.index("RECENT LEDGER"):]
        pos_3 = ledger_section.index("0003-c")
        pos_2 = ledger_section.index("0002-b")
        pos_1 = ledger_section.index("0001-a")
        self.assertLess(pos_3, pos_2, "0003 should appear before 0002")
        self.assertLess(pos_2, pos_1, "0002 should appear before 0001")


class TestStatusLedgerBodyLine(unittest.TestCase):
    """
    Body line = first non-empty line AFTER the frontmatter closing `---`
    (the second `---` occurrence per amendment A6).
    """

    @_skip_if_absent
    def test_body_line_after_second_dashes(self, mod):
        """A `---` inside the body must NOT be treated as frontmatter close."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            council = _make_dir(root, "council")
            _write(council / "state.md", _state_md())
            _make_dir(root, "executors", "active")

            ledger = _make_dir(root, "ledger")
            # Third `---` is in the body — must not confuse the parser
            _write(ledger / "0001-tricky.md", textwrap.dedent("""\
                ---
                type: ledger
                ---
                This is the real body line.
                ---
                This is NOT the body line.
            """))

            stdout, _, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 0)
        self.assertIn("  0001-tricky · This is the real body line.", stdout)
        self.assertNotIn("This is NOT the body line.", stdout)

    @_skip_if_absent
    def test_body_line_skips_empty_lines(self, mod):
        """First NON-EMPTY line after frontmatter is the body line."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            council = _make_dir(root, "council")
            _write(council / "state.md", _state_md())
            _make_dir(root, "executors", "active")

            ledger = _make_dir(root, "ledger")
            _write(ledger / "0001-spaced.md", textwrap.dedent("""\
                ---
                type: ledger
                ---


                Actual body here.
            """))

            stdout, _, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 0)
        self.assertIn("  0001-spaced · Actual body here.", stdout)


class TestStatusLedgerNonMatchingFilesExcluded(unittest.TestCase):
    """Files that do not match NNNN-*.md pattern are excluded from ledger."""

    @_skip_if_absent
    def test_non_matching_files_excluded(self, mod):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            council = _make_dir(root, "council")
            _write(council / "state.md", _state_md())
            _make_dir(root, "executors", "active")

            ledger = _make_dir(root, "ledger")
            _write(ledger / "0001-valid.md", _ledger_entry("Valid entry"))
            _write(ledger / "_index.md", _ledger_entry("Index — must be excluded"))
            _write(ledger / "README.md", _ledger_entry("Readme — must be excluded"))
            _write(ledger / "123-short.md", _ledger_entry("Three digits — excluded"))
            _write(ledger / "00001-long.md", _ledger_entry("Five digits — excluded"))

            stdout, _, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 0)
        self.assertIn("0001-valid", stdout)
        self.assertNotIn("Index — must be excluded", stdout)
        self.assertNotIn("Readme — must be excluded", stdout)
        self.assertNotIn("123-short", stdout)
        self.assertNotIn("00001-long", stdout)


class TestStatusIndexMdExcluded(unittest.TestCase):
    """_index.md is excluded from both executors/active/ and ledger/."""

    @_skip_if_absent
    def test_index_excluded_from_executors(self, mod):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            council = _make_dir(root, "council")
            _write(council / "state.md", _state_md())

            active = _make_dir(root, "executors", "active")
            _write(active / "_index.md", _executor_note(
                agent="should-not-appear", status="active", current_task="hidden"
            ))
            _make_dir(root, "ledger")

            stdout, _, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 0)
        self.assertIn("EXECUTORS (0 active)", stdout)
        self.assertNotIn("should-not-appear", stdout)

    @_skip_if_absent
    def test_index_excluded_from_ledger(self, mod):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            council = _make_dir(root, "council")
            _write(council / "state.md", _state_md())
            _make_dir(root, "executors", "active")

            ledger = _make_dir(root, "ledger")
            # _index.md does not match NNNN-*.md anyway, but be explicit
            _write(ledger / "_index.md", _ledger_entry("Should be excluded"))
            _write(ledger / "0001-real.md", _ledger_entry("Real entry"))

            stdout, _, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 0)
        self.assertNotIn("Should be excluded", stdout)
        self.assertIn("0001-real", stdout)


class TestStatusExecutorsSortedByFilename(unittest.TestCase):
    """Executor lines are sorted by filename."""

    @_skip_if_absent
    def test_executors_sorted_by_filename(self, mod):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            council = _make_dir(root, "council")
            _write(council / "state.md", _state_md())

            active = _make_dir(root, "executors", "active")
            # Write in reverse order to ensure sorting isn't filesystem-order dependent
            _write(active / "zzz-last.md", _executor_note(
                agent="zzz-last", status="active", current_task="task z"
            ))
            _write(active / "aaa-first.md", _executor_note(
                agent="aaa-first", status="active", current_task="task a"
            ))
            _write(active / "mmm-mid.md", _executor_note(
                agent="mmm-mid", status="active", current_task="task m"
            ))
            _make_dir(root, "ledger")

            stdout, _, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 0)
        executor_section_start = stdout.index("EXECUTORS")
        ledger_section_start = stdout.index("RECENT LEDGER")
        section = stdout[executor_section_start:ledger_section_start]

        pos_aaa = section.index("aaa-first")
        pos_mmm = section.index("mmm-mid")
        pos_zzz = section.index("zzz-last")
        self.assertLess(pos_aaa, pos_mmm)
        self.assertLess(pos_mmm, pos_zzz)


class TestStatusNoteWithoutFrontmatter(unittest.TestCase):
    """Executor note without frontmatter → agent = filename stem, status = `?`."""

    @_skip_if_absent
    def test_no_frontmatter_note(self, mod):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            council = _make_dir(root, "council")
            _write(council / "state.md", _state_md())

            active = _make_dir(root, "executors", "active")
            # No leading `---` at all
            _write(active / "bare-note.md", textwrap.dedent("""\
                # This note has no frontmatter

                ## Current task
                doing something important
            """))
            _make_dir(root, "ledger")

            stdout, _, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 0)
        self.assertIn("EXECUTORS (1 active)", stdout)
        self.assertIn("bare-note", stdout)
        # status should be `?`
        self.assertIn("· ?", stdout)


class TestStatusTruncation(unittest.TestCase):
    """Lines longer than 100 chars are truncated to 97 + `...`."""

    @_skip_if_absent
    def test_long_executor_task_truncated(self, mod):
        long_task = "x" * 120
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            council = _make_dir(root, "council")
            _write(council / "state.md", _state_md())

            active = _make_dir(root, "executors", "active")
            _write(active / "agent-long.md", _executor_note(
                agent="agent-long", status="active", current_task=long_task
            ))
            _make_dir(root, "ledger")

            stdout, _, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 0)
        expected_truncated = long_task[:97] + "..."
        self.assertIn(expected_truncated, stdout)
        self.assertNotIn(long_task, stdout, "Full 120-char string should not appear")

    @_skip_if_absent
    def test_long_ledger_body_truncated(self, mod):
        long_body = "y" * 105
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            council = _make_dir(root, "council")
            _write(council / "state.md", _state_md())
            _make_dir(root, "executors", "active")

            ledger = _make_dir(root, "ledger")
            _write(ledger / "0001-long.md", _ledger_entry(long_body))

            stdout, _, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 0)
        expected_truncated = long_body[:97] + "..."
        self.assertIn(expected_truncated, stdout)

    @_skip_if_absent
    def test_exactly_100_chars_not_truncated(self, mod):
        exact_100 = "z" * 100
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            council = _make_dir(root, "council")
            _write(council / "state.md", _state_md())
            _make_dir(root, "executors", "active")

            ledger = _make_dir(root, "ledger")
            _write(ledger / "0001-exact.md", _ledger_entry(exact_100))

            stdout, _, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 0)
        self.assertIn(exact_100, stdout, "Exactly 100 chars should not be truncated")

    @_skip_if_absent
    def test_101_chars_truncated(self, mod):
        over_101 = "w" * 101
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            council = _make_dir(root, "council")
            _write(council / "state.md", _state_md())
            _make_dir(root, "executors", "active")

            ledger = _make_dir(root, "ledger")
            _write(ledger / "0001-over.md", _ledger_entry(over_101))

            stdout, _, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 0)
        self.assertNotIn(over_101, stdout)
        self.assertIn(over_101[:97] + "...", stdout)


class TestStatusReturnCode(unittest.TestCase):
    """Return 0 on success."""

    @_skip_if_absent
    def test_return_0_on_success(self, mod):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            council = _make_dir(root, "council")
            _write(council / "state.md", _state_md())
            _make_dir(root, "executors", "active")
            _make_dir(root, "ledger")

            _, _, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 0)


class TestStatusExecutorCurrentTaskAbsent(unittest.TestCase):
    """Executor note with no ## Current task heading → current task = empty string."""

    @_skip_if_absent
    def test_no_current_task_heading(self, mod):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            council = _make_dir(root, "council")
            _write(council / "state.md", _state_md())

            active = _make_dir(root, "executors", "active")
            _write(active / "no-task.md", textwrap.dedent("""\
                ---
                agent: no-task
                status: idle
                ---
                # Working State
                ## Some other heading
                content here
            """))
            _make_dir(root, "ledger")

            stdout, _, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 0)
        # Should render with empty current task (no crash)
        self.assertIn("no-task", stdout)
        self.assertIn("idle", stdout)


class TestStatusExecutorFrontmatterA6(unittest.TestCase):
    """
    Amendment A6: frontmatter closes at the SECOND `---`, not any later one.
    Body of note (for ## Current task parsing) is everything after the second `---`.
    """

    @_skip_if_absent
    def test_dashes_in_body_do_not_close_frontmatter_early(self, mod):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            council = _make_dir(root, "council")
            _write(council / "state.md", _state_md())

            active = _make_dir(root, "executors", "active")
            # The body contains `---` lines — these are NOT frontmatter closers
            _write(active / "complex.md", textwrap.dedent("""\
                ---
                agent: complex-agent
                status: active
                ---
                # Working State
                ## Current task
                real task here
                ---
                separator in body
                ## Next step
                next
            """))
            _make_dir(root, "ledger")

            stdout, _, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 0)
        self.assertIn("complex-agent", stdout)
        self.assertIn("active", stdout)
        self.assertIn("real task here", stdout)


class TestStatusVaultPathInHeader(unittest.TestCase):
    """The header line shows the vault path exactly as given."""

    @_skip_if_absent
    def test_vault_path_in_header(self, mod):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            council = _make_dir(root, "council")
            _write(council / "state.md", _state_md())
            _make_dir(root, "executors", "active")
            _make_dir(root, "ledger")

            stdout, _, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 0)
        self.assertTrue(
            stdout.startswith(f"VAULT STATUS — {tmp}"),
            f"Header should start with 'VAULT STATUS — {tmp}', got: {stdout[:80]!r}"
        )


class TestStatusLedgerOnlyExactlyFourDigits(unittest.TestCase):
    """NNNN pattern requires EXACTLY 4 digits (not 3, not 5)."""

    @_skip_if_absent
    def test_four_digit_prefix_only(self, mod):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            council = _make_dir(root, "council")
            _write(council / "state.md", _state_md())
            _make_dir(root, "executors", "active")

            ledger = _make_dir(root, "ledger")
            _write(ledger / "0042-valid.md", _ledger_entry("Valid four-digit"))
            _write(ledger / "042-invalid.md", _ledger_entry("Three digits invalid"))
            _write(ledger / "00042-invalid.md", _ledger_entry("Five digits invalid"))

            stdout, _, rc = _run_main(mod, tmp)

        self.assertEqual(rc, 0)
        self.assertIn("0042-valid", stdout)
        self.assertNotIn("Three digits invalid", stdout)
        self.assertNotIn("Five digits invalid", stdout)


if __name__ == "__main__":
    unittest.main()
