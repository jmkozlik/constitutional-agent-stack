"""
Gate fixtures for t1-cli (run r002-vaultctl).
Tests vaultctl.main() against the interface spec exclusively.
Fake cmd_* modules are injected into sys.modules; no implementation files
in this worktree need to exist.
"""

import io
import sys
import types
import unittest
import importlib
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_cmd(name, return_value=0):
    """Return a fresh fake cmd_<name> module whose main() returns return_value."""
    mod = types.ModuleType(f"cmd_{name}")
    mod.main = lambda rest: return_value
    return mod


def _inject_fakes(*names, return_value=0):
    """Inject fake cmd_<name> modules for each name; return a cleanup callable."""
    injected = {}
    for name in names:
        key = f"cmd_{name}"
        injected[key] = _make_fake_cmd(name, return_value=return_value)
        sys.modules[key] = injected[key]

    def cleanup():
        for key in injected:
            sys.modules.pop(key, None)

    return injected, cleanup


def _load_vaultctl():
    """
    Import (or reload) the vaultctl module so tests always get a fresh copy.
    If it was previously cached, reload it so top-level import checks work.
    """
    if "vaultctl" in sys.modules:
        return importlib.reload(sys.modules["vaultctl"])
    return importlib.import_module("vaultctl")


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestDispatchTable(unittest.TestCase):
    """Dispatch: known subcommands → correct cmd_* module, correct rest-argv."""

    def setUp(self):
        # Remove cmd_* and vaultctl from sys.modules so each test is isolated.
        for k in list(sys.modules):
            if k in ("cmd_status", "cmd_index", "cmd_runs", "vaultctl"):
                del sys.modules[k]

    def _run_subcommand(self, subcommand, extra_args, expected_rest):
        fakes, cleanup = _inject_fakes(subcommand)
        received = []

        def capturing_main(rest):
            received.append(rest)
            return 0

        fakes[f"cmd_{subcommand}"].main = capturing_main
        try:
            vaultctl = _load_vaultctl()
            rc = vaultctl.main([subcommand] + extra_args)
        finally:
            cleanup()
            sys.modules.pop("vaultctl", None)

        self.assertEqual(rc, 0)
        self.assertEqual(len(received), 1, "cmd module main() called exactly once")
        self.assertEqual(received[0], expected_rest)

    def test_status_dispatches_to_cmd_status(self):
        self._run_subcommand("status", [], [])

    def test_index_dispatches_to_cmd_index(self):
        self._run_subcommand("index", ["somefolder"], ["somefolder"])

    def test_runs_dispatches_to_cmd_runs(self):
        self._run_subcommand("runs", [], [])

    def test_rest_argv_passed_correctly(self):
        """Extra arguments after subcommand are forwarded verbatim."""
        self._run_subcommand("status", ["--vault", "/tmp/v", "--json"], ["--vault", "/tmp/v", "--json"])

    def test_dispatch_return_value_propagated(self):
        """Return value from cmd module's main() is returned by vaultctl.main()."""
        fakes, cleanup = _inject_fakes("status", return_value=42)
        try:
            vaultctl = _load_vaultctl()
            rc = vaultctl.main(["status"])
        finally:
            cleanup()
            sys.modules.pop("vaultctl", None)
        self.assertEqual(rc, 42)


class TestLazyImport(unittest.TestCase):
    """Only the requested cmd_* module is imported, and only at dispatch time."""

    def setUp(self):
        for k in list(sys.modules):
            if k in ("cmd_status", "cmd_index", "cmd_runs", "vaultctl"):
                del sys.modules[k]

    def test_unrelated_cmd_modules_not_imported_on_status(self):
        """Dispatching 'status' must not import cmd_index or cmd_runs."""
        fakes, cleanup = _inject_fakes("status", "index", "runs")
        # Track which fake modules' main() gets called
        calls = []
        for name in ("status", "index", "runs"):
            orig = fakes[f"cmd_{name}"].main
            def make_tracker(n, orig_fn=orig):
                def tracker(rest):
                    calls.append(n)
                    return 0
                return tracker
            fakes[f"cmd_{name}"].main = make_tracker(name)

        # Remove index and runs so if vaultctl tries to import them it will fail
        # (they shouldn't be needed for 'status')
        del sys.modules["cmd_index"]
        del sys.modules["cmd_runs"]
        try:
            vaultctl = _load_vaultctl()
            vaultctl.main(["status"])
        finally:
            cleanup()
            sys.modules.pop("vaultctl", None)

        self.assertEqual(calls, ["status"], "only cmd_status.main() was invoked")
        self.assertNotIn("cmd_index", sys.modules)
        self.assertNotIn("cmd_runs", sys.modules)

    def test_help_does_not_import_any_cmd_module(self):
        """main(['-h']) must work even if no cmd_* modules exist at all."""
        for k in ("cmd_status", "cmd_index", "cmd_runs"):
            sys.modules.pop(k, None)
        try:
            vaultctl = _load_vaultctl()
            with patch("sys.stdout", new_callable=io.StringIO):
                rc = vaultctl.main(["-h"])
        finally:
            sys.modules.pop("vaultctl", None)
        self.assertEqual(rc, 0)
        self.assertNotIn("cmd_status", sys.modules)
        self.assertNotIn("cmd_index", sys.modules)
        self.assertNotIn("cmd_runs", sys.modules)

    def test_no_top_level_import_of_cmd_modules(self):
        """
        Importing vaultctl itself must not cause cmd_status/index/runs to be
        imported (tests the 'lazy' part of the contract).
        """
        for k in ("cmd_status", "cmd_index", "cmd_runs"):
            sys.modules.pop(k, None)
        try:
            _load_vaultctl()
        finally:
            sys.modules.pop("vaultctl", None)
        self.assertNotIn("cmd_status", sys.modules)
        self.assertNotIn("cmd_index", sys.modules)
        self.assertNotIn("cmd_runs", sys.modules)


