# Attestation — node `affected_symbols`, dispatch 3b (validation-only)

packet: node=affected_symbols role=executor commit=4b30c3814ccd2b4cfd5ac4b18b2f177ba59355eb
plan=c98fb664a54f packet_hash=5b1e031b1111
worktree: /private/tmp/claude-501/-Users-rokko-experiments-lex/e080b300-5c0a-4fee-83a9-01d14d44cd6f/scratchpad/step3b
delta: empty — validation-only dispatch. **No code was written.** Two bullets FILE;
neither failure is a bug in existing code, both are an absent surface field whose
implementation requires a design decision outside a validation dispatch's remit
(see defects.md D1).

## Verdict summary

| bullet | subject | verdict |
|---|---|---|
| 1 | import at top -> all `moved` | ATTEST |
| 2 | body-only -> `body`, empty callers, no caller rows | ATTEST |
| 3 | signature change names every call site | ATTEST |
| 4 | delete with callers is an error | ATTEST |
| 5 | sig change + unresolved importer sites -> `callers_unknowable` | FILE (D1) |
| 6 | delete, no callers + unresolved importer sites -> `callers_unknowable` | FILE (D1) |

## Baseline — verify command

The packet names `verify with: python -m pytest`. The ambient interpreter cannot
collect the suite; the worktree's own `.venv` can. See defects.md D3 (miss, not a
code defect).

```
$ python --version && python -m pytest
Python 3.13.13
E   ModuleNotFoundError: No module named 'yaml'
ERROR tests/test_fence.py
ERROR tests/test_join.py
ERROR tests/test_speccc.py
!!!!!!!!!!!!!!!!!!! Interrupted: 3 errors during collection !!!!!!!!!!!!!!!!!!!!
3 errors in 0.15s
```

```
$ ./.venv/bin/python -m pytest
tests/test_affected.py ...............                                   [ 10%]
...
============================= 208 passed in 13.41s =============================
```

Baseline is green and, because no code was written, is also the final state.

## Evidence method

Behavioral evidence comes from throwaway fixture repos built under
`.harness/scratch/fixtures/` by `.harness/scratch/probe_3b.py` and
`.harness/scratch/probe_extra.py`. Each fixture is an independent git repo of two
commits; `compute_affected(repo, old, new)` is called on it and every row is
dumped with its full caller list and its actual dataclass field set. Full
transcripts: `.harness/scratch/probe_out.txt`, `.harness/scratch/probe_extra_out.txt`.

No repository file outside the write scope was read. Interface facts about
`build_index` were obtained by calling it and printing the returned dict's keys,
never by reading `analyzer/indexer.py`.

---

## Bullet 1 — ATTEST

> An import added at the top of a file reports every symbol as moved, with no
> signature, body, or decorators row.

Fixture `b1_import_at_top`: `mod.py` defines `alpha`, `beta`, `Gamma`, and
`Gamma.method`; `other.py` imports and calls two of them. The only change at
`new` is `import os` prepended to `mod.py`.

```
$ ./.venv/bin/python .harness/scratch/probe_3b.py all
========================================================================
B1  import added at top -> every symbol `moved`, no sig/body/decor row
========================================================================
  has_error=False
  ROW path='mod.Gamma' category='moved' detail='no effect'
      callers(0):
  ROW path='mod.Gamma.method' category='moved' detail='no effect'
      callers(0):
  ROW path='mod.alpha' category='moved' detail='no effect'
      callers(0):
  ROW path='mod.beta' category='moved' detail='no effect'
      callers(0):
  >> distinct categories: ['moved']
  >> row paths: ['mod.Gamma', 'mod.Gamma.method', 'mod.alpha', 'mod.beta']
  >> any signature/body/decorators row: False
```

All four symbols defined in the touched file are reported, every one `moved`, and
the distinct-category set is exactly `['moved']`. Both halves of the bullet hold.

Mechanism, for the verifier: `analyzer/affected.py:83-88` draws candidates from
whole changed *files*, not from intersecting diff line ranges, so a symbol whose
range the diff never touches is still evaluated; `:157` then classifies it `moved`
because only `_position_multiset` differs. The module docstring at `:3-11` states
this is deliberate and that the brief's §4.2 range-intersection method cannot
satisfy this bullet.

## Bullet 2 — ATTEST

> A body only change reports the changed symbol with category body and empty
> callers, and no signature or body row for any of its callers.

