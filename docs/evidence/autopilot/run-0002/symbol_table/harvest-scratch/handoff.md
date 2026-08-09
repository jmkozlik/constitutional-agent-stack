# Handoff — node symbol_table, validation-only dispatch

packet: commit=225e2da300ea9253100fd93e870cca06fe67def5 plan=66e648664216 packet_hash=6d7c0c2fe44e

## Verified facts
- Delta was empty; I wrote nothing in the write scope (analyzer/modpath.py,
  analyzer/symbols.py are untouched — `git status --porcelain` shows only
  `?? .venv`).
- Full suite passes at the packet commit: 440 passed, 1 skipped
  (`.venv/bin/python -m pytest`).
- Both done_when bullets ATTESTED; evidence in .harness/out/attestation.md.
  Probe script preserved at .harness/scratch/probe_done_when.py — rerunnable,
  prints `ALL PROBES PASSED`.
- Bullet 1: body_hash identical across a whitespace-only reformat for
  function/class/method symbols (5fa7d4e9, 8c3963d2, c4e22c83), and across a
  55-line position shift. In-repo test test_body_hash_survives_reformat_and_comments
  (tests/test_symbols.py:68) covers the same property.
- Bullet 2: position shift moves start_line/end_line but leaves sig_hash,
  body_hash, decor_hash byte-identical.

## Interpretive claims (mine, not verified law)
- I read "reformatting whitespace" as formatter-style changes that preserve
  the AST. Whitespace inside string literals/docstrings DOES change
  body_hash; the repo pins that as intended behavior
  (test_body_hash_changes_on_docstring_change, tests/test_symbols.py:82),
  so I did not treat it as a defect.
- I read "never stored as identity" as: line ranges appear in records as
  positional metadata but feed no hash. Static reading of _visit
  (analyzer/symbols.py:142-177) supports this — no lineno reaches _hash.
- The two `open` questions (nested functions as own symbols; module-level
  constants) remain open; current behavior is nested-functions-get-own-
  dotted-entries and constants-not-indexed, both marked TODO in source.

## No defects filed, no request_mem, no fence denials.
