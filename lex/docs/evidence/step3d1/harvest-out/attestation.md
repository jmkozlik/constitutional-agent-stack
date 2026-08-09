# Attestation — 3d-1 · node symbol_table · role executor

packet: node=symbol_table role=executor commit=c7c6f7e0535cdc5de579cfadbd436af5860bc924
plan=c98fb664a54f packet_hash=6624a3b2aef7 dispatch_id=3d-1

**Verdict summary: 4 ATTEST · 1 FILE (blocking).**

No file in the write scope was modified. The one outstanding delta item
(`analyzer.indexer.import_origins` + the top-level `imports` table) is FILED,
not built — the two spec lines that govern it disagree about what an origin
is, and the disagreement is demonstrated below through the surface alone.
Blocking REQUEST_MEM lines are at the end of this file and in defects.md.

Every command below was run from the worktree root
`/private/tmp/claude-501/-Users-rokko-experiments-lex/e080b300-5c0a-4fee-83a9-01d14d44cd6f/scratchpad/dispatches/3d-1`
with the interpreter named by the packet's verify line,
`/Users/rokko/experiments/lex/.venv/bin/python`.

Fixtures: `.harness/scratch/mkfixture.py` builds a three-commit git repo —
c1 baseline (package facade `pkg/__init__.py` re-exporting `pkg/impl.py`, a
class with a property/setter pair, a decorated method, a nested def, an async
def, a subclass with bases+metaclass, an importer under `app/`), c2 a
**whitespace/comment/blank-line-only** reformat of `pkg/impl.py` plus an
import added at the top of `app/main.py`, c3 a **one-token real body edit**
as the discriminating control.

Probe: `.harness/scratch/probe_3d1.py`. Full output: `.harness/scratch/probe_out.txt`.

```
$ PYTHONPATH=.harness/scratch /Users/rokko/experiments/lex/.venv/bin/python .harness/scratch/probe_3d1.py
...
RESULT: ALL CHECKS HELD
$ echo $?
0
```

---

## 1. ATTEST — "Indexing the same commit twice produces byte identical output."

Observed through `serialize(build_index(repo, commit))`. Attested twice over:
two builds in one process, and three fresh processes under different
`PYTHONHASHSEED` values (the index is assembled through `defaultdict` and set
iteration, so seed-independence is the property that actually matters).

```
=== BULLET 1: same commit twice -> byte identical ===
  in-process build #1 sha256=7be05041b68e108a36af10c50dd69ed510e075b873b6a4954b5523d032f2cbd5 bytes=6187
  in-process build #2 sha256=7be05041b68e108a36af10c50dd69ed510e075b873b6a4954b5523d032f2cbd5 bytes=6187
  [OK] two in-process builds of c1 are byte identical
  fresh process PYTHONHASHSEED=0      sha256=7be05041b68e108a36af10c50dd69ed510e075b873b6a4954b5523d032f2cbd5
  fresh process PYTHONHASHSEED=1      sha256=7be05041b68e108a36af10c50dd69ed510e075b873b6a4954b5523d032f2cbd5
  fresh process PYTHONHASHSEED=random sha256=7be05041b68e108a36af10c50dd69ed510e075b873b6a4954b5523d032f2cbd5
  [OK] three fresh processes agree with the in-process bytes
  [OK] a different commit produces different bytes (probe is discriminating)
```

The last line is the control: a probe that passed on a constant would prove
nothing, so a different commit is shown to produce different bytes.

**Scope note carried forward:** this bullet is attested against the index as
it exists at c7c6f7e. The FILED bullet 5 adds a new top-level key whose
per-file entry list and per-entry `origins` list are **lists, and
`serialize()` sorts dict keys only** — list order is therefore load-bearing
for this bullet, and no ordering rule is stated anywhere in the packet. That
is one of the blocking request_mem lines.

## 2. ATTEST — "The emitted index maps every symbol path to at least one record carrying its definition location and signature."

Observed through `build_index(...)["symbols"]`, cross-checked against
`extract_symbols(blob, rel)` run over every blob `gitio` lists at the same
commit — so "every symbol path" is measured against the extractor's own
output rather than against a hand-written list.