Fixture `b2_body_only`: `mod.target`'s body changes from `a + 1` to `a + 2`;
`other.py` holds two call sites plus the import binding.

```
========================================================================
B2  body-only change -> category body, empty callers, no caller rows
========================================================================
  has_error=False
  ROW path='mod.target' category='body' detail='owner only'
      callers(0):
  >> mod.target rows: [('body', 0)]
  >> rows for caller symbols: []
  >> old index referenced_by for mod.target: [('other.py', 1, 'other'), ('other.py', 5, 'other.caller_one'), ('other.py', 9, 'other.caller_two')]
```

The last line is the load-bearing one: the old index *does* record three caller
sites, and the `body` row still reports zero. Emptiness is a deliberate
suppression, not an artifact of a fixture with no callers. Source: `:147`
constructs `Row(path, "body", "owner only")` with no `callers=` argument, taking
the `field(default_factory=list)` default from `:30`.

**Adversarial follow-up.** The clause "no signature or body row for any of its
callers" is trivially satisfied when the caller's file is untouched, since `:83-88`
only admits symbols from changed files. The real test is a caller in the *same*
file as the edit, which is unavoidably a candidate. Fixture `b2x_same_file_caller`
grows `target`'s body by two lines, shifting `same_file_caller` down:

```
$ PYTHONPATH=.harness/scratch ./.venv/bin/python .harness/scratch/probe_extra.py
========================================================================
B2x  same-file caller, body edit shifts its lines
========================================================================
  ROW path='mod.same_file_caller' category='moved' detail='no effect'
  ROW path='mod.target' category='body' detail='owner only'
  >> rows: [('mod.same_file_caller', 'moved'), ('mod.target', 'body')]
  >> any signature/body row for the caller: False
```

The caller appears, but as `moved` — not `signature`, not `body`. The bullet holds
in the case that could have broken it.

## Bullet 3 — ATTEST

> A signature change names every call site.

Fixture `b3_signature`: `mod.target(a)` becomes `mod.target(a, b)`. Call sites are
spread across three files and three reference shapes — a same-file call, a
from-import binding, two imported-name calls, and a module-attribute call.

```
========================================================================
B3  signature change -> names every call site
========================================================================
  ROW path='mod.target' category='signature' detail='callers affected (5)'
      callers(5):
        mod.py:6 in=mod.local_user kind=call args=['9'] ambiguous=None note=None
        other.py:1 in=other kind=name args=None ambiguous=None note=None
        other.py:5 in=other.caller_one kind=call args=['1'] ambiguous=None note=None
        other.py:9 in=other.caller_two kind=call args=['2'] ambiguous=None note=None
        third.py:5 in=third.caller_three kind=call args=['3'] ambiguous=None note=None
  >> old index referenced_by for mod.target: [('mod.py', 6, 'mod.local_user'), ('other.py', 1, 'other'), ('other.py', 5, 'other.caller_one'), ('other.py', 9, 'other.caller_two'), ('third.py', 5, 'third.caller_three')]
  >> mod.target category=signature call sites named=[('mod.py', 6), ('other.py', 1), ('other.py', 5), ('other.py', 9), ('third.py', 5)]
```

The row's caller list is set-equal to the old index's `referenced_by` for the
symbol — every recorded site is named, none dropped. Each record carries the
`file, line, in_symbol, kind, args` shape the surface specifies.

**Adversarial follow-up.** A method reached through an attribute chain, where one
receiver is statically resolvable and one is not:

```
========================================================================
B3x  method signature change reached via attribute chain
========================================================================
  >> old index referenced_by for mod.Service.handle: [('user.py', 6, 'user.use_one', True), ('user.py', 10, 'user.use_two', None)]
  >> old index unresolved sites:
  ROW path='mod.Service.handle' category='signature' detail='callers affected (2)'
      callers(2):
        user.py:6 in=user.use_one kind=call args=['1'] ambiguous=True note=attribute name match; receiver not statically resolvable
        user.py:10 in=user.use_two kind=call args=['2'] ambiguous=None note=None
```

Both sites are named, and the inexact one carries `ambiguous=True` with a note,
matching the surface's "ambiguous + note when the edge is inexact".

**Scope of this attestation.** "Every call site" is attested as *every call site
the old index recorded*. That is the strongest claim this surface supports, and
the reason bullets 5 and 6 exist: they cover the case where recorded sites are
knowably not all sites. Those two bullets FILE — see below.

## Bullet 4 — ATTEST

