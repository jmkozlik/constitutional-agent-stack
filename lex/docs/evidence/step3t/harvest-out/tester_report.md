# Tester report — node `affected_symbols`

    role: tester
    packet: node=affected_symbols commit=f7b67141fbe0e0ca82dcfd5b871d0807be3a0ecf
            plan=c98fb664a54f packet_hash=712cdfe4ecef

Tests were written from the contract alone. No implementation source was
read: not `analyzer/`, not the repository's own `tests/`, not the
`docs/evidence/step3*` harvests from earlier runs. Every claim below is
observed through the declared surface — the value returned by
`compute_affected`, plus `render_report` for the one rendering smoke test.

## How to run

    cd <worktree root>
    /Users/rokko/experiments/lex/.venv/bin/python -m pytest .harness/out/tests -q

`conftest.py` prepends the worktree root to `sys.path`, so the suite is
runnable from any cwd and always tests the worktree's `analyzer`, not an
installed copy. Fixtures are real git repositories built into `tmp_path`
by `build_repo`, one commit per revision, with git identity supplied
per-command. Nothing outside the worktree and pytest's tmp dir is touched.

## Headline

    43 tests: 36 passed, 7 failed.

Four of the seven guarantees pass. Three — G5, G6, G7 — fail, all for a
single root cause: **`Row` carries no `callers_unknowable` attribute at
all.** The returned dataclass exposes exactly the five `[seeded]` fields:

    Row fields: ['path', 'category', 'detail', 'callers', 'error']

`callers_unknowable` is an `[authored]` line against a `[seeded]` field
list, and the ratified seeded-vs-authored rule in my protocol says the
authored line leads: the attribute is contract and is due to exist. So
this is not a spec contradiction to file — it is an unmet guarantee.

Worth noting precisely, because it narrows the fix: the same ratified rule
*was* honoured for `AffectedReport.has_error`, which is present and
correct. The omission is specific to `callers_unknowable`, not a
systematic misreading of the authored/seeded rule.

---

## G1 — an import added at the top of a file reports every symbol as moved, with no signature, body, or decorators row

**Discriminating fixture.** `mod.py` holds `alpha`, `beta`, and a class
`Gamma` with a method; at new_rev the file is byte-identical except for a
prepended `import os\n\n`, so every symbol shifts by two lines and nothing
changes content. `other.py` imports and calls `alpha` and is untouched.

**Boundary.** `test_g1_boundary_a_real_edit_still_reports_a_change_row`
prepends the same import *and* edits `alpha`'s body: `alpha` must come
back `body` while `beta` stays `moved`. Without this side, an analyzer
that reported everything as `moved` unconditionally would pass G1.

**Verdict: pass.** All three tests pass. No row in the shifted-only
report carries `signature`, `body`, or `decorators`.

## G2 — a body only change reports the changed symbol with category body and empty callers, and no signature or body row for any of its callers

**Discriminating fixture.** `mod.target` changes `return 1` to `return 2`,
same line count. `other.caller` imports and calls it.

Three separate tests, so a failure localises: the category is `body`; the
row's `callers` is empty; and no row for `other.caller` carries
`signature` or `body`.

**Verdict: pass.**

## G3 — a signature change names every call site

**Discriminating fixture.** `def target(a)` becomes `def target(a, b)`.
Two call sites in two files, reached two different ways: `other.py` does
`from mod import target` then `target(1)`; `third.py` does `import mod`
then `mod.target(2)`.

**Boundary.** `test_g3_boundary_uninvolved_symbol_is_not_named` adds
`bystander.py`, which never references `target`. "Every call site" must
not degrade into "every file".

**Verdict: pass** — after a correction on my side, recorded here because
it changed what the test asserts.

My first version demanded that the row's caller records be exactly the two
call sites. It failed: the row also carries the `from mod import target`
line as `{'file': 'other.py', 'line': 1, 'in_symbol': 'other', 'kind':
'name'}`. That is within contract, not a defect — the record type declares
`kind: call | name`, so an import binding is a legitimate `name` record,
and G3 constrains call sites, not the whole record set. The tests now read
call-site claims through `call_sites()`, which filters on `kind == "call"`,
and a separate test asserts the kind vocabulary stays within
`{call, name}`. The same correction applied to G4, the G5 boundary, and
the parse-failure caller test.

Call-site records carry `args` as written (`['1']`, `['2']`) and name
their enclosing symbol (`other.use_one`, `third.use_two`).

## G4 — deleting a symbol with recorded callers is an error, not a silent success

**Discriminating fixture.** `mod.target` is deleted at new_rev while
`other.caller` still calls it; `mod.keep` survives so the file itself is
not removed.

