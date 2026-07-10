"""
Gate fixtures for t3-index (cmd_index.py).

Covers every behavior promised in the interface spec and amendments A5, A6, A7.
Import is defensive so test collection does not crash when cmd_index is absent.
"""

import hashlib
import os
import sys
import tempfile
import textwrap
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Defensive import — collection must not crash when cmd_index is absent.
# ---------------------------------------------------------------------------
try:
    import cmd_index  # noqa: F401
    _CMD_INDEX_AVAILABLE = True
except ImportError:
    cmd_index = None  # type: ignore[assignment]
    _CMD_INDEX_AVAILABLE = False


def _skip_if_absent(test_func):
    """Decorator: skip the test when cmd_index is not importable yet."""
    return unittest.skipUnless(_CMD_INDEX_AVAILABLE, "cmd_index not yet implemented")(test_func)


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


class TestImportAndMainSignature(unittest.TestCase):
    """Verify the module exposes main(argv) -> int as specified."""

    def test_collection_does_not_crash_when_absent(self):
        # If we reach here collection succeeded regardless of import outcome.
        self.assertTrue(True)

    @_skip_if_absent
    def test_main_callable(self):
        self.assertTrue(callable(cmd_index.main))

    @_skip_if_absent
    def test_main_accepts_argv_list(self):
        # Just check it accepts a list argument without TypeError on invocation;
        # we test return value separately.
        with tempfile.TemporaryDirectory() as d:
            with patch("sys.stdout", new_callable=StringIO):
                result = cmd_index.main([d])
        self.assertIsInstance(result, int)


class TestMissingPositionalArg(unittest.TestCase):
    """Missing positional arg → SystemExit with code 2."""

    @_skip_if_absent
    def test_no_args_raises_systemexit_2(self):
        with self.assertRaises(SystemExit) as ctx:
            with patch("sys.stderr", new_callable=StringIO):
                cmd_index.main([])
        self.assertEqual(ctx.exception.code, 2)

    @_skip_if_absent
    def test_only_vault_flag_raises_systemexit_2(self):
        with tempfile.TemporaryDirectory() as vault:
            with self.assertRaises(SystemExit) as ctx:
                with patch("sys.stderr", new_callable=StringIO):
                    cmd_index.main(["--vault", vault])
            self.assertEqual(ctx.exception.code, 2)


class TestFolderResolution(unittest.TestCase):
    """Folder resolution: as-given first, then <vault>/<folder>, else stderr+1."""

    @_skip_if_absent
    def test_as_given_absolute_path(self):
        with tempfile.TemporaryDirectory() as d:
            with patch("sys.stdout", new_callable=StringIO):
                rc = cmd_index.main([d])
            self.assertEqual(rc, 0)

    @_skip_if_absent
    def test_vault_subfolder_resolution(self):
        """If as-given doesn't exist but <vault>/<folder> does, use that."""
        with tempfile.TemporaryDirectory() as vault:
            subfolder = os.path.join(vault, "notes")
            os.makedirs(subfolder)
            with patch("sys.stdout", new_callable=StringIO):
                rc = cmd_index.main(["notes", "--vault", vault])
            self.assertEqual(rc, 0)
            # _index.md written in the vault subfolder
            self.assertTrue(os.path.exists(os.path.join(subfolder, "_index.md")))

    @_skip_if_absent
    def test_as_given_preferred_over_vault_subfolder(self):
        """When as-given exists it is used; the vault subfolder is NOT used."""
        with tempfile.TemporaryDirectory() as vault:
            with tempfile.TemporaryDirectory() as direct:
                vault_subfolder = os.path.join(vault, os.path.basename(direct))
                os.makedirs(vault_subfolder)
                with patch("sys.stdout", new_callable=StringIO):
                    rc = cmd_index.main([direct, "--vault", vault])
                self.assertEqual(rc, 0)
                # _index.md must appear in 'direct', NOT vault_subfolder
                self.assertTrue(os.path.exists(os.path.join(direct, "_index.md")))
                self.assertFalse(os.path.exists(os.path.join(vault_subfolder, "_index.md")))

    @_skip_if_absent
    def test_nonexistent_folder_returns_1_and_writes_stderr(self):
        with tempfile.TemporaryDirectory() as vault:
            stderr_buf = StringIO()
            with patch("sys.stderr", stderr_buf):
                rc = cmd_index.main(["does_not_exist_xyz", "--vault", vault])
            self.assertEqual(rc, 1)
            self.assertTrue(stderr_buf.getvalue().strip() != "")


