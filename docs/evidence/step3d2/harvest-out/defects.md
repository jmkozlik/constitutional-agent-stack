# Defects — node `affected_symbols`, dispatch 3d-2

## D-1 (blocking the packet's verify line) — `test_f20_locked_demonstration_on_real_spec` locks a state this dispatch was sent to end

**Filed against:** `tests/test_join.py:947` (and the seeded surface line at
`harness/specs/analyzer.yaml:161`). Both are outside my write scope, so
this is filed, not fixed.

**What it is.** The F20 demonstration test asserts, against the *live*
repository rather than a fixture, that `analyzer.affected.Row.callers_
unknowable` is **absent** from the delta. Landing the attribute — the sole
outstanding line in my packet's delta, and the whole point of this
dispatch — makes it present. The test names its own expiry in its comment:

    tests/test_join.py:932-935
    # The 3b-packet demonstration, locked as ratified: nine authored lines
    # on affected_symbols; the structural ones presence-check; exactly one
    # is absent (callers_unknowable, unbuilt until 3d); behavioral lines
    # stay exempt. F20 closes on this being true.

I am 3d. "Unbuilt until 3d" is now false.

**Evidence.** The test passed at HEAD and fails only because of this
change — confirmed by stashing the edit and re-running:

    $ git stash push -- analyzer/affected.py
    $ python -m pytest tests/test_join.py::test_f20_locked_demonstration_on_real_spec -q
    .                                                                [100%]
    1 passed in 0.21s
    $ git stash pop

With the change in place:

    $ python -m pytest -q
    >       assert stat("analyzer.affected.Row.callers_unknowable") == "absent"
    E       AssertionError: assert 'present' == 'absent'
    E         - absent
    E         + present
    tests/test_join.py:947: AssertionError
    1 failed, 342 passed in 22.64s

**What a fix would require.** Two changes, neither in my scope, and they
must land together — the second is what keeps the test's *other*
assertions meaningful.

1. **`harness/specs/analyzer.yaml:161` — reseed the `[seeded]` Row line.**
   This is the mechanical reseed the ratified seeded-vs-authored rule
   already anticipates ("the `[seeded]` line reseeds byte-for-byte after
   the work lands"). It is currently stale, and the delta says so — the
   outstanding line has *moved* rather than disappeared:

       $ python -c "...compute_delta(..., 'affected_symbols', ...)"
       kind        = partial
       outstanding = ['analyzer.affected.Row(path: str, category: str,
                       detail: str, callers: list = field(default_factory=list),
                       error: bool = False)  [seeded]']
       status(callers_unknowable) = present

   The reseed text, taken from the index's own extraction of the landed
   class rather than written by hand:

       analyzer.affected.Row(path: str, category: str, detail: str, callers: list = field(default_factory=list), error: bool = False, callers_unknowable: bool = False)

   Until this lands, `delta["kind"]` stays `"partial"` — but for the
   *seeded* line, not for `callers_unknowable`. A reader who fixes only
   the test would see `partial` and wrongly conclude the node is unbuilt.

2. **`tests/test_join.py:947` and `:953-954` — re-lock the demonstration.**
   Line 947 must become `== "present"`. Lines 953-954 also expire:

       assert delta["kind"] == "partial"
       assert delta["outstanding"] and any("callers_unknowable" in o for o in delta["outstanding"])

   Once the seeded line is reseeded there is nothing outstanding, so the
   node's delta becomes `empty` and both lines must change with it.

**Interpretive note, not a claim of fact.** The deeper issue is that this
test pins a *transient* property of the live repository — "exactly one
line is outstanding" — as though it were a property of the delta engine.
The engine behaviour F20 closes on (structural authored lines
presence-check, behavioural lines stay exempt) is real and still
demonstrated; the absent/present verdict is a snapshot that any executor
completing any node will break. `test_structural_authored_present_and_
behavioral_exempt` at line 913 makes the same engine claim against a
`tmp_path` fixture and is unaffected by this landing. Whether the F20
demonstration should be re-locked against a fixture instead of the live
spec is a question for the loop, not a call I can make from inside my
scope. I flag it because re-locking it as-is guarantees the next
node-completing dispatch files this defect again.

---

## D-2 (non-blocking, observation — no verdict attached)

**Filed against:** nothing; this is a signal-quality observation about the
contract's own definition, raised because the loop may want it.

The importer-set definition includes "the symbol's own file". Implemented
faithfully, that clause dominates on a real codebase. Across
`HEAD~1..HEAD` of this repository:

    rows=53  flagged=51
    flagged by OWN file        : 51
    flagged only via importers : 0
    flagged by category        : {'moved': 51}
    files with unresolved sites: 3 of 42

The flag is not indiscriminate — only 3 of 42 files carry unresolved sites
— but this commit touched one of them (`analyzer/refs.py`, whose records
the packet already shows at `confidence low`, which the indexer sets iff
the file has an unresolved record). Every symbol in it shifted, so 51
`moved` rows all inherit the flag from their own file.

Two things follow, both offered as judgement rather than defect:

- On `moved` and `body` rows the flag is true per the iff but carries
  nothing actionable, since those categories have already established
  that callers are unaffected. This is why I kept the note out of their
  `detail` strings; the alternative reading is that the iff should be
  scoped to caller-bearing categories, which would be a spec change and
  is not mine to make.
- The own-file clause substantially overlaps the existing `confidence`
  field, which already means "this file has an unresolved record".

I did **not** narrow the iff to make the numbers look better. The contract
states it without category qualification, the tester's boundary tests
confirm both directions, and implementing it as written is what lets this
observation be made at all.

---

## Disagreements between the importer-set definition and the tester's fixtures

None. The packet instructed me to say so if the definition and the
fixtures disagreed about what should fire. They agree: every 3t fixture's
expected verdict is reproduced by the definition applied literally, in
both the positive and boundary directions, and the mechanism probe in the
attestation shows the computed importer set matching the definition
clause by clause. Nothing was quietly satisfied to make a test pass.

## REQUEST_MEM

None blocking. The two the tester raised (the caller record's access shape
and which of its fields are conditional; the surface form of `file` and
`in_symbol`) did not obstruct this work — I read caller records only to
count them and never constructed one.