class TestSystemExitMapping(unittest.TestCase):
    """Amendment A2: SystemExit from cmd module is caught and mapped to int."""

    def setUp(self):
        for k in list(sys.modules):
            if k in ("cmd_status", "cmd_index", "cmd_runs", "vaultctl"):
                del sys.modules[k]

    def _run_with_exit(self, exit_arg):
        fakes, cleanup = _inject_fakes("status")

        def raising_main(rest):
            raise SystemExit(exit_arg)

        fakes["cmd_status"].main = raising_main
        try:
            vaultctl = _load_vaultctl()
            rc = vaultctl.main(["status"])
        finally:
            cleanup()
            sys.modules.pop("vaultctl", None)
        return rc

    def test_systemexit_int_code_returned_unchanged(self):
        self.assertEqual(self._run_with_exit(0), 0)

    def test_systemexit_nonzero_int_returned_unchanged(self):
        self.assertEqual(self._run_with_exit(1), 1)

    def test_systemexit_int_3_returned_as_3(self):
        self.assertEqual(self._run_with_exit(3), 3)

    def test_systemexit_none_returns_0(self):
        self.assertEqual(self._run_with_exit(None), 0)

    def test_systemexit_string_returns_2(self):
        self.assertEqual(self._run_with_exit("error"), 2)

    def test_systemexit_list_returns_2(self):
        self.assertEqual(self._run_with_exit(["bad"]), 2)

    def test_normal_return_not_wrapped(self):
        """Non-SystemExit return value is returned unchanged."""
        fakes, cleanup = _inject_fakes("status", return_value=7)
        try:
            vaultctl = _load_vaultctl()
            rc = vaultctl.main(["status"])
        finally:
            cleanup()
            sys.modules.pop("vaultctl", None)
        self.assertEqual(rc, 7)


class TestEmptyArgv(unittest.TestCase):
    """main([]) → print usage to STDERR, return 2."""

    def setUp(self):
        for k in list(sys.modules):
            if k in ("cmd_status", "cmd_index", "cmd_runs", "vaultctl"):
                del sys.modules[k]

    def test_empty_argv_returns_2(self):
        try:
            vaultctl = _load_vaultctl()
            with patch("sys.stderr", new_callable=io.StringIO) as mock_err:
                rc = vaultctl.main([])
        finally:
            sys.modules.pop("vaultctl", None)
        self.assertEqual(rc, 2)

    def test_empty_argv_writes_to_stderr(self):
        try:
            vaultctl = _load_vaultctl()
            with patch("sys.stderr", new_callable=io.StringIO) as mock_err:
                vaultctl.main([])
                output = mock_err.getvalue()
        finally:
            sys.modules.pop("vaultctl", None)
        self.assertTrue(len(output) > 0, "Usage text must be written to stderr")

    def test_empty_argv_usage_contains_subcommand_names(self):
        try:
            vaultctl = _load_vaultctl()
            with patch("sys.stderr", new_callable=io.StringIO) as mock_err:
                vaultctl.main([])
                output = mock_err.getvalue()
        finally:
            sys.modules.pop("vaultctl", None)
        for name in ("status", "index", "runs"):
            self.assertIn(name, output, f"Usage must mention '{name}'")

    def test_empty_argv_nothing_on_stdout(self):
        try:
            vaultctl = _load_vaultctl()
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out, \
                 patch("sys.stderr", new_callable=io.StringIO):
                vaultctl.main([])
                stdout = mock_out.getvalue()
        finally:
            sys.modules.pop("vaultctl", None)
        self.assertEqual(stdout, "", "Nothing should be written to stdout on empty argv")


