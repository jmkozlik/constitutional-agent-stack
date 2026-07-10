# vaultctl

Stdlib-only Python 3.13 CLI for operating the agent-stack vault
(default `~/vault`, override with the `VAULT_ROOT` env var or `--vault`).

## Usage

```
python3 vaultctl.py status            # RUN-STATE, executor heartbeats, recent ledger
python3 vaultctl.py index <folder>    # regenerate <folder>/_index.md from note frontmatter
python3 vaultctl.py runs              # list archived runs + ledger outcomes
```

All subcommands accept `--vault PATH` (default: `VAULT_ROOT` env var, else `~/vault`).

## Layout

- `vaultctl.py` — entry point, dispatches to `cmd_<name>.py`
- `cmd_status.py`, `cmd_index.py`, `cmd_runs.py` — one module per subcommand,
  each self-contained (no shared lib by design)
- `tests/` — unittest suite: `python3 -m unittest discover -s tests -t .`

No dependencies beyond the Python 3.13 standard library.