class TestZeroNotes(unittest.TestCase):
    """Empty folder → header line + blank line + trailing newline; 0 notes."""

    @_skip_if_absent
    def test_empty_folder_output(self):
        with tempfile.TemporaryDirectory() as d:
            stdout_buf = StringIO()
            with patch("sys.stdout", stdout_buf):
                rc = cmd_index.main([d])
            self.assertEqual(rc, 0)
            index_path = os.path.join(d, "_index.md")
            content = _read(index_path)
            basename = os.path.basename(d)
            expected = f"# Index: {basename}\n\n"
            self.assertEqual(content, expected)

    @_skip_if_absent
    def test_empty_folder_success_message(self):
        with tempfile.TemporaryDirectory() as d:
            stdout_buf = StringIO()
            with patch("sys.stdout", stdout_buf):
                rc = cmd_index.main([d])
            self.assertEqual(rc, 0)
            out = stdout_buf.getvalue()
            index_path = os.path.join(d, "_index.md")
            self.assertIn(index_path, out)
            self.assertIn("0 notes", out)


class TestIndexFormat(unittest.TestCase):
    """Exact _index.md format: header, blank line, one bullet per note."""

    def _make_note(self, folder: str, filename: str, content: str) -> None:
        _write(os.path.join(folder, filename), content)

    @_skip_if_absent
    def test_header_uses_folder_basename(self):
        with tempfile.TemporaryDirectory() as d:
            self._make_note(d, "a.md", "# Alpha\n")
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            content = _read(os.path.join(d, "_index.md"))
            self.assertTrue(content.startswith(f"# Index: {os.path.basename(d)}\n"))

    @_skip_if_absent
    def test_blank_line_after_header(self):
        with tempfile.TemporaryDirectory() as d:
            self._make_note(d, "a.md", "# Alpha\n")
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            lines = _read(os.path.join(d, "_index.md")).split("\n")
            # lines[0] = header, lines[1] = blank
            self.assertEqual(lines[1], "")

    @_skip_if_absent
    def test_trailing_newline(self):
        with tempfile.TemporaryDirectory() as d:
            self._make_note(d, "a.md", "# Alpha\n")
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            raw = _read(os.path.join(d, "_index.md"))
            self.assertTrue(raw.endswith("\n"))

    @_skip_if_absent
    def test_bullet_format(self):
        """- [title](file.md) — type: <t> · labels: <l>"""
        with tempfile.TemporaryDirectory() as d:
            self._make_note(d, "note.md", textwrap.dedent("""\
                ---
                type: knowledge
                labels: [foo, bar]
                ---
                # My Note
                body text
            """))
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            content = _read(os.path.join(d, "_index.md"))
            self.assertIn("- [My Note](note.md) — type: knowledge · labels: foo, bar", content)

    @_skip_if_absent
    def test_filename_sorted_order(self):
        with tempfile.TemporaryDirectory() as d:
            self._make_note(d, "z.md", "# Zed\n")
            self._make_note(d, "a.md", "# Alpha\n")
            self._make_note(d, "m.md", "# Middle\n")
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            content = _read(os.path.join(d, "_index.md"))
            lines = [l for l in content.split("\n") if l.startswith("- ")]
            self.assertEqual(len(lines), 3)
            self.assertIn("a.md", lines[0])
            self.assertIn("m.md", lines[1])
            self.assertIn("z.md", lines[2])

    @_skip_if_absent
    def test_codepoint_sort_order(self):
        """Codepoint order: uppercase letters sort before lowercase (ord('A')<ord('a'))."""
        with tempfile.TemporaryDirectory() as d:
            self._make_note(d, "b.md", "# Lower B\n")
            self._make_note(d, "A.md", "# Upper A\n")
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            content = _read(os.path.join(d, "_index.md"))
            lines = [l for l in content.split("\n") if l.startswith("- ")]
            # 'A.md' (ord 65) sorts before 'b.md' (ord 98)
            self.assertIn("A.md", lines[0])
            self.assertIn("b.md", lines[1])