```
=== BULLET 2: every symbol path -> >=1 record with location + signature ===
  files indexed: ['app/__init__.py', 'app/main.py', 'pkg/__init__.py', 'pkg/impl.py']
  extract_symbols paths: 9   index symbol records: 10   distinct index paths: 9
  paths in extract_symbols but absent from the index: []
  [OK] no extracted symbol path is missing from the index
  [OK] every record carries a usable file + start_line/end_line
  [OK] every record carries a signature key
  records whose signature renders as the empty string: ['pkg.impl.Widget [class]']
  (observation, not a check: _signature_display returns '' for a class
   with no bases/keywords — see the FILE note in the attestation)
    app.main.run                 function  app/main.py:4-6  sig='()'
    pkg.impl.Gadget              class     pkg/impl.py:28-30  sig='(Widget, metaclass=type)'
    pkg.impl.Gadget.poke         function  pkg/impl.py:29-30  sig='(self)'
    pkg.impl.Widget              class     pkg/impl.py:6-25  sig=''
    pkg.impl.Widget.compute      function  pkg/impl.py:20-25  sig='(self, a, b=2, *rest, key=None, **kw) -> int'
    pkg.impl.Widget.compute.inner function  pkg/impl.py:23-24  sig='(x)'
```

10 records over 9 distinct paths is the property/setter pair — the "at least
one record" wording is exercised, not assumed.

**Reported, not hidden:** a class with no bases and no keywords renders
`signature: ""`. Under the strictest reading of "carrying ... its signature"
an empty string could be read as carrying nothing. I attest the bullet
because the empty string is the *correct rendering* of that class's empty
base list (`pkg.impl.Gadget` shows the non-empty case,
`'(Widget, metaclass=type)'`), the `signature` key is always present, and the
identity that distinguishes such classes lives in `sig_hash`, which is
non-empty for both. Flagged for the verifier rather than judged by me.

## 3. ATTEST — "Reformatting whitespace does not change the body hash."

c1 → c2 changes `pkg/impl.py` by 12 pure insertions (blank lines and one
comment); no statement's token sequence differs. Every symbol in the file is
checked, not a sample.

```
=== BULLET 3: whitespace reformat -> body_hash unchanged ===
  git diff --stat c1..c2 -- pkg/impl.py: pkg/impl.py | 12 ++++++++++++
 1 file changed, 12 insertions(+)
    pkg.impl.Gadget              c1  28-30  body=5db56db1  ->  c2  36-40  body=5db56db1
    pkg.impl.Gadget.poke         c1  29-30  body=486d9aff  ->  c2  38-40  body=486d9aff
    pkg.impl.Widget              c1   6-25  body=efe220b7  ->  c2   8-33  body=efe220b7
    pkg.impl.Widget.compute      c1  20-25  body=aa6b398a  ->  c2  25-33  body=aa6b398a
    pkg.impl.Widget.compute.inner c1  23-24  body=60fcefe1  ->  c2  29-31  body=60fcefe1
    pkg.impl.Widget.value        c1  12-14  body=b3742c15  ->  c2  15-18  body=b3742c15
    pkg.impl.Widget.value        c1  16-18  body=e63f054c  ->  c2  20-23  body=e63f054c
    pkg.impl.fetch               c1  37-38  body=4e2be2b9  ->  c2  48-50  body=4e2be2b9
    pkg.impl.helper              c1  33-34  body=2f8cf442  ->  c2  43-45  body=2f8cf442
  [OK] no body_hash changed across the whitespace-only reformat
  [OK] the reformat did move line ranges (probe is discriminating)
  control, one real token edited at c3: pkg.impl.helper body 2f8cf442 -> 8d7fbbd0
  [OK] a real body edit does change body_hash (hash is not a constant)
```

Both controls are present: the ranges demonstrably moved (so the reformat was
real), and a single real token flips `body_hash` (so the hash is not inert).
Note the property/setter pair `pkg.impl.Widget.value` keeps two distinct
`body_hash` values across the move — the duplicate-path records are matched
pairwise, not collapsed.

## 4. ATTEST — "Ranges are recomputed per commit, never stored as identity."

This is a negative architectural claim, so it is attested through three
positive, surface-observable consequences rather than one. Evidence-form
question logged as a NON-BLOCKING request_mem below.

```
=== BULLET 4: ranges recomputed per commit, not identity ===
  app.main.run  c1 lines 4-6  c2 lines 6-8  (import added at top)
  identity triple c1: path=app.main.run sig=9bc8d3d3 body=c51ad774 decor=e3b0c442
  identity triple c2: path=app.main.run sig=9bc8d3d3 body=c51ad774 decor=e3b0c442
  [OK] the range moved while path and all three hashes held
  c2 records whose range disagrees with the c2 blob's own AST: []
  [OK] every c2 range is the c2 source's own range (recomputed, not carried)
  same def at line 1 vs line 6: sig d5542cc0==d5542cc0, body 6e55e32b==6e55e32b
  [OK] line position contributes nothing to sig_hash or body_hash
```

