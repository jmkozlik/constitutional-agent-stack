# Handoff — node `affected_symbols`, dispatch 3d-2

For whoever replaces me. Verified facts and interpretive claims are
separated below; do not promote anything from the second list to the
first without re-deriving it.

## Where the work stands

Done. `Row.callers_unknowable` is built, all 43 of the 3t contract tests
pass, 342 of 343 repo tests pass. The single repo failure is filed as D-1
and is not a bug in this node — it is a locked demonstration whose
premise this dispatch was sent to end. Nothing is half-finished; if you
are reading this because the dispatch was re-run, start at D-1.

## Verified facts (re-derivable, each was checked)

- `analyzer/affected.py` is the only file modified. `git status
  --porcelain` shows ` M analyzer/affected.py` plus untracked `.harness/`.
- The 3t tests at `docs/evidence/step3t/harvest-out/tests/*.py.txt` were
  run **unmodified**; `diff -q` against the copies in
  `.harness/scratch/tests/` reports them identical.
- They must live exactly one directory below `.harness/scratch/` (i.e.
  `.harness/scratch/tests/`). `conftest.py` computes the package root as
  `parents[3]`; any other depth silently tests a different `analyzer`.
- Baseline before the edit: 36 passed, 7 failed — matching the tester's
  report headline exactly. After: 43 passed.
- `import_origins(index, module)` matches the imports table's `module`
  field. `_defining_modules` (`analyzer/indexer.py:62-65`) writes that
  field via `module_path(r["file"])`. So deriving the module in
  `affected.py` with the same `module_path` agrees by construction. This
  was checked in the source, not taken from the packet's assurance.
- `test_f20_locked_demonstration_on_real_spec` passed at HEAD with the
  edit stashed, and fails with it applied. The causal direction is
  established, not inferred.
- After the landing the delta's outstanding line is the **seeded** `Row`
  line, not `callers_unknowable` (which reads `present`). `delta["kind"]`
  is still `"partial"` for that reason. Exact reseed text is in D-1.
- Real-repo behaviour on `HEAD~1..HEAD`: 51 of 53 rows flagged, all
  `moved`, all via the own-file clause; 3 of 42 files carry unresolved
  sites.
- No write outside scope was attempted; no denial was encountered.

## Interpretive claims (mine, argued in the deliverables, not established)

- That the flag should be computed uniformly for every row from the old
  records, rather than scoped to caller-bearing categories. The contract
  states the iff without category qualification, so I read it literally.
  A reviewer could reasonably hold that a `moved` row carrying the flag
  is noise — see D-2, where the real-repo numbers make that case.
- That `added` rows correctly never carry the flag. I did not special-case
  this: a symbol with no old records has no own file and no defining
  module, so its importer set is empty and the iff yields False. I claim
  that falls out of the definition rather than being a decision, but it
  is a reading.
- That appending the unknowability note to `detail` is an improvement, and
  that withholding it from `body`/`moved`/`added` is the right line. The
  packet explicitly left this to judgement. Both halves are reversible
  without touching the flag.
- That `render_report` should print the flag. Optional under
  `observed_through`; I argued the CLI reader needs it. Also reversible.

## Things that would have cost me a round

- `.venv` does not exist inside the worktree. Use
  `/Users/rokko/experiments/lex/.venv/bin/python`.
- The tester's report says to run from `.harness/out/tests`; that path is
  a deliverable directory. `.harness/scratch/tests/` gives the same
  `parents[3]` depth and keeps `out/` clean.
- The harvested `.py.txt` files copy out read-only (`r--r--r--`). That is
  fine for running them and is a useful guard against editing them.

## Files

- `analyzer/affected.py` — the change.
- `.harness/out/attestation.md`, `.harness/out/defects.md` — deliverables.
- `.harness/scratch/tests/` — the 3t suite, unmodified, runnable.
- `.harness/scratch/probe_mechanism.py` + `probe_mechanism_out.txt` —
  importer-set mechanism evidence, including the own-file clause that no
  3t fixture covers.
- `.harness/scratch/verbose_out.txt` — per-test PASSED lines.