class TestTitleExtraction(unittest.TestCase):
    """title = first # heading after frontmatter; else filename stem."""

    @_skip_if_absent
    def test_title_from_heading_after_frontmatter(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "doc.md"), textwrap.dedent("""\
                ---
                type: note
                ---
                # Real Title
                content
            """))
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            content = _read(os.path.join(d, "_index.md"))
            self.assertIn("[Real Title](doc.md)", content)

    @_skip_if_absent
    def test_title_from_heading_no_frontmatter(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "doc.md"), "# Heading Only\nbody\n")
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            content = _read(os.path.join(d, "_index.md"))
            self.assertIn("[Heading Only](doc.md)", content)

    @_skip_if_absent
    def test_title_fallback_to_stem_when_no_heading(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "my-note.md"), textwrap.dedent("""\
                ---
                type: note
                ---
                just body text, no heading
            """))
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            content = _read(os.path.join(d, "_index.md"))
            self.assertIn("[my-note](my-note.md)", content)

    @_skip_if_absent
    def test_title_fallback_stem_no_frontmatter_no_heading(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "bare.md"), "just text\n")
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            content = _read(os.path.join(d, "_index.md"))
            self.assertIn("[bare](bare.md)", content)

    @_skip_if_absent
    def test_heading_in_frontmatter_not_used_as_title(self):
        """A '# line' inside frontmatter must NOT be treated as the title."""
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "tricky.md"), textwrap.dedent("""\
                ---
                title: # not a heading
                type: note
                ---
                # Actual Heading
            """))
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            content = _read(os.path.join(d, "_index.md"))
            self.assertIn("[Actual Heading](tricky.md)", content)


class TestTypeField(unittest.TestCase):
    """type from frontmatter; absent → '?'."""

    @_skip_if_absent
    def test_type_present(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "n.md"), "---\ntype: contract\n---\n# T\n")
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            content = _read(os.path.join(d, "_index.md"))
            self.assertIn("type: contract", content)

    @_skip_if_absent
    def test_type_absent(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "n.md"), "---\nlabels: [x]\n---\n# T\n")
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            content = _read(os.path.join(d, "_index.md"))
            self.assertIn("type: ?", content)

    @_skip_if_absent
    def test_type_absent_no_frontmatter(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "n.md"), "# Just a heading\n")
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            content = _read(os.path.join(d, "_index.md"))
            self.assertIn("type: ?", content)


class TestLabelsField(unittest.TestCase):
    """
    labels: [a, b] → 'a, b'
    absent / [] / non-bracket value → '-'   (amendment A5)
    """

    @_skip_if_absent
    def test_labels_list_formatted(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "n.md"), "---\ntype: x\nlabels: [alpha, beta, gamma]\n---\n# T\n")
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            content = _read(os.path.join(d, "_index.md"))
            self.assertIn("labels: alpha, beta, gamma", content)

    @_skip_if_absent
    def test_labels_single_item(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "n.md"), "---\ntype: x\nlabels: [only]\n---\n# T\n")
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            content = _read(os.path.join(d, "_index.md"))
            self.assertIn("labels: only", content)

    @_skip_if_absent
    def test_labels_absent(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "n.md"), "---\ntype: x\n---\n# T\n")
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            content = _read(os.path.join(d, "_index.md"))
            self.assertIn("labels: -", content)

    @_skip_if_absent
    def test_labels_empty_brackets(self):
        """labels: [] → '-'"""
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "n.md"), "---\ntype: x\nlabels: []\n---\n# T\n")
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            content = _read(os.path.join(d, "_index.md"))
            self.assertIn("labels: -", content)

    @_skip_if_absent
    def test_labels_bare_word_not_bracket(self):
        """labels: someword (not [...]form) → '-'  (amendment A5)"""
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "n.md"), "---\ntype: x\nlabels: someword\n---\n# T\n")
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            content = _read(os.path.join(d, "_index.md"))
            self.assertIn("labels: -", content)

    @_skip_if_absent
    def test_labels_no_frontmatter(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "n.md"), "# Just heading\n")
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            content = _read(os.path.join(d, "_index.md"))
            self.assertIn("labels: -", content)


