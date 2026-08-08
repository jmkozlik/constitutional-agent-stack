# Handoff — 3d-1 · node symbol_table · role executor

packet: node=symbol_table role=executor commit=c7c6f7e0535cdc5de579cfadbd436af5860bc924
plan=c98fb664a54f packet_hash=6624a3b2aef7 dispatch_id=3d-1

For whoever resumes this node — most likely me after the blocking
request_mem is answered, otherwise a replacement. State is separated into
**verified** (a command produced it, and the command is named) and
**interpretive** (my reading, which may be wrong and was not acted on).

---

## Where the dispatch stopped

Done_when bullets 1-4 are ATTESTED with evidence. Bullet 5 is FILED, not
built: the outstanding delta item `analyzer.indexer.import_origins` plus the
top-level `imports` table. No tracked file was modified; the three write-scope
files stand byte-for-byte as delivered. Resuming means starting bullet 5 from
zero, with the request_mem answers in hand — nothing half-built to clean up.

## Verified — commands were run, output is on disk

- **Suite is green at the dispatch commit: 234 passed.**
  `/Users/rokko/experiments/lex/.venv/bin/python -m pytest -q`
  → `.harness/scratch/suite_baseline.txt`
- **Bullets 1-4 all hold.**
  `PYTHONPATH=.harness/scratch … python .harness/scratch/probe_3d1.py`, exit 0
  → `.harness/scratch/probe_out.txt`. Fixture builder:
  `.harness/scratch/mkfixture.py` (three commits: baseline / whitespace-only
  reformat + import-at-top / one-token body edit as control).
- **A new top-level `imports` key breaks nothing outside the write scope.**
  234 passed with every index carrying an injected key
  (`-p inject_imports_key`) → `.harness/scratch/suite_with_imports_key.txt`.
  The injection is itself controlled: `.harness/scratch/test_patch_effective.py`
  passes with the plugin and fails without it. **So the scope worry the
  pre-dispatch probe raised is dead — this task is completable inside the
  fence.** Delete that line from the request_mem list; do not re-measure.
- **The index contains no module records, and a bare `import pkg.impl` leaves
  no trace in the returned index at all** — no reference record, no unresolved
  site. `.harness/scratch/probe_origin_contradiction.py` →
  `.harness/scratch/probe_origins_out.txt`. This is the whole basis of
  D-3d1-1 and it is surface-only evidence.
- **The re-export chase already works for a called name**: a call reaching
  `pkg.impl.helper` only through `pkg/__init__.py` resolves to the real
  defining path. Same probe, part (b). Whatever the imports table ends up
  emitting, the chasing machinery underneath it is not the problem.
- **`start_line` participates in the record sort key** `(path, file,
  start_line, sig_hash, body_hash)` and in **no** hash input. Verified by
  reading `analyzer/indexer.py:178-186` (my own write scope) and by the
  identical-text-different-position check in bullet 4.
- **A base-less class renders `signature: ""`**; a class with bases renders
  `'(Widget, metaclass=type)'`. Attested and flagged, not changed.
- **Duplicate dotted paths survive as separate records with distinct
  body hashes** across a whitespace move (the property/setter pair
  `pkg.impl.Widget.value`, 10 records over 9 paths). Anything the imports work
  does must not collapse them.

## Interpretive — my reading, NOT acted on, may be wrong

- **The `origins` contradiction is real, not a wording nit.** My claim: the
  `symbol_table` line describes the Resolver's output (symbol paths) while
  `affected_symbols.Row.callers_unknowable` tests against a defining module,
  and those cannot both be satisfied by one flat `list[str]` of symbol paths.
  The *facts* underneath it are verified above; the *judgement* that this
  blocks rather than admits an obvious reading is mine.
- **My guess at the intended shape, offered only so a ruling has something to
  reject:** origins carry module-level information (either module paths, or
  both namespaces), because the only declared consumer needs modules and
  because bare `import pkg.mod` — named explicitly in that consumer's own
  line — has no symbol to resolve to. I did **not** implement this.
- **`import_origins(index, module)` most likely maps a dotted module to its
  own file's bindings** (parameter named `module`, table keyed by `file`, so
  the function is where `module_path(rel)` gets inverted). But report 005's
  phrase *"importer-set consumption via import_origins"* reads the other way —
  "which files import this module" — and the `list[str]` return cannot
  distinguish the two. Genuinely 50/50; this is blocking request_mem line 2.
- **If origins end up as lists inside the index, sort them.** Bullet 1 is
  attested today and `serialize()` sorts dict keys only, so an unsorted list
  would silently regress a bullet I have already signed. Sorted-by-name for
  entries and sorted for origins is my expectation, not a rule I was given.

## Sequencing note for the resumer

`affected_symbols` (3d-2) is downstream of the ruling on D-3d1-1, not merely
downstream of this code. 3t's seven blind fixtures are already on disk as its
acceptance criteria; if the origin shape is decided in a way that makes
`callers_unknowable` unable to see module imports, those fixtures will fail
for a spec reason rather than an implementation one. Worth deciding D-3d1-1
with 3d-2's fixtures open.

## Read disclosure

Before writing anything I read `analyzer/refs.py` lines 1-270 (outside the
write scope; a module `analyzer/indexer.py` already imports from). No
implementation was derived from it and D-3d1-1's evidence deliberately does
not depend on it. Filed as D-3d1-3 because the packet defines no read fence
and the pre-dispatch probe for this same node read the same sentence the
opposite way. A resumer should not treat my read as precedent until it is
ruled on.
