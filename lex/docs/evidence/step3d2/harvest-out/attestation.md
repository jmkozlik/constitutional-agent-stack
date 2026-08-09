# Attestation — node `affected_symbols`, dispatch 3d-2

    role: executor
    packet: node=affected_symbols commit=8bbb99ffd082334af26cd0904f425fe912dcf3f0
            plan=66e648664216 packet_hash=1139fffde3e8
    write scope touched: analyzer/affected.py (only)

The landing was the one outstanding delta line, `Row.callers_unknowable`.
It is built; the three fail-first guarantees flip; the four that already
passed still pass.

## How the done_when bullets were observed

The acceptance criteria were written by a blind tester (dispatch 3t) from
the contract alone. They were run **unmodified** — copied out of the inert
harvest and stripped of the `.txt` suffix, nothing else. Byte-identity of
what ran against what was harvested is itself attested:

    $ for f in docs/evidence/step3t/harvest-out/tests/*.py.txt; do
        b=$(basename "$f" .txt); diff -q "$f" ".harness/scratch/tests/$b" \
          && echo "IDENTICAL: $b"; done
    IDENTICAL: conftest.py
    IDENTICAL: test_affected_errors.py
    IDENTICAL: test_affected_guarantees.py
    IDENTICAL: test_affected_surface.py

They live at `.harness/scratch/tests/` rather than `.harness/out/tests/`
because `conftest.py` resolves the package under test as
`Path(__file__).resolve().parents[3]`; a `tests/` directory one level under
`.harness/scratch/` puts the worktree root at that depth, so the suite
tests this worktree's `analyzer` with the file unaltered.

    $ python -c "print(Path('.harness/scratch/tests/conftest.py').resolve().parents[3])"
    /private/tmp/.../dispatches/3d-2

**Baseline before any edit** — reproduces the tester's headline exactly
(43 tests, 36 passed, 7 failed, all on the absent attribute):

    $ python -m pytest .harness/scratch/tests -q
    FAILED ...::test_g5_never_reports_a_bare_zero
    FAILED ...::test_g5_flag_survives_a_partially_resolved_caller_list
    FAILED ...::test_g5_boundary_clean_importer_set_does_not_set_flag
    FAILED ...::test_g6_delete_without_callers_but_unresolved_sites_sets_flag
    FAILED ...::test_g7_unknowable_fires_through_a_re_export_chain
    FAILED ...::test_g7_boundary_clean_facade_importer_does_not_set_flag
    FAILED ...::test_rows_expose_callers_unknowable
    7 failed, 36 passed in 8.12s

**After the landing:**

    $ python -m pytest .harness/scratch/tests -q
    ...........................................                    [100%]
    43 passed in 7.53s

---

## ATTEST — an import added at the top of a file reports every symbol as moved, with no signature, body, or decorators row

    test_g1_added_import_reports_every_symbol_as_moved PASSED
    test_g1_added_import_emits_no_change_row PASSED
    test_g1_boundary_a_real_edit_still_reports_a_change_row PASSED

The boundary is the load-bearing half: an analyzer that answered `moved`
unconditionally would satisfy the bullet's positive side. It does not —
prepending the same import *and* editing `alpha`'s body returns `alpha` as
`body` while `beta` stays `moved`.

## ATTEST — a body only change reports the changed symbol with category body and empty callers, and no signature or body row for any of its callers

    test_g2_body_change_is_categorised_body PASSED
    test_g2_body_change_carries_empty_callers PASSED
    test_g2_body_change_emits_no_change_row_for_callers PASSED

## ATTEST — a signature change names every call site

    test_g3_signature_change_names_every_call_site PASSED
    test_g3_call_sites_name_their_enclosing_symbol PASSED
    test_g3_caller_records_use_the_declared_kind_vocabulary PASSED
    test_g3_call_site_records_carry_their_args_as_written PASSED
    test_g3_boundary_uninvolved_symbol_is_not_named PASSED

Two call sites reached two different ways (`from mod import target` then
`target(1)`; `import mod` then `mod.target(2)`), with a bystander file
proving "every call site" has not degraded into "every file".

## ATTEST — deleting a symbol with recorded callers is an error, not a silent success

    test_g4_delete_with_callers_is_an_error PASSED
    test_g4_delete_with_callers_still_names_them PASSED
    test_g4_boundary_delete_without_callers_is_not_an_error PASSED

The errors clause is an iff, and both directions hold: deleting an orphan
reports `deleted` with `error is False`.

## ATTEST — a signature change to a symbol whose importer set carries unresolved sites reports callers_unknowable, never a bare zero

    test_g5_never_reports_a_bare_zero PASSED
    test_g5_flag_survives_a_partially_resolved_caller_list PASSED
    test_g5_boundary_clean_importer_set_does_not_set_flag PASSED

Was fail-first (0/3). The flag survives alongside a partially resolved
caller list rather than standing in for an empty one, and the boundary
confirms it stays unset when the importer set is clean — so the flag
discriminates rather than always firing.

## ATTEST — deleting a symbol with no recorded callers but unresolved sites in its importer set reports callers_unknowable

    test_g6_delete_without_callers_but_unresolved_sites_sets_flag PASSED
    test_g6_unknowable_deletion_is_not_promoted_to_an_error PASSED

Was 1/2. The companion test holds the errors clause honest in the other
direction and still passes: unknowability did **not** become an error.
`Row.error` remains set iff the old index records callers.

## ATTEST — callers_unknowable fires through a re-export chain: an importer reaching the symbol's module only via a package facade, carrying an unresolved site, sets the flag

    test_g7_unknowable_fires_through_a_re_export_chain PASSED
    test_g7_re_exported_symbol_uses_its_defining_module_path PASSED
    test_g7_boundary_clean_facade_importer_does_not_set_flag PASSED

Was 1/3.

---

## Mechanism evidence — the flag fires for the contract's stated reason

Passing the tester's assertions is not by itself evidence that the
importer set is the one the contract defines. This probe prints the set
actually computed, the old index's unresolved sites, and their
intersection (`.harness/scratch/probe_mechanism.py`, output at
`.harness/scratch/probe_mechanism_out.txt`):

    === own-file clause: star import inside the symbol's own module ===
      importer set     : ['mod.py']
      unresolved(old)  : {'mod.py': 'star_import'}
      intersection     : ['mod.py']
      callers_unknowable = True

    === own-file control: no trigger anywhere, no importers ===
      importer set     : ['mod.py']
      unresolved(old)  : {}
      intersection     : []
      callers_unknowable = False

    === importer-file clause: subscript_call in an importing file ===
      importer set     : ['mod.py', 'other.py']
      unresolved(old)  : {'other.py': 'subscript_call'}
      intersection     : ['other.py']
      callers_unknowable = True

    === re-export chain: importer reaches the module only via the facade ===
      row              : pkg.core.target  category=signature
      importer set     : ['app.py', 'pkg/__init__.py', 'pkg/core.py']
      unresolved(old)  : {'app.py': 'subscript_call'}
      intersection     : ['app.py']
      callers_unknowable = True

The first pair covers the clause **no 3t fixture exercises**: "the
symbol's own file". Every tester fixture puts the trigger in an importing
file, so the own-file half of the definition would have passed the suite
untested. The two cases differ only by the presence of the star import,
so the flag tracks the trigger and not the shape.

The fourth shows `app.py` entering the importer set although it never
names `pkg.core` — the re-export is resolved by the index's `imports`
table, not by any walk of mine.

## Provenance of the module string

The importer set is read through `analyzer.indexer.import_origins(index,
module)`, which matches the imports table's `module` field. The module
string is derived with `analyzer.modpath.module_path(record["file"])`.
The packet asserted these agree; verified rather than assumed —
`analyzer/indexer.py:62-65`:

    def _defining_modules(resolver: Resolver, path: str) -> list[str]:
        return sorted({module_path(r["file"]) for r in resolver.symbols.get(path, ())})

`_symbol_entry(bound, path, module)` writes `module` from that value, so
the two sides agree by construction. This was the gate's named failure
mode (a mismatched derivation returns `[]` and reads as a correct
negative); it is closed by shared provenance, not by luck.

No import graph was re-derived. The existing channel answers it.

## Judgement calls the packet left open

**`detail` on a flagged row.** The packet ruled this a judgement, not a
requirement. I changed it. `detail='callers affected (0)'` and
`detail='no callers recorded'` are the exact strings the tester's report
named as the bare zero and the "silent false-safety"; a row whose flag is
set while its detail still reads as a clearance is misleading to anyone
reading the value rather than the attribute. Flagged rows now read:

    'callers affected (0); importer set carries unresolved sites'
    'no callers recorded; importer set carries unresolved sites'

The note is appended only to details that make a claim **about callers** —
`signature`, `decorators`, and both `deleted` branches. `body` ("owner
only"), `moved` ("no effect") and `added` speak to effect rather than to
the caller list, and appending it there would imply an exposure that the
category has already ruled out. The flag itself is still set on those rows
per the iff; only the prose is withheld. No test pins any of these
strings: `tests/test_affected.py:63` pins `"owner only"` (unflagged
fixture) and `:208` pins `"parse" in row.detail`, both unaffected.

**`render_report`.** `observed_through` pins the bullets to the returned
value and no bullet names the renderer, so this was optional. Added
anyway, as one line per flagged row, because the CLI exits on
`has_error` and prints `detail` — a reader acting on that output would
otherwise have no way to see a gap on a row whose detail withholds the
note by the rule above. The `[seeded]` line pins the signature, which is
unchanged; the surface test asserting `render_report(...) is None` with
non-empty output still passes.

## Scope

`analyzer/affected.py` only.

    $ git status --porcelain
     M analyzer/affected.py
    ?? .harness/

No write was attempted outside the write scope, `.harness/scratch/`, or
`.harness/out/`. No denial was encountered. `docs/evidence/step3t/` was
read, which the packet anticipated and authorised.

## FILE — full-suite verification

The packet's verify line does not pass clean, and the failure is **caused
by this landing working**:

    $ python -m pytest -q
    tests/test_join.py:947: AssertionError
    FAILED tests/test_join.py::test_f20_locked_demonstration_on_real_spec
    1 failed, 342 passed in 22.42s

`tests/test_join.py` is outside my write scope, so this is filed rather
than fixed. It is D-1 in `defects.md`, with the evidence that it passed at
HEAD before the edit and the exact two-line change a fix requires. Every
other test in the repository passes (342), as does the whole 3t contract
suite (43).