class TestFrontmatterParsing(unittest.TestCase):
    """Frontmatter closes at the SECOND exact '---'; later '---' are body. (A6)"""

    @_skip_if_absent
    def test_frontmatter_closes_at_second_dashes(self):
        """A '---' in the body must not be treated as frontmatter boundary."""
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "n.md"), textwrap.dedent("""\
                ---
                type: mytype
                labels: [x]
                ---
                # My Title
                body paragraph
                ---
                more body after second dashes
            """))
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            content = _read(os.path.join(d, "_index.md"))
            self.assertIn("type: mytype", content)
            self.assertIn("labels: x", content)
            self.assertIn("[My Title](n.md)", content)

    @_skip_if_absent
    def test_no_frontmatter_when_first_line_not_dashes(self):
        """File not starting with '---' → no frontmatter."""
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "n.md"), textwrap.dedent("""\
                # Title Without FM
                ---
                not frontmatter
                ---
                body
            """))
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            content = _read(os.path.join(d, "_index.md"))
            self.assertIn("type: ?", content)
            self.assertIn("labels: -", content)
            self.assertIn("[Title Without FM](n.md)", content)

    @_skip_if_absent
    def test_frontmatter_keys_after_second_dashes_not_parsed(self):
        """Keys appearing after the closing '---' are body, not frontmatter."""
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "n.md"), textwrap.dedent("""\
                ---
                type: real
                ---
                # Title
                ---
                type: fake
            """))
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            content = _read(os.path.join(d, "_index.md"))
            self.assertIn("type: real", content)


class TestIndexMdExcluded(unittest.TestCase):
    """_index.md itself must not appear in the output."""

    @_skip_if_absent
    def test_index_md_not_listed(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "a.md"), "# Alpha\n")
            # Pre-create _index.md to confirm it won't be scanned
            _write(os.path.join(d, "_index.md"), "# Index: old\n\n")
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            content = _read(os.path.join(d, "_index.md"))
            # Should list a.md but never _index.md as a bullet entry
            bullets = [l for l in content.split("\n") if l.startswith("- ")]
            for bullet in bullets:
                self.assertNotIn("_index.md", bullet)
            # a.md should be present
            self.assertTrue(any("a.md" in b for b in bullets))

    @_skip_if_absent
    def test_only_index_md_present_gives_zero_notes(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "_index.md"), "# Index: old\n\n")
            with patch("sys.stdout", new_callable=StringIO):
                rc = cmd_index.main([d])
            self.assertEqual(rc, 0)
            content = _read(os.path.join(d, "_index.md"))
            bullets = [l for l in content.split("\n") if l.startswith("- ")]
            self.assertEqual(len(bullets), 0)


class TestNonRecursive(unittest.TestCase):
    """Scan is non-recursive — subdirectory .md files are not included."""

    @_skip_if_absent
    def test_subdir_notes_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "top.md"), "# Top Level\n")
            subdir = os.path.join(d, "sub")
            os.makedirs(subdir)
            _write(os.path.join(subdir, "deep.md"), "# Deep\n")
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            content = _read(os.path.join(d, "_index.md"))
            bullets = [l for l in content.split("\n") if l.startswith("- ")]
            self.assertEqual(len(bullets), 1)
            self.assertIn("top.md", bullets[0])


class TestSuccessMessage(unittest.TestCase):
    """On success: print 'wrote <path> (<n> notes)' to stdout; return 0."""

    @_skip_if_absent
    def test_success_message_format_and_return_code(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "a.md"), "# A\n")
            _write(os.path.join(d, "b.md"), "# B\n")
            stdout_buf = StringIO()
            with patch("sys.stdout", stdout_buf):
                rc = cmd_index.main([d])
            self.assertEqual(rc, 0)
            out = stdout_buf.getvalue()
            expected_path = os.path.join(d, "_index.md")
            self.assertIn(expected_path, out)
            self.assertIn("2 notes", out)

    @_skip_if_absent
    def test_success_message_starts_with_wrote(self):
        with tempfile.TemporaryDirectory() as d:
            stdout_buf = StringIO()
            with patch("sys.stdout", stdout_buf):
                cmd_index.main([d])
            out = stdout_buf.getvalue().strip()
            self.assertTrue(out.startswith("wrote "), f"Expected 'wrote ...', got: {out!r}")

    @_skip_if_absent
    def test_success_one_note(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "x.md"), "# X\n")
            stdout_buf = StringIO()
            with patch("sys.stdout", stdout_buf):
                rc = cmd_index.main([d])
            self.assertEqual(rc, 0)
            out = stdout_buf.getvalue()
            self.assertIn("1 notes", out)  # spec says "<n> notes" — no special-case for 1