**Boundary.** `test_g4_boundary_delete_without_callers_is_not_an_error`
deletes `mod.orphan`, which nothing references, from a repo whose importer
file is clean. The errors clause is an *iff*, so this side must report
`deleted` with `error is False` and `has_error is False` — otherwise the
error is being caused by deletion rather than by orphaned callers.

**Verdict: pass.** `error is True`, `has_error is True`, and the row still
names the caller line that justifies the error.

## G5 — a signature change to a symbol whose importer set carries unresolved sites reports callers_unknowable, never a bare zero

**Discriminating fixture (bare zero).** `other.py` does `import mod` —
putting it in `target`'s importer set per the ratified definition, since
the binding's resolved origin is `target`'s defining module — never names
`target`, and dispatches through `TABLE[key](value)`, which the trigger
catalog lists as `subscript_call`. `target`'s signature then changes.
This is the literal bare zero the guarantee forbids.

Observed:

    Row(path='mod.target', category='signature',
        detail='callers affected (0)', callers=[], error=False)

Zero callers, no flag, no way for a reader to tell this from a symbol that
genuinely has no callers.

**Second positive fixture.** `test_g5_flag_survives_a_partially_resolved_caller_list`
adds `TABLE = {"t": mod.target}`, so one edge resolves. The flag must
survive *alongside* a non-empty caller list rather than standing in for an
empty one.

**Boundary.** `test_g5_boundary_clean_importer_set_does_not_set_flag` uses
an importer with no trigger at all: the call site must be named and the
flag must be unset. This one fails for the same missing-attribute reason,
so it is **not independent evidence of a second defect** — it currently
cannot distinguish "correctly unset" from "absent", which is precisely why
`unknowable()` refuses to read the attribute through a default.

**Verdict: fail-first.** All three tests fail on the absent attribute.

## G6 — deleting a symbol with no recorded callers but unresolved sites in its importer set reports callers_unknowable

**Discriminating fixture.** `importer.py` does `import mod`, references
only `mod.keep`, and dispatches through `TABLE[key]()`. `mod.target` —
zero recorded callers, one unresolved site in its importer set — is
deleted.

Observed:

    Row(path='mod.target', category='deleted',
        detail='no callers recorded', callers=[], error=False)

`detail` asserts "no callers recorded" as though that settled the
question. This is the silent false-safety G6 exists to prevent.

**Companion test, passing.** `test_g6_unknowable_deletion_is_not_promoted_to_an_error`
holds the errors clause honest in the other direction: no recorded
callers means `error is False`, per the iff, even when the flag should
fire. That passes today and must keep passing once the flag lands — the
fix must not turn unknowability into an error.

**Verdict: fail-first.**

## G7 — callers_unknowable fires through a re-export chain

**Discriminating fixture.** `pkg/core.py` defines `target`;
`pkg/__init__.py` re-exports it with `from pkg.core import target`;
`app.py` reaches it *only* through the facade (`from pkg import target`)
and carries `REGISTRY[key](value)`. `target`'s signature changes.

**Boundary.** `test_g7_boundary_clean_facade_importer_does_not_set_flag`
is the same chain with a clean importer.

**Verdict: fail-first**, on the same absent attribute.

One genuinely positive finding underneath the failure: the re-export chain
*is* traced for reference purposes. The row is correctly keyed to the
defining module rather than the facade —
`test_g7_re_exported_symbol_uses_its_defining_module_path` passes, giving
`pkg.core.target` — and its callers reach through the facade to `app.py`:

    callers=[{'file': 'app.py', 'line': 1, 'in_symbol': 'app', 'kind': 'name'},
             {'file': 'app.py', 'line': 5, 'in_symbol': 'app.run',
              'kind': 'call', 'args': ['value']},
             {'file': 'pkg/__init__.py', 'line': 1, 'in_symbol': 'pkg',
              'kind': 'name'}]

So the chain-walking G7 needs already works. What is missing is only the
flag that reports what the walk could not see.

---

## Errors clause (`test_affected_errors.py`) — pass

The deletion branch is covered by G4. This file covers the parse-failure
branch and both sides of the iff:

- symbol with callers, file unparseable at new_rev (`def target(a:`) →
  `row.error is True`, `has_error is True`, the symbol is not swallowed
  from the report, and the caller record that justifies the error survives;
- same parse failure with **no** recorded callers → no error anywhere;
- body change **with** callers → no error (callers alone are not an error);
- `has_error is any(row.error)` checked in both directions.

All seven tests pass.

## Surface properties (`test_affected_surface.py`) — pass, except the flag

These are not done_when bullets. They cover the `[authored]` lines the
guarantees lean on:

- `report.old` / `report.new` echo the revisions asked about (fixtures pass
  full shas so the resolved-vs-literal ambiguity cannot mask a failure);
- rows carry the declared field types; categories stay inside the declared
  seven-value vocabulary; one row per symbol path, no duplicates;
- `added` and `decorators` are reachable categories (vocabulary coverage
  beyond the guarantees);
