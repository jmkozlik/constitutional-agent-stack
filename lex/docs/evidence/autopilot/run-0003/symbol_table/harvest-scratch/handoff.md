# Handoff — node symbol_table, validation-only dispatch

packet: node=symbol_table role=executor commit=9d3bc13c0611b8bea23658237a755960245344bb plan=66e648664216 packet_hash=48344a19274d

## Status
Complete. Both done_when bullets ATTESTED; no code changes made (empty
delta, validation-only). Deliverables written: .harness/out/attestation.md,
.harness/out/defects.md, this file.

## Verified facts (I ran the commands; outputs in attestation.md)
- `.venv/bin/python -m pytest` → 441 passed, 1 skipped at worktree state.
- Whitespace-only reformat (blank lines, operator spacing, reindent 4→8,
  parenthesized continuations) leaves body_hash byte-identical for class,
  method, and function records: probe `.harness/scratch/probe_done_when.py`.
- Moving identical defs 37 lines (in-memory) and 6 lines (across two real
  commits in `.harness/scratch/gitfix`) changes start_line/end_line while
  sig_hash/body_hash/decor_hash stay identical: probes
  `probe_done_when.py` and `probe_per_commit.py`.
- Repeat extraction reproduces ranges from source alone; extract_symbols
  holds no state between calls.
- Write-fence denial (verbatim in attestation.md and defects.md D1): bare
  `mod.py` redirect after `cd` into scratch was denied although the real
  target was under `.harness/scratch/`. File was written instead via the
  Write tool at the explicit path, which the fence allowed.

## Interpretive claims (mine, not verified facts)
- "Ranges recomputed per commit" is satisfied structurally because
  extract_symbols is pure over (source, rel_path) and no hash input
  contains line numbers; I read this off the packet's verified source
  (symbols.py lines 31-60, 97-101, 126-131, 162-164) rather than auditing
  any downstream store. The indexer side is out of my scope; if a later
  layer persists ranges as identity, that would be its defect, not this
  node's.
- D1's proposed fix (cwd-aware path normalization in write-fence.py) is a
  suggestion; I have not read the hook's source (out of scope).

## Untouched
- analyzer/modpath.py and analyzer/symbols.py unchanged — verify with
  `git status`/`git diff` (only .harness/ contents are new).
- Open questions in the packet (nested-function folding, module-level
  constants) left open as instructed.