class TestWriteGuardLedger(unittest.TestCase):
    """
    Amendment A7 — hard requirement.

    Build a synthetic ledger tree with NNNN-*.md entries.
    Run the index command against it.
    Assert:
      - Every NNNN-*.md file is byte-identical (hash before == hash after).
      - Only _index.md may differ/appear.
      - No file other than _index.md was created, deleted, or renamed.
    """

    def _build_ledger(self, base: str, n: int = 5) -> dict:
        """Create n synthetic NNNN-*.md files; return {filename: sha256}."""
        hashes = {}
        for i in range(n):
            fname = f"{i:04d}-entry-{chr(ord('a') + i)}.md"
            content = textwrap.dedent(f"""\
                ---
                type: ledger
                labels: [run, r{i:03d}]
                ---
                # Ledger Entry {i}

                Some body text for entry {i}.
                Nothing special here.
            """)
            path = os.path.join(base, fname)
            _write(path, content)
            hashes[fname] = _sha256(path)
        return hashes

    @_skip_if_absent
    def test_ledger_files_byte_identical_after_index(self):
        with tempfile.TemporaryDirectory() as d:
            before = self._build_ledger(d, n=8)
            # Snapshot all files before
            before_all = {f: _sha256(os.path.join(d, f)) for f in os.listdir(d)}

            with patch("sys.stdout", new_callable=StringIO):
                rc = cmd_index.main([d])
            self.assertEqual(rc, 0)

            # Every NNNN-*.md must be byte-identical
            for fname, sha_before in before.items():
                sha_after = _sha256(os.path.join(d, fname))
                self.assertEqual(
                    sha_before, sha_after,
                    f"{fname} was modified by cmd_index (byte mismatch)"
                )

    @_skip_if_absent
    def test_only_index_md_is_new_or_changed(self):
        """No file other than _index.md may be created, deleted, or renamed."""
        with tempfile.TemporaryDirectory() as d:
            self._build_ledger(d, n=6)
            files_before = set(os.listdir(d))

            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])

            files_after = set(os.listdir(d))

            # New files: only _index.md is allowed to be added
            new_files = files_after - files_before
            self.assertTrue(
                new_files <= {"_index.md"},
                f"Unexpected new files created: {new_files - {'_index.md'}}"
            )

            # Deleted files: none allowed
            deleted = files_before - files_after
            self.assertEqual(deleted, set(), f"Files were deleted: {deleted}")

    @_skip_if_absent
    def test_existing_index_md_replaced_not_others(self):
        """When _index.md already exists, it may be overwritten; no other changes."""
        with tempfile.TemporaryDirectory() as d:
            self._build_ledger(d, n=4)
            # Pre-create an old _index.md
            old_index = os.path.join(d, "_index.md")
            _write(old_index, "# Index: old\n\nold content\n")

            before_hashes = {
                f: _sha256(os.path.join(d, f))
                for f in os.listdir(d)
                if f != "_index.md"
            }

            with patch("sys.stdout", new_callable=StringIO):
                rc = cmd_index.main([d])
            self.assertEqual(rc, 0)

            # All non-index files unchanged
            for fname, sha_before in before_hashes.items():
                sha_after = _sha256(os.path.join(d, fname))
                self.assertEqual(
                    sha_before, sha_after,
                    f"{fname} was unexpectedly modified"
                )

            # _index.md should exist and contain the right header
            new_content = _read(old_index)
            self.assertTrue(new_content.startswith(f"# Index: {os.path.basename(d)}\n"))

    @_skip_if_absent
    def test_ledger_index_content_correct(self):
        """Verify _index.md content is correct for the synthetic ledger."""
        with tempfile.TemporaryDirectory() as d:
            self._build_ledger(d, n=3)
            with patch("sys.stdout", new_callable=StringIO):
                rc = cmd_index.main([d])
            self.assertEqual(rc, 0)
            content = _read(os.path.join(d, "_index.md"))
            basename = os.path.basename(d)
            self.assertTrue(content.startswith(f"# Index: {basename}\n\n"))
            bullets = [l for l in content.split("\n") if l.startswith("- ")]
            self.assertEqual(len(bullets), 3)
            # Entries should be sorted: 0000 < 0001 < 0002
            self.assertIn("0000-entry-a.md", bullets[0])
            self.assertIn("0001-entry-b.md", bullets[1])
            self.assertIn("0002-entry-c.md", bullets[2])
            # Type and labels correctly extracted
            for bullet in bullets:
                self.assertIn("type: ledger", bullet)
                # labels: [run, rNNN] → "run, rNNN"
                self.assertIn("labels: run,", bullet)

    @_skip_if_absent
    def test_no_temp_files_created(self):
        """Confirm cmd_index creates no intermediate/temp files in the folder."""
        with tempfile.TemporaryDirectory() as d:
            self._build_ledger(d, n=3)
            with patch("sys.stdout", new_callable=StringIO):
                cmd_index.main([d])
            allowed = {f"{i:04d}-entry-{chr(ord('a') + i)}.md" for i in range(3)} | {"_index.md"}
            actual = set(os.listdir(d))
            unexpected = actual - allowed
            self.assertEqual(unexpected, set(), f"Unexpected files in folder: {unexpected}")


