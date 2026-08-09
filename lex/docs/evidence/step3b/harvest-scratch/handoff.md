# Handoff — `affected_symbols` dispatch 3b (validation-only)

For whoever picks this up. Facts and interpretations are separated on purpose;
do not promote anything from the second list to the first without re-deriving it.

State at handoff: **no code written**, `analyzer/affected.py` byte-identical to
HEAD, `git status --porcelain` shows only `?? .harness/`. The dispatch is complete;
all three artifacts are written.

---

## VERIFIED FACTS (each re-derivable from a command in this worktree)

1. Worktree HEAD is `4b30c3814ccd2b4cfd5ac4b18b2f177ba59355eb`, matching the
   packet's provenance line. No tracked file was modified.
2. `python -m pytest` (ambient, Python 3.13.13) fails collection with 3 errors, all
   `ModuleNotFoundError: No module named 'yaml'` (confirmed by grep count = 3), in
   `test_fence` / `test_join` / `test_speccc`. None relate to this node.
3. `./.venv/bin/python -m pytest` → `208 passed`. Reproduced twice (13.41s, 13.19s).
   This is both the baseline and the final state.
4. `Row` has exactly five fields: `path, category, detail, callers, error`.
   `callers_unknowable` does not exist. Verified via `dataclasses.fields(Row)`.
5. `build_index` returns exactly five top-level keys: `commit, files, symbols,
   unresolved, version`. Symbol records carry no import information; unresolved
   records are `{expression, file, in_symbol, line, reason}` and name no target
   module — `mod` appears only as text inside `expression`.
6. Bullets 1-4 pass against purpose-built fixtures, including two adversarial
   follow-ups (same-file caller under a line-shifting body edit → `moved`, not
   `signature`/`body`; attribute-chain method call → both sites named, the inexact
   one carrying `ambiguous=True` + note).
7. Bullets 5 and 6 fail. Fixtures satisfy every stated precondition (`import mod`
   in the importer set + a `getattr_call` unresolved site), and the report emits
   `callers affected (0)` / `no callers recorded` with no qualification.
8. `affected.py:93-98` consults `index["unresolved"]` only for
   `reason == "parse_error"`. Every other unresolved reason is discarded.
9. The packet carries 9 `[authored]` surface lines; 6 are attribute-on-declared-type
   shape. A presence check over those 6 flags exactly one absent
   (`Row.callers_unknowable`) with zero false positives.

## INTERPRETIVE CLAIMS (my judgement — argue with these)

1. **I chose to file D1 rather than implement it.** The dispatch says a
   validation-only dispatch "writes no code unless a bullet fails for a code reason",
   which arguably licensed implementing `callers_unknowable`. I read an absent
   *feature* as different from a *bug in existing code*, and the fix requires choosing
   between duplicating import-table construction inside `affected.py` (double parse,
   `test_perf.py` exists) and widening the index shape (out of scope, cross-node). A
   successor who reads the dispatch line more permissively could reasonably implement
   Option A. If you do, do not skip re-export chains — see D1's last paragraph.
2. **D2 is the more important finding.** D1 is one missing field; D2 is the reason
   the delta reported this node complete while the field was missing. I think the
   `delta-exempt` rule, as applied to structural authored lines, makes the delta
   blind exactly where the surface is newest. That is a claim about the format, and
   the dispatcher should weigh it, not me.
3. **Fixture adequacy.** My fixtures use `getattr(mod, name)` to generate the
   unresolved site. The surface's importer-set definition also covers from-imports and
   re-export chains, which I did **not** exercise — no point, since the field does not
   exist at all. When D1 is fixed, those two paths need their own fixtures; a fix that
   only handles direct module imports would pass my B5/B6 fixtures while still being
   wrong.
4. **Bullet 3's scope.** I attested "names every call site" as "names every call site
   the old index recorded". I believe that is the strongest claim the surface supports,
   and that bullets 5-6 exist precisely to cover the gap. If a verifier reads bullet 3
   as an absolute completeness claim, it should FILE too, and D1 becomes its cause.
5. **Observation, not filed as a defect.** In fixture `b3x`, a method signature change
   also produces a `body` row for the *enclosing class* (`mod.Service`, `owner only`,
   empty callers), because the class's body hash covers the method. No `done_when`
   bullet forbids it and the method's own row carries the callers, so the report is
   correct overall. Flagging it only because it looks surprising in output and someone
   will eventually ask.

## Miss log (REQUEST_MEM)

REQUEST_MEM: the interpreter/environment the packet's `verify with: python -m pytest`
assumes — the ambient `python` (3.13.13) lacks `yaml` and cannot collect the suite,
while the worktree's `.venv` runs it green at 208 passed. Non-blocking: resolved
locally by probing for a virtualenv directory and using `./.venv/bin/python`. Filed
as D3 so the packet line gets fixed rather than re-discovered each dispatch.

No other misses. In particular the packet's `build_index` documentation accurately
listed the index's five top-level keys, so establishing that the index exposes no
import tables was a confirmation of packet content, not a gap in it.

## Context-discipline notes

- Repository files read: **only** `analyzer/affected.py` (my write scope).
- Everything I know about `indexer` / `refs` / `gitio` came from the packet, or from
  *calling* those interfaces and printing results — never from reading their source.
- I checked for the existence of a `.venv` directory (environment probe, not a
  repository read) to resolve the verify-command failure. Flagging it as the one
  judgement call at the edge of the discipline; the alternative was reporting a
  broken baseline that is not in fact broken.

## Files in scratch

- `probe_3b.py` — fixture builder + probes for all six bullets and the surface shape.
  `./.venv/bin/python .harness/scratch/probe_3b.py [all|surface|b1..b6]`
- `probe_extra.py` — adversarial B2x / B3x follow-ups. Needs
  `PYTHONPATH=.harness/scratch`.
- `probe_out.txt`, `probe_extra_out.txt` — full transcripts quoted in the attestation.
- `verify_ambient.txt`, `verify_venv.txt` — the two verify runs.
- `d2_check_demo.txt` — the proposed D2 presence check run over this packet.
- `fixtures/` — throwaway git repos, regenerated on every probe run.
