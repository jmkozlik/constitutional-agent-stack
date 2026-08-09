# Handoff — node symbol_table, validation-only dispatch

## What this dispatch was
Empty delta at commit c734ce5 (packet_hash 0b86db190129): both surface
callables, the ParseFailure error, and the authored record-shape type were
already present. Task reduced to attesting the two done_when bullets. No
source files were modified; write scope untouched.

## Verified facts (commands + output in .harness/out/attestation.md)
- Full suite green before probing: 449 passed, 1 skipped.
- Bullet 1 ATTESTED: whitespace-only reformatting (blank lines, indent width,
  operator spacing, line wrapping, trailing spaces) leaves body_hash unchanged
  for every symbol; a real body edit changes it (control, non-vacuous probe).
- Bullet 2 ATTESTED: prepending lines shifts start_line/end_line by exactly
  the prepended count while all identity fields (path, kind, file, signature,
  sig_hash, body_hash, decor_hash, parent) stay byte-identical; ranges match
  the current call's source (decorator line is start_line); repeat calls
  reproduce identical records — extract_symbols is stateless.
- Boundary fact: whitespace INSIDE a docstring DOES change body_hash (verified
  by direct probe). Deliberate per analyzer/symbols.py:99-100 — docstrings are
  body statements, their content is data, not formatting.

## Interpretive claims (mine, not verified fact)
- I read "reformatting whitespace" as code formatting, not string-literal
  content; on that reading the docstring boundary is consistent with the
  bullet, so I attested rather than filed. If a verifier reads the bullet to
  cover docstring reflow, that is a spec-interpretation question, not an
  implementation bug.
- "Recomputed per commit" has no per-commit machinery to observe at this
  layer; extract_symbols takes (source, rel_path) per call. I treated
  statelessness + line-shift-invariant identity as the observable form of the
  bullet through the named surface. The per-commit loop lives upstream
  (indexer/build_index), outside this node's scope.

## Probes (rerunnable)
- .harness/scratch/probe_whitespace.py — bullet 1
- .harness/scratch/probe_ranges.py — bullet 2
Run with: .venv/bin/python .harness/scratch/probe_<name>.py from the worktree
root.

## Open questions left as-is (packet says do not resolve)
- Nested functions: currently own records, dotted through the enclosing
  function (analyzer/symbols.py TODO at _visit).
- Module-level constants: not indexed (TODO in extract_from_tree).

## request_mem
None needed; nothing was missing for a validation-only pass.
