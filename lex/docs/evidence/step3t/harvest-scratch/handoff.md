# Handoff — tester, node `affected_symbols`

State: **complete**. All deliverables written. If you are picking this up,
it is to revise, not to finish.

    packet: node=affected_symbols packet_hash=712cdfe4ecef plan=c98fb664a54f

## What exists

    .harness/out/tests/conftest.py                 helpers + git repo builder
    .harness/out/tests/test_affected_guarantees.py G1-G7, one section each
    .harness/out/tests/test_affected_errors.py     both sides of the errors iff
    .harness/out/tests/test_affected_surface.py    surface + input-sourcing
    .harness/out/tester_report.md                  verdicts and defects
    .harness/scratch/probe_surface.py              trigger-catalog sweep
    .harness/scratch/probe_surface_out.txt         its output (D-1 evidence)
    .harness/scratch/run_full.txt                  last -q run
    .harness/scratch/run_verbose.txt               last -v run, per-test verdicts

Run: `python -m pytest .harness/out/tests -q` from the worktree root, with
`/Users/rokko/experiments/lex/.venv/bin/python`. 43 tests, 36 pass, 7 fail.

## The blind constraint — keep it

No implementation source was read: not `analyzer/`, not the repo's own
`tests/`, not `docs/evidence/step3*` (those harvests contain earlier
probe output, which would leak implementation shape just as effectively as
the source). `probe_surface.py` observes only the *returned value* —
`dataclasses.fields`, `hasattr` — which is what `observed_through` licenses.
Do not relax this to resolve an ambiguity; file the ambiguity instead.

## The one open finding

`Row` has no `callers_unknowable` attribute. Fields are exactly the five
seeded ones. That single cause fails G5 (3 tests), G6 (1 of 2), G7 (2 of
3), plus `test_rows_expose_callers_unknowable`. Everything those tests
assert *before* the flag already passes.

When the attribute lands, expect all seven to flip together. If some flip
and others do not, the interesting ones are:

- `test_g5_never_reports_a_bare_zero` — `other.py` has `import mod` and
  `TABLE[key](value)` but never names `target`; currently `callers=[]`,
  `detail='callers affected (0)'`. This is the fixture that matters most:
  a flag that only fires when some edge already resolved would still leave
  this bare zero.
- `test_g6_unknowable_deletion_is_not_promoted_to_an_error` — passes
  today. The errors clause is an iff on *recorded callers*, so setting the
  flag on a deletion must not also set `error`. Watch that this does not
  regress when D-1 is fixed.
- the two boundary tests (`g5_boundary_clean_importer_set`,
  `g7_boundary_clean_facade_importer`) currently fail on absence, not on a
  wrong value. Once the attribute exists they become real controls: they
  are what stops a fix that sets the flag unconditionally.

## Judgement calls baked into the tests

Revisit these before changing an assertion — each was a deliberate reading.

1. **`kind: call | name` means caller records are a superset of call
   sites.** My first draft asserted the record set equalled the call sites
   and failed on the `from mod import target` line. That was my error, not
   the implementation's. Call-site claims read through `call_sites()`,
   which filters `kind == "call"`. Do not revert this to exact equality.
2. **`unknowable()` refuses a default.** Reading the flag as
   `getattr(row, 'callers_unknowable', False)` makes every negative
   control pass vacuously while the attribute is missing. It asserts
   presence instead. This is why the boundary tests fail today, and it is
   deliberate.
3. **`file` compared by basename, `in_symbol` by containment.** The
   contract pins neither form (D-3). Tightening these encodes a guess.
4. **Exact dotted paths asserted for root modules** (`mod.target`) and for
   the package case (`pkg.core.target`), because "the affected symbol's
   dotted path" has one plain reading there. The G7 *guarantee* test
   locates its row by `.endswith('.target')` so a naming disagreement
   cannot masquerade as a flag failure; a separate test pins the name.
5. **`error is False` asserted on the no-callers side** of G4 and G6,
   because the errors clause is written as an iff.

## Reading of the importer set I could not verify from outside

G5/G6/G7 assume that a `subscript_call` in a file that does `import mod`
counts as "the old index records unresolved sites in the symbol's importer
set". That follows from the ratified importer-set definition plus the
trigger catalog, both handed to me as contract. But whether the *index*
actually records such a site is internal and unobservable through the
surface. If the executor disputes these fixtures, that is the seam to
argue about — and if the index does not record unresolved sites at all,
the guarantee is vacuous as written and the spec node needs a fixture
named in it.

## Not done, deliberately

No test asserts the `ambiguous` / `note` fields (D-4): no entry in the
trigger catalog is identified as producing an inexact edge, so no fixture
for them can be built from the contract alone.