1. *Not identity:* the range moved while `path`, `sig_hash`, `body_hash` and
   `decor_hash` all held — the symbol is the same symbol at a new position.
2. *Recomputed, not carried:* every range in the c2 index was re-derived
   independently from the c2 blob's own AST (including the decorator-start
   rule) and compared; zero disagreements. Nothing is inherited from the c1
   index.
3. *No hash consumes a position:* the same `def` at line 1 and at line 6
   yields identical `sig_hash` and `body_hash`.

**Reported, not hidden:** `start_line` *does* appear in the record **sort
key** `(path, file, start_line, sig_hash, body_hash)` in `build_index`. I read
that as ordering — it is what keeps two same-path records in source order —
not as identity, since nothing consumes it as a key and no hash ingests it.
Flagged so the verifier can rule rather than take my reading.

## 5. FILE — "build_index exposes each file's import bindings with resolved origins, re-export chains included, and import_origins answers from them."

**Not attested. Not built. Filed, with a blocking request_mem.** This is the
sole outstanding delta item
(`analyzer.indexer.import_origins(index: dict, module: str) -> list[str]
[authored]`), and it is filed rather than guessed for a reason stronger than
terseness: **the two spec lines that govern it contradict each other**, and
the contradiction is observable through the surface without reading any
implementation.

`symbol_table` says origins are *"dotted origins as resolved by the reference
layer ... taken from the Resolver's output"*. The reference layer resolves to
**indexed symbol paths**. The only declared consumer,
`affected_symbols.Row.callers_unknowable`, requires *"every file whose import
table contains any binding whose resolved origin is the symbol's defining
**module** (module imports, from-imports of any name in it, and re-export
chains)"*. A module is not a symbol, and the index contains no module records:

```
$ /Users/rokko/experiments/lex/.venv/bin/python .harness/scratch/probe_origin_contradiction.py
files indexed: ['app/lazy.py', 'app/via_facade.py', 'pkg/__init__.py', 'pkg/impl.py']
top-level index keys: ['commit', 'files', 'symbols', 'unresolved', 'version']
every symbol path in the index: ['app.via_facade.go', 'pkg.impl.helper']
module paths present as symbol records: []

(a) app/lazy.py contains exactly `import pkg.impl` and uses nothing.
    reference records naming app/lazy.py : []
    unresolved sites naming app/lazy.py  : []
    => nothing in the returned index ties app/lazy.py to pkg.impl.
       A symbol-path origin for the binding `pkg` does not exist,
       because `pkg.impl` is a module and modules get no records.

(b) app/via_facade.py reaches pkg.impl.helper only through the facade.
    call edge resolved to pkg.impl.helper <- app/via_facade.py:1 in app.via_facade
    call edge resolved to pkg.impl.helper <- app/via_facade.py:5 in app.via_facade.go
    => the re-export chase works for a CALLED name. The consumer's
       line needs the same edge for an IMPORTED-but-uncalled name,
       which no current index field carries.
```

Under the literal `symbol_table` reading, a bare `import pkg.impl` — named
explicitly by the consumer's line as a case that must count — produces an
entry with **empty** origins, and `callers_unknowable` silently never fires
for it. Picking either reading unilaterally decides `affected_symbols`'
behaviour from inside `symbol_table`'s write scope, which is exactly the
guess the identity block forbids. Filed as **D-3d1-1** in defects.md.

**What is NOT blocking, because I measured it:** the scope question of
whether a new top-level `imports` key is tolerated by the consumers outside my
write scope (`harness/join.py`, `harness/fence.py`, `analyzer/cli.py`,
`analyzer/affected.py`, the whole `tests/` tree). It is.

```
$ /Users/rokko/experiments/lex/.venv/bin/python -m pytest -q          # baseline
234 passed in 18.43s
$ PYTHONPATH=.harness/scratch /Users/rokko/experiments/lex/.venv/bin/python -m pytest -q -p inject_imports_key
234 passed in 18.63s
```

`.harness/scratch/inject_imports_key.py` is a measurement plugin, not an
implementation: it wraps `build_index` so every index grown during the suite
carries an extra top-level `imports` key. Its effectiveness is itself
controlled, so the green run cannot be a no-op:

```
$ PYTHONPATH=.harness/scratch /Users/rokko/experiments/lex/.venv/bin/python -m pytest -q -p inject_imports_key .harness/scratch/test_patch_effective.py
1 passed in 0.15s
$ PYTHONPATH=.harness/scratch /Users/rokko/experiments/lex/.venv/bin/python -m pytest -q .harness/scratch/test_patch_effective.py
.harness/scratch/test_patch_effective.py:12: AssertionError
FAILED .harness/scratch/test_patch_effective.py::test_injected_key_is_visible_to_a_test_module
1 failed in 0.16s
```

No consumer enforces an exact top-level key set or a golden index fixture, so
this bullet **is** completable inside the exhaustive write scope once the
origin question is answered. That removes one of the two candidate halt
reasons; the semantic contradiction remains.

---

## Write scope, unchanged

```
$ git status --porcelain
?? .harness/
$ git diff --stat
(no output)
```

No tracked file was modified. `analyzer/modpath.py`, `analyzer/symbols.py`
and `analyzer/indexer.py` stand byte-for-byte as delivered at c7c6f7e —
`exists@f585b83b`, `exists@b3689cbc`, `exists@8a42ca02`. The delta's one
outstanding item is still outstanding, by design, and the suite is where the
dispatch found it (234 passed).

## REQUEST_MEM

**BLOCKING** — I stop here and return the report carrying these lines. They
are ordered; (1) is the one that actually decides the design.

REQUEST_MEM: [BLOCKING] Origin semantics — are `origins` entries indexed SYMBOL paths (the reference layer's own resolution output, per the symbol_table line) or dotted MODULE paths (what affected_symbols' callers_unknowable line tests against), or both in one list? Demonstrated contradiction and evidence in .harness/scratch/probe_origins_out.txt: a bare `import pkg.impl` resolves to no symbol, and the index has no module records, so under the symbol reading the "module imports" case the consumer names explicitly can never fire.

REQUEST_MEM: [BLOCKING] Semantics of `module` in `import_origins(index, module)` — the dotted module path of an indexed file (i.e. `module_path(rel)`, so the function maps module -> file -> that file's bindings), or the name of a module being imported (so it answers "who imports this")? The parameter is named `module` while the table is keyed by `file`, and report 005's "importer-set consumption via import_origins" reads like the second. The return `list[str]` cannot distinguish them.

REQUEST_MEM: [BLOCKING] Return contract for `import_origins` — ordering (sorted? source order?), de-duplication, behaviour for a module that is not in the index, and behaviour for an index built before this key existed (empty list vs IndexLoadError vs KeyError). `load_index` today validates only `symbols` and `unresolved`, so legacy indexes will reach this function.

REQUEST_MEM: [BLOCKING] Deterministic ordering rule for the imports table itself — sort order of each file's entry list (by local binding name? by source line?) and of each `origins` list. `serialize()` sorts dict keys only, so list order is load-bearing for done_when bullet 1, which I have just attested and must not regress.

REQUEST_MEM: [BLOCKING] Key-presence contract — does every path in `files` get an entry (including files with no imports at all, and files that failed to parse and produced no tree), or only files with at least one binding?

REQUEST_MEM: [BLOCKING] Representation of imports the reference layer cannot resolve (the existing `star_import` and `unresolved_import_target` reasons): an entry with empty `origins`, no entry at all, or a sentinel — and whether emitting one should also push the file to confidence "low" or add an unresolved site. Under the current rules an entry with empty origins is indistinguishable from "resolved to nothing", which is precisely the case in the contradiction above.

**NON-BLOCKING** — logged, work continued.

REQUEST_MEM: Evidence bar for done_when bullet 4, a negative architectural claim ("never stored as identity"). I attested it through three positive consequences (range moves while hashes hold; every range re-derived from the commit's own AST; identical text at different positions hashes identically) and disclosed that `start_line` participates in the record sort key. If the intended bar is different, say so and I will re-attest.

REQUEST_MEM: Whether `signature: ""` for a base-less class satisfies bullet 2's "carrying ... its signature", or whether the intended rendering is `"()"`. I attested as-is and flagged it; changing it would be a one-line edit in `analyzer/symbols.py`, inside my write scope.

REQUEST_MEM: The read-fence, disclosed rather than assumed — see D-3d1-3 in defects.md. Early in this dispatch, before writing anything, I read `analyzer/refs.py` lines 1-270 to learn the Resolver's resolution API. The packet defines a WRITE fence exactly (fence.json, hook-enforced) but never defines a read fence; its only read-related words are "never read around it" under request_mem. I did not implement from that read, and the filed contradiction above rests only on surface-observable evidence. Rule on whether that read was legal, and make the answer explicit in the Protocol section either way.