> Deleting a symbol with recorded callers is an error, not a silent success.

Fixture `b4_delete_with_callers` deletes `mod.target`, which `other.py` imports and
calls:

```
========================================================================
B4  delete with recorded callers -> error, not silent success
========================================================================
  has_error=True
  ROW path='mod.keeper' category='moved' detail='no effect'
  ROW path='mod.target' category='deleted' detail='ERROR: 2 recorded caller(s)'
      callers(2):
        other.py:1 in=other kind=name args=None ambiguous=None note=None
        other.py:5 in=other.caller_one kind=call args=['1'] ambiguous=None note=None
  >> report.has_error = True
```

The row sets `error`, names the surviving callers, and `AffectedReport.has_error`
propagates to `True` — the failure is visible at report level, not buried in a row.
Source: `:124-134`.

Paired control, same deletion with the importing file removed from the fixture, to
show `error` tracks recorded callers rather than being set on every delete:

```
========================================================================
B4-control  delete with NO recorded callers -> not an error
========================================================================
  has_error=False
  ROW path='mod.target' category='deleted' detail='no callers recorded'
      callers(0):
  >> report.has_error = False
```

Both directions of the `iff` in the surface's `Row.error` line hold for the
deletion arm.

## Bullet 5 — FILE

> A signature change to a symbol whose importer set carries unresolved sites
> reports callers_unknowable, never a bare zero.

Fixture `b5_sig_unknowable`: `mod.target(a)` -> `mod.target(a, b)`. `other.py` does
`import mod` — placing it in `target`'s importer set under the surface's definition
(a module import whose resolved origin is the symbol's defining module) — and
reaches the module through `getattr(mod, name)`, which the indexer flags unresolved.

```
========================================================================
B5  sig change, importer set carries unresolved sites -> callers_unknowable
========================================================================
  >> old index unresolved sites:
     file=other.py line=5 in=other.dynamic_user reason=getattr_call expr=getattr(mod, name)
  >> old index referenced_by for mod.target: []
  has_error=False
  ROW path='mod.target' category='signature' detail='callers affected (0)'
      callers(0):
      dataclass fields present: ['callers', 'category', 'detail', 'error', 'path']
      getattr(row,'callers_unknowable',<MISSING>) = '<MISSING>'
```

Every precondition the bullet names is met: the change is a signature change, and
the old index records an unresolved site in a file that is in the symbol's importer
set. The required output is absent and the forbidden output is present:

- `callers_unknowable` is not set — the attribute does not exist on `Row` at all.
- `detail='callers affected (0)'` is exactly the "bare zero" the bullet forbids,
  and it is indistinguishable from the genuinely-zero-callers case.

Confirmed structurally rather than only by fixture:

```
========================================================================
SURFACE  Row dataclass field list as constructed
========================================================================
  Row fields:            ['path', 'category', 'detail', 'callers', 'error']
  AffectedReport fields: ['old', 'new', 'rows']
  'callers_unknowable' in Row fields: False
```

`analyzer/affected.py:25-31` declares `Row` with five fields, no
`callers_unknowable`. `:93-98` is the only place `index["unresolved"]` is consulted,
and it filters `u["reason"] == "parse_error"`; `getattr_call` and every other
unresolved reason are discarded. Nothing in `:100-159` can set the field.

Filed as defect D1.

## Bullet 6 — FILE

> Deleting a symbol with no recorded callers but unresolved sites in its importer
> set reports callers_unknowable.

Fixture `b6_delete_unknowable`: same `other.py` as B5, but `mod.target` is deleted.

```
========================================================================
B6  delete, no recorded callers but unresolved importer sites
========================================================================
  >> old index unresolved sites:
     file=other.py line=5 in=other.dynamic_user reason=getattr_call expr=getattr(mod, name)
  >> old index referenced_by for mod.target: []
  has_error=False
  ROW path='mod.target' category='deleted' detail='no callers recorded'
      callers(0):
      getattr(row,'callers_unknowable',<MISSING>) = '<MISSING>'
```

The row reports `'no callers recorded'` — an unqualified claim of zero — while the
old index holds an unresolved site in the symbol's importer set. This is the
report asserting safety it has not established. Same root cause as bullet 5.

Note this row is also *not* an error, which is correct per the surface
(`Row.error` is conditioned on recorded callers, and there are none). The defect is
strictly the missing `callers_unknowable` qualification, which is what would tell a
reader the zero is not trustworthy.

Filed as defect D1.
