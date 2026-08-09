# Attestation — node symbol_table (validation-only dispatch)

packet: node=symbol_table role=executor commit=225e2da300ea9253100fd93e870cca06fe67def5 plan=66e648664216 packet_hash=6d7c0c2fe44e

Delta was empty; no writes were made to the write scope. Both bullets were
validated behaviorally through the surface callable
`analyzer.symbols.extract_symbols` (per `observed_through`), using a probe
script at `.harness/scratch/probe_done_when.py`.

Baseline: full suite at the packet commit passes.

```
$ .venv/bin/python -m pytest 2>&1 | tail -5
  /Users/rokko/experiments/lex/.venv/lib/python3.13/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================== 440 passed, 1 skipped, 1 warning in 26.17s ==================
```

## ATTEST — Reformatting whitespace does not change the body hash

Probe: the same three symbols (function, class, method) extracted from an
original source and from a whitespace-only reformat of it — indent width
changed (4 → 2 and deeper), blank lines inserted/removed, parameters split
across lines, spaces around operators/commas/colons changed, trailing
whitespace added. `body_hash` is identical for every symbol.

```
$ .venv/bin/python .harness/scratch/probe_done_when.py
bullet1 OK  src.shop.total: body_hash 5fa7d4e9 == 5fa7d4e9
bullet1 OK  src.shop.Cart: body_hash 8c3963d2 == 8c3963d2
bullet1 OK  src.shop.Cart.add: body_hash c4e22c83 == c4e22c83
bullet2 OK  src.shop.total: lines 1-4 -> 56-59, sig/body/decor hashes unchanged
bullet2 OK  src.shop.Cart: lines 7-11 -> 62-66, sig/body/decor hashes unchanged
bullet2 OK  src.shop.Cart.add: lines 10-11 -> 65-66, sig/body/decor hashes unchanged
ALL PROBES PASSED
```

Corroborating in-repo test (`tests/test_symbols.py:68`
`test_body_hash_survives_reformat_and_comments`, asserting equal `body_hash`
across a reformat at line 79):

```
$ .venv/bin/python -m pytest tests/test_symbols.py -q 2>&1 | tail -3
.......................                                                  [100%]
23 passed in 0.01s
```

Mechanism (read, not asserted): `_body_hash` (analyzer/symbols.py:97-101)
hashes `ast.unparse` of the body statements; unparsing discards all
formatting. Note the boundary: whitespace *inside string literals*
(including docstrings) is string content, not formatting, and does change
the hash — `test_body_hash_changes_on_docstring_change`
(tests/test_symbols.py:82) pins that intentionally.

## ATTEST — Ranges are recomputed per commit, never stored as identity

Probe: the identical source shifted down by 55 padding lines. `start_line`
and `end_line` move for every symbol (e.g. `src.shop.total` 1-4 → 56-59)
while all three identity hashes (`sig_hash`, `body_hash`, `decor_hash`) are
byte-identical — position participates in no hash. Verbatim output is the
`bullet2 OK` block quoted above (same probe run).

Recomputation: `extract_symbols` takes only `(source, rel_path)` — no cache,
no prior index — and derives `start_line`/`end_line` fresh from the AST on
every call (analyzer/symbols.py:146-154); the indexer re-invokes extraction
per file per commit (analyzer/indexer.py:212 per the packet's caller list).
There is no code path that persists a range into an identity field.