- `repo` accepts `str` and `Path` alike; any rev-parse-able revision works
  (`HEAD~1`/`HEAD` matches the sha form);
- **no index artifact is written into the repo** — the file set under the
  repo is byte-identical before and after;
- **uncommitted worktree state is never consulted** — overwriting `mod.py`
  with unparseable garbage and adding an untracked `intruder.py` leaves the
  report unchanged, and the garbage is still on disk afterwards;
- **neither rev is checked out** — `HEAD` is unmoved across the call;
- a three-commit repo analysed at `first..second` does not leak the symbol
  added in the third commit;
- `render_report(report, out=StringIO())` returns `None` and writes the
  affected symbol's path.

The one failure here is `test_rows_expose_callers_unknowable`, which exists
to make the missing attribute a first-class verdict rather than something
the G5/G7 boundary tests pass over vacuously.

---

## Defects filed

**D-1 (implementation, blocking three guarantees).** `Row` does not expose
`callers_unknowable`. Evidence: `dataclasses.fields(Row)` returns
`['path', 'category', 'detail', 'callers', 'error']`; `hasattr(row,
'callers_unknowable')` is `False` on every row of every fixture. Probed
across the whole trigger catalog — `subscript_call`, `getattr_call`, bare
`getattr`, `attribute_of_call`, `star_import`, `def __getattr__`,
`setattr` — for both signature changes and deletions, with the trigger in
an importer file and in the symbol's own file. The attribute is absent in
all sixteen combinations. Raw output:
`.harness/scratch/probe_surface_out.txt`.

**D-2 (spec, non-blocking).** The reference-record contract lists
`(file, line, in_symbol, kind, args)` without saying which fields are
conditional. Observed: `args` is present on `kind: 'call'` records and
absent from `kind: 'name'` records. That is a defensible design — a name
reference has no arguments as written — but the contract does not say so,
so a test written strictly from it would wrongly demand `args` everywhere.
The spec should mark `args` as call-only. I worked around it by reading
`args` only from call-kind records.

**D-3 (spec, non-blocking).** The record contract does not pin the
*access* shape — mapping or attribute-carrying object. Observed: plain
`dict`. My `ref()` accessor spans both readings rather than guessing one.
Also unpinned: whether `file` is repo-relative or absolute (observed
repo-relative), and what `in_symbol` holds for a module-level reference
(observed the module's dotted path, e.g. `'other'`, versus `'other.use'`
for a reference inside a function). My tests compare `file` by basename and
`in_symbol` by containment so they do not encode a guess as a requirement.

**D-4 (spec, non-blocking, no verdict attached).** The record contract
mentions `ambiguous` and a `note` "when the edge is inexact", but no entry
in the trigger catalog is identified as producing an inexact edge, so I
could not construct a fixture that exercises those fields from the
contract alone. No test asserts them. If they are meant to be reachable,
the spec needs a named shape that produces one.

**Not filed.** The absence of `callers_unknowable` from the `[seeded]`
`Row` field list is *not* filed as a spec contradiction: the ratified
seeded-vs-authored rule in my protocol resolves it in favour of the
authored line.

## REQUEST_MEM

REQUEST_MEM: the caller reference record's access shape (mapping vs attribute object) and which of its declared fields are conditional — `args` is absent on `kind: 'name'` records; non-blocking, worked around with a shape-agnostic accessor, but the spec should pin it so tests can assert exactly.

REQUEST_MEM: the surface form of the caller record's `file` and `in_symbol` values — repo-relative vs absolute path, and whether a module-level reference reports the module's dotted path or the enclosing symbol; non-blocking, compared by basename and containment instead, which is weaker than the contract deserves.

## Verdict table

| # | Guarantee | Verdict | Tests |
|---|-----------|---------|-------|
| G1 | import added at top → every symbol `moved`, no change row | **pass** | 3/3 pass |
| G2 | body-only change → `body`, empty callers, no caller change row | **pass** | 3/3 pass |
| G3 | signature change names every call site | **pass** | 5/5 pass |
| G4 | deleting a symbol with recorded callers is an error | **pass** | 3/3 pass |
| G5 | signature change + unresolved importer sites → `callers_unknowable`, never a bare zero | **fail-first** | 0/3 pass |
| G6 | deletion, no callers, unresolved importer sites → `callers_unknowable` | **fail-first** | 1/2 pass |
| G7 | `callers_unknowable` fires through a re-export chain | **fail-first** | 1/3 pass |
| — | errors clause (both sides of the iff) | pass | 7/7 pass |
| — | surface / input-sourcing properties | pass | 13/14 pass |

G5, G6 and G7 fail on one cause, D-1. No other defect is implicated in
any failure: every assertion those tests make *before* reaching the flag —
category, caller list contents, error state, dotted path — passes.
