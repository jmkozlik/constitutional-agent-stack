"""vaultctl — vault control CLI dispatcher.

Lazily imports cmd_<name> subcommand modules and delegates to them.
"""

from __future__ import annotations

import importlib
import sys

_SUBCOMMANDS: dict[str, str] = {
    "status": "cmd_status",
    "index": "cmd_index",
    "runs": "cmd_runs",
}

_USAGE = """\
usage: vaultctl <subcommand> [args ...]

Subcommands:
  status    show vault status
  index     manage the vault index
  runs      list or inspect agent runs

Run `vaultctl <subcommand> -h` for subcommand-specific help.
"""


def main(argv: list[str]) -> int:
    """Dispatch to a subcommand module.

    Parameters
    ----------
    argv:
        Arguments *excluding* the program name (i.e. sys.argv[1:]).

    Returns
    -------
    int
        Exit code suitable for sys.exit().
    """
    if not argv:
        sys.stderr.write(_USAGE)
        return 2

    first = argv[0]

    if first in ("-h", "--help"):
        sys.stdout.write(_USAGE)
        return 0

    if first not in _SUBCOMMANDS:
        sys.stderr.write(f"vaultctl: unknown subcommand '{first}'\n")
        sys.stderr.write(_USAGE)
        return 2

    module_name = _SUBCOMMANDS[first]
    rest = argv[1:]

    mod = importlib.import_module(module_name)
    try:
        return mod.main(rest)
    except SystemExit as e:
        if e.code is None:
            return 0
        if isinstance(e.code, int):
            return e.code
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
