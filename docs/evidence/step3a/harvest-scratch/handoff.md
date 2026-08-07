# Handoff — affected_symbols executor (validation-only dispatch)

commit: e667744bbbf58591746d367cc082eb20c6d93173
packet_hash: 68437893ac8d  plan: c98fb664a54f
node: affected_symbols   role: executor

## What this dispatch was

Empty delta — every surface entry was already `present` or a delta-exempt
authored contract. So: no code written. `git diff -- analyzer/affected.py`
is empty and stays empty. The job was to attest or file against the four
`done_when` bullets.

## What I did

1. Ran the verify command: `.venv/bin/python -m pytest` → 204 passed.
2. Did NOT read `tests/test_affected.py` — outside this dispatch's read
   scope. Test names visible in pytest output map suggestively onto the
   bullets, but a passing test whose body I cannot see is weak evidence, so
   I built independent fixtures instead.
3. Wrote `.harness/scratch/probe.py` — four throwaway git repos under
   `.harness/scratch/fixtures/`, one per bullet, plus a control for bullet 4
   (deletion with no callers must NOT be an error). All assertions pass;
   exit 0. Transcript saved at `.harness/scratch/probe_out.txt`.
4. Wrote `.harness/scratch/probe_edges.py` — three non-gating diagnostics
   (E1 method sig change via instance, E2 import + body edit in one commit,
   E3 signature change with a `getattr` call site).

## Verified (fact, with transcripts in probe_out.txt)

- Bullet 1: import at top of `mod.py` → all four symbols `moved`, no
  signature/body/added/deleted row, `has_error` False.
- Bullet 2: body-only edit → exactly one row, `body`, `callers == []`, and
  neither caller (`mod.caller_one`, `other.caller_two`) gets a
  signature/body row.
- Bullet 3: param added → `signature`, and all four authored reference sites
  named. Expected line numbers are derived by searching the fixture source,
  not hand-counted (my first pass hand-counted and produced a false FAIL).
- Bullet 4: delete with callers → `deleted`, `error=True`, 3 caller records,
  `has_error` True. Control: delete with no callers → `has_error` False.

## Claims (NOT verified — my reading, for whoever picks this up)

- I read bullet 3's "every call site" as scoped to edges the old index
  resolved, because the surface says `Row.callers` is "reference records as
  compiled in the old index". Under a stricter reading, E3 below is a miss.
  A spec owner should confirm which reading is intended.

## Observations worth a spec decision (not bullet failures)

- **E3, the interesting one.** A signature change whose only call site is
  `getattr(mod, name)(1)` reports `signature` with `callers affected (0)` —
  a symbol that IS dynamically called reads as having zero callers. The site
  is not lost: it sits in `old_index["unresolved"]` as
  `{'reason': 'getattr_call', 'expression': 'getattr(mod, name)', ...}`.
  `compute_affected` consults `unresolved` only for `parse_error`
  (lines 93-98), so undecidable sites never reach the report. This is the
  same "flag, don't guess" concern the module already honors for parse
  failures, applied to reference edges. Fixing it means a surface change
  (a new field or row category), so it is out of scope for this dispatch.
- **E1.** A method signature change also marks the enclosing class `body`,
  since the class `body_hash` covers nested method source. Harmless, but a
  reader may find the extra row noisy.
- **E1, good news.** Inexact edges do carry `ambiguous: True` plus
  `note: 'attribute name match; receiver not statically resolvable'`,
  matching the surface contract.

## What I would do next

1. Get a ruling on E3. If undecidable sites should surface, that is a spec
   node edit (surface + a done_when bullet), then an executor dispatch —
   not a patch here.
2. If a stricter reading of bullet 3 wins, `compute_affected` would need to
   intersect `old_index["unresolved"]` with the changed symbol's module and
   attach those sites to the row, probably with `error` semantics matching
   the deleted-with-callers case.
3. Nothing else. The write scope is correct as-is for the bullets as written.

## Scratch inventory (all throwaway)

- `.harness/scratch/probe.py`, `probe_edges.py`, `probe_out.txt`
- `.harness/scratch/fixtures/` — 7 fixture git repos, regenerated on each run
