# analyzer

Indexes a Python repo and answers three questions for any symbol:

1. Where is it defined, and what is its signature?
2. Who references it?
3. When a diff lands, which symbols changed, and how?

Bottom layer of an agent harness (see `docs/brief.md`); pure stdlib at
runtime, `ast`-based, no daemon, no database.

## Install / run

```sh
uv venv .venv && uv pip install -e '.[dev]' --python .venv/bin/python
.venv/bin/python -m pytest            # full suite
.venv/bin/python -m analyzer --help   # or the `analyzer` console script
```

## Commands

```sh
analyzer index <repo> [--commit REV] [-o index.json]
analyzer symbol <dotted.path> [--index index.json]
analyzer affected <old-rev> <new-rev> [--repo .]
analyzer unresolved [--index index.json]
```

`index` walks the working tree (tracked + untracked, via `git ls-files`)
or, with `--commit`, reads blobs straight from git — no checkouts. Output
is byte-identical for the same commit. `affected` builds both commits'
indexes in memory and classifies each symbol by hash comparison:
`signature` (callers affected, each named), `body` (owner only),
`decorators` (callers affected), `moved` (no effect), `added`, `deleted`
(nonzero exit if the deleted symbol had recorded callers).

## Semantics worth knowing

- Identity is `path + sig_hash + body_hash`. Line ranges are per-commit
  derivatives. `sig_hash` sees parameter names/annotations and default
  *presence* — not default values. `body_hash` is computed over the
  unparsed AST, so reformatting and comments never register.
- Reference resolution is scope-aware (shadowing, nested defs, imports,
  re-export chasing through `__init__` facades, src-layout suffix
  matching). When a receiver can't be resolved statically, the terminal
  name is matched against every indexed symbol and the reference is
  marked `ambiguous` — over-reporting is preferred to silence.
- Call sites whose target cannot be determined statically become
  `unresolved` records (`subscript_call`, `getattr_call`,
  `attribute_of_call`, `star_import`, `dynamic_attribute`,
  `parse_error`, `unresolved_import_target`), and every symbol in a
  flagged file is marked `confidence: "low"` — consumers treat that as
  "assume an edge to everything here".

Design record: `docs/superpowers/plans/2026-08-05-analyzer-v0.md`
(including the post-red-team amendments A1–A12 and documented deviations
from the brief).
