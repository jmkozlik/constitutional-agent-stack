# Handoff — reference_map validation dispatch

## Verified facts (evidence in .harness/out/attestation.md)
- Validation-only dispatch: packet delta was empty; all seeded surface
  callables/types present at commit c734ce52451af00181b7264d81573c4029096964.
- No source code was written or modified. `git status --porcelain` shows
  only the pre-existing untracked `.venv`.
- Full suite via the declared command `.venv/bin/python -m pytest`:
  449 passed, 1 skipped. Refs subset (test_refs.py + test_unresolved.py):
  59 passed.
- Probe `.harness/scratch/validate_done_when.py` (surface-only:
  ImportTable.from_module → Resolver → collect_references) exits 0 and
  demonstrates all three done_when bullets:
  1. callers at module / function / method level each carry
     file + line + in_symbol;
  2. args are verbatim source text (`p`, `strict=flag`,
     `compute_path()`, `strict=not False`), never traced to origin;
  3. opaque-receiver `worker.load()` is emitted against the
     terminal-name match with `ambiguous: True` and note
     "attribute name match; receiver not statically resolvable".
- Deliverables written: out/attestation.md (3× ATTEST), out/defects.md
  (none), this file.

## Interpretive claims (mine, not verified beyond the probe)
- "Every caller" was validated on a 2-file fixture covering the three
  enclosing-scope shapes, plus the existing 59-test suite; it is not an
  exhaustive enumeration of Python call-site shapes. The packet's own
  "Unresolved sites in scope" section (getattr dispatch in refs.py
  itself) is a known, flagged limitation of static resolution, not a
  done_when violation — ambiguity/unresolved flagging is the designed
  behavior for those.
- No request_mem calls were needed; the packet's compiled state matched
  the file on disk everywhere I checked (spot-checked signatures and
  line ranges while writing the probe).

## If you replace me
Re-run: `.venv/bin/python -m pytest` then
`.venv/bin/python .harness/scratch/validate_done_when.py` from the
worktree root. Both green ⇒ the attestation still holds.
