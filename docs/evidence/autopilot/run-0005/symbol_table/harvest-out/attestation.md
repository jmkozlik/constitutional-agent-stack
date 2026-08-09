# Attestation — node symbol_table (validation-only dispatch)

packet: node=symbol_table role=executor commit=c734ce52451af00181b7264d81573c4029096964 plan=66e648664216 packet_hash=0b86db190129

Baseline: full suite green before any probing.

```
$ .venv/bin/python -m pytest 2>&1 | tail -1
================== 449 passed, 1 skipped, 1 warning in 25.08s ==================
```

## ATTEST — Reformatting whitespace does not change the body hash.

Observed through `analyzer.symbols.extract_symbols` (the surface callable).
Probe: `.harness/scratch/probe_whitespace.py` builds two byte-identical-in-semantics
sources differing only in whitespace formatting — blank lines, indentation width,
spaces around operators, wrapped expressions, trailing whitespace — extracts both,
and asserts `body_hash` equality per symbol path. A control asserts a real body
edit (`return 0` → `return 1`) *does* change the hash, so the probe is not vacuous.

```
$ .venv/bin/python .harness/scratch/probe_whitespace.py
src.w.Widget: body_hash f21ff8d7 == f21ff8d7 -> True
src.w.Widget.area: body_hash e9bcb90a == e9bcb90a -> True
src.w.helper: body_hash 37ac326f == 37ac326f -> True
control (real edit changes hash): True
PROBE 1 OK
```

Boundary, verified: whitespace *inside a docstring* does change the hash — a
docstring is a string constant in `node.body`, so its content is body, not
formatting. This matches the module's documented stance (analyzer/symbols.py:99–100,
"Docstrings are body, not comments, so they participate").

```
$ .venv/bin/python -c "
from analyzer.symbols import extract_symbols
a = extract_symbols(b'def f():\n    \"\"\"doc  text\"\"\"\n', 'src/d.py')[0]['body_hash']
b = extract_symbols(b'def f():\n    \"\"\"doc text\"\"\"\n', 'src/d.py')[0]['body_hash']
print('docstring-internal whitespace changes body_hash:', a != b)
"
docstring-internal whitespace changes body_hash: True
```

## ATTEST — Ranges are recomputed per commit, never stored as identity.

Observed through `analyzer.symbols.extract_symbols` return value.
Probe: `.harness/scratch/probe_ranges.py` checks both halves of the bullet:

- *Never identity*: prepending 5 lines shifts every `start_line`/`end_line` by
  exactly 5 while `path`, `kind`, `file`, `signature`, `sig_hash`, `body_hash`,
  `decor_hash`, `parent` are all byte-identical — ranges cannot participate in
  identity, or the hashes would move with them.
- *Recomputed per call*: ranges match known line numbers of the source passed to
  *that* call (including decorator-start handling: `@staticmethod` at line 1 is
  the record's `start_line`), and a repeat call reproduces records exactly —
  `extract_symbols` is stateless, nothing is stored between invocations.

```
$ .venv/bin/python .harness/scratch/probe_ranges.py
src.m.C: lines 6-8 -> 11-13, identity fields unchanged
src.m.C.m: lines 7-8 -> 12-13, identity fields unchanged
src.m.top: lines 1-3 -> 6-8, identity fields unchanged
repeat call reproduces identical records (no stored state)
PROBE 2 OK
```

Static corroboration: in `analyzer/symbols.py` the three hash inputs are
`_sig_canonical` (names/annotations/default-presence), `_body_hash`
(`ast.unparse` of `node.body`), and the unparsed decorator list — no line
numbers flow into any of them; `start_line`/`end_line` are read fresh from the
AST node on every `_visit` call (lines 146–154 of the packet's verbatim source).