class TestUnknownSubcommand(unittest.TestCase):
    """Amendment A3: any first arg not in table and not -h/--help → 2 + stderr."""

    def setUp(self):
        for k in list(sys.modules):
            if k in ("cmd_status", "cmd_index", "cmd_runs", "vaultctl"):
                del sys.modules[k]

    def _run_unknown(self, arg):
        try:
            vaultctl = _load_vaultctl()
            with patch("sys.stderr", new_callable=io.StringIO) as mock_err, \
                 patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                rc = vaultctl.main([arg])
                stderr = mock_err.getvalue()
                stdout = mock_out.getvalue()
        finally:
            sys.modules.pop("vaultctl", None)
        return rc, stderr, stdout

    def test_unknown_word_returns_2(self):
        rc, _, _ = self._run_unknown("bogus")
        self.assertEqual(rc, 2)

    def test_unknown_word_writes_to_stderr(self):
        _, stderr, _ = self._run_unknown("bogus")
        self.assertTrue(len(stderr) > 0, "Error/usage must be written to stderr")

    def test_unknown_word_stderr_names_the_unknown_subcommand(self):
        _, stderr, _ = self._run_unknown("bogus")
        self.assertIn("bogus", stderr, "Error message must name the unknown subcommand")

    def test_unknown_word_nothing_on_stdout(self):
        _, _, stdout = self._run_unknown("bogus")
        self.assertEqual(stdout, "", "Unknown subcommand must not write to stdout")

    def test_flag_like_arg_vault_returns_2(self):
        """--vault is a flag-like first arg that is not a valid subcommand."""
        rc, _, _ = self._run_unknown("--vault")
        self.assertEqual(rc, 2)

    def test_flag_like_arg_vault_stderr_names_it(self):
        _, stderr, _ = self._run_unknown("--vault")
        self.assertIn("--vault", stderr, "--vault must be named in the error")

    def test_flag_like_arg_foo_returns_2(self):
        rc, _, _ = self._run_unknown("--foo")
        self.assertEqual(rc, 2)

    def test_unknown_with_usage_text_in_stderr(self):
        """Stderr on unknown subcommand must also contain usage (all three names)."""
        _, stderr, _ = self._run_unknown("bogus")
        for name in ("status", "index", "runs"):
            self.assertIn(name, stderr, f"Usage in stderr must mention '{name}'")


class TestHelpFlag(unittest.TestCase):
    """-h/--help → usage to STDOUT, return 0."""

    def setUp(self):
        for k in list(sys.modules):
            if k in ("cmd_status", "cmd_index", "cmd_runs", "vaultctl"):
                del sys.modules[k]

    def _run_help(self, flag):
        try:
            vaultctl = _load_vaultctl()
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out, \
                 patch("sys.stderr", new_callable=io.StringIO) as mock_err:
                rc = vaultctl.main([flag])
                stdout = mock_out.getvalue()
                stderr = mock_err.getvalue()
        finally:
            sys.modules.pop("vaultctl", None)
        return rc, stdout, stderr

    def test_dash_h_returns_0(self):
        rc, _, _ = self._run_help("-h")
        self.assertEqual(rc, 0)

    def test_dash_dash_help_returns_0(self):
        rc, _, _ = self._run_help("--help")
        self.assertEqual(rc, 0)

    def test_dash_h_writes_to_stdout(self):
        _, stdout, _ = self._run_help("-h")
        self.assertTrue(len(stdout) > 0, "Usage must be written to stdout")

    def test_dash_dash_help_writes_to_stdout(self):
        _, stdout, _ = self._run_help("--help")
        self.assertTrue(len(stdout) > 0, "Usage must be written to stdout")

    def test_dash_h_usage_contains_status(self):
        _, stdout, _ = self._run_help("-h")
        self.assertIn("status", stdout)

    def test_dash_h_usage_contains_index(self):
        _, stdout, _ = self._run_help("-h")
        self.assertIn("index", stdout)

    def test_dash_h_usage_contains_runs(self):
        _, stdout, _ = self._run_help("-h")
        self.assertIn("runs", stdout)

    def test_dash_dash_help_usage_contains_all_three(self):
        _, stdout, _ = self._run_help("--help")
        for name in ("status", "index", "runs"):
            self.assertIn(name, stdout, f"--help stdout must mention '{name}'")

    def test_dash_h_nothing_on_stderr(self):
        _, _, stderr = self._run_help("-h")
        self.assertEqual(stderr, "", "-h must not write to stderr")

    def test_dash_dash_help_nothing_on_stderr(self):
        _, _, stderr = self._run_help("--help")
        self.assertEqual(stderr, "", "--help must not write to stderr")


class TestImportModuleUsed(unittest.TestCase):
    """
    Dispatch uses importlib.import_module — we verify that a module freshly
    added to sys.modules (simulating a real lazy import) is actually called.
    This is a proxy test: if vaultctl used a bare 'import' at top level, the
    module pre-injected into sys.modules before the vaultctl import would never
    be re-imported, but the main() on the live object would still be called.
    The real guard is TestLazyImport.test_no_top_level_import_of_cmd_modules.
    Here we confirm the dispatch path actually invokes our injected module's main.
    """

    def setUp(self):
        for k in list(sys.modules):
            if k in ("cmd_status", "cmd_index", "cmd_runs", "vaultctl"):
                del sys.modules[k]

    def test_injected_module_main_is_called(self):
        called = []
        mod = types.ModuleType("cmd_runs")
        mod.main = lambda rest: called.append(rest) or 0
        sys.modules["cmd_runs"] = mod
        try:
            vaultctl = _load_vaultctl()
            vaultctl.main(["runs", "extra"])
        finally:
            sys.modules.pop("cmd_runs", None)
            sys.modules.pop("vaultctl", None)
        self.assertEqual(called, [["extra"]])


if __name__ == "__main__":
    unittest.main()