class TestMultipleNotesCombined(unittest.TestCase):
    """Integration: mixed notes produce correct full output."""

    @_skip_if_absent
    def test_full_output_structure(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "alpha.md"), textwrap.dedent("""\
                ---
                type: note
                labels: [a, b]
                ---
                # Alpha Note
            """))
            _write(os.path.join(d, "beta.md"), textwrap.dedent("""\
                ---
                type: contract
                labels: []
                ---
                # Beta Contract
            """))
            _write(os.path.join(d, "gamma.md"), "just text no heading\n")

            with patch("sys.stdout", new_callable=StringIO):
                rc = cmd_index.main([d])
            self.assertEqual(rc, 0)

            content = _read(os.path.join(d, "_index.md"))
            lines = content.split("\n")
            basename = os.path.basename(d)

            # Header
            self.assertEqual(lines[0], f"# Index: {basename}")
            # Blank line
            self.assertEqual(lines[1], "")
            # Bullets in filename order
            bullets = [l for l in lines if l.startswith("- ")]
            self.assertEqual(len(bullets), 3)
            self.assertIn("[Alpha Note](alpha.md)", bullets[0])
            self.assertIn("type: note", bullets[0])
            self.assertIn("labels: a, b", bullets[0])

            self.assertIn("[Beta Contract](beta.md)", bullets[1])
            self.assertIn("type: contract", bullets[1])
            self.assertIn("labels: -", bullets[1])

            self.assertIn("[gamma](gamma.md)", bullets[2])
            self.assertIn("type: ?", bullets[2])
            self.assertIn("labels: -", bullets[2])

            # Trailing newline
            self.assertTrue(content.endswith("\n"))


class TestSymlinkEscapeWriteGuard(unittest.TestCase):
    """
    GATE GAP — write-guard clause: "no path by which this module modifies
    any other file." If <folder>/_index.md is a symlink pointing OUTSIDE the
    folder, a naive open(_index.md, 'w') follows the link and clobbers the
    external target. Chair arbitration: the external target must remain
    byte-identical; _index.md must become a REGULAR file (not a symlink)
    holding the correct index; return 0.
    """

    @_skip_if_absent
    def test_symlink_index_does_not_clobber_external_target(self):
        with tempfile.TemporaryDirectory() as folder, \
                tempfile.TemporaryDirectory() as external:
            # External file the symlink will point at.
            target = os.path.join(external, "precious.md")
            target_content = "# Precious External File\n\nDO NOT TOUCH ME.\n"
            _write(target, target_content)
            target_sha_before = _sha256(target)

            # A real note in the folder so the index is non-empty.
            _write(os.path.join(folder, "a.md"), "# Alpha\n")

            # _index.md is a symlink to the external file.
            index_path = os.path.join(folder, "_index.md")
            os.symlink(target, index_path)
            self.assertTrue(os.path.islink(index_path))

            with patch("sys.stdout", new_callable=StringIO):
                rc = cmd_index.main([folder])

            # (c) return 0
            self.assertEqual(rc, 0)

            # (a) external target byte-identical
            self.assertEqual(
                target_sha_before, _sha256(target),
                "external symlink target was modified — write-guard violated"
            )
            # external target content unchanged verbatim
            self.assertEqual(_read(target), target_content)

    @_skip_if_absent
    def test_symlink_index_replaced_by_regular_file(self):
        with tempfile.TemporaryDirectory() as folder, \
                tempfile.TemporaryDirectory() as external:
            target = os.path.join(external, "precious.md")
            _write(target, "# Precious External File\n\nDO NOT TOUCH ME.\n")

            _write(os.path.join(folder, "a.md"), "# Alpha\n")

            index_path = os.path.join(folder, "_index.md")
            os.symlink(target, index_path)

            with patch("sys.stdout", new_callable=StringIO):
                rc = cmd_index.main([folder])
            self.assertEqual(rc, 0)

            # (b) _index.md is now a REGULAR file, not a symlink
            self.assertFalse(
                os.path.islink(index_path),
                "_index.md is still a symlink — should be a regular file"
            )
            self.assertTrue(os.path.isfile(index_path))

            # (b) with correct index content
            content = _read(index_path)
            basename = os.path.basename(folder)
            self.assertTrue(content.startswith(f"# Index: {basename}\n\n"))
            bullets = [l for l in content.split("\n") if l.startswith("- ")]
            self.assertEqual(len(bullets), 1)
            self.assertIn("[Alpha](a.md)", bullets[0])
            self.assertTrue(content.endswith("\n"))

    @_skip_if_absent
    def test_symlink_index_external_target_not_listed(self):
        """The symlinked _index.md must still be excluded from the scan."""
        with tempfile.TemporaryDirectory() as folder, \
                tempfile.TemporaryDirectory() as external:
            target = os.path.join(external, "precious.md")
            _write(target, "# Precious\n")
            _write(os.path.join(folder, "a.md"), "# Alpha\n")
            index_path = os.path.join(folder, "_index.md")
            os.symlink(target, index_path)

            stdout_buf = StringIO()
            with patch("sys.stdout", stdout_buf):
                rc = cmd_index.main([folder])
            self.assertEqual(rc, 0)

            content = _read(index_path)
            bullets = [l for l in content.split("\n") if l.startswith("- ")]
            # Only a.md — _index.md (even as symlink) is never an entry.
            self.assertEqual(len(bullets), 1)
            for bullet in bullets:
                self.assertNotIn("_index.md", bullet)
            self.assertIn("1 notes", stdout_buf.getvalue())


class TestNonFileMdEntries(unittest.TestCase):
    """
    GATE GAP — non-file '.md' entries. A DIRECTORY named 'sub.md' inside the
    folder must be skipped: no crash, return 0, not counted in <n> notes,
    not listed in the index.
    """

    @_skip_if_absent
    def test_directory_named_md_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "real.md"), "# Real Note\n")
            # A directory whose name ends in .md
            os.makedirs(os.path.join(d, "sub.md"))

            stdout_buf = StringIO()
            with patch("sys.stdout", stdout_buf):
                rc = cmd_index.main([d])

            # No crash, return 0
            self.assertEqual(rc, 0)

            content = _read(os.path.join(d, "_index.md"))
            bullets = [l for l in content.split("\n") if l.startswith("- ")]
            # Only the real file counted
            self.assertEqual(len(bullets), 1)
            self.assertIn("real.md", bullets[0])
            # sub.md directory not listed
            for bullet in bullets:
                self.assertNotIn("sub.md", bullet)
            # Count reflects 1 note only
            self.assertIn("1 notes", stdout_buf.getvalue())

    @_skip_if_absent
    def test_only_directory_md_gives_zero_notes(self):
        """A folder containing only a 'foo.md' DIRECTORY yields zero notes."""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "foo.md"))

            stdout_buf = StringIO()
            with patch("sys.stdout", stdout_buf):
                rc = cmd_index.main([d])
            self.assertEqual(rc, 0)

            content = _read(os.path.join(d, "_index.md"))
            basename = os.path.basename(d)
            self.assertEqual(content, f"# Index: {basename}\n\n")
            self.assertIn("0 notes", stdout_buf.getvalue())

    @_skip_if_absent
    def test_directory_md_not_opened_or_modified(self):
        """The 'sub.md' directory and its contents are untouched."""
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "real.md"), "# Real\n")
            subdir = os.path.join(d, "sub.md")
            os.makedirs(subdir)
            inner = os.path.join(subdir, "inner.md")
            _write(inner, "# Inner Untouched\n")
            inner_sha = _sha256(inner)

            with patch("sys.stdout", new_callable=StringIO):
                rc = cmd_index.main([d])
            self.assertEqual(rc, 0)

            # Inner file untouched, directory still a directory
            self.assertTrue(os.path.isdir(subdir))
            self.assertEqual(inner_sha, _sha256(inner))


if __name__ == "__main__":
    unittest.main()
